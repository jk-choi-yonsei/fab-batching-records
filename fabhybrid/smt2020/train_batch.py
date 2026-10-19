"""The learned batch policy: the law's decision, learned.

Decision points are the batch tools' only (FabEnv batch_only): which candidate
group runs on a freed batch machine, or wait. Reward is the scrap game's own
objective (FabEnv reward='yield': +w per completion, -w per scrapped lot),
credited per lot to the decisions that arbitrated it -- the lot-scoped
estimator of the whole-fab trainer (archive/deadtime-final/legacy/fabhybrid-v1/smt2020/train_l1.py),
with point charges in place of tardiness intervals:

    A_t = sum over lots l in the candidate set C_t of
          [ gamma_day^((t_l - tau_t)/day) * v_l * 1(tau_t < t_l <= tau_t + H) - V_lot(l | s_t) ]

Theta_0 is the law. --bc fits the actor to the law's own decisions on the
training windows (the wait head sees the MIN over groups of the clock-margin
column, so the threshold is representable exactly), and --learn starts PPO
from those weights. Windows start from scrap_snap.py snapshots (a fab the law
has been running for 90 days) with the simulator reseeded per worker.

  python train_batch.py --calibrate --snap-glob "../../experiments/smt2020/scrap_snaps/snap_HVLM_*.pkl.gz"
  python train_batch.py --bc --law clock:2 --snap-glob ... --days 10 --episodes 8
  python train_batch.py --learn --init runs/batch/weights_bc.pt --snap-glob ... --days 15 --iters 20 --workers 6
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn

import batch_fire
from fab_env import FabEnv, N_EXTRA
from train_l1 import (EMB, N_G, Norm, global_vec, row_feats, ppo_epochs, NEG)

RUNS = os.environ.get("FAB_BATCH_RUNS", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     "..", "..", "experiments", "smt2020", "runs", "batch"))
N_LOTF = 12 + N_EXTRA            # per-group row: the head lot's 12 features + the extras
CLOCK_COL = 12 + 3               # extras[3]: the group's tightest live clock, hours (clamped +-48)


# ----------------------------------------------------------------- policy ---
class BatchPolicy(nn.Module):
    """Group logit from the group's own row; wait logit from the mean row, the
    MIN over groups of the extras (the law is a threshold on the minimum clock
    margin at the tool), and the globals; per-group value for the credit."""

    def __init__(self, n_tools, n_lotf=N_LOTF, n_g=N_G):
        super().__init__()
        self.n_lotf = n_lotf
        self.emb = nn.Embedding(n_tools, EMB)
        self.group = nn.Sequential(nn.Linear(n_lotf + EMB, 64), nn.Tanh(),
                                   nn.Linear(64, 64), nn.Tanh(), nn.Linear(64, 1))
        self.wait = nn.Sequential(nn.Linear(2 * (n_lotf + EMB) + n_g, 64), nn.Tanh(),
                                  nn.Linear(64, 64), nn.Tanh(), nn.Linear(64, 1))
        # the value head has its own embedding: the actor (emb, group, wait) must not
        # move when only the critic is trained, so theta_0 is the law exactly
        self.emb_v = nn.Embedding(n_tools, EMB)
        self.lotval = nn.Sequential(nn.Linear(n_lotf + EMB + n_g, 128), nn.Tanh(),
                                    nn.Linear(128, 64), nn.Tanh(), nn.Linear(64, 1))

    def load_compat(self, sd):
        """Load weights saved before the value head had its own embedding."""
        missing = self.load_state_dict(sd, strict=False)
        if "emb_v.weight" not in sd:
            self.emb_v.weight.data.copy_(self.emb.weight.data)
        return missing

    def heads(self, feats, tg, g):
        x = torch.cat([feats[:, :self.n_lotf], self.emb(tg)], dim=1)
        gl = self.group(x).squeeze(-1)
        pooled = torch.cat([x.mean(dim=0), x.min(dim=0).values, g])
        wl = self.wait(pooled).squeeze(-1)
        return torch.cat([gl, wl.view(1)]), torch.zeros(())

    def lot_values(self, feats, tg, g):
        xv = torch.cat([feats[:, :self.n_lotf], self.emb_v(tg)], dim=1)
        return self.lotval(torch.cat([xv, g.expand(xv.shape[0], -1)], 1)).squeeze(-1)

    def batch(self, feats, tg, seg, pos, counts, gm, wait_ok):
        seg, pos = seg.long(), pos.long()          # numpy's arange is int32 on Windows
        M = counts.shape[0]
        maxn = int(counts.max())
        x = torch.cat([feats[:, :self.n_lotf], self.emb(tg)], dim=1)
        gl = self.group(x).squeeze(-1)
        mean = torch.zeros(M, x.shape[1], dtype=x.dtype).index_add(0, seg, x) / counts.unsqueeze(1)
        mn = torch.full((M, x.shape[1]), float("inf"), dtype=x.dtype)
        mn = mn.scatter_reduce(0, seg.unsqueeze(1).expand_as(x), x, reduce="amin", include_self=True)
        wl = self.wait(torch.cat([mean, mn, gm], 1)).squeeze(-1)
        L = torch.full((M, maxn), NEG).index_put((seg, pos), gl)
        wcol = torch.where(wait_ok, wl, torch.full_like(wl, NEG))
        logits = torch.cat([L, wcol.unsqueeze(1)], dim=1)
        xv = torch.cat([feats[:, :self.n_lotf], self.emb_v(tg)], dim=1)
        vals = self.lotval(torch.cat([xv, gm[seg]], 1)).squeeze(-1)
        return logits, vals


def n_tools_of(dataset):
    env = FabEnv(dataset=dataset, episode_days=1, horizon_days=2, batch_only=True, scrap=True, reward="yield")
    return len(env.tools_type)


# ---------------------------------------------------------------- rollout ---
def law_fn(arm):
    kind, coef = batch_fire.parse_arm(arm)
    return lambda env: batch_fire.choose(env, kind, coef)


def run_window(policy, norm, env, snapshot, seed, collect=None, keep_prob=1.0,
               greedy=False, law=None, rng=None):
    """One training window from a snapshot. `law` (an env -> action function)
    overrides the policy's choice and is what --bc records."""
    obs = env.reset(seed=seed, snapshot=snapshot)
    from simulation.randomizer import Randomizer
    Randomizer().random.seed(seed * 7919 + 13)          # diversity across workers
    rng = rng or np.random.default_rng(seed)
    R, steps, agree = 0.0, 0, 0
    with torch.no_grad():
        while obs is not None:
            f, tg = row_feats(obs)
            nf = torch.from_numpy(norm.lots(f))
            gnp = norm.glob(global_vec(env, norm.time_inputs)).astype(np.float32)
            g = torch.from_numpy(gnp)
            logits, _ = policy.heads(nf, tg, g)
            if greedy:
                a_pol, logp = int(torch.argmax(logits)), 0.0
            else:
                dist = torch.distributions.Categorical(logits=logits)
                a_pol = int(dist.sample())
                logp = float(dist.log_prob(torch.tensor(a_pol)))
            a = law(env) if law is not None else a_pol
            if law is not None and int(torch.argmax(logits)) == a:
                agree += 1
            if collect is not None:
                collect["rew"].append(0.0)
                collect["logp"].append(logp)
                collect["act"].append(a)
                collect["n"].append(f.shape[0])
                collect["wait_ok"].append(True)
                collect["tstep"].append(env.instance.current_time)
                collect["g"].append(gnp)
                if rng.random() < keep_prob:
                    ids, sizes = env.cand_ids()
                    collect["kidx"].append(steps)
                    collect["feats"].append(nf.numpy().astype(np.float16))
                    collect["tg"].append(tg.numpy().astype(np.int16))
                    collect["cand"].append(ids)
                    collect["gsz"].append(sizes)
            obs, r, done, _ = env.step(a)
            if collect is not None:
                collect["rew"][-1] = r
            R += r
            steps += 1
            if done:
                break
    return R, steps, agree


