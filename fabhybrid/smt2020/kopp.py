"""The benchmark authors' own queue-time control, reimplemented here.

Kopp, Hassoun, Kalir and Mönch -- the four who built SMT2020 -- published the
only production control logic for the queue-time constraints their testbed
ships (WSC 2020, "Integrating Critical Queue Time Constraints into SMT2020
Simulation Models"). They say plainly that the constraints are in the routes
and that "no production control logic is proposed so far that is able to treat
the CQT constraints in an appropriate way", and they offer two dispatching
rules plus a stopping strategy as "a non-trivial benchmark for other more
advanced approaches". That is what this module is: their benchmark, so that
anything built on top is measured against the authors rather than against
whatever this project invented.

Two of their results shape everything downstream.

QTCR halves violations for free. On their dataset 2, violations fall from
17.5% under a CQT-blind rule to 9.4%, while cycle time goes 37.7 -> 37.5 days
and on-time 92.7% -> 93.4%. This project measured a fixed-rate trade instead --
roughly 3.2 points of on-time per point of violations -- using a binary
urgent/not-urgent flag in the priority tuple. A binary flag orders nothing
within the urgent set, and that is most likely what was being measured.

Stopping is catastrophic without CQT-aware dispatching and harmless with it.
Under their medium threshold setting a CQT-blind dispatcher collapses to 0.5%
on-time with cycle time 47.0 days, while QTCR holds 93.8% at 37.7 days. Their
explanation is that prioritising constrained lots gives "an accelerated
resolution of stopping situations" -- the held lots get cleared. This project
put a stopping directive on top of a CQT-blind CR rule and measured it making
violations worse; that is the same combination, in the same direction.

QTS, their second rule, is not implemented. It needs per-step flow factors
"determined from long simulation runs" to split the queue time across the
intermediate steps, and in their own results it lands within a tenth of a
point of QTCR on violations while doing worse on on-time (91.3% against
93.4%). The calibration is real work for no measured gain.

One deliberate deviation: the ordering. Kopp applies priority, then least
setup, then QTCR, then CR. Upstream PySCFabSim orders setup before priority,
and this environment is validated bit-for-bit against upstream, so the QTCR
term is inserted into upstream's tuple rather than upstream's tuple being
rewritten into theirs.
"""
from bisect import bisect_right
from collections import defaultdict

BIG = 1e12          # the "huge" CQT end date for a lot under no constraint


def segment_families(instance, rules):
    """For each constrained source step, the (order, family) of every step from
    just after it up to and including the exit step.

    Precomputed once because the stopping strategy needs, for a lot standing
    anywhere inside a segment, the families it has still to pass before the
    clock runs out. Walking the route per lot per tick would cost tens of
    millions of steps over a run; this turns it into a slice.
    """
    out = {}
    for route in instance.routes.values():
        steps = sorted(route.steps, key=lambda s: s.order)
        orders = [s.order for s in steps]
        for s in steps:
            rec = rules.get(id(s))
            if rec is None:
                continue
            tgt = rec[0]
            i = bisect_right(orders, s.order)
            j = bisect_right(orders, tgt)
            out[id(s)] = ([x.order for x in steps[i:j]],
                          [getattr(x, "family", None) for x in steps[i:j]])
    return out


def remaining_pt_to_exit(lot, tgt):
    """Processing time from the lot's current step up to and including the exit
    step of its CQT segment -- the denominator of the queue-time critical
    ratio."""
    st = lot.actual_step
    if st is None:
        return 0.0
    total = st.processing_time.avg()
    for s in lot.remaining_steps:
        if s.order > tgt:
            break
        total += s.processing_time.avg()
    return total


