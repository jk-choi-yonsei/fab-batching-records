"""Feature normalisation, feature rows, global vector and PPO update shared by
train_batch.py and eval_batch.py.

  Norm        per-column normalisation read from a norm.json (candidate rows
              and the global vector), clipped at +-20
  row_feats   one row per candidate group: the head lot's 12 benchmark
              features followed by FabEnv's N_EXTRA per-group columns
  global_vec  the fab_features snapshot, cached per simulated day, plus four
              per-step extras (groups, usable machines, fraction of the day,
              episode progress); N_G is its width
  ppo_epochs  clipped-PPO passes over the kept steps of a set of chunks, with
              the per-lot value loss (cfg.credit == "lot") or a global critic,
              and an optional KL anchor to a reference policy
  EMB, NEG    the tool-group embedding width and the masked-logit value

ppo_epochs asks the policy for batch(feats, tg, seg, pos, counts, gm, wait_ok)
-> (logits, per-row values), and for critic(gm) under the episode credit; it
asks each chunk for kidx, feats, tg, g_all, wait_ok, act, logp, step_slice(sel),
and y (lot credit) or ret (episode credit); and cfg for epochs, minibatch,
clip, credit, vcoef, entcoef and kl_beta.

Until 2026-10-10 this file was also the whole-fab layer-1 PPO trainer (the
Policy actor, rollout workers, lot-scoped credit and the learn loop). That
trainer is archived byte-identical at
archive/deadtime-final/legacy/fabhybrid-v1/smt2020/train_l1.py; its evaluator,
eval_l1.py, is in archive/2026-08-closed-probes/smt2020/. Nothing here runs as
a script.
"""
import json
from collections import defaultdict

import numpy as np
import torch
import torch.nn as nn

from rl_env import SECONDS_PER_DAY as SPD
from fab_features import snapshot as global_snapshot, FEATURES as GFEATS_ALL

# 2026-10-19: the days since the episode start (t_days) and the episode progress are no longer inputs; they spanned
# the 10-day training windows in training and the 360-day run in evaluation. Weights trained with them (the
# 2026-10-10 runs) are still evaluated: Norm reads the width from norm.json and global_vec takes time_inputs.
GFEATS = [k for k in GFEATS_ALL if k != "t_days"]
N_G = len(GFEATS) + 3     # + n_groups, free_machines, frac_of_day
N_G_TIME = len(GFEATS_ALL) + 4   # the width with t_days and ep_progress, as before 2026-10-19
EMB = 12
NEG = -1e9


class Norm:
    """Fixed feature normalisation, calibrated once from a random-policy run."""

    def __init__(self, path):
        j = json.load(open(path))
        self.lmu = np.array(j["lot_mu"], np.float32)
        self.lsd = np.array(j["lot_sd"], np.float32)
        self.gmu = np.array(j["g_mu"], np.float32)
        self.gsd = np.array(j["g_sd"], np.float32)
        self.time_inputs = len(self.gmu) == N_G_TIME    # weights trained before 2026-10-19

    def lots(self, f):
        if f.shape[1] != self.lmu.shape[0]:
            f = f[:, :self.lmu.shape[0]]
        return np.clip((f - self.lmu) / self.lsd, -20.0, 20.0)

    def glob(self, g):
        return np.clip((g - self.gmu) / self.gsd, -20.0, 20.0)


def global_vec(env, time_inputs=False):
    """Daily-cached global features + cheap per-step extras; with time_inputs, the width of the weights trained
    before 2026-10-19 (t_days among the daily features, the episode progress among the extras)."""
    inst = env.instance
    d = int(inst.current_time / SPD)
    keys = GFEATS_ALL if time_inputs else GFEATS
    if getattr(env, "_gday", None) != (d, time_inputs):
        f = global_snapshot(inst, inst.current_time,
                            (inst.current_time - env.t0) / SPD, env.fam_machines)
        env._gcache = np.array([f[k] for k in keys], np.float32)
        env._gday = (d, time_inputs)
    frac = (inst.current_time / SPD) % 1.0
    n = len(env._groups) if env._groups else 0
    extras = [n, float(len(inst.usable_machines)), frac]
    if time_inputs:
        extras.append((inst.current_time - env.t0) / SPD / env.episode_days)
    return np.concatenate([env._gcache, np.array(extras, np.float32)])