def make_env(cfg, days=None):
    # cqt_rule: the queue-time critical ratio of the evaluation runs (eval_batch --cqt-rule). The
    # 2026-09-07 weights were trained with the default "none" and evaluated with "qtcr"; the
    # 2026-10 retraining passes qtcr here so that the windows sequence lots as the block does.
    return FabEnv(dataset=cfg.dataset, seed=cfg.seed, episode_days=days or cfg.days,
                  horizon_days=int((days or cfg.days) + 2), rule="cr", scrap=True,
                  reward="yield", batch_only=True, cqt_rule=getattr(cfg, "cqt_rule", "none"))


def snapshots(cfg):
    paths = sorted(glob.glob(cfg.snap_glob))
    if not paths:
        raise SystemExit(f"no snapshots match {cfg.snap_glob}")
    return paths


# ------------------------------------------------------------- calibrate ---
def calibrate(cfg):
    """Feature normalisation from a random-policy window on the first snapshot."""
    env = make_env(cfg, days=min(cfg.days, 5))
    obs = env.reset(seed=cfg.seed, snapshot=snapshots(cfg)[0])
    rng = np.random.default_rng(cfg.seed)
    L, G = [], []
    while obs is not None:
        f, tg = row_feats(obs)
        L.append(f); G.append(global_vec(env))
        n = f.shape[0]
        a = n if rng.random() < 0.3 else int(rng.integers(n))
        obs, r, done, _ = env.step(a)
        if done:
            break
    L, G = np.vstack(L), np.vstack(G)
    out = {"lot_mu": L.mean(0).tolist(),
           "lot_sd": np.maximum(L.std(0), 1e-3 + 1e-3 * np.abs(L.mean(0))).tolist(),
           "g_mu": G.mean(0).tolist(),
           "g_sd": np.maximum(G.std(0), 1e-3 + 1e-3 * np.abs(G.mean(0))).tolist()}
    os.makedirs(RUNS, exist_ok=True)
    json.dump(out, open(os.path.join(RUNS, "norm.json"), "w"))
    print(f"[calibrate] {len(G)} batch decisions ({len(L)} rows) -> norm.json")


