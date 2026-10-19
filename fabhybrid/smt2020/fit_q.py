"""Off-policy fit of the fire/wait decision: value iteration on the empirical cell MDP.

Why (rounds 1-3 of fit_decision.py, 2026-09-16; that script is now in
archive/2026-09-batch-line-closed/): the bandit table compares "fire now"
with "wait, then do whatever the exploration policy does at the next decision". Under a
policy that fires soon anyway every single firing looks redundant, the greedy refit deletes
them all, and the deployed table is `full` (LVHM rounds 2 and 3: 24.8 and 25.7 lots/day
against the rule's 36.0; the round-3 refit with 39-75 counterfactual waits per cell still
kept one FIRE cell in 72). The value of waiting has to be the NEW policy's own continuation.

This script turns every furnace step of every exploration dump into a decision chain --
(cell, action) -> (reward, elapsed time, next cell) -- and solves the aggregated MDP by
value iteration. At the fixed point V(c) = max_a Q(c, a), so "wait" in a cell is valued
under the table policy itself (wait until the cell changes, then act), not under the
behaviour policy's next firing. A transition does not depend on which policy logged it,
so all rounds pool. Deployment is the same table lookup as before (Level kind `table`).

State cells: tightest live residual x time-to-next-arrival x fill of the head load, with
fill = k / batch_max (the deployed feature; label.py's earlier "B" was a queue length).
Forced states -- full load (fire) and no live clock (wait) -- carry their own cells so the
continuation value exists everywhere. Reward per transition (the classical batch-service cost: shortage, capacity, holding):
    -(scraps at this step until the next decision) - lam * (batch_max - k) * R * 1[fire]
    - mu * k * elapsed_hours * 1[wait]
with R the observed run length of the fired machine, k the head-group lots; lam (lots per
slot-hour) and mu (lots per lot-hour waited) are the two disclosed exchange rates, chosen on
search seeds. Without mu the learner delays a firing whenever no death is at stake and the
fab pays in WIP (LVHM, 2026-09-16). Elapsed time is discounted at gamma_h per hour.

  python fit_q.py "E/HVLM_explore0p02_s*.json" "E/r2/HVLM_r2_s*.json" "E/r3/HVLM_r3*_s*.json" \\
      --lam 0.003 --out E/q/HVLM_q_l0p003.json
"""
import argparse
import glob
import json
from collections import Counter, defaultdict

import numpy as np

from label import batch_max_per_step

EDGES = {
    "tightest": [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 24.01],
    "nxt":      [0.0, 0.25, 1.0, 3.0, 24.01],
    "fill":     [0.0, 0.3, 0.55, 1.001],
}
K0 = 10.0
WAIT, FIRE = 0, 1


def cell(x, edges):
    return int(np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2))


class States:
    """free cells (T x N x F), then no-clock cells (N x F), then the full-load cell.
    With head=True the fill index carries a second half: k + F0 when the tightest clocked
    lot is NOT in the head load (F = 2 F0), so the table can tell the two apart."""

    def __init__(self, edges, head=False):
        self.T, self.N, self.F = (len(edges[k]) - 1 for k in ("tightest", "nxt", "fill"))
        self.F0, self.head = self.F, bool(head)
        if self.head:
            self.F = 2 * self.F0
        self.n_free = self.T * self.N * self.F
        self.n_noclock = self.N * self.F
        self.n = self.n_free + self.n_noclock + 1
        self.full = self.n - 1

    def free(self, i, j, k):
        return (i * self.N + j) * self.F + k

    def noclock(self, j, k):
        return self.n_free + j * self.F + k

    def unravel(self, s):
        return np.unravel_index(s, (self.T, self.N, self.F))