def row_feats(obs):
    """Per-candidate-group input: the head lot's benchmark features, plus the
    group's fill and size and its tightest live queue-time clock."""
    feats, tg, extra, _ = obs
    return np.concatenate([feats.numpy(), extra.numpy()], axis=1), tg


# ----------------------------------------------------------------- update ---
def ppo_epochs(policy, opt, ref, chunks, A, cfg, actor=True):
    """A single PPO pass over the kept steps of every chunk.

    With `actor` false only the critic moves: a freshly initialised V_lot makes
    the advantage a picture of its own error rather than of lot outcomes, so
    the first --critic-warmup iterations fit the baseline before the policy is
    allowed to react to it.
    """
    index = [(ci, i) for ci, c in enumerate(chunks) for i in range(len(c.kidx))]
    index = np.array(index, np.int64)
    stats = defaultdict(list)
    for _ in range(cfg.epochs):
        order = np.random.permutation(len(index))
        for s in range(0, len(order), cfg.minibatch):
            mb = index[order[s:s + cfg.minibatch]]
            loss = torch.zeros(())
            for ci in np.unique(mb[:, 0]):
                c = chunks[ci]
                sel = mb[mb[:, 0] == ci, 1]
                rows, seg, pos, lens = c.step_slice(sel)
                feats = torch.from_numpy(c.feats[rows].astype(np.float32))
                tg = torch.from_numpy(c.tg[rows].astype(np.int64))
                gm = torch.from_numpy(c.g_all[c.kidx[sel]].astype(np.float32))
                counts = torch.from_numpy(lens.astype(np.int64))
                wok = torch.from_numpy(c.wait_ok[c.kidx[sel]])
                logits, vals = policy.batch(
                    feats, tg, torch.from_numpy(seg), torch.from_numpy(pos),
                    counts, gm, wok)
                dist = torch.distributions.Categorical(logits=logits)
                act = torch.from_numpy(c.act[c.kidx[sel]].astype(np.int64))
                acol = torch.where(act == counts,
                                   torch.full_like(act, logits.shape[1] - 1), act)
                ratio = torch.exp(dist.log_prob(acol)
                                  - torch.from_numpy(c.logp[c.kidx[sel]]))
                adv = torch.from_numpy(A[ci][sel])
                un = ratio * adv
                cl = torch.clamp(ratio, 1 - cfg.clip, 1 + cfg.clip) * adv
                loss_pi = -torch.min(un, cl).mean()
                ent = dist.entropy().mean()
                if cfg.credit == "lot":
                    tgt = torch.from_numpy(c.y[rows])
                    loss_v = ((vals - tgt) ** 2).mean()
                else:
                    gv = policy.critic(gm).squeeze(-1)
                    loss_v = ((gv - torch.from_numpy(
                        c.ret[c.kidx[sel]].astype(np.float32))) ** 2).mean()
                part = cfg.vcoef * loss_v
                if actor:
                    part = part + loss_pi - cfg.entcoef * ent
                kl = torch.zeros(())
                if actor and ref is not None:
                    with torch.no_grad():
                        rlogits, _ = ref.batch(
                            feats, tg, torch.from_numpy(seg),
                            torch.from_numpy(pos), counts, gm, wok)
                    kl = torch.distributions.kl_divergence(
                        dist, torch.distributions.Categorical(logits=rlogits)
                    ).mean()
                    part = part + cfg.kl_beta * kl
                loss = loss + part * (len(sel) / len(mb))
                stats["loss_pi"].append(float(loss_pi))
                stats["loss_v"].append(float(loss_v))
                stats["entropy"].append(float(ent))
                stats["kl"].append(float(kl))
                stats["clip_frac"].append(
                    float((ratio - 1).abs().gt(cfg.clip).float().mean()))
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            opt.step()
    return {k: float(np.mean(v)) for k, v in stats.items()}
