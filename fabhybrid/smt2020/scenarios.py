"""Long-tail scenario injection for the warmed SMT2020 instance.

The simulator's NATIVE randomness never produces a large correlated shock (failures
are independent per machine; 2x the mean number-down is a ~4-sigma event), so the
tail we want the LLM to audit has to be injected deliberately.

We reuse the simulator's own ``BreakdownEvent`` so an injected outage flows through
exactly the same code path as a native failure -- only the timing, the targets and
the duration are ours. Native semantics: a breakdown delays the machine's in-flight
work by ``length`` (a BUSY machine is effectively out for that long); a machine that
is idle at that instant is unaffected. Bottleneck families run >90% busy, so an
outage lands on nearly all of them.

Import this AFTER `rl_env` (which puts the vendored simulator on sys.path).
"""
from simulation.events import BreakdownEvent

SPD = 86400.0
_NEVER = 10 ** 12  # repeat interval large enough that the injected event never recurs


class Constant:
    """Minimal stand-in for the simulator's distributions: ``sample()`` is constant."""

    def __init__(self, v):
        self._v = float(v)

    def sample(self):
        return self._v

    def avg(self):
        return self._v


def inject_outage(inst, family, at_day, duration_days, fraction=0.5, warmup_days=365):
    """Take ``fraction`` of one tool family down for ``duration_days``, starting at
    sim day ``warmup_days + at_day``. Returns a dict describing what was injected."""
    targets = [m for m in inst.machines if m.family == family]
    if not targets:
        raise ValueError(f"no machines in family {family!r}; "
                         f"try one of {sorted(set(m.family for m in inst.machines))[:6]}")
    n = max(1, int(round(len(targets) * fraction)))
    chosen = targets[:n]
    at = (warmup_days + at_day) * SPD
    for m in chosen:
        inst.add_event(BreakdownEvent(at, Constant(duration_days * SPD),
                                      Constant(_NEVER), m, True))
    return {"type": "outage", "family": family, "group": chosen[0].group,
            "machines_down": n, "of_total": len(targets),
            "at_day": warmup_days + at_day, "duration_days": duration_days}


def inject_hotlot_surge(inst, at_day, count, deadline_days=15.0, warmup_days=365):
    """Turn the ``count`` soonest-to-be-released lots into urgent ones released now:
    top priority tier and a tight deadline. Capacity is untouched; what changes is
    which decisions are correct."""
    at = (warmup_days + at_day) * SPD
    pool = sorted((l for l in inst.dispatchable_lots if l.release_at > at),
                  key=lambda l: l.release_at)[:count]
    if not pool:
        return {"type": "hotlot_surge", "count": 0}
    hot = max((l.priority for l in inst.active_lots), default=30)
    for l in pool:
        l.release_at = at
        l.priority = hot
        l.deadline_at = at + deadline_days * SPD
    inst.dispatchable_lots.sort(key=lambda l: l.release_at)
    return {"type": "hotlot_surge", "count": len(pool), "at_day": warmup_days + at_day,
            "priority": hot, "deadline_days": deadline_days}


def scale_release(inst, factor):
    """Scale the ARRIVAL RATE of not-yet-released lots by ``factor`` (<1 = slower).

    Rationale: under the SOTA policy this fab is chronically over-loaded (release
    57.2 lots/day vs ~46.7 completed, WIP grows without bound). No real fab runs
    with unboundedly growing WIP, and a 'long tail' is only meaningful if there is
    a normal body to contrast it with -- so we study the tail at a realistic,
    below-saturation operating point.

    Inter-arrival gaps are stretched by 1/factor. Each lot keeps its own deadline
    ALLOWANCE (deadline - release), so the due-date definition, the product mix and
    the priority mix are all unchanged; only the arrival rate moves.
    """
    if factor >= 1.0:
        return {"type": "release_scale", "factor": factor, "changed": 0}
    return _rescale_release(inst, factor)


