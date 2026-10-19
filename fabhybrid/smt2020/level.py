"""The level and the gate, learned. The form is not.

`kappa_ladder.py` (archive/2026-10-closed-lines/theory) settles ONE station exactly: the average-reward optimal
firing policy is a one-number control limit on the tightest residual exactly
when kappa is outside (1, B-1). Two properties never break there -- the optimal
fire set is a lower set in the residual profile, and firing always takes the
largest available load.

`chain_model.py` (archived beside it) settles the CHAIN, and it finds something the one-station
result cannot: every arm run here, upstream's own rule included, hard-codes
that a FULL load always fires -- and so does every batch policy whose
optimality we have been able to check. Deb and Serfozo (1973) prove the optimal
batch-service policy is a control limit on the NUMBER WAITING under holding
costs, which is what makes MBS the classical rule; Makis (1985) adds a hard
bound on waiting time and gets a count threshold that varies with elapsed time,
with forced service at the bound. Neither ever holds a full batch, and under
their cost structures neither could: with a holding cost proportional to the
queue, or with unbounded batch capacity, running the largest available load is
never worse. At one station that is right here too -- a full load earns
B - kappa > 0 and no cell contradicts it. In a chain it is wrong. If the frame
the cohort lands in cannot absorb it, the lots you send die there and the
completion is lost either way, so holding the full load upstream
is strictly better. On the calibrated cell the optimum holds a full load in 442
states, and that one suppressed decision carries most of a gap worth 6.90% of
throughput. Meanwhile choosing WHICH load to fire is worth -4.4e-16, exactly
zero -- the model's own reproduction of the `select:h` measurement on the fab.

So the decision class here is the law plus one thing it cannot say:

    fire  iff  (the load is full AND gate(s))  OR  0 <= tightest residual < h(s)

    h(s)    = h0 + beta * tanh(f_theta(phi(s)))
    gate(s) = (g0 + gamma . phi(s)) >= 0

At beta*f == 0 and g0 >= sum|gamma| this is `clock:h0`, decision for
decision, on every sample path -- asserted with the feature code fully
exercised rather than short-circuited, so the assertion tests the path the
search actually runs. There is therefore no behaviour-cloning step: theta_0 IS
the paper's arm by construction. The previous attempt cloned the law first,
reached near-one-hot logits at 0.999995, and PPO could not move the actor off
them.

*** SCOPE OF THAT CLAIM -- corrected 2026-09-15, it was written as if it held
for every kind and it does not. It is true only for the kinds that go through
`decide()`: const, m1, linear, gate1, gate2, gate, mlp, mlpgate, knob. It is
FALSE for kind="policy", which is the kind both frozen fab learners were
searched in. `batch_fire.choose` routes `is_policy` to `act()` and returns
before the full-load branch and before the clock branch; `act(self, env,
groups, now)` takes no `tightest` argument at all, so that kind never evaluates
`0 <= tightest < h*HOUR` and h0 is inert metadata for it. Its inert point is
every weight zero with 0 < bw < FULL_BONUS, which is the `full` arm -- verified
in fit/{HVLM,LVHM}_policy_d60/theta0/: batch_fill 1.0, batches_partial 0, 29.8
and 30.7 completions/day against clock:1's 38.5 on the same seeds. So a
kind="policy" search starts ~8.8/day BELOW the rule and has to rediscover
clocked firing; its gain over theta_0 is the climb back, not a gain over the
rule. The policy still SEES the clock (phi column own_res) and the class can
express clock:h exactly -- distill.py --window (now in
archive/2026-09-batch-line-closed/) builds it from two tanh units
with zero disagreements -- so what is missing is the starting point and the
rule's FORM, not the information. To search from the rule in this kind, use
fit_level.py's --init (same archive folder) with a distilled window artefact
and --expect-base, which asserts it.

Nested classes, so the question is model selection rather than "did RL win":

    M0  const     h                          1 param   the law
    M1  m1        h + beta*tanh(w * A)       2 free    one downstream coefficient
    M2  linear    h + beta*tanh(w . phi)     1 + d     linear in the state
    M1g gate1     M0 + a cut on the headroom  1 free   the model's own answer
    M2g gate      M0 + a linear gate         1 + d     the decision, not the level
    M3  mlp       h + beta*tanh(MLP(phi))    ~55       the learner
    M3g mlpgate   M3 + the gate                        both

The chain model says which of these can matter: entering ANY downstream feature
linearly into the THRESHOLD recovered 0.0-2.7% of the gap, while the same
feature entered as a GATE on the full load recovered 53.9%. So M1 and M2 are
expected to be null and are run precisely because the theory predicts they will
be -- a prediction that can fail.

phi carries only what the theory says the decision depends on, each column
bounded and scaled by a divisor baked in here, so there is no calibration
artefact to go stale and no per-run fitting to break determinism between arms.
"""
import json