def base_ptuple(lot, time, machine=None, setups=None):
    """Kopp's BASE scheme: lot priority, then least setup time, then critical
    ratio -- in that order.

    Upstream PySCFabSim orders setup BEFORE priority, which is not the same
    fab. With hot lots at priority 20 against 10 for regular ones, putting
    setup first lets a setup match outrank a hot lot, and that is a candidate
    explanation for this environment running about 5% slower than the numbers
    the authors report on the same dataset. The min-runs term stays in front
    because it is upstream's hard constraint, not a preference.
    """
    from simulation.dispatching.dispatcher import Dispatchers
    if machine is None:
        return -lot.priority, lot.cr(time)
    lot.ptuple = (
        0 if machine.min_runs_left is None
        or machine.min_runs_setup == lot.actual_step.setup_needed else 1,
        -lot.priority,
        Dispatchers.get_setup(lot.actual_step.setup_needed, machine,
                              lot.actual_step.setup_time, setups),
        lot.cr(time),
    )
    return lot.ptuple


def qtcr_index(lot, time, monitor):
    """Their queue-time critical ratio for one lot, or None if no clock runs.

    (d_j - t) / sum_{k=i..n} p_jk while the lot can still make it, and
    (d_j - t) * sum p_jk once it cannot -- so among lots already past their
    queue time the one with the most work left is the most urgent rather than
    the least, and a lot that is beyond saving does not outrank one that is
    not. Smaller is dispatched first.
    """
    rec = monitor.open.get(id(lot))
    if rec is None:
        return None
    tgt, deadline, _, _ = rec
    p = remaining_pt_to_exit(lot, tgt)
    slack = deadline - time
    return (slack / p) if (slack >= 0 and p > 0) else (slack * max(p, 1.0))


def qtcr_ptuple(base_fcn, monitor):
    """Upstream's priority tuple with the queue-time critical ratio inserted
    ahead of the rule's own ordering.

    QTCR_j(t,i) = (d_j - t) / sum_{k=i..n} p_jk   while the lot can still make
    it, and (d_j - t) * sum p_jk once it cannot -- so among lots already past
    their queue time, the one with the most work left is the most urgent rather
    than the least. Smaller is dispatched first; an unconstrained lot gets a
    huge end date and therefore a huge index, which puts it last among
    otherwise equal lots without disturbing their relative order.
    """
    def f(lot, time, machine=None, setups=None):
        t = list(base_fcn(lot, time, machine, setups))
        q = qtcr_index(lot, time, monitor)
        # an unconstrained lot gets a huge index, which puts it last among
        # otherwise equal lots without disturbing their relative order;
        # ahead of the rule's own term (cr / free_since), behind priority and
        # setup, which is where their scheme puts it
        return tuple(t[:-1]) + (BIG if q is None else q, t[-1])
    return f


def cqt_first_ptuple(base_fcn, monitor, at=2):
    """Saturation arm: every lot on a running queue-time clock is dispatched
    ahead of every lot that is not, ordered among themselves by their index.

    This is not a proposal, it is a bound. QTCR blends the queue-time ratio into
    the ordering behind priority and setup; this is the corner of that family
    where the queue-time term dominates everything the dispatcher is still free
    to choose. The lot priority tier stays in front, because reordering hot lots
    against regular ones changes the fab rather than the queue-time policy.
    Whatever violation rate this leaves is what dispatching alone cannot remove
    at this operating point, and its cycle time is what that removal costs at
    the extreme.

    Two constructions were tried and discarded on the way to this one, both on
    LVHM at 0.98, 25 days, against QTCR's 3.05% violations. Ordering the
    constrained lots by raw remaining margin gives 5.53%: sorting on margin
    alone puts the lots already beyond saving at the very front, where they
    consume the capacity that would have rescued the lots still in reach. And
    inserting the pair where QTCR sits -- behind setup -- reproduces QTCR
    exactly to the decimal, because an unconstrained lot already carries a
    huge index there, so the flag decides nothing that the index had not.

    `at` is therefore the whole content of this arm: the pair goes in front of
    the setup term, so a running clock outranks a setup match. Defined against
    `base_ptuple`, whose tuple is (min-runs, -priority, setup, CR), so at=2
    keeps the min-runs hard constraint and the lot priority tier in front and
    dominates everything after them.
    """
    def f(lot, time, machine=None, setups=None):
        t = list(base_fcn(lot, time, machine, setups))
        q = qtcr_index(lot, time, monitor)
        head = (1, BIG) if q is None else (0, q)
        return tuple(t[:at]) + head + tuple(t[at:])
    return f