def compress_release(inst, factor):
    """The same transform for factor > 1: inter-arrival gaps shrink by 1/factor,
    each lot keeps its own allowance. Kept separate from `scale_release` so the
    slow-only guard every existing caller relies on stays as it is. Used to
    measure the congestion side of the load axis (2026-09-06)."""
    if factor <= 1.0:
        return {"type": "release_compress", "factor": factor, "changed": 0}
    return _rescale_release(inst, factor)


def _rescale_release(inst, factor):
    now = inst.current_time
    n = 0
    for l in inst.dispatchable_lots:
        allowance = l.deadline_at - l.release_at
        l.release_at = now + (l.release_at - now) / factor
        l.deadline_at = l.release_at + allowance
        n += 1
    inst.dispatchable_lots.sort(key=lambda l: l.release_at)
    return {"type": "release_scale", "factor": factor, "changed": n,
            "new_rate_per_day": round(57.2 * factor, 2)}


def thin_wip(inst, keep_fraction, seed=0):
    """Remove a fraction of the WAITING work-in-process so the fab starts from a
    healthy inventory level instead of the backlog built up during overload.

    The shipped warm state carries WIP ~3550 at ~45 lots/day, i.e. a cycle time near
    80 days against 30-54 day deadline allowances — a congested fab. The SMT2020
    reference implies WIP ~2200. Draining that by simulation costs hours, so we
    construct the initial condition directly and then verify it is a genuine steady
    state (flat WIP slope) with a short settling run.

    Only lots that are NOT currently being processed are removed (in-process lots are
    referenced by pending LotDoneEvents). All bookkeeping the dispatch manager keeps
    -- lots_waiting_for_family, usable_lots / lot_in_usable, machine.waiting_lots,
    lot.waiting_machines -- is cleaned for each removed lot.
    """
    import random as _r
    if keep_fraction >= 1.0:
        return {"type": "thin_wip", "keep": keep_fraction, "removed": 0}

    in_process = set()
    for ev in getattr(inst.events, "event_array", []):
        for l in getattr(ev, "lots", []) or []:
            in_process.add(id(l))

    removable = [l for l in inst.active_lots if id(l) not in in_process]
    rng = _r.Random(seed)
    rng.shuffle(removable)
    n_remove = int(round(len(inst.active_lots) * (1.0 - keep_fraction)))
    n_remove = min(n_remove, len(removable))

    for l in removable[:n_remove]:
        step = getattr(l, "actual_step", None)
        if step is not None:
            inst.lots_waiting_for_family[step.family].discard(l)
        for m in list(getattr(l, "waiting_machines", [])):
            if l in m.waiting_lots:
                m.waiting_lots.remove(l)
        l.waiting_machines.clear()
        if inst.lot_in_usable.get(l.idx):
            inst.lot_in_usable[l.idx] = False
            if l in inst.usable_lots:
                inst.usable_lots.remove(l)
        inst.active_lots.remove(l)

    return {"type": "thin_wip", "keep": keep_fraction, "removed": n_remove,
            "in_process_protected": len(in_process), "wip_now": len(inst.active_lots)}


def apply(inst, spec, warmup_days=365):
    """spec e.g. 'outage:Litho_BE_110:5:7:0.5'  (family, at_day, duration_days, frac)
              or 'hotlot:5:200'                 (at_day, count)
              or 'none'."""
    if not spec or spec == "none":
        return None
    parts = spec.split(":")
    kind = parts[0]
    if kind == "outage":
        fam = parts[1]
        at_day = float(parts[2]) if len(parts) > 2 else 5.0
        dur = float(parts[3]) if len(parts) > 3 else 7.0
        frac = float(parts[4]) if len(parts) > 4 else 0.5
        return inject_outage(inst, fam, at_day, dur, frac, warmup_days)
    if kind == "hotlot":
        at_day = float(parts[1]) if len(parts) > 1 else 5.0
        count = int(parts[2]) if len(parts) > 2 else 200
        return inject_hotlot_surge(inst, at_day, count, warmup_days=warmup_days)
    raise ValueError(f"unknown scenario spec: {spec!r}")
