"""The isolated station with a price on the tool's time and arrivals announced ahead.

Proposition 1's station (non-interfering runs, common limit, a run costs kappa) with two
additions: while a load waits, the tool's time is priced at c per period; and every
arrival is announced L periods before it happens (a lot in process upstream), arrivals
further out being unknown. Solved exactly by value iteration on the full state, so that
the structure of the optimal policy can be read off: is it a control limit on the
tightest residual, how does its level depend on the time u to the next announced
arrival, and does anything else (the count, the other residuals, later arrivals) enter.

Time is in periods. State: the residuals of the waiting lots (distinct, in 1..R, since
at most one lot arrives per period; residual 1 is the last period in which the lot can
be served) and the announcement bits w_1..w_L (w_j = 1: a lot arrives at the start of
period t+j). At the start of a period the controller starts a run with the j oldest
lots, 1 <= j <= k, in ceil(j/B) runs at kappa each (runs take no tool from one another,
so several may start in a period), earning one per lot, or waits; then, if any
lot is still waiting, it pays c; then residuals fall by one (a lot at 0 is lost), the
announced lot for the next period arrives with residual R, the bits shift, and a new
bit is drawn Bernoulli(p). Discounted total reward, gamma per period.

  python theory/announced_station.py --B 3 --R 8 --L 4 --p 0.2 --kappa 0.5 --c 0.05
  python theory/announced_station.py --grid --out ../../experiments/smt2020/theory/announced.json
"""
import argparse
import itertools
import json
import os
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def popcount(x):
    return np.array([bin(int(v)).count("1") for v in x])


def lowest_bits_removed(mask, n):
    """remove the n lowest set bits of each mask (the n oldest lots)"""
    res = []
    for m, k in zip(mask, n):
        m = int(m)
        for _ in range(int(k)):
            m &= m - 1                 # clears the lowest set bit
        res.append(m)
    return np.array(res, dtype=np.int64)