# ---------------------------------------------------------------------- BC ---
def behaviour_clone(cfg):
    """Fit the actor to the law's decisions on the training windows; report
    agreement on a held-out window and the greedy policy's window yield
    against the law's on that window (the theta_0 check)."""
    torch.manual_seed(cfg.seed)
    norm = Norm(os.path.join(RUNS, "norm.json"))
    snaps = snapshots(cfg)
    law = law_fn(cfg.law)
    policy = BatchPolicy(n_tools_of(cfg.dataset), n_g=len(norm.gmu))
    X, TG, GG, SEG, ACT = [], [], [], [], []
    n_dec = 0
    for ep in range(cfg.episodes):
        env = make_env(cfg)
        col = defaultdict(list)
        run_window(policy, norm, env, snaps[ep % len(snaps)], cfg.seed0 + ep, collect=col, law=law,
                   keep_prob=1.0)
        for k, i in enumerate(col["kidx"]):
            f = col["feats"][k].astype(np.float32); n = f.shape[0]
            X.append(f); TG.append(col["tg"][k].astype(np.int64))
            GG.append(col["g"][i]); SEG.append(np.full(n, n_dec)); ACT.append(col["act"][i])
            n_dec += 1
        print(f"[bc] episode {ep}: {len(col['kidx'])} decisions", flush=True)
    feats = torch.from_numpy(np.concatenate(X)); tg = torch.from_numpy(np.concatenate(TG))
    seg = torch.from_numpy(np.concatenate(SEG)); gm = torch.from_numpy(np.stack(GG).astype(np.float32))
    counts = torch.bincount(seg, minlength=n_dec)
    pos = torch.from_numpy(np.concatenate([np.arange(int(c)) for c in counts]))
    act = torch.tensor(ACT, dtype=torch.long)
    acol = torch.where(act == counts, torch.full_like(act, -1), act)      # -1 -> last column
    hold = int(0.9 * n_dec)
    tr = torch.arange(n_dec) < hold
    opt = torch.optim.Adam(policy.parameters(), lr=1e-3)
    wait_ok = torch.ones(n_dec, dtype=torch.bool)

    def logits_of(sel):
        rows = torch.isin(seg, sel)
        s = seg[rows]
        remap = torch.full((n_dec,), -1, dtype=torch.long); remap[sel] = torch.arange(len(sel))
        return policy.batch(feats[rows], tg[rows], remap[s], pos[rows], counts[sel], gm[sel], wait_ok[sel])[0]

    tr_idx = torch.nonzero(tr).squeeze(1); ho_idx = torch.nonzero(~tr).squeeze(1)
    for epoch in range(cfg.bc_epochs):
        perm = tr_idx[torch.randperm(len(tr_idx))]
        tot = 0.0
        for s in range(0, len(perm), 512):
            sel = perm[s:s + 512]
            lg = logits_of(sel)
            tgt = torch.where(acol[sel] < 0, torch.full_like(acol[sel], lg.shape[1] - 1), acol[sel])
            loss = nn.functional.cross_entropy(lg, tgt)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += float(loss) * len(sel)
        with torch.no_grad():
            lg = logits_of(ho_idx)
            tgt = torch.where(acol[ho_idx] < 0, torch.full_like(acol[ho_idx], lg.shape[1] - 1), acol[ho_idx])
            acc = float((lg.argmax(1) == tgt).float().mean())
        print(f"[bc] epoch {epoch}: loss {tot / len(perm):.4f}  held-out agreement {100 * acc:.2f}%", flush=True)
    os.makedirs(RUNS, exist_ok=True)
    torch.save(policy.state_dict(), os.path.join(RUNS, "weights_bc.pt"))
    # theta_0 check: greedy policy vs the law on a fresh window
    env = make_env(cfg)
    Rl, _, _ = run_window(policy, norm, env, snaps[0], cfg.seed0 + 999, law=law)
    env = make_env(cfg)
    Rp, _, _ = run_window(policy, norm, env, snaps[0], cfg.seed0 + 999, greedy=True)
    print(json.dumps({"bc_heldout_agreement": acc, "window_yield_law": Rl, "window_yield_greedy_bc": Rp,
                      "decisions": n_dec}), flush=True)
    json.dump({"agreement": acc, "yield_law": Rl, "yield_bc": Rp, "decisions": n_dec},
              open(os.path.join(RUNS, "bc.json"), "w"))