import numpy as np

# column order is part of the artefact; never reorder, only append
FEATURES = ("fill", "slack2", "idle", "nxt", "tgt_rel", "tgt_lvl", "own_rel",
            "budget", "tgt_free", "headroom", "own_res")
D = len(FEATURES)
ABSORPTION = FEATURES.index("headroom")     # M1's single coordinate
OWN_RES = FEATURES.index("own_res")         # the tool's own tightest live clock
HOUR = 3600.0


def _cell(x, edges):
    """Index of the half-open bin [edges[i], edges[i+1]) holding x, clipped to the ends."""
    i = 0
    while i < len(edges) - 2 and x >= edges[i + 1]:
        i += 1
    return i


def _mean_service(env):
    """Mean per-lot service time by family, in hours, from the routes. A batch
    step serves batch_max lots in one run, so its per-lot cost is that much
    smaller -- this is a capacity figure, not a cycle time. Static, so it is
    computed once per instance and cached on the environment."""
    cache = getattr(env, "_level_mean_pt", None)
    if cache is not None:
        return cache
    tot, cnt = {}, {}
    for route in env.instance.routes.values():
        for s in route.steps:
            per = float(s.processing_time.avg()) / max(1, s.batch_max)
            tot[s.family] = tot.get(s.family, 0.0) + per
            cnt[s.family] = cnt.get(s.family, 0) + 1
    cache = {f: tot[f] / cnt[f] / HOUR for f in tot}
    env._level_mean_pt = cache
    return cache


def next_frame(env, lot):
    """The next queue-time constraint this lot will run into after the step it
    is standing at, as (limit seconds, target family, hops ahead).

    Necessary, not decorative: on this benchmark NO constraint has a batch step
    as its SOURCE -- the furnaces are clock TARGETS, never clock sources -- so
    asking what clock THIS load would start returns nothing at every furnace
    decision, and a headroom built on it would be constant. The frame the
    discharged cohort actually lands in is the first constraint SOURCE further
    along the route, and that is where the exported deaths were measured:
    firing under-full at Diffusion averts 612 + 397 deaths per seed there and
    creates them at Litho_BE_99 (+91), Dielectric_BE_60 (+63), WE_FE_41 (+41)
    and WE_FE_47 (+39).

    Deliberately NOT cached by step identity, even though the route is static:
    `has_to_perform` prunes sampled steps per lot, so two lots standing at the
    same step can have different routes ahead, and a cache would hand whichever
    lot arrived first to every lot after it. That would make a feature depend on
    run history in a way nothing else here does."""
    for hops, s in enumerate(getattr(lot, "remaining_steps", ())[:40], start=1):
        st = env.cqt.starts_clock(s)
        if st is not None:
            return float(st[1]), env.cqt.target_family(s), hops
    return None


# Deployment-time error in the time to the next arrival (an option, not used in the final runs). The simulator
# knows the next arrival exactly; a fab's dispatcher reads an MES/RTD estimate. Off unless
# batch_fire.py --nxt-noise-min / --nxt-missing sets it, and drawn from its own stream, so the
# simulator's random stream, and every paired comparison, is unchanged.
NXT_NOISE = {"sd_h": 0.0, "missing": 0.0, "rng": None, "err": {}}


