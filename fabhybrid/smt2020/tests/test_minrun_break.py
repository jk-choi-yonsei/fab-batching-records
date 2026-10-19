"""The law's second deferral: a setup min-run lock can be broken for a lot
whose clock is about to run out. finalize_choice keeps upstream's deferral
unless asked to break it."""
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fab_env  # noqa: E402


def machine(lock_setup):
    return types.SimpleNamespace(current_setup="A", min_runs_left=3, min_runs_setup=lock_setup,
                                 dispatch_failed=0, family="F")


def lot_needing(setup):
    return types.SimpleNamespace(actual_step=types.SimpleNamespace(batch_max=1, setup_needed=setup))


def test_lock_defers_by_default_and_breaks_on_request():
    inst = types.SimpleNamespace(family_machines={"F": []}, usable_machines=set())
    lot = lot_needing("B")
    m = machine("A")
    assert fab_env.finalize_choice(inst, m, [lot])[1] is None             # upstream: defer
    assert m.dispatch_failed == 1
    m = machine("A")
    assert fab_env.finalize_choice(inst, m, [lot], break_lock=True)[1] == [lot]
    assert m.dispatch_failed == 0


def test_no_lock_means_no_deferral_either_way():
    inst = types.SimpleNamespace(family_machines={"F": []}, usable_machines=set())
    lot = lot_needing("A")                                                # same setup as the lock
    for brk in (False, True):
        m = machine("A")
        assert fab_env.finalize_choice(inst, m, [lot], break_lock=brk)[1] == [lot]


def test_deferral_budget_still_runs_out():
    inst = types.SimpleNamespace(family_machines={"F": []}, usable_machines=set())
    lot = lot_needing("B")
    m = machine("A")
    m.dispatch_failed = fab_env.MAX_DISPATCH_FAILED                       # budget spent: upstream dispatches
    assert fab_env.finalize_choice(inst, m, [lot])[1] == [lot]
