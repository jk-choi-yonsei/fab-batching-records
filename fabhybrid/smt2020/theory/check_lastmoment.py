"""Brute-force check of the last-moment policy (the sentence of Section 3.2 of the paper that cites Berg et al.
1998; stated as a proposition in the appendix until 2026-10-19): with non-interfering runs and a
common limit tau, the last-moment policy is optimal against EVERY schedule -- including
ones that drop lots and ones that know the future -- whenever kappa <= 1.

For each random instance the true optimum is computed by dynamic programming over subsets:
a group of lots can share a run iff it has at most B lots and the latest arrival in it is
no later than the earliest deadline; every lot is either dropped or placed in exactly one
such group; value = lots served - kappa * runs. No structure of the proof is assumed.

  python theory/check_lastmoment.py
"""
import itertools
import random


def optimum(a, tau, B, kappa):
    n = len(a)
    d = [x + tau for x in a]
    feas = {}
    for r in range(1, B + 1):
        for G in itertools.combinations(range(n), r):
            if max(a[i] for i in G) <= min(d[i] for i in G):
                m = 0
                for i in G:
                    m |= 1 << i
                feas[m] = r
    groups_by_low = [[] for _ in range(n)]
    for m, r in feas.items():
        low = (m & -m).bit_length() - 1
        groups_by_low[low].append((m, r))
    best = [0.0] * (1 << n)
    for S in range(1, 1 << n):
        low = (S & -S).bit_length() - 1
        v = best[S & ~(1 << low)]                       # drop the lowest-indexed lot
        for m, r in groups_by_low[low]:
            if m & S == m:
                v = max(v, r - kappa + best[S & ~m])
        best[S] = v
    return best[(1 << n) - 1]


def last_moment(a, tau, B, kappa):
    n, f, runs = len(a), 0, 0
    while f < n:
        q = f
        while q + 1 < n and q + 1 - f + 1 <= B and a[q + 1] <= a[f] + tau:
            q += 1
        runs += 1
        f = q + 1
    return n - kappa * runs


def main():
    rng = random.Random(7)
    worst, cases, fails_above = 0.0, 0, 0
    for trial in range(6000):
        n = rng.randint(1, 9)
        B = rng.randint(1, 4)
        tau = rng.choice([0, 1, 2, 3, 5, 8])
        a = sorted(rng.randint(0, 14) for _ in range(n))          # ties in arrival time allowed
        for kappa in (0.0, 0.3, 0.7, 1.0):
            gap = optimum(a, tau, B, kappa) - last_moment(a, tau, B, kappa)
            worst = max(worst, gap)
            assert gap <= 1e-9, (a, tau, B, kappa, gap)
            cases += 1
        if optimum(a, tau, B, 1.5) - last_moment(a, tau, B, 1.5) > 1e-9:
            fails_above += 1                                   # the bound kappa <= 1 is needed
    print(f"{cases} cases with kappa <= 1: the last-moment policy attains the optimum in all; largest excess {worst:.1e}")
    print(f"at kappa = 1.5 it is beaten in {fails_above} of 6000 instances, so the condition is not vacuous")


if __name__ == "__main__":
    main()