def phi(env, g0, now):
    """The decision's state, as a bounded vector. Reads only what is already
    maintained: the per-family state `_obs` refreshes hourly (a family's queue
    is a slow variable by that module's own argument), the arrival heap, the
    open clocks, and a static per-family service time. Nothing here mutates the
    environment -- in particular it does NOT force a family refresh, because
    that would move the refresh instant and make the feature code observable in
    the trajectory even at zero weights."""
    x = np.zeros(D, np.float64)
    lot0 = g0[0]
    step = lot0.actual_step
    bm = max(1, step.batch_max)
    x[0] = len(g0) / bm

    # the residual profile beyond its minimum -- exactly what a control limit
    # on the tightest clock throws away, and what the lower-set result says is
    # legitimate to read
    live = []
    for lot in g0:
        rec = env.cqt.open.get(id(lot))
        if rec is not None and lot.actual_step.order == rec[0]:
            live.append(rec[1] - now)
    live.sort()
    x[1] = min(24.0, (live[1] - live[0]) / HOUR) / 24.0 if len(live) > 1 else 1.0

    # the ample-server premise, measured rather than assumed
    fam_ms = env.fam_machines.get(step.family, ())
    free = getattr(env.instance, "free_machines", None)
    if fam_ms and free is not None:
        x[2] = sum(1 for m in fam_ms if free[m.idx]) / len(fam_ms)

    # what waiting actually buys: when the next lot for this load arrives
    nxt = env.next_arrival(step.family, step.step_name)
    u = min(24.0, (nxt - now) / HOUR) if nxt is not None else 24.0
    if NXT_NOISE["rng"] is not None and nxt is not None:
        # one error per arriving lot (keyed by its arrival time), kept while it is on its way, as an
        # MES estimate of that lot would be; a fresh draw at every decision would add flicker no
        # dispatcher sees
        err = NXT_NOISE["err"]
        if nxt not in err:
            if len(err) > 4096:
                for t in [t for t in err if t <= now]:
                    del err[t]
            rng = NXT_NOISE["rng"]
            err[nxt] = (rng.random() < NXT_NOISE["missing"], rng.normal(0.0, NXT_NOISE["sd_h"]) if NXT_NOISE["sd_h"] > 0.0 else 0.0)
        miss, e = err[nxt]
        u = 24.0 if miss else min(24.0, max(0.0, u + e))   # no estimate: read as no lot due within the cap
    x[3] = u / 24.0

    # the frame the discharged cohort lands in. Prefer the family the clock
    # this load would START has to reach, since that is the one the firing
    # decision exports congestion to; fall back to the next step's family.
    frame = next_frame(env, lot0)
    budget_h = frame[0] / HOUR if frame else 0.0
    x[7] = min(24.0, budget_h) / 24.0
    tf = frame[1] if frame else None
    if not tf:
        rem = getattr(lot0, "remaining_steps", None)
        tf = rem[0].family if rem else None
    cs = env._fam_state.get(tf) if tf else None
    if cs is not None:
        x[4] = min(5.0, cs[1]) / 5.0 - 0.2          # queue vs its own typical level
        x[5] = min(20.0, cs[0]) / 20.0              # and the level itself, per tool
    tgt_ms = env.fam_machines.get(tf, ()) if tf else ()
    if tgt_ms and free is not None:
        x[8] = sum(1 for m in tgt_ms if free[m.idx]) / len(tgt_ms)

    # HEADROOM -- the variable the chain model says carries the decision:
    # what the clock budget has left after the cohort queues for service in the
    # frame it lands in. Negative means the cohort arrives already dead, and
    # firing exports a death instead of averting one.
    if cs is not None and tgt_ms:
        wait_h = cs[0] * _mean_service(env).get(tf, 0.0)
        x[9] = max(-24.0, min(24.0, budget_h - wait_h)) / 24.0
    else:
        x[9] = 1.0                                   # no known target: no constraint
    os_ = env._fam_state.get(step.family)
    if os_ is not None:
        x[6] = min(5.0, os_[1]) / 5.0 - 0.2

    # OWN_RES -- the tightest live clock standing at THIS tool, the same
    # quantity `choose` thresholds. Without it the gate cannot say "hold only
    # if nothing here is about to die", and on this benchmark that is fatal:
    # the furnaces are clock TARGETS, so holding a full load holds lots whose
    # deadline is to this very machine. A cut on downstream headroom alone,
    # blocking only 0.54% of full loads, cost 1.07 completions/day on HVLM.
    best = None
    for lot in env._machine.waiting_lots:
        rec = env.cqt.open.get(id(lot))
        if rec is not None and lot.actual_step.order == rec[0]:
            left = rec[1] - now
            best = left if best is None else min(best, left)
    x[10] = 1.0 if best is None else max(-24.0, min(24.0, best / HOUR)) / 24.0
    return x