class Stopping:
    """Kopp's lot stopping strategy: hold lots at the entrance of a CQT segment
    when the far end is already carrying too many constrained lots.

    Two counts per tool group, exactly as they define them:

      n1  constrained lots standing at that family plus those currently on its
          machines
      n2  n1 plus every constrained lot upstream that has still to pass this
          family before its own clock expires

    If either count reaches its threshold, no lot may ENTER a CQT segment whose
    span includes that family. Lots already inside a segment are untouched --
    stopping is about not adding to a queue that cannot absorb it, which is the
    opposite of holding a lot that is already committed.

    A single threshold per segment does not work, in their words, because tools
    are shared within and across CQT segments; that is why the count is kept
    per tool group and why the upstream term exists.
    """

    # Kopp set thresholds on two tool groups and left every other group
    # effectively open at 1,000. Those two groups are LithoTrack_FE_95 and
    # LithoTrack_FE_115, at 40 and 41 tools -- the same names and the same tool
    # counts as in this data, so their values transfer directly rather than
    # having to be re-tuned.
    SCENARIOS = {
        "none":   {},
        "high":   {"LithoTrack_FE_95": (90, 130), "LithoTrack_FE_115": (90, 220)},
        "medium": {"LithoTrack_FE_95": (60, 95),  "LithoTrack_FE_115": (70, 150)},
        "small":  {"LithoTrack_FE_95": (50, 85),  "LithoTrack_FE_115": (55, 125)},
    }

    def __init__(self, monitor, instance, per_family, refresh_s=1800.0):
        self.mon = monitor
        self.segf = segment_families(instance, monitor.rules or {})
        self.per = dict(per_family)
        self.refresh_s = refresh_s
        self._next = -1.0
        self.blocked = set()            # families over threshold right now
        self.n_held = 0

    def refresh(self, instance):
        now = instance.current_time
        if now < self._next:
            return
        self._next = now + self.refresh_s
        n1 = defaultdict(int)
        n2 = defaultdict(int)
        for lot in instance.active_lots:
            rec = self.mon.open.get(id(lot))
            if rec is None:
                continue
            st = getattr(lot, "actual_step", None)
            if st is None:
                continue
            fam = getattr(st, "family", None)
            if fam is not None:
                n1[fam] += 1
            # families still ahead of this lot inside its own segment
            src_step = self._source_step(lot, rec)
            if src_step is None:
                continue
            orders, fams = self.segf.get(src_step, ((), ()))
            k = bisect_right(orders, st.order)
            for f in fams[k:]:
                if f is not None:
                    n2[f] += 1
        blocked = set()
        for f, (a, b) in self.per.items():
            if n1[f] >= a or n1[f] + n2[f] >= b:
                blocked.add(f)
        self.blocked = blocked

    def _source_step(self, lot, rec):
        """id() of the step that started this lot's clock, recovered from the
        order the monitor recorded."""
        src_order = rec[2]
        for s in reversed(lot.processed_steps):
            if s.order == src_order:
                return id(s)
        return None

    def holds(self, lot):
        """Would starting this lot's clock feed a family that is over its
        threshold? Only asked of lots about to ENTER a segment."""
        if not self.blocked:
            return False
        st = getattr(lot, "actual_step", None)
        if st is None or self.mon.starts_clock(st) is None:
            return False
        _, fams = self.segf.get(id(st), ((), ()))
        for f in fams:
            if f in self.blocked:
                self.n_held += 1
                return True
        return False