# ----------------------------------------------------------------- worker ---
def phase_worker(cfg):
    torch.set_num_threads(1)
    norm = Norm(os.path.join(RUNS, "norm.json"))
    policy = BatchPolicy(n_tools_of(cfg.dataset), n_g=len(norm.gmu))
    policy.load_compat(torch.load(cfg.weights, map_location="cpu", weights_only=True))
    policy.eval()
    env = make_env(cfg)
    col = defaultdict(list)
    R, steps, _ = run_window(policy, norm, env, cfg.snapshot, cfg.seed, collect=col,
                             keep_prob=cfg.subsample, greedy=cfg.greedy)
    ids, t, v = env.yield_events()
    if not col["feats"]:
        col["feats"] = [np.zeros((0, N_LOTF), np.float16)]; col["tg"] = [np.zeros(0, np.int16)]
        col["cand"] = [np.zeros(0, np.int32)]; col["gsz"] = [np.zeros(0, np.int32)]
    inst = env.instance
    np.savez_compressed(
        cfg.out,
        rew=np.array(col["rew"], np.float32), logp=np.array(col["logp"], np.float32),
        act=np.array(col["act"], np.int32), n=np.array(col["n"], np.int32),
        wait_ok=np.array(col["wait_ok"], bool), tstep=np.array(col["tstep"], np.float64),
        g=np.stack(col["g"]).astype(np.float16) if col["g"] else np.zeros((0, len(norm.gmu)), np.float16),
        kidx=np.array(col["kidx"], np.int64), feats=np.concatenate(col["feats"], axis=0),
        tg=np.concatenate(col["tg"], axis=0), cand=np.concatenate(col["cand"], axis=0),
        gsz=np.concatenate(col["gsz"], axis=0), ev_ids=ids, ev_t=t, ev_v=v)
    print(json.dumps({"R": R, "steps": steps, "kept": len(col["kidx"]),
                      "done": len(inst.done_lots), "scrapped": len(env.cqt.scrapped),
                      "stats": dict(env.stats)}, default=float))


# ----------------------------------------------------------------- credit ---
class YChunk:
    """One worker window unpacked for the update (the archived whole-fab trainer's Chunk with point
    charges instead of tardy intervals)."""

    def __init__(self, path):
        z = np.load(path)
        self.rew = z["rew"]; self.n = z["n"]; self.act = z["act"]; self.tstep = z["tstep"]
        self.g_all = z["g"]; self.logp = z["logp"]; self.wait_ok = z["wait_ok"]
        self.kidx = z["kidx"]; self.feats = z["feats"]; self.tg = z["tg"]
        self.cand = z["cand"]; self.gsz = z["gsz"]
        self.goff = np.zeros(len(self.gsz) + 1, np.int64); np.cumsum(self.gsz, out=self.goff[1:])
        self.counts = self.n[self.kidx]
        self.off = np.zeros(len(self.kidx) + 1, np.int64); np.cumsum(self.counts, out=self.off[1:])
        assert self.off[-1] == len(self.feats) and self.goff[-1] == len(self.cand)
        nlot = int(max(self.cand.max(initial=-1), z["ev_ids"].max(initial=-1))) + 1
        self.ev_t = np.full(nlot, np.inf); self.ev_v = np.zeros(nlot, np.float32)
        self.ev_t[z["ev_ids"]] = z["ev_t"]; self.ev_v[z["ev_ids"]] = z["ev_v"]

    def rows_time(self):
        return np.repeat(self.tstep[self.kidx], self.counts)

    def lot_times(self):
        return np.repeat(self.rows_time(), self.gsz)

    def group_sum(self, per_lot):
        out = np.zeros(len(self.gsz), np.float32)
        np.add.at(out, np.repeat(np.arange(len(self.gsz)), self.gsz), per_lot)
        return out

    def step_slice(self, sel):
        lens = self.counts[sel]; starts = self.off[sel]
        rows = (np.concatenate([np.arange(s, s + l) for s, l in zip(starts, lens)])
                if len(sel) else np.zeros(0, np.int64))
        seg = np.repeat(np.arange(len(sel)), lens)
        pos = rows - np.repeat(starts, lens)
        return rows, seg, pos, lens