class Level:
    """The decision: `fire iff (full and gate) or 0 <= tightest < h`.
    `kind` selects the class; `flat` is the search's view of the free
    parameters, always in the same order."""

    KINDS = ("const", "m1", "linear", "gate1", "gate2", "gate", "mlp", "mlpgate", "policy", "knob", "table", "setnet")
    FULL_BONUS = 1.0        # fixed, not learned: a full load starts one unit ahead

    def __init__(self, h0, kind="linear", beta=0.0, w=None, W1=None, b1=None,
                 w2=None, b2=0.0, gamma=None, g0=1.0, hidden=6,
                 t_head=-1.0, t_own=-1.0, mask=None, temp=1.0):
        assert kind in self.KINDS, f"unknown level kind {kind!r}"
        self.h0, self.kind, self.beta, self.hidden = float(h0), kind, float(beta), int(hidden)
        # TEMPERATURE -- multiplies the argument of every tanh in the policy, and
        # nothing else. temp = 1 IS the fitted artefact, decision for decision.
        # As temp grows tanh -> sign, so the decision boundary stops being a ramp
        # and becomes a surface. This matters because a noisy score search has no
        # pressure to grow the weights: the readout measured the HVLM learner
        # firing across a BAND of residuals (p10 0.7 h, median 3.2, p90 4.1) where
        # the rule fires at one point (0.72 h, never past 1.00). Scaling the OUTER
        # weights would do nothing -- argmax is invariant to a positive scale --
        # so the only knob that sharpens is this one, inside the nonlinearity.
        self.temp = float(temp)
        # ROUND-2 EXPLORATION for the `table` kind: with probability eps the table's
        # call is flipped. Set per run by batch_fire (--eps), never stored in the
        # artefact; rng is seeded from the run seed there. eps = 0 is the table itself.
        self.eps = 0.0
        self.rng = None
        # ASYMMETRIC exploration: policy-FIRE cells are 1-5% of decisions, so a
        # symmetric eps leaves their counterfactual (wait) arm with single-digit
        # samples -- the round-2 LVHM collapse rested on 3+3 waits. eps_fw flips
        # FIRE -> WAIT (set high), eps_wf flips WAIT -> FIRE (set low). When both
        # are 0 the symmetric eps applies.
        self.eps_fw = 0.0
        self.eps_wf = 0.0
        self.w = np.zeros(D) if w is None else np.asarray(w, np.float64)
        self.W1 = np.zeros((hidden, D)) if W1 is None else np.asarray(W1, np.float64)
        self.b1 = np.zeros(hidden) if b1 is None else np.asarray(b1, np.float64)
        self.w2 = np.zeros(hidden) if w2 is None else np.asarray(w2, np.float64)
        self.b2 = float(b2)
        self.gamma = np.zeros(D) if gamma is None else np.asarray(gamma, np.float64)
        self.g0 = float(g0)
        # the `knob` kind: the rule with three departures, each continuous in its
        # own parameter and inert at zero --
        #   THRESHOLD   h(x) = h0 exp(beta tanh(w x))      beta = 0 -> clock:h0
        #   LOOK-AHEAD  fire with no urgent clock iff q0 + wq x > 0   q0 = -1, wq = 0 -> never
        #   HOLD        fire a full load iff g0 + gamma x >= 0        g0 = 1, gamma = 0 -> always
        # Turning a knob moves the FRACTION OF STATES it applies to continuously,
        # which is what the searched score could not do: there the rule's margin
        # was a hard +/-0.5 step, so a correction either changed nothing or
        # flipped a whole region (10 of 64 candidates held every load and stopped
        # the fab). Same action space, a landscape an ES can actually walk.
        self.wq = np.zeros(D)
        self.q0 = -1.0
        self.t_head, self.t_own = float(t_head), float(t_own)
        # the STATE ABLATION: columns the policy is never allowed to see. The
        # theorem names the sufficient statistic -- the tightest residual --
        # and this is how "without it the learner cannot find the rule" gets
        # measured rather than asserted. phi still computes every column (the
        # readout needs them); the policy just multiplies the masked ones by 0.
        self.mask = sorted(int(i) for i in (mask or []))
        self.keep = np.ones(D)
        if self.mask:
            self.keep[self.mask] = 0.0
        # the `policy` kind: one shared hidden layer, a group head and a wait
        # head. All zero except the wait bias, which sits between an under-full
        # group's score (0) and a full one's (FULL_BONUS): that is `full`.
        self.Wp = np.zeros((hidden, D))
        self.bp = np.zeros(hidden)
        self.wg = np.zeros(hidden)
        self.bg = 0.0
        self.ww = np.zeros(hidden)
        self.bw = 0.5 * self.FULL_BONUS

    @property
    def gated(self):
        return self.kind in ("gate1", "gate2", "gate", "mlpgate", "knob")

    @property
    def is_policy(self):
        return self.kind == "policy"

    # --------------------------------------------------------- the policy ---
    def act(self, env, groups, now):
        """The full action space: score every candidate group and the wait
        option, take the argmax. Returns a group index or len(groups).

        This is the learner the paper trains. It is told nothing about clocks
        or thresholds: it starts as the shipped rule (`full`) and moves only on
        throughput. It can fire an under-full load, choose WHICH load, and hold
        a full one -- every dimension the theory has an opinion about -- so
        what it learns to use is the finding, not a foregone conclusion.
        """
        from fab_env import group_is_full
        best, best_i, h0 = None, len(groups), None
        for i, g in enumerate(groups):
            if g[0].actual_step.batch_max <= 1:
                continue
            x = phi(env, g, now) * self.keep
            h = np.tanh(self.temp * (self.Wp @ x + self.bp))
            if h0 is None:
                h0 = h                                   # the head group's view
            # the fixed prior is the shipped rule EXACTLY: `full` fires groups[0]
            # iff it is full and never fires another group, so the bonus goes to
            # groups[0] alone. Firing a full groups[1] while groups[0] is
            # under-full is a legitimate action upstream never takes; it stays
            # reachable through the learned weights, not through the prior.
            sc = float(self.wg @ h) + self.bg + (self.FULL_BONUS if (i == 0 and group_is_full(g)) else 0.0)
            if best is None or sc > best:
                best, best_i = sc, i
        if h0 is None:
            return 0
        wait = float(self.ww @ h0) + self.bw
        return len(groups) if wait > best else best_i

    def decide(self, env, g0, now, tightest, is_full):
        """The whole predicate, so the arm has one place to call and the
        inertness argument covers both halves."""
        if self.kind == "setnet":
            # THE SET LEARNER (fit_setnet.py, archive/2026-10-closed-lines/setnet): the forced states as in the table; in a free
            # decision the ensemble reads every clocked lot at the machine and may overturn
            # the table's decision only unanimously, and only in the table cells that passed
            # the own-entry test -- elsewhere the table decides. The clock set is built with
            # readout.py's test (the same lots `tightest` is the minimum of), so the network
            # sees what it was fitted on.
            if is_full:
                return True
            if tightest is None or tightest < 0.0:
                return False
            x = phi(env, g0, now)
            e = self.table["edges"]
            i = _cell(tightest / HOUR, e["tightest"])
            j = _cell(x[3] * 24.0, e["nxt"])
            k = _cell(x[0], e["fill"])
            if not self.own[i][j][k]:
                return bool(self.table["fire"][i][j][k])
            cl = []
            for l in env._machine.waiting_lots:
                rec = env.cqt.open.get(id(l))
                if rec is not None and l.actual_step.order == rec[0]:
                    cl.append(((rec[1] - now) / HOUR, l in g0))
            bm = g0[0].actual_step.batch_max
            import setnet_feat          # the set learner is archived (archive/2026-10-closed-lines/setnet)
            toks, g = setnet_feat.features(cl, len(g0), bm, x[3] * 24.0, len(env._groups), False)
            return setnet_feat.decide_free(self.setnet, toks, g, self.margin[i][j][k])
        if self.kind == "table":
            # THE DECISION-LEVEL LEARNER (written by fit_q.py; first by fit_decision.py,
            # now in archive/2026-09-batch-line-closed/): a 3-d table of causal
            # estimates from randomised exploration -- fire where the estimated lives
            # saved exceed lambda x slot-hours spent. No rule anywhere in it; h0 is
            # inert metadata. Full loads fire as in every arm; no live clock -> wait,
            # as the shipped dispatcher does.
            if is_full:
                return True
            if tightest is None or tightest < 0.0:
                return False
            x = phi(env, g0, now)
            e = self.table["edges"]
            i = _cell(tightest / HOUR, e["tightest"])
            j = _cell(x[3] * 24.0, e["nxt"])
            k = _cell(x[0], e["fill"])
            if self.table.get("head_axis"):
                # fit_q.py --head-axis: the second half of the fill index holds the decisions
                # where the tightest clocked lot waits OUTSIDE the head load. Same lot set and
                # the same tie rule (first lot at the minimum) as the dump the table was fitted on.
                best, inh = None, True
                for l in env._machine.waiting_lots:
                    rec = env.cqt.open.get(id(l))
                    if rec is not None and l.actual_step.order == rec[0]:
                        left = rec[1] - now
                        if best is None or left < best:
                            best, inh = left, (l in g0)
                if not inh:
                    k += len(e["fill"]) - 1
            d = bool(self.table["fire"][i][j][k])
            if self.rng is not None:
                if self.eps_fw > 0.0 or self.eps_wf > 0.0:
                    p = self.eps_fw if d else self.eps_wf
                    if p > 0.0 and self.rng.random() < p:
                        d = not d        # asymmetric exploration around the fitted policy
                elif self.eps > 0.0 and self.rng.random() < self.eps:
                    d = not d            # symmetric exploration
            return d
        if self.kind == "const":
            return is_full or (tightest is not None and 0.0 <= tightest < self.h0 * HOUR)
        x = phi(env, g0, now) * self.keep
        if self.kind == "knob":
            if is_full:
                return self.g0 + float(self.gamma @ x) >= 0.0
            if self.q0 + float(self.wq @ x) > 0.0:
                return True                      # look-ahead: fire without an urgent clock
            h = self.h0 * float(np.exp(self.beta * np.tanh(self.temp * float(self.w @ x))))
            return tightest is not None and 0.0 <= tightest < h * HOUR
        if is_full:
            if not self.gated:
                return True
            if self.kind == "gate2":
                # fire unless the downstream frame is short AND nothing standing
                # here is urgent. Not a halfspace, so not nested in `gate`; it IS
                # gate1 at t_own = -inf, so const < gate1 < gate2 holds.
                return x[ABSORPTION] >= self.t_head or x[OWN_RES] <= self.t_own
            return self.g0 + float(self.gamma @ x) >= 0.0
        h = self.h0 + self.beta * np.tanh(self.temp * self.f(x))
        return tightest is not None and 0.0 <= tightest < h * HOUR

    def f(self, x):
        if self.kind in ("m1", "linear", "gate1", "gate2", "gate"):
            return float(self.w @ x)
        return float(self.w2 @ np.tanh(self.temp * (self.W1 @ x + self.b1)) + self.b2)

    @property
    def inert(self):
        """True when the policy is `clock:h0` in every state, so the arm must
        reproduce it bit for bit. Deliberately NOT `beta == 0`: the search runs
        with beta free, and the assertion has to exercise the feature code."""
        if self.kind in ("table", "setnet"):
            return False
        if self.kind == "const":
            return True
        if self.kind == "policy":
            # every group scores 0 (+FULL_BONUS if full), wait scores bw:
            # `full` exactly when 0 < bw < FULL_BONUS and every weight is 0
            zero = not (self.Wp.any() or self.bp.any() or self.wg.any() or self.ww.any())
            return zero and self.bg == 0.0 and 0.0 < self.bw < self.FULL_BONUS
        if self.kind == "knob":
            # every column of phi is bounded in [-1, 1], so these three are
            # sufficient: the hold gate cannot close, the look-ahead cannot fire,
            # the threshold cannot move off h0
            return (self.g0 - float(np.abs(self.gamma).sum()) >= 0.0
                    and self.q0 + float(np.abs(self.wq).sum()) <= 0.0
                    and (self.beta == 0.0 or not self.w.any()))
        # the gate is inert when it cannot close anywhere in the feature box.
        # Every column of phi is bounded inside [-1, 1] by construction, so
        # g0 - sum|gamma| >= 0 is sufficient and covers gamma = 0, g0 >= 0.
        if self.kind == "gate2":
            gate_open = self.t_head <= -1.0        # every headroom clears the cut
        else:
            gate_open = (not self.gated) or (self.g0 - float(np.abs(self.gamma).sum()) >= 0.0)
        if self.beta == 0.0:
            return gate_open
        if self.kind in ("m1", "linear", "gate"):
            return gate_open and not self.w.any()
        return gate_open and (not self.w2.any()) and self.b2 == 0.0

    # ------------------------------------------------------ search vector ---
    def _level_n(self):
        if self.kind == "policy":
            H = self.hidden
            return H * D + H + H + 1 + H + 1
        return {"const": 0, "m1": 2, "linear": 1 + D, "gate1": 0, "gate2": 0, "gate": 0,
                "mlp": 1 + self.hidden * D + 2 * self.hidden + 1,
                "mlpgate": 1 + self.hidden * D + 2 * self.hidden + 1}[self.kind]

    def _gate_n(self):
        # gate1 is ONE number: the threshold on the absorption column. The chain
        # model says the recoverable gap needs exactly that -- one feature and a
        # cut -- and a scalar search has no seed, so it is exactly reproducible.
        # In the general gate the magnitude of gamma is redundant with g0's
        # scale, which is why the restricted class drops to a single parameter.
        if not self.gated:
            return 0
        return {"gate1": 1, "gate2": 2}.get(self.kind, 1 + D)

    def n_free(self):
        if self.kind == "knob":
            return 3 + 3 * D                     # beta, w | q0, wq | g0, gamma
        return self._level_n() + self._gate_n()

    def get_flat(self):
        v = []
        if self.kind == "knob":
            return np.concatenate([[self.beta], self.w, [self.q0], self.wq, [self.g0], self.gamma])
        if self.kind == "policy":
            return np.concatenate([self.Wp.ravel(), self.bp, self.wg, [self.bg], self.ww, [self.bw]])
        if self.kind == "m1":
            v = [self.beta, self.w[ABSORPTION]]
        elif self.kind == "linear":
            v = np.concatenate([[self.beta], self.w])
        elif self.kind in ("mlp", "mlpgate"):
            v = np.concatenate([[self.beta], self.W1.ravel(), self.b1, self.w2, [self.b2]])
        v = np.asarray(v, np.float64).ravel()
        if self.kind == "gate1":
            v = np.concatenate([v, [-self.g0]])          # the threshold itself
        elif self.kind == "gate2":
            v = np.concatenate([v, [self.t_head, self.t_own]])
        elif self.gated:
            v = np.concatenate([v, [self.g0], self.gamma])
        return v

    def set_flat(self, v):
        v = np.asarray(v, np.float64).ravel()
        assert v.size == self.n_free(), f"{self.kind} wants {self.n_free()}, got {v.size}"
        if self.kind == "knob":
            self.beta = float(v[0]); self.w = v[1:1 + D].copy()
            self.q0 = float(v[1 + D]); self.wq = v[2 + D:2 + 2 * D].copy()
            self.g0 = float(v[2 + 2 * D]); self.gamma = v[3 + 2 * D:].copy()
            return self
        if self.kind == "policy":
            H, k = self.hidden, 0
            self.Wp = v[k:k + H * D].reshape(H, D).copy(); k += H * D
            self.bp = v[k:k + H].copy(); k += H
            self.wg = v[k:k + H].copy(); k += H
            self.bg = float(v[k]); k += 1
            self.ww = v[k:k + H].copy(); k += H
            self.bw = float(v[k])
            return self
        nl = self._level_n()
        lv, gv = v[:nl], v[nl:]
        if self.kind == "m1":
            self.beta = float(lv[0])
            self.w = np.zeros(D)
            self.w[ABSORPTION] = lv[1]
        elif self.kind == "linear":
            self.beta, self.w = float(lv[0]), lv[1:].copy()
        elif self.kind in ("mlp", "mlpgate"):
            self.beta = float(lv[0])
            k, H = 1, self.hidden
            self.W1 = lv[k:k + H * D].reshape(H, D).copy(); k += H * D
            self.b1 = lv[k:k + H].copy(); k += H
            self.w2 = lv[k:k + H].copy(); k += H
            self.b2 = float(lv[k])
        if self.kind == "gate1":
            self.gamma = np.zeros(D)
            self.gamma[ABSORPTION] = 1.0
            self.g0 = -float(gv[0])                      # gate: headroom >= t
        elif self.kind == "gate2":
            self.t_head, self.t_own = float(gv[0]), float(gv[1])
        elif self.gated:
            self.g0, self.gamma = float(gv[0]), gv[1:].copy()
        return self

    # ------------------------------------------------------------- record ---
    def to_dict(self):
        return {"h0": self.h0, "kind": self.kind, "beta": self.beta, "hidden": self.hidden,
                "features": list(FEATURES), "w": self.w.tolist(), "W1": self.W1.tolist(),
                "b1": self.b1.tolist(), "w2": self.w2.tolist(), "b2": self.b2,
                "gamma": self.gamma.tolist(), "g0": self.g0,
                "t_head": self.t_head, "t_own": self.t_own,
                "Wp": self.Wp.tolist(), "bp": self.bp.tolist(), "wg": self.wg.tolist(),
                "bg": self.bg, "ww": self.ww.tolist(), "bw": self.bw,
                "mask": self.mask, "masked_features": [FEATURES[i] for i in self.mask],
                "wq": self.wq.tolist(), "q0": self.q0, "temp": self.temp,
                **({"edges": self.table["edges"], "fire": self.table["fire"], "lam": self.table["lam"],
                    "H": self.table["H"]} if getattr(self, "table", None) else {})}

    @classmethod
    def from_dict(cls, d):
        if list(d.get("features", FEATURES)) != list(FEATURES):
            raise ValueError("artefact was fitted against a different feature order")
        L = cls(d["h0"], kind=d["kind"], beta=d["beta"], w=d["w"], W1=d["W1"],
                b1=d["b1"], w2=d["w2"], b2=d["b2"], gamma=d.get("gamma"),
                g0=d.get("g0", 1.0), hidden=d.get("hidden", 6),
                t_head=d.get("t_head", -1.0), t_own=d.get("t_own", -1.0),
                mask=d.get("mask"))
        L.wq = np.asarray(d.get("wq", np.zeros(D)), np.float64)
        L.q0 = float(d.get("q0", -1.0))
        # artefacts written before the temperature knob existed load at 1.0, which
        # is the identity, so every frozen result stays reproducible from its file
        L.temp = float(d.get("temp", 1.0))
        if d.get("kind") in ("table", "setnet"):
            L.table = {"edges": d["edges"], "fire": d["fire"], "lam": d.get("lam"), "H": d.get("H"),
                       "head_axis": bool(d.get("head_axis", False))}
        if d.get("kind") == "setnet":
            L.own = d["own_entry"]
            L.margin = d["margin"]
            L.setnet = [{k: np.asarray(v, np.float64) for k, v in P.items()} for P in d["setnet"]]
        if "Wp" in d:
            L.Wp, L.bp = np.asarray(d["Wp"], np.float64), np.asarray(d["bp"], np.float64)
            L.wg, L.bg = np.asarray(d["wg"], np.float64), float(d["bg"])
            L.ww, L.bw = np.asarray(d["ww"], np.float64), float(d["bw"])
        return L

    def save(self, path):
        json.dump(self.to_dict(), open(path, "w"), indent=1)
        return path

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.load(open(path)))


