"""Simulator wiring: SMT2020 through the upstream PySCFabSim, built at t=0.

Provenance matters here, so it is spelled out. The benchmark is SMT2020 (Kopp,
Hassoun, Kalir, Moench, IEEE TSM 2020); the simulator is PySCFabSim
(`external/PySCFabSim-release`), whose datasets/ directory holds the SMT2020
files byte-for-byte. We used to load a different repo's fork of that simulator
and, worse, its shipped `365days_HVLM.pkl` -- a fab that had already been run
for a year by one dispatching rule. That artifact was not a neutral start:

    WIP.txt as shipped ............  2,255 lots, cycle time 39 d (design point)
    + 365 d under that rule .......  3,549 lots, 62 d,  33% of WIP past due
    + 232 d under net+hold ........  5,391 lots, 94 d,  58% of WIP past due

Every evaluation done on top of that inherited the second row's damage, and
every policy compared there was measured on a state some other policy made.
So this module builds the instance the way the simulator's own reproduction
script does -- `FileInstance` over the dataset files, t=0, the shipped initial
WIP -- and the pickle is gone.

The upstream protocol, from `greedy_runner.py` and `simulation/stats.py`:
730 simulated days per run, seeds 0-9, statistics over every completed lot
(no warm-up truncation -- 730 days is ~18 cycle times, and each policy runs
its own). Reported per product: average cycle time, throughput, on-time
percentage, tardiness, plus per-family machine utilisation. The reference
values a correct run should land near ship in `datasets/lots_SMT2020_*.txt`.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
SIM = os.path.join(PROJECT_ROOT, "external", "PySCFabSim-release")
DATASETS = os.path.join(SIM, "datasets")
for _p in (SIM, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from simulation.classes import Lot as _Lot  # noqa: E402,F401
from simulation.dispatching.dispatcher import Dispatchers, dispatcher_map  # noqa: E402,F401
from simulation.file_instance import FileInstance  # noqa: E402
from simulation.greedy import build_batch  # noqa: E402,F401
from simulation.instance import Instance as _Instance  # noqa: E402
from simulation.events import ReleaseEvent as _ReleaseEvent  # noqa: E402
from simulation.randomizer import Randomizer  # noqa: E402
from simulation.read import read_all  # noqa: E402

SECONDS_PER_DAY = 3600 * 24
BENCH_DAYS = 730                     # upstream greedy_runner.py: 365 * 2
BENCH_SEEDS = tuple(range(10))       # upstream greedy_runner.py: seeds 0..9

# Reference values the benchmark ships for HVLM, per product:
# (throughput, average cycle time in days, on-time percentage).
REFERENCE = {
    "HVLM": {"Lot_3": (18914.60, 51.21, 91.19), "Lot_4": (19577.20, 28.38, 90.20),
             "HotLot_3": (499.45, 31.73, 90.83), "HotLot_4": (508.60, 18.46, 89.54)},
}


def _next_step_guarded(self):
    """Stock next_step indexes dispatchable_lots[0] unconditionally, so a run
    that outlives the pending-release supply dies with IndexError while lots
    are still in flight. Same logic with the empty cases handled; patched here
    because external/ is untracked."""
    process_until = []
    if len(self.events.arr) > 0:
        process_until.append(max(0, self.events.first.timestamp))
    if len(self.dispatchable_lots) > 0:
        process_until.append(max(0, self.dispatchable_lots[0].release_at))
    if not process_until:
        raise RuntimeError("simulation starved: no events and no pending releases")
    process_until = min(process_until)
    while len(self.events.arr) > 0 and self.events.first.timestamp <= process_until:
        ev = self.events.pop_first()
        self.current_time = max(0, ev.timestamp, self.current_time)
        ev.handle(self)
    _ReleaseEvent.handle(self, process_until)


_Instance.next_step = _next_step_guarded

_FILES = {}


def dataset_files(dataset):
    """Parsed dataset tables. Re-read per instance: FileInstance builds its own
    machines/lots but the parsed rows are shared, and a cached instance would
    hand two simulations the same objects."""
    key = dataset
    if key not in _FILES:
        _FILES[key] = os.path.join(DATASETS, f"SMT2020_{dataset}")
    return read_all(_FILES[key])


def new_instance(dataset="HVLM", seed=0, days=BENCH_DAYS, plugins=None,
                 lot_for_machine=False):
    """A fresh benchmark instance at t=0 with the shipped initial WIP.

    Seeding happens here because the Randomizer is a process-global singleton
    the simulator draws every breakdown, PM and processing time from; the seed
    is the only thing that differs between replications.

    `lot_for_machine` picks the simulator's decision manager. False gives the
    machine-for-lot manager, which maintains one global `usable_lots` set --
    the flat "which lot moves next" formulation our policy acts on. True is
    the per-machine formulation the shipped FIFO/CR baselines run under
    (`greedy_runner.py --alg l4m`), so baselines are built with True.
    """
    Randomizer().random.seed(seed)
    return FileInstance(dataset_files(dataset), SECONDS_PER_DAY * days,
                        lot_for_machine, list(plugins or []))


def _instance(dataset="HVLM", seed=0, days=BENCH_DAYS):
    """Back-compatible alias. NOTE: this used to return a 365-day pre-warmed
    pickle; it now returns the benchmark's own t=0 state. Anything that assumed
    a warmed fab needs to run its own warm-up."""
    return new_instance(dataset, seed=seed, days=days)


def tool_groups(instance):
    """Stable tool-group vocabulary for the policy's embedding."""
    return sorted(set(m.group if not m.group.startswith("Delay_") else "Delay"
                      for m in instance.machines))


def compute_features(lots, instance, current_time, tg_index):
    """The 12 per-lot features the benchmark's own dispatchers and gym wrapper
    are built on, plus the tool-group index."""
    n = len(lots)
    feats = np.zeros((n, 12), dtype=np.float32)
    tg = np.zeros((n,), dtype=np.int64)
    setups = instance.setups
    for k, lot in enumerate(lots):
        step = lot.actual_step
        feats[k, 0] = (lot.full_time - lot.remaining_time) / lot.full_time
        feats[k, 1] = lot.deadline_at - current_time
        feats[k, 2] = lot.waiting_time
        feats[k, 3] = current_time - lot.free_since
        feats[k, 4] = len(lot.dedications)
        feats[k, 5] = lot.priority
        feats[k, 6] = lot.remaining_time
        min_setup, tmp_nb = float("inf"), 0
        if step.setup_needed != "":
            for m in lot.waiting_machines:
                if m.current_setup != step.setup_needed:
                    if step.setup_time is not None:
                        min_setup = min(min_setup, step.setup_time)
                    elif (m.current_setup, step.setup_needed) in setups:
                        min_setup = min(min_setup, setups[(m.current_setup, step.setup_needed)])
                    elif ("", step.setup_needed) in setups:
                        min_setup = min(min_setup, setups[("", step.setup_needed)])
                    else:
                        min_setup = 0
                else:
                    tmp_nb += 1
                    min_setup = 0
        else:
            min_setup, tmp_nb = 0, len(lot.waiting_machines)
        feats[k, 7] = 0.0 if min_setup == float("inf") else min_setup
        feats[k, 8] = step.processing_time.avg()
        feats[k, 9] = tmp_nb
        feats[k, 10] = step.batch_min
        feats[k, 11] = step.batch_max
        g = lot.waiting_machines[0].group
        tg[k] = tg_index["Delay" if g.startswith("Delay_") else g]
    return torch.from_numpy(feats), torch.from_numpy(tg)
