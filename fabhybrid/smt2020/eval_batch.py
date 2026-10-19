"""Score a learned batch policy the way batch_fire scores an arm: greedy, from
the benchmark's own t=0 state, over --days with the back half measured, in the
scrap game, writing the same JSON block so bf_report.py (archive/2026-10-closed-lines/stage-b-report) reads it as an arm
named rl:<weights file>. Nothing about the dataset or release scale is baked
into the policy, so the same weights run on either fab at any load.

  python eval_batch.py --weights ../../experiments/smt2020/runs/batch/weights_best.pt \
      --dataset LVHM --scale 0.98 --days 180 --seed 0 --out ../../experiments/smt2020/batch_fire_scrap
"""
import argparse
import json
import os
import time

import numpy as np
import torch

from fab_env import FabEnv                 # puts the simulator on sys.path; scenarios needs it
from rl_env import SECONDS_PER_DAY as SPD
import scenarios
from train_batch import BatchPolicy, n_tools_of, RUNS
from train_l1 import Norm, global_vec, row_feats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--norm", default=os.path.join(RUNS, "norm.json"))
    ap.add_argument("--dataset", default="HVLM")
    ap.add_argument("--scale", type=float, default=0.98)
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--measure-from", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--cqt-rule", default="none",
                    help="sequencing rule to compose with; the paper's base is qtcr. "
                         "Was silently dropped before 2026-09-09, so every learned "
                         "number on record was measured against cqt_rule=none.")
    ap.add_argument("--warm-arm", default=None,
                    help="hand over at --measure-from: this arm (e.g. clock:1) drives the warm-up, the policy "
                         "drives the measured window. The snapshot-trained policies were only ever shown a "
                         "running fab, and from a cold start they defer until the fab stops; this scores them "
                         "the way they were trained. Reported ALONGSIDE the cold-start number, never instead "
                         "of it -- no other arm gets a warmed start.")
    ap.add_argument("--tag", default=None, help="name for the report (default: weights file stem)")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    torch.set_num_threads(1)
    t_wall = time.time()
    horizon = int(a.days * max(1.0, a.scale)) + 2
    env = FabEnv(dataset=a.dataset, seed=a.seed, episode_days=a.days, horizon_days=horizon,
                 rule="cr", cqt_rule=a.cqt_rule, scrap=True, reward="yield",
                 batch_only=True)
    obs = env.reset(seed=a.seed)
    if a.scale < 1.0:
        scenarios.scale_release(env.instance, a.scale); env.rebuild_deadlines()
    elif a.scale > 1.0:
        scenarios.compress_release(env.instance, a.scale); env.rebuild_deadlines()
    norm = Norm(a.norm)
    policy = BatchPolicy(n_tools_of(a.dataset), n_g=len(norm.gmu))
    policy.load_compat(torch.load(a.weights, map_location="cpu", weights_only=True))
    policy.eval()
    inst, t0 = env.instance, env.t0
    fired_sizes, fired_max, n_partial, n_dec = [], [], 0, 0
    wip_trace, nxt = [], t0 + 10 * SPD
    warm_kind = warm_coef = None
    if a.warm_arm:
        import batch_fire
        warm_kind, warm_coef = batch_fire.parse_arm(a.warm_arm)
    t_hand = t0 + a.measure_from * a.days * SPD
    with torch.no_grad():
        while obs is not None:
            if warm_kind is not None and inst.current_time < t_hand:
                import batch_fire
                act = batch_fire.choose(env, warm_kind, warm_coef)
                n_dec += 1
                if act < len(env._groups):
                    g = env._groups[act]; bm = g[0].actual_step.batch_max
                    if bm > 1:
                        fired_sizes.append(min(len(g), bm)); fired_max.append(bm)
                        if len(g) < bm:
                            n_partial += 1
                obs, _, done, _ = env.step(act)
                if inst.current_time >= nxt or done:
                    wip_trace.append({"day": round((inst.current_time - t0) / SPD, 1),
                                      "wip": len(inst.active_lots), "done": len(inst.done_lots)})
                    nxt = inst.current_time + 10 * SPD
                if done:
                    break
                continue
            f, tg = row_feats(obs)
            logits, _ = policy.heads(torch.from_numpy(norm.lots(f)), tg,
                                     torch.from_numpy(norm.glob(global_vec(env, norm.time_inputs)).astype(np.float32)))
            act = int(torch.argmax(logits))
            n_dec += 1
            if act < len(env._groups):
                g = env._groups[act]; bm = g[0].actual_step.batch_max
                if bm > 1:
                    fired_sizes.append(min(len(g), bm)); fired_max.append(bm)
                    if len(g) < bm:
                        n_partial += 1
            obs, _, done, _ = env.step(act)
            if inst.current_time >= nxt or done:
                wip_trace.append({"day": round((inst.current_time - t0) / SPD, 1),
                                  "wip": len(inst.active_lots), "done": len(inst.done_lots)})
                nxt = inst.current_time + 10 * SPD
            if done:
                break
    t_meas = t0 + a.measure_from * a.days * SPD
    t_stop = min(inst.current_time, t0 + a.days * SPD)
    win = max(1e-9, (t_stop - t_meas) / SPD)
    in_win = lambda t: t is not None and t_meas <= t < t_stop
    done_w = [l for l in inst.done_lots if in_win(l.done_at)]
    scr_w = [l for l in env.cqt.scrapped if in_win(getattr(l, "scrapped_at", None))]
    ontime_w = [l for l in done_w if l.done_at <= l.deadline_at]
    cyc = sorted((l.done_at - l.release_at) / SPD for l in done_w)
    d = np.array([r["day"] for r in wip_trace]); w = np.array([r["wip"] for r in wip_trace], float)
    half = d >= a.measure_from * a.days
    tag = a.tag or os.path.splitext(os.path.basename(a.weights))[0]
    out = {
        "arm": f"rl:{tag}", "weights": a.weights, "dataset": a.dataset, "scale": a.scale, "seed": a.seed,
        "days": a.days, "base": "cr", "cqt_rule": a.cqt_rule, "scrap": True, "minrun_break_h": 0.0,
        "scrap_kpi": {
            "completed_per_day": round(len(done_w) / win, 2),
            "scrapped_per_day": round(len(scr_w) / win, 2),
            "on_time_pct_of_completed": round(100.0 * len(ontime_w) / max(1, len(done_w)), 2),
            "on_time_pct_of_completed_plus_scrapped": round(100.0 * len(ontime_w) / max(1, len(done_w) + len(scr_w)), 2),
            "cycle_p50_days": round(cyc[len(cyc) // 2], 2) if cyc else None,
            "scrapped_total": len(env.cqt.scrapped)},
        "warmup_days": round(a.measure_from * a.days, 1), "wall_s": round(time.time() - t_wall, 1),
        "batch_fill": round(float(np.sum(fired_sizes) / np.sum(fired_max)), 4) if fired_sizes else None,
        "batches_fired": len(fired_sizes), "batches_partial": n_partial, "policy_decisions": n_dec,
        "wip_end": int(w[-1]) if len(w) else None,
        "wip_slope_back_half": float(np.polyfit(d[half], w[half], 1)[0]) if half.sum() > 3 else None,
        "released_per_day": (len(inst.done_lots) + len(inst.active_lots) + len(env.cqt.scrapped)) / a.days,
        "env_stats": dict(env.stats), "trace": wip_trace,
    }
    os.makedirs(a.out, exist_ok=True)
    out["warm_arm"] = a.warm_arm
    suffix = "" if a.cqt_rule == "none" else f"_{a.cqt_rule}"
    if a.warm_arm:
        suffix = "_warm" + a.warm_arm.replace(":", "") + suffix
    path = os.path.join(a.out, f"batch_fire_{a.dataset}_r{a.scale}_d{a.days}_s{a.seed}_rl-{tag}{suffix}_scrap.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=float)
    print(json.dumps({k: v for k, v in out.items() if k != "trace"}, default=float))
    print("wrote", path)


if __name__ == "__main__":
    main()