def source_gate(th):
    """The comparator: gate at the tool that STARTS the clock, not at the one
    that must meet it.

    US 6,647,307 B1 (Taiwan Semiconductor Manufacturing Co.; Huang, Lu, You and
    Hsu; filed 2002-11-07, granted 2003-11-11) puts the decision at the
    queue-time-start tool a1 and has it consider the loading of the target tool
    a2: compute the processing demand, compare it against the queue-time
    tolerance, and permit processing only if the demand fits. Claim 1 carries no
    batching and nothing that holds a full batch, so it is prior art for
    "refuse to start a clock the downstream cannot honour" and not for the
    decision this paper measures -- which is why it is the right baseline.
    Having both on the same protocol also measures the upstream-coordination
    lead directly, instead of leaving it as a suggestion.

    Refuse to dispatch a lot whose completion would start a clock when the
    target family's queue implies the clock cannot be met with `th` of the
    budget (scaled) to spare. th very negative never refuses, so the arm is
    inert by construction and is asserted that way.
    """
    def gate(env, group):
        step = group[0].actual_step
        rule = env.cqt.starts_clock(step)
        if rule is None:
            return False
        tf = env.cqt.target_family(step)
        cs = env._fam_state.get(tf) if tf else None
        if cs is None or not env.fam_machines.get(tf):
            return False
        budget_h = float(rule[1]) / HOUR
        wait_h = cs[0] * _mean_service(env).get(tf, 0.0)
        head = max(-24.0, min(24.0, budget_h - wait_h)) / 24.0
        return head < th
    gate.th = th
    return gate