def lot_targets_points(cand, row_time, ev_t, ev_v, gamma_day, horizon_days):
    """Discounted point charge each arbitrated lot still has ahead of it."""
    dt = (ev_t[cand] - row_time) / 86400.0
    live = np.isfinite(dt) & (dt > 0)
    if horizon_days > 0:
        live &= dt <= horizon_days
    y = np.zeros(len(cand), np.float32)
    y[live] = (ev_v[cand][live] * (gamma_day ** dt[live])).astype(np.float32)
    return y


def build_advantages(policy, chunks, cfg):
    advs = []
    with torch.no_grad():
        for c in chunks:
            y = c.group_sum(lot_targets_points(c.cand, c.lot_times(), c.ev_t, c.ev_v,
                                               cfg.credit_gamma, cfg.credit_horizon))
            c.y = y
            resid = np.zeros(len(c.kidx), np.float32)
            B = 4096
            for s in range(0, len(c.kidx), B):
                sel = np.arange(s, min(s + B, len(c.kidx)))
                rows, seg, pos, lens = c.step_slice(sel)
                feats = torch.from_numpy(c.feats[rows].astype(np.float32))
                tg = torch.from_numpy(c.tg[rows].astype(np.int64))
                gm = torch.from_numpy(c.g_all[c.kidx[sel]].astype(np.float32))
                v = policy.lotval(torch.cat([feats[:, :policy.n_lotf], policy.emb_v(tg),
                                             gm[torch.from_numpy(seg)]], 1)).squeeze(-1).numpy()
                np.add.at(resid, sel[seg], y[rows] - v)
            advs.append(resid * cfg.rew_scale)
    return advs


# ------------------------------------------------------------------ learn ---
def spawn(cfg, wpath, it, greedy=False, tag="chunk"):
    snaps = snapshots(cfg)
    procs = []
    for w in range(cfg.workers):
        out = os.path.join(RUNS, f"{tag}_{w}.npz")
        seed = cfg.seed0 + it * cfg.workers + w
        ef = open(os.path.join(RUNS, f"{tag}_{w}.err"), "w")
        cmd = [sys.executable, os.path.abspath(__file__), "--worker", "--dataset", cfg.dataset,
               "--snapshot", snaps[w % len(snaps)], "--seed", str(seed), "--days", str(cfg.days),
               "--subsample", str(cfg.subsample), "--weights", wpath, "--out", out,
               "--cqt-rule", getattr(cfg, "cqt_rule", "none")]
        if greedy:
            cmd.append("--greedy")
        procs.append((subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=ef, text=True,
                                       cwd=os.path.dirname(os.path.abspath(__file__))), ef))
    outs = []
    for p, ef in procs:
        o = p.communicate()[0].strip().splitlines()
        ef.close()
        if p.returncode:
            raise RuntimeError(f"worker rc={p.returncode}; see {tag}_*.err in {RUNS}")
        outs.append(json.loads(o[-1]))
    return outs