def chains(path, S, edges, batch_max=None, unit="step", from_day=0.0):
    """unit='step': one chain per furnace step, deaths at that step. unit='family': one chain per
    tool family (every machine's decisions, whichever step its head group belongs to), deaths at
    any step of the family -- the unit the decision actually spans: the tightest clock the
    policy reads is tool-wide, and 99% of urgent lots outside the head belong to ANOTHER step
    of the same family (23-29% of them die), which a per-step chain credits elsewhere."""
    D = json.load(open(path))
    dec, scr = D["decisions"], D["scrapped"]
    if from_day > 0.0:                  # a logging window that starts after the warm-up
        dec = [d for d in dec if d["day"] >= from_day]
        scr = [x for x in scr if x["day"] >= from_day]
    B = batch_max_per_step(dec, scr, batch_max)
    key = (lambda step: step) if unit == "step" else (lambda step: step.split("|")[0])
    deaths = defaultdict(list)
    for s in scr:
        if s["batch_max"] > 1:
            deaths[key(s["step"])].append(s["day"])
    deaths = {k: np.sort(np.array(v)) for k, v in deaths.items()}
    by_m = defaultdict(list)
    for d in dec:
        by_m[d["mach"]].append(d["day"])
    by_m = {m: np.sort(np.array(v)) for m, v in by_m.items()}
    by_s = defaultdict(list)
    for d in dec:                       # dumps are in decision order
        by_s[key(d["step"])].append(d)

    def state(d, bm):
        fill = d["size"] / bm
        j, k = cell(d["nxt_h"], edges["nxt"]), cell(fill, edges["fill"])
        if d["full"]:
            return S.full, None
        tight = min(c[1] for c in d["clocks"]) if d["clocks"] else None
        if tight is None or tight < 0.0:
            return S.noclock(j, k), None
        if S.head and not min(d["clocks"], key=lambda c: c[1])[2]:
            k += S.F0                   # the tightest clocked lot waits outside the head load
        return S.free(cell(tight, edges["tightest"]), j, k), tight

    rows = []                           # s, a, C, deaths, dt_h, s2, head-group lots
    for unit_key, ds in by_s.items():
        dd = deaths.get(unit_key, np.array([]))
        st = [state(d, B[d["step"]])[0] for d in ds]
        for n in range(len(ds) - 1):
            d, t, t2 = ds[n], ds[n]["day"], ds[n + 1]["day"]
            nd = int(np.searchsorted(dd, t2, side="right") - np.searchsorted(dd, t, side="right"))
            fired = d["act"] < d["n_groups"]
            assert (not fired) or d["act"] == 0, "non-head firing in the dump"
            C = 0.0
            if fired and not d["full"]:                       # run length R = time to this machine's next decision
                times = by_m[d["mach"]]; nxt_i = int(np.searchsorted(times, t + 1e-9))
                R = (times[nxt_i] - t) * 24.0 if nxt_i < len(times) else np.nan
                C = (B[d["step"]] - d["size"]) * R
            rows.append((st[n], FIRE if fired else WAIT, C, nd, (t2 - t) * 24.0, st[n + 1], d["size"]))
    return rows, D["seed"], D["arm"]


