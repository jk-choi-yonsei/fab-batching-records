# Facts the manuscript quotes that no run of the block produces

Everything here is computed from the logged decisions, from fits, or from runs that already exist; no new simulation is run.

| File | What it gives | Quoted in |
|---|---|---|
| `rule_tables.py` → `rule_tables/*.json`, `rule_tables_summary.json` | For each set of records (timeout, minimum batch size, NACH as they stand; full batch with 2% of the free decisions started): the facts of the records (free decisions, share started, next lot within 15 min, none announced, tightest lot in the chosen load) and the fitted table refitted over the price (0.0005 to 0.02), the discount (0.8, 0.95, 0.99 per hour) and n0 (1, 3, 30). The timeout and minimum-batch-size tables are the same at 0.003 and 0.004, change in at most two cells from 0.001 to 0.0075 and in at most five from 0.0005 to 0.02; in at most one cell over the discounts and n0. | Table 1 and Section 5.1.2 (records), Section 5.3 and Table 4 (settings) |
| `levels_vs_scope.py` → `levels_vs_scope.json`, `.txt` | Development seeds 0-31, paired: the remaining-time threshold (the threshold, `clock`, in the code) at each level of its grid against each rule, and the table fitted from a rule's records against that rule and against the threshold at 0.5, 1.5 and 3 h. A control limit at 0.5 h completes +0.07 [-0.16, +0.30] lots per day over the timeout rule on HVLM and +0.57 on LVHM; the table from the timeout rule's records +1.67 and +1.92. | The argument of Section 5.2 that the gain depends on the levels (the manuscript quotes the selection seeds for the grid) |
| `rec_facts.py` → `rec_facts.json` | The same record facts for the full-batch records, with decision instants per day. | (superseded in the text by `rule_tables_summary.json`) |
| `refit.py` → `refit/*.json`, `refit_summary.json` | The table fitted from the full-batch records refitted over the discount and n0: the same for every discount from 0.8 to 0.99; at most one cell (HVLM) and two cells (LVHM) for n0 from 1 to 30. | not quoted |

Related facts kept elsewhere:

- Price grid of the table fitted from the full-batch records (0.0005 to 0.02): `../betarx/grid_summary.json`.
- Completions of each rule and of the threshold over their parameter grids on the selection seeds 108 to 115: `../selection.json` (the range of the threshold and the timeout rule's completions quoted in Section 5.2).
- Instances of the isolated station: `../../theory/announced.json` and `announced_kappa0p1_*.json` (720 instances; 3,861 of 28,800 cells mixed).

| `testbed_facts.py` → `testbed_facts.json` | Table 1's testbed rows (tools and families without the Delay placeholder, furnaces, load capacity, run duration, lots released per day at 0.98 of the testbed's rate, the queue-time constraints and those ending at a furnace step with their limits) and the run cost kappa at beta = 0.003 over the constrained furnace steps (0.078 to 0.136), from the data files in the simulator submodule. Added 2026-10-10; before it these numbers had no generator. | Table 1, Appendix A.3 (kappa) |