def phase_learn(cfg):
    os.makedirs(RUNS, exist_ok=True)
    if not os.path.exists(os.path.join(RUNS, "norm.json")):
        calibrate(cfg)
    norm = Norm(os.path.join(RUNS, "norm.json"))
    policy = BatchPolicy(n_tools_of(cfg.dataset), n_g=len(norm.gmu))
    if cfg.init:
        policy.load_compat(torch.load(cfg.init, map_location="cpu", weights_only=True))
        print(f"[learn] initialised from {cfg.init}", flush=True)
    wpath = os.path.join(RUNS, "weights.pt")
    torch.save(policy.state_dict(), wpath)
    ref = BatchPolicy(n_tools_of(cfg.dataset), n_g=len(norm.gmu)); ref.load_state_dict(policy.state_dict()); ref.eval()
    opt = torch.optim.Adam(policy.parameters(), lr=cfg.lr)
    log = open(os.path.join(RUNS, "train_log.jsonl"), "a")
    best = -np.inf
    for it in range(cfg.iters):
        t0 = time.time()
        # deterministic window yield of the current weights (iteration 0 = theta_0),
        # on the SAME windows every iteration (fixed seeds, common random numbers), so
        # that iterates are compared paired and the best one is not the luckiest window
        det = spawn(cfg, wpath, 10_000, greedy=True, tag="det")
        det_R = float(np.mean([d["R"] for d in det]))
        if det_R > best:
            best = det_R
            shutil.copyfile(wpath, os.path.join(RUNS, "weights_best.pt"))
            json.dump({"iter": it, "det_yield": det_R}, open(os.path.join(RUNS, "best.json"), "w"))
        outs = spawn(cfg, wpath, it)
        chunks = [YChunk(os.path.join(RUNS, f"chunk_{w}.npz")) for w in range(cfg.workers)]
        A = build_advantages(policy, chunks, cfg)
        flat = np.concatenate(A)
        A = [((a - float(flat.mean())) / (float(flat.std()) + 1e-8)).astype(np.float32) for a in A]
        actor = it >= cfg.critic_warmup
        st = ppo_epochs(policy, opt, ref if cfg.kl_beta > 0 else None, chunks, A, cfg, actor=actor)
        torch.save(policy.state_dict(), wpath)
        torch.save(policy.state_dict(), os.path.join(RUNS, f"weights_it{it + 1}.pt"))   # every iterate kept
        row = {"iter": it, "det_yield": det_R, "det_done": float(np.mean([d["done"] for d in det])),
               "det_scrapped": float(np.mean([d["scrapped"] for d in det])),
               "sampled_yield": float(np.mean([o["R"] for o in outs])),
               "steps": int(sum(o["steps"] for o in outs)), "kept": int(sum(len(c.kidx) for c in chunks)),
               "wait_frac": float(np.mean([(c.act == c.n).mean() for c in chunks])),
               "adv_sd_raw": float(flat.std()), "actor": actor, "wall_s": round(time.time() - t0, 1)}
        row.update(st)
        print(json.dumps(row, default=float), flush=True)
        log.write(json.dumps(row, default=float) + "\n"); log.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--bc", action="store_true")
    ap.add_argument("--learn", action="store_true")
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--greedy", action="store_true")
    ap.add_argument("--dataset", default="HVLM")
    ap.add_argument("--snap-glob", default="../../experiments/smt2020/scrap_snaps/snap_HVLM_r0.98_s*.pkl.gz")
    ap.add_argument("--snapshot", default=None)
    ap.add_argument("--law", default="clock:2")
    ap.add_argument("--cqt-rule", default="none",
                    help="queue-time rule of the training windows (none or qtcr); the evaluation runs use qtcr")
    ap.add_argument("--init", default=None)
    ap.add_argument("--weights", default=os.path.join(RUNS, "weights.pt"))
    ap.add_argument("--out", default=os.path.join(RUNS, "chunk.npz"))
    ap.add_argument("--days", type=float, default=15.0)
    ap.add_argument("--episodes", type=int, default=8, help="--bc windows")
    ap.add_argument("--bc-epochs", type=int, default=30)
    ap.add_argument("--iters", type=int, default=20)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--credit", default="lot")
    ap.add_argument("--credit-gamma", type=float, default=0.9)
    ap.add_argument("--credit-horizon", type=float, default=10.0)
    ap.add_argument("--critic-warmup", type=int, default=2)
    ap.add_argument("--rew-scale", type=float, default=1.0)
    ap.add_argument("--clip", type=float, default=0.2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--minibatch", type=int, default=256)
    ap.add_argument("--subsample", type=float, default=0.5)
    ap.add_argument("--vcoef", type=float, default=0.5)
    ap.add_argument("--entcoef", type=float, default=0.001)
    ap.add_argument("--kl-beta", type=float, default=0.01)
    cfg = ap.parse_args()
    if cfg.calibrate:
        calibrate(cfg)
    elif cfg.bc:
        behaviour_clone(cfg)
    elif cfg.worker:
        phase_worker(cfg)
    elif cfg.learn:
        phase_learn(cfg)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