def solve(B, R, L, p, kappa, c, gamma, tol=1e-13, max_iter=400000):
    nres, nw = 1 << R, 1 << L
    S = nres * nw
    res = np.repeat(np.arange(nres), nw)             # residual mask of each state
    w = np.tile(np.arange(nw), nres)                  # announcement mask
    k = popcount(res)

    def step(res_after, w_now):
        """residuals fall by one, the announced lot arrives, the bits shift; the next
        state for each draw of the new bit"""
        res_next = res_after >> 1                     # bit 0 (residual 1) drops out: lost
        arrives = (w_now & 1) == 1
        res_next = np.where(arrives, res_next | (1 << (R - 1)), res_next)
        w_shift = w_now >> 1
        return res_next * nw + w_shift, res_next * nw + (w_shift | (1 << (L - 1)))

    # one "fire j" action per number of oldest lots served, j = 1..R, in ceil(j/B) runs at kappa each
    # (runs take no tool from one another, so any number may start in a period); unavailable where j > k
    fire = []
    for j in range(1, R + 1):
        avail = k >= j
        res_fired = lowest_bits_removed(res, np.where(avail, j, 0))
        n0, n1 = step(res_fired, w)
        r = np.where(avail, j - kappa * -(-j // B) - c * ((k - j) >= 1), -np.inf)
        fire.append((avail, r, n0, n1))
    wait_n0, wait_n1 = step(res, w)
    r_wait = -c * (k >= 1).astype(float)

    def backup(V):
        Qw = r_wait + gamma * ((1 - p) * V[wait_n0] + p * V[wait_n1])
        Qf = np.full((R, S), -np.inf)
        for j, (avail, r, n0, n1) in enumerate(fire):
            Qf[j] = np.where(avail, r + gamma * ((1 - p) * V[n0] + p * V[n1]), -np.inf)
        return Qw, Qf

    V = np.zeros(S)
    converged = False
    for it in range(max_iter):
        Qw, Qf = backup(V)
        Vn = np.maximum(Qw, Qf.max(axis=0))
        d = np.abs(Vn - V).max()
        V = Vn
        if d < tol:
            converged = True
            break
    if not converged:
        raise RuntimeError(f"value iteration did not converge in {max_iter} sweeps (last change {d:.2e})")
    Qw, Qf = backup(V)                 # the action values of the converged V, not of the sweep before it
    # |V - V*| <= gamma/(1-gamma) * tol; the tie margin in analyse() must sit above that
    return {"V": V, "Qf": Qf, "Qw": Qw, "res": res, "w": w, "k": k, "iters": it + 1, "B": B, "R": R, "L": L,
            "value_error_bound": gamma / (1 - gamma) * tol}


def first_bit(mask):
    return (mask & -mask).bit_length() if mask else None


def analyse(sol, margin=1e-9):
    """The optimal action at every decision with a waiting lot, keyed by the tightest
    residual m, the time u to the next announced arrival (None: none within L), and the
    rest of the state; the threshold and nothing-joins checks run over every such state,
    the readings of the level over the under-full ones (1 <= k < B)."""
    assert margin > 2 * sol["value_error_bound"], "tie margin below the solver's error"
    res, w, k, Qf, Qw, B, R, L = sol["res"], sol["w"], sol["k"], sol["Qf"], sol["Qw"], sol["B"], sol["R"], sol["L"]
    best_fire = Qf.max(axis=0)
    fires = (best_fire > Qw + margin)
    ties = np.abs(best_fire - Qw) <= margin
    full_load = (Qf.argmax(axis=0) + 1) == k                      # the optimal fire serves every waiting lot
    act = {}                                                      # (u, m, k, others, later_bits) -> action
    partial_runs = 0
    for s in np.nonzero(k >= 1)[0]:
        rm, wm = int(res[s]), int(w[s])
        m = first_bit(rm)
        u = first_bit(wm)
        others = rm & (rm - 1)
        later = wm & (wm - 1)
        a = "F" if fires[s] else ("T" if ties[s] else "W")
        act[(u, m, int(k[s]), others, later)] = a
        if fires[s] and not full_load[s] and int(k[s]) < B:
            partial_runs += 1
    # 1. threshold in m for every fixed (u, k, others, later)
    groups = {}
    for (u, m, kk, others, later), a in act.items():
        groups.setdefault((u, kk, others, later), {})[m] = a
    non_threshold = 0
    for g in groups.values():
        f = [m for m, a in g.items() if a == "F"]; wt = [m for m, a in g.items() if a == "W"]
        if f and wt and max(f) > min(wt):
            non_threshold += 1
    # 2. the action at (u, m) at under-full decisions: does the rest of the state matter?
    by_um = {}
    for (u, m, kk, others, later), a in act.items():
        if kk < B:
            by_um.setdefault((u, m), set()).add(a)
    mixed = sum(1 for s in by_um.values() if len(s - {"T"}) > 1)
    # 3. fire whenever nothing can join: m <= min(u, L+1)
    viol_nothing_joins = sum(1 for (u, m, kk, others, later), a in act.items()
                             if m <= min(u if u is not None else 10 ** 9, L + 1) and a == "W")
    # 4. level nondecreasing in u: moving the first announced arrival later never turns a fire into a wait
    viol_mono = 0; pairs = 0
    for (u, m, kk, others, later), a in act.items():
        if u is None or a != "F" or kk >= B:
            continue
        u2 = first_bit(later)
        top = (u2 - 1) if u2 else L
        for u_ in range(u + 1, top + 1):
            a_ = act.get((u_, m, kk, others, later))
            if a_ is None:
                continue
            pairs += 1
            if a_ == "W":
                viol_mono += 1
    # 5. does the count enter: same (u, m, later), different k or others
    by_uml = {}
    for (u, m, kk, others, later), a in act.items():
        if kk < B:
            by_uml.setdefault((u, m, later), set()).add(a)
    count_matters = sum(1 for s in by_uml.values() if len(s - {"T"}) > 1)
    rows = {}
    for u in sorted({u for (u, m) in by_um}, key=lambda x: (x is None, x)):
        rows["none" if u is None else u] = "".join(
            ("?" if len(by_um[(u, m)] - {"T"}) > 1 else next(iter(by_um[(u, m)] - {"T"}), "T")) if (u, m) in by_um else "."
            for m in range(1, R + 1))
    return {"non_threshold": non_threshold, "um_cells": len(by_um), "um_mixed": mixed,
            "nothing_joins_violations": viol_nothing_joins, "mono_pairs": pairs, "mono_violations": viol_mono,
            "uml_cells": len(by_uml), "uml_count_matters": count_matters, "partial_runs": partial_runs,
            "actions_by_u": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=3)
    ap.add_argument("--R", type=int, default=8)
    ap.add_argument("--L", type=int, default=4)
    ap.add_argument("--p", type=float, default=0.2)
    ap.add_argument("--kappa", type=float, default=0.5)
    ap.add_argument("--c", type=float, default=0.05)
    ap.add_argument("--gamma", type=float, default=0.99)
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "..", "..", "experiments", "smt2020", "theory", "announced.json"))
    a = ap.parse_args()

    def report(B, R, L, p, kappa, c, gamma):
        t0 = time.time()
        sol = solve(B, R, L, p, kappa, c, gamma)
        an = analyse(sol)
        print(f"B{B} R{R} L{L} p{p} k{kappa} c{c} g{gamma}: {len(sol['V'])} states {sol['iters']} sweeps {time.time() - t0:.1f}s | "
              f"non-threshold {an['non_threshold']}, nothing-joins viol {an['nothing_joins_violations']}, "
              f"mono viol {an['mono_violations']}/{an['mono_pairs']}, rest-matters {an['um_mixed']}/{an['um_cells']}, "
              f"count-matters {an['uml_count_matters']}/{an['uml_cells']}, partial runs {an['partial_runs']}", flush=True)
        for u, row in an["actions_by_u"].items():
            print(f"    u={u!s:5} m=1..{R}: {row}")
        return {"B": B, "R": R, "L": L, "p": p, "kappa": kappa, "c": c, "gamma": gamma, **an}

    if not a.grid:
        report(a.B, a.R, a.L, a.p, a.kappa, a.c, a.gamma)
        return
    grid = list(itertools.product([2, 3, 4], [8, 12], [2, 4], [0.1, 0.25, 0.5], [0.25, 0.5, 1.0], [0.0, 0.02, 0.05, 0.1, 0.2]))
    out = [report(B, R, L, p, kappa, c, a.gamma) for B, R, L, p, kappa, c in grid]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