def solve(rows, S, lam, gamma_h, mu=0.0, iters=5000, tol=1e-9):
    s, a, C, nd, dt, s2, k = (np.array(x) for x in zip(*rows))
    C = np.where(np.isfinite(C), C, np.nanmean(C[(a == FIRE) & np.isfinite(C)]))
    # reward: scraps, empty slot-hours if fired, and -- the holding term of the classical batch-service
    # cost -- the lot-hours the head group keeps waiting when the decision is to wait
    r = -nd.astype(float) - lam * C * (a == FIRE) - mu * k * dt * (a == WAIT)
    disc = gamma_h ** dt
    n = np.zeros((S.n, 2)); Rsum = np.zeros((S.n, 2)); W = np.zeros((S.n, 2, S.n))
    np.add.at(n, (s, a), 1.0)
    np.add.at(Rsum, (s, a), r)
    np.add.at(W, (s, a, s2), disc)
    # marginals over the tightest bin (free cells only), for shrinkage of thin cells
    tb = np.full(S.n, -1)
    for i in range(S.T):
        for j in range(S.N):
            for k in range(S.F):
                tb[S.free(i, j, k)] = i
    nm = np.zeros((S.T, 2)); Rm = np.zeros((S.T, 2)); Wm = np.zeros((S.T, 2, S.n))
    for i in range(S.T):
        m = tb == i
        nm[i] = n[m].sum(0); Rm[i] = Rsum[m].sum(0); Wm[i] = W[m].sum(0)
    # shrunk per-(cell, action) reward and transition operator
    Rbar = np.zeros((S.n, 2)); Wbar = np.zeros((S.n, 2, S.n)); nn = n.copy()
    for st in range(S.n):
        for ac in range(2):
            if tb[st] >= 0:
                i = tb[st]
                Rbar[st, ac] = (Rsum[st, ac] + K0 * (Rm[i, ac] / max(nm[i, ac], 1))) / (n[st, ac] + K0)
                Wbar[st, ac] = (W[st, ac] + K0 * (Wm[i, ac] / max(nm[i, ac], 1))) / (n[st, ac] + K0)
                nn[st, ac] = n[st, ac] + K0
            elif n[st, ac] > 0:
                Rbar[st, ac] = Rsum[st, ac] / n[st, ac]; Wbar[st, ac] = W[st, ac] / n[st, ac]
    allowed = np.ones((S.n, 2), bool)
    allowed[S.n_free:S.n_free + S.n_noclock, FIRE] = False       # no live clock: policy family waits
    allowed[S.full, WAIT] = False                                # full load: always fires
    V = np.zeros(S.n)
    for it in range(iters):
        Q = Rbar + Wbar @ V
        Q = np.where(allowed, Q, -np.inf)
        V2 = Q.max(1)
        if np.max(np.abs(V2 - V)) < tol:
            V = V2; break
        V = V2
    Q = Rbar + Wbar @ V
    return Q, V, n, r, it + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dumps", nargs="+", help="glob patterns of readout --dump-lots files (all rounds pool)")
    ap.add_argument("--lam", type=float, default=0.003, help="lots per slot-hour")
    ap.add_argument("--gamma-h", type=float, default=0.9, help="discount per hour of elapsed time")
    ap.add_argument("--mu", type=float, default=0.0, help="holding cost, lots per lot-hour a head-group lot waits (0 = deaths and capacity only)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--batch-max", default=None, help="JSON step -> batch_max, for dumps written without phi")
    ap.add_argument("--chain", choices=("step", "family"), default="step", help="decision-chain unit: furnace step, or tool family (all its steps)")
    ap.add_argument("--fold", default="", help="state ablation: comma-separated axes (tightest, nxt, fill) collapsed to ONE bin, "
                    "so the table cannot condition on them; the artefact carries the folded edges and deploys unchanged")
    ap.add_argument("--from-day", type=float, default=0.0,
                    help="drop records before this simulated day (the logging window)")
    ap.add_argument("--head-axis", action="store_true",
                    help="a fourth, binary axis: whether the tightest clocked lot is in the head load "
                         "(stored as a second half of the fill index; deployment reads the flag head_axis)")
    ap.add_argument("--backoff", action="store_true",
                    help="an entry is the cell's own decision only where BOTH actions were observed at least K0 "
                         "times there; elsewhere it is the decision of the residual-only table fitted from the same "
                         "records (whose own bins need K0 of each action too, else the load-building rule: wait)")
    ap.add_argument("--edges-tightest", default="",
                    help="interior bin edges of the tightest residual in hours, comma-separated "
                         "(default 0.25,0.5,1,2,4); the artefact carries them and deploys unchanged")
    ap.add_argument("--edges-nxt", default="",
                    help="interior bin edges of the time to the next arrival in hours (default 0.25,1,3)")
    a = ap.parse_args()
    for ax, spec in (("tightest", a.edges_tightest), ("nxt", a.edges_nxt)):
        if spec:
            inner = sorted(float(x) for x in spec.split(","))
            assert 0.0 < inner[0] and inner[-1] < 24.01, spec
            EDGES[ax] = [0.0] + inner + [24.01]
    for ax in filter(None, a.fold.split(",")):
        assert ax in EDGES, ax
        EDGES[ax] = [EDGES[ax][0], EDGES[ax][-1]]
    S = States(EDGES, head=a.head_axis)
    bmax = json.load(open(a.batch_max)) if a.batch_max else None
    rows, srcs = [], []
    for pat in a.dumps:
        for p in sorted(glob.glob(pat)):
            rr, seed, arm = chains(p, S, EDGES, bmax, a.chain, a.from_day)
            rows += rr; srcs.append(p)
            print(f"{p.split('/')[-1]:34s} {arm:12s} seed {seed}: {len(rr):,} transitions")
    if not srcs:
        raise SystemExit(f"no records file matches {a.dumps} (the records are not in the public repository; "
                         "see experiments/smt2020/final/collect/README.md)")
    Q, V, n, r, its = solve(rows, S, a.lam, a.gamma_h, a.mu)
    s_all, a_all = np.array([x[0] for x in rows]), np.array([x[1] for x in rows])
    free = s_all < S.n_free
    print(f"\n{len(rows):,} transitions, {int(free.sum()):,} at free (under-full, live-clock) decisions, "
          f"{int((a_all[free] == FIRE).sum()):,} fired; lam {a.lam}, mu {a.mu}, gamma_h {a.gamma_h}; VI converged in {its} sweeps")
    fire = np.zeros((S.T, S.N, S.F), bool); margin = np.zeros((S.T, S.N, S.F))
    nf = np.zeros((S.T, S.N, S.F), int); nw = np.zeros_like(nf)
    for i in range(S.T):
        for j in range(S.N):
            for k in range(S.F):
                st = S.free(i, j, k)
                margin[i, j, k] = Q[st, FIRE] - Q[st, WAIT]
                fire[i, j, k] = margin[i, j, k] > 0
                nf[i, j, k], nw[i, j, k] = int(n[st, FIRE]), int(n[st, WAIT])
    fire_own, own, fire_res = fire.copy(), np.ones_like(fire, bool), None
    if a.backoff:
        edges_r = {"tightest": EDGES["tightest"], "nxt": [EDGES["nxt"][0], EDGES["nxt"][-1]],
                   "fill": [EDGES["fill"][0], EDGES["fill"][-1]]}
        S_r = States(edges_r)
        rows_r = []
        for p in srcs:
            rows_r += chains(p, S_r, edges_r, bmax, a.chain, a.from_day)[0]
        Q_r, _, n_r, _, _ = solve(rows_r, S_r, a.lam, a.gamma_h, a.mu)
        fire_res = np.zeros(S_r.T, bool)
        for i in range(S_r.T):
            st = S_r.free(i, 0, 0)
            fire_res[i] = (min(n_r[st, FIRE], n_r[st, WAIT]) >= K0) and (Q_r[st, FIRE] - Q_r[st, WAIT] > 0)
        own = np.minimum(nf, nw) >= K0
        fire = np.where(own, fire_own, fire_res[:, None, None])
        vis = (nf + nw).astype(float)
        print(f"back-off: {int((~own).sum())} of {own.size} cells lack {K0:g} observations of both actions "
              f"({100 * vis[~own].sum() / max(vis.sum(), 1):.2f}% of logged free decisions) and take the residual-only "
              f"decision {fire_res.astype(int).tolist()}; {int((fire != fire_own).sum())} entries change")
    tl, nl, fl = EDGES["tightest"], EDGES["nxt"], EDGES["fill"]
    print(f"\n{'tightest':>11} | " + " | ".join(f"nxt[{nl[j]:g},{nl[j+1]:g})".center(29) for j in range(S.N)))
    print(f"{'':>11} | " + " | ".join("  ".join(f"{'o' if k >= S.F0 else ''}f{fl[k % S.F0]:.2g}".rjust(8) for k in range(S.F)).center(29) for j in range(S.N)))
    for i in range(S.T):
        row = f"[{tl[i]:g},{tl[i+1]:g})h".rjust(11) + " | "
        cells = []
        for j in range(S.N):
            s = []
            for k in range(S.F):
                mark = "FIRE" if fire[i, j, k] else "wait"
                s.append(f"{mark}{nf[i,j,k]:>3d}/{nw[i,j,k]:<4d}".rjust(8))
            cells.append("  ".join(s).center(29))
        print(row + " | ".join(cells))
    print("   (each cell: decision, then fired/waited transitions observed there)")
    print("\nQ(fire) - Q(wait), lots, by tightest bin (mean over the bin's cells weighted by visits):")
    for i in range(S.T):
        w = (nf[i] + nw[i]).astype(float); m = margin[i]
        print(f"  [{tl[i]:g},{tl[i+1]:g})h  {np.average(m, weights=w) if w.sum() else float('nan'):+.3f}   "
              f"fire cells {int(fire[i].sum())}/{S.N * S.F}")
    it_free = s_all[free]
    share = np.mean([fire[S.unravel(st)] for st in it_free]) if len(it_free) else float("nan")
    print(f"fire region: {int(fire.sum())} of {fire.size} cells; share of logged free decisions it fires: {100 * share:.2f}%  "
          f"(the rule clock:1 fires ~1.2%)")
    print(f"V: full {V[S.full]:+.3f}; no-clock mean {V[S.n_free:S.n_free + S.n_noclock].mean():+.3f}; free mean {V[:S.n_free].mean():+.3f}")
    base = {"h0": 1.0, "beta": 0.0, "hidden": 6, "w": [0.0] * 11, "W1": [[0.0] * 11] * 6,
            "b1": [0.0] * 6, "w2": [0.0] * 6, "b2": 0.0, "gamma": [0.0] * 11, "g0": 1.0,
            "features": ["fill", "slack2", "idle", "nxt", "tgt_rel", "tgt_lvl", "own_rel",
                         "budget", "tgt_free", "headroom", "own_res"]}
    json.dump({**base, "kind": "table", "method": "value-iteration on the empirical cell MDP (fit_q.py)",
               "lam": a.lam, "mu": a.mu, "gamma_h": a.gamma_h, "K0": K0, "chain": a.chain, "fold": a.fold, "head_axis": bool(a.head_axis), "edges": EDGES,
               "from_day": a.from_day, "backoff": bool(a.backoff), "fire_own": fire_own.astype(int).tolist(),
               "own_entry": own.astype(int).tolist(),
               "fire_residual_only": None if fire_res is None else fire_res.astype(int).tolist(),
               "fire": fire.astype(int).tolist(), "margin": margin.tolist(),
               "Q_fire": Q[:S.n_free, FIRE].reshape(S.T, S.N, S.F).tolist(),
               "Q_wait": Q[:S.n_free, WAIT].reshape(S.T, S.N, S.F).tolist(),
               "n_fired": nf.tolist(), "n_waited": nw.tolist(),
               "V_full": float(V[S.full]), "V_noclock": V[S.n_free:S.n_free + S.n_noclock].reshape(S.N, S.F).tolist(),
               "source": srcs, "n_transitions": len(rows), "batch_max_table": a.batch_max}, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
