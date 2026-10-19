"""The tables and the quoted numbers of the paper, rendered from a results file of confirm_report.py and
nothing else.

Writes, in the Taylor & Francis Interact layout of the manuscript (as the archived final_tables.py: a `table` float
whose caption and tabular go through \\tbl{caption}{tabular}, \\label after it):

  policies.tex   Table 3 of the paper: completed lots per day, mean (SD), the scenarios side by side; each rule
                 next to the table fitted from its records and the gain over the rule (bold: more on every
                 seed; ** paired t p < 0.01; dagger: more than the remaining-time threshold at paired t p < 0.05),
                 then the remaining-time threshold tuned in the simulator, BC and PPO
  numbers.tex    one \\newcommand per number the text may quote: \\num<Scenario><policy><Quantity> and
                 \\num<Scenario><policyA><PolicyB><Quantity> for "A minus B" (e.g. \\numHVLMlearnerMbsPct),
                 followed by the macros the present text of paper/sections uses

and prints the same content as plain text.

  python confirm_tables.py                              # final/confirm/results.json -> paper/tables/
  python confirm_tables.py --results X.json --out DIR   # any other results file (an explicit --out is
                                                        # required for a development or unfinished one)
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
RESULTS = os.path.join(ROOT, "experiments", "smt2020", "final", "confirm", "results.json")
OUT = os.path.join(ROOT, "paper", "tables")
FABS = ("HVLM", "LVHM")
NA3 = r"\multicolumn{3}{c}{--}"
BLANK3 = r"\multicolumn{3}{c}{}"
HOLE = r"\textbf{??}"                 # a number the results file does not hold yet

# the policies of Table 1, grouped by where their levels come from; the heading of each group is printed
# as a row (edit the wording here)
GROUPS = (("Rules", ("default", "logging", "timeout", "mbs", "nach")),
          ("Threshold tuned in the simulator", ("clock",)),
          ("Trained in the simulator", ("bc", "ppo")),
          ("Table fitted from the records of", ("tbl_timeout", "tbl_mbs", "tbl_nach", "learner", "resid")))
# the names of the policies in the tables and figures (2026-10-15): no parameter values, which Table 2 of the
# paper holds, and the full-batch rule with 2% of its free decisions started at random under the name the
# paper defines once, "full batch with random starts"
SHORT_LABEL = {"default": "full batch", "logging": "full batch, random starts", "timeout": "timeout",
               "mbs": "minimum batch size", "nach": "NACH", "clock": "remaining-time threshold",
               "bc": "BC", "ppo": "PPO",
               "learner": "full batch, random starts", "resid": "the same, residual only",
               "tbl_timeout": "timeout", "tbl_mbs": "minimum batch size", "tbl_nach": "NACH"}
# row labels inside the last group: the rule whose records the table was fitted from
ROW = {"tbl_timeout": "timeout", "tbl_mbs": "minimum batch size", "tbl_nach": "NACH"}
TABLE1 = tuple(p for _, ps in GROUPS for p in ps)
RECORD_ROWS = ("timeout", "mbs", "nach", "default")
# macro tokens: \num<Scenario><token of A><Token of B><Quantity>
TOKEN = {"learner": "learner", "resid": "resid", "tbl_timeout": "tblTimeout", "tbl_mbs": "tblMbs",
         "tbl_nach": "tblNach", "logging": "logging", "clock": "clock", "mbs": "mbs", "timeout": "timeout",
         "nach": "nach", "default": "default", "bc": "bc", "ppo": "ppo", "sens": "sens"}


# ---------------------------------------------------------------- formats

def _z(s):
    """no negative zero: '-0.00' -> '0.00', '+0.00' stays"""
    return s[1:] if s.startswith("-") and float(s) == 0.0 else s


def num(x, nd=2):
    return HOLE if x is None else _z(f"{x:.{nd}f}")


def mnum(x, nd=2):
    """a number in math mode, so that a minus sign is a minus sign"""
    return HOLE if x is None else f"${_z(f'{x:.{nd}f}')}$"


def sgn(x, nd=2):
    """signed, in math mode: $+0.18$"""
    if x is None:
        return HOLE
    s = f"{x:+.{nd}f}"
    return f"${'+' + s[1:] if float(s) == 0.0 else s}$"


def ci(lo, hi, nd=2):
    return HOLE if lo is None or hi is None else rf"$[{_z(f'{lo:.{nd}f}')},\,{_z(f'{hi:.{nd}f}')}]$"


def pval(p):
    return HOLE if p is None else ("$<0.001$" if p < 0.001 else f"{p:.3f}")


def p_paired_t(c):
    """two-sided p of the paired t-test of a comparison, from its t statistic and n (the interval of the
    results file is from the same paired t distribution)"""
    if c is None or c.get("t") is None or not c.get("n") or c["n"] < 2:
        return None
    from scipy import stats
    return float(2 * stats.t.sf(abs(c["t"]), c["n"] - 1))


def stars(c):
    """significance marks of a paired difference: ** p < 0.01, * p < 0.05, paired t-test"""
    p = p_paired_t(c)
    return "" if p is None else ("**" if p < 0.01 else "*" if p < 0.05 else "")


def starred(s, c):
    """a rendered number with the marks of its comparison as a superscript, inside its math group if it has one"""
    st = stars(c)
    if not st:
        return s
    return s[:-1] + rf"^{{{st}}}$" if s.endswith("$") else s + rf"$^{{{st}}}$"


STARS_NOTE = r"$^{*}p < 0.05$, $^{**}p < 0.01$, paired $t$-test."


def tex(label):
    """a label of the results file as LaTeX"""
    return label.replace("%", r"\%").replace("$ h", "$~h").replace("$h = ", r"$\theta = ")


def cap(s):
    return s[0].upper() + s[1:]


def flip(c):
    """B - A from A - B"""
    if c is None:
        return None
    neg = lambda x: None if x is None else -x
    return dict(c, mean=neg(c["mean"]), lo=neg(c["hi"]), hi=neg(c["lo"]), wins=c["losses"], losses=c["wins"])


def diff_cells(c, n_full, notes):
    """paired difference: signed mean, its 95% interval, wins over the untied seeds"""
    if c is None or not c["n"] or c["mean"] is None:
        return NA3
    if c["mean"] == 0 and c["wins"] + c["losses"] == 0:
        return r"\multicolumn{3}{c}{identical}"
    wins = f"{c['wins']}/{c['wins'] + c['losses']}"
    if c["n"] < n_full:
        wins += notes.mark(f"Paired on {c['n']} of the {n_full} seeds.")
    return f"{sgn(c['mean'])} & {'--' if c['lo'] is None else ci(c['lo'], c['hi'])} & {wins}"


class Notes:
    """table footnotes: one letter per distinct text, in order of first use"""

    def __init__(self):
        self.texts = []

    def mark(self, text):
        if text not in self.texts:
            self.texts.append(text)
        return rf"\textsuperscript{{{chr(ord('a') + self.texts.index(text))}}}"

    def render(self, general=""):
        """the table's notes: a general note without a letter, then the lettered ones"""
        body = " ".join(([general] if general else [])
                        + [rf"\textsuperscript{{{chr(ord('a') + i)}}}{t}" for i, t in enumerate(self.texts)])
        return f"  \\tabnote{{{body}}}\n" if body else ""


def interact_table(caption, label, colspec, head, body, tabcolsep="4pt", notes="", comment=""):
    """a Taylor & Francis Interact table: \\tbl sets the caption above the tabular at the table's width
    and the tabular in the class's 8 pt table font; \\toprule, \\midrule and \\bottomrule are the class's"""
    return rf"""{comment}\begin{{table}}
  \tbl{{{caption}}}
  {{\setlength{{\tabcolsep}}{{{tabcolsep}}}%
  \begin{{tabular}}{{{colspec}}}
    \toprule
{head}
    \midrule
{body}
    \bottomrule
  \end{{tabular}}}}
{notes}  \label{{{label}}}
\end{{table}}
"""


def header(res, results_path):
    """comment lines that say where a generated file comes from"""
    m = res["meta"]
    try:
        src = os.path.relpath(results_path, ROOT)
    except ValueError:                      # another drive
        src = results_path
    if src.startswith(".."):                # outside the repository
        src = results_path
    lines = ["% generated by fabhybrid/smt2020/confirm_tables.py from " + src.replace("\\", "/"),
             f"% {m['mode']} results of {m['generated']}, seeds {m['seeds'][0]}-{m['seeds'][1]}, "
             f"{m['runs_present']} of {m['runs_expected']} runs; do not edit by hand"]
    if m["mode"] != "confirm":
        lines.append("% DEVELOPMENT RECORD (seeds 0-31, tables fitted at other prices): not the confirmatory block")
    if not m.get("finished", True):
        lines.append("% PARTIAL: the block had not finished when these numbers were computed")
    return "\n".join(lines) + "\n"


def n_seeds(res):
    return len(res["HVLM"]["seeds"])


# ---------------------------------------------------------------- Table 1: the policies

NETWORK_NOTE = ("For the network policies the scrapped lots are the total, and the under-full loads are counted "
                "over all 360 days of the run.")


def underfull(p, notes):
    """under-full loads started per day over the measured window; BC and PPO are run by eval_batch.py,
    which keeps only the count over the whole run"""
    if p["underfull_per_day"] is not None:
        return num(p["underfull_per_day"], 1)
    if p.get("underfull_per_day_run") is not None:
        return num(p["underfull_per_day_run"], 1) + notes.mark(NETWORK_NOTE)
    return "--"


def scrap_cells(p, notes):
    """lots scrapped per day while waiting for a furnace, and for any other tool; a run file without the
    location (BC, PPO) gives the total across both columns"""
    if p.get("scrapped_furnace") is not None and p.get("scrapped_other") is not None:
        return f"{num(p['scrapped_furnace'], 1)} & {num(p['scrapped_other'], 1)}"
    return rf"\multicolumn{{2}}{{c}}{{{num(p['scrapped'], 1)}{notes.mark(NETWORK_NOTE)}}}"


def policies_table(res, comment=""):
    """Table 3: each rule next to the table fitted from its records, the scenarios side by side, then the policies
    tuned or trained in the simulator. Bold: the table completes more lots than its rule on every seed. Gain: the
    paired difference as a percentage of the rule, with ** at paired t p < 0.01. Dagger: more lots than the control
    limit at paired t p < 0.05. The random-starts row prints no gain, so that the 5-10% of the rules' own records
    stays the headline (Section 5.2 states the comparison with the full-batch rule)."""
    N = n_seeds(res)
    pairs = [("timeout", "tbl_timeout"), ("mbs", "tbl_mbs"), ("nach", "tbl_nach"), None,
             ("default", None), ("logging", "learner")]

    def cells(fab, rule, table):
        P, C = res[fab]["policies"], res[fab]["comparisons"]
        p = P.get(rule)
        pol = f"{num(p['completed'])} ({num(p['sd'])})" if p and p["n"] else "--"
        if table is None:
            return [pol, "", ""]
        t, c, k = P.get(table), C.get(f"{table}-{rule}"), C.get(f"{table}-clock")
        mean = num(t["completed"])
        if c and c["n"] and c["wins"] == c["n"]:
            mean = rf"\textbf{{{mean}}}"
        pk = p_paired_t(k)
        dag = r"$^{\dagger}$" if pk is not None and pk < 0.05 and k["mean"] > 0 else r"\phantom{$^{\dagger}$}"
        gain = "" if rule == "logging" else starred(num(c["pct"], 1), c)
        return [pol, f"{mean}{dag} ({num(t['sd'])})", gain]

    rows = []
    for item in pairs:
        if item is None:
            rows.append(r"\addlinespace[3pt]")
            continue
        rule, table = item
        rows.append(" & ".join([SHORT_LABEL[rule]] + cells("HVLM", rule, table) + cells("LVHM", rule, table)) + r" \\")
    rows.append(r"\midrule")
    rows.append(r"\multicolumn{7}{@{}l}{\emph{Tuned or trained in the simulator}} \\")
    for ref in ("clock", "bc", "ppo"):
        rows.append(" & ".join([SHORT_LABEL[ref]] + cells("HVLM", ref, None) + cells("LVHM", ref, None)) + r" \\")
    body = "\n".join("    " + r for r in rows)
    head = r"""    & \multicolumn{3}{c}{HVLM} & \multicolumn{3}{c}{LVHM} \\
    \cmidrule(lr){2-4} \cmidrule(l){5-7}
    & Policy & Fitted table & Gain (\%) & Policy & Fitted table & Gain (\%) \\"""
    cap_ = rf"Completed lots per day, mean (SD) over the {N} seeds."
    note = (r"  \tabnote{Fitted table: the table fitted from the records of the policy in its row. Bold: more lots than "
            r"that policy on every seed. Paired $t$-test: $^{**}p < 0.01$ for the gain over that policy, "
            r"$^{\dagger}p < 0.05$ for more lots than the remaining-time threshold.}" + "\n")
    return interact_table(cap_, "tab:policies", r"@{}l ccc ccc@{}", head, body, "4pt", note, comment)


# ---------------------------------------------------------------- numbers.tex

class Macros:
    def __init__(self):
        self.lines, self.names = [], set()

    def add(self, name, value, note=""):
        assert re.fullmatch(r"[A-Za-z]+", name), f"not a TeX control word: {name}"
        assert name not in self.names, f"macro defined twice: {name}"
        self.names.add(name)
        self.lines.append(rf"\newcommand{{\{name}}}{{{value}}}" + (f"% {note}" if note else ""))

    def rem(self, text=""):
        self.lines.append(f"% {text}" if text else "%")


def _pct_abs(x, nd=0):
    return HOLE if x is None else f"{abs(x):.{nd}f}"


def systematic(res, M):
    N = n_seeds(res)
    m = res["meta"]
    M.rem("the block")
    M.add("numSeeds", str(N))
    M.add("numSeedFirst", str(m["seeds"][0]))
    M.add("numSeedLast", str(m["seeds"][1]))
    M.add("numWindowDays", f"{m['window_days']:g}")
    M.add("numMargin", f"{m['noninferiority_margin']:g}", "non-inferiority margin, completed lots per day")
    for fab in FABS:
        P, C, R, T = (res[fab][k] for k in ("policies", "comparisons", "records", "tables"))
        M.rem()
        M.rem(f"{fab}: policies (means over the seeds each policy has)")
        for k, p in P.items():
            t = f"num{fab}{TOKEN[k]}"
            uf = p["underfull_per_day"] if p["underfull_per_day"] is not None else p.get("underfull_per_day_run")
            M.add(t + "Completed", num(p["completed"]), p["label"])
            M.add(t + "Sd", num(p["sd"]))
            M.add(t + "Scrapped", num(p["scrapped"]))
            M.add(t + "ScrappedFurnace", num(p.get("scrapped_furnace"), 1), "scrapped per day while waiting for a batch tool")
            M.add(t + "ScrappedOther", num(p.get("scrapped_other"), 1), "scrapped per day while waiting for any other tool")
            M.add(t + "Underfull", num(uf, 1), "" if p["underfull_per_day"] is not None or uf is None
                  else "over all 360 days of the run (no window count in the run file)")
            M.add(t + "Cycle", num(p["cycle_p50_days"], 1))
            M.add(t + "N", str(p["n"]))
        M.rem()
        M.rem(f"{fab}: paired differences A - B in completed lots per day; Diff signed, Abs unsigned, Pct and PctOne "
              f"the difference as an unsigned percentage of B, WinsOf wins of A over the paired seeds")
        for key, c in C.items():
            a, b = key.split("-")
            t = f"num{fab}{TOKEN[a]}{cap(TOKEN[b])}"
            M.rem(f"{key}")
            M.add(t + "Diff", sgn(c["mean"]))
            M.add(t + "Abs", HOLE if c["mean"] is None else num(abs(c["mean"])))
            M.add(t + "Lo", mnum(c["lo"]))
            M.add(t + "Hi", mnum(c["hi"]))
            M.add(t + "CI", ci(c["lo"], c["hi"]))
            M.add(t + "Wins", str(c["wins"]))
            M.add(t + "Losses", str(c["losses"]))
            M.add(t + "Ties", str(c["ties"]))
            M.add(t + "N", str(c["n"]))
            M.add(t + "WinsOf", f"{c['wins']} of {c['n']}")
            M.add(t + "P", pval(c["p_sign"]), "exact two-sided sign test")
            if c.get("p_holm") is not None or any(key in fam for fam in m["holm_families"].values()):
                M.add(t + "PHolm", pval(c.get("p_holm")), "Holm within its family of three")
            M.add(t + "Pct", _pct_abs(c["pct"]))
            M.add(t + "PctOne", _pct_abs(c["pct"], 1))
            s = c.get("secondary", {})
            for name, q, nd in (("Scrapped", "scrapped", 2), ("Underfull", "underfull_per_day", 1), ("Cycle", "cycle_p50_days", 2)):
                x = s.get(q) or {}
                M.add(t + name + "Diff", sgn(x.get("mean"), nd))
                M.add(t + name + "CI", ci(x.get("lo"), x.get("hi"), nd))
                if q != "cycle_p50_days":
                    M.add(t + name + "Pct", _pct_abs(x.get("pct")))
        M.rem()
        M.rem(f"{fab}: the tables fitted from each set of records (Cells: cells holding each action at least n0 "
              f"times; ShareOwn: % of the records' free decisions in those cells; Agree: % of the free decisions "
              f"at which the table takes the learner's action; Differ: cells whose action differs from the learner's)")
        for key, r in R.items():
            t = f"num{fab}rec{cap(key)}"
            ag = r.get("agree_with_learner")
            M.add(t + "Cells", str(r["cells_both"]))
            M.add(t + "ShareOwn", num(100 * r["share_decisions_own"], 1))
            M.add(t + "Agree", HOLE if ag is None else num(100 * ag, 1))
            M.add(t + "AgreeInt", HOLE if ag is None else num(100 * ag, 0))
            M.add(t + "Differ", HOLE if r.get("cells_differ_learner") is None else str(r["cells_differ_learner"]))
        for k in ("learner", "resid", "sens"):
            if k not in T:
                continue
            t, lv = f"num{fab}{TOKEN[k]}", T[k]["level_h_by_arrival_bin"]
            ok = [x for x in lv if x is not None]
            if k == "resid":
                M.add(t + "Level", HOLE if lv[0] is None else f"{lv[0]:g}", "the residual-only table as a control limit, h")
            else:
                M.add(t + "LevelMin", f"{min(ok):g}" if ok else HOLE, "lowest level over the arrival bins, h")
                M.add(t + "LevelMax", f"{max(ok):g}" if ok else HOLE, "highest level over the arrival bins, h")
                M.add(t + "CellsAll", str(T[k]["cells"]))
                M.add(t + "AdjacentPairs", str(T[k]["adjacent_pairs"]), "comparisons of adjacent cells")
                M.add(t + "MonotoneViolations", str(T[k]["monotone_violations"]),
                      "adjacent pairs at which the start region is not closed downward in the residual or shrinks as the arrival moves later")
            M.add(t + "Price", HOLE if T[k].get("lam") is None else f"{T[k]['lam']:g}", "lots per empty slot-hour")


def prose(res, M):
    """The macros the text of paper/sections uses (the sections of 2026-10-03), from the same results. Each is
    one reading of the systematic numbers; when the text changes, change it here."""
    RULES = ("timeout", "mbs", "nach")

    def c(fab, key, field="mean", sec=None):
        x = res[fab]["comparisons"].get(key)
        x = (x or {}).get("secondary", {}).get(sec) if sec else x
        return None if not x else x.get(field)

    def rng(vals, nd=0):
        v = [x for x in vals if x is not None]
        return (HOLE, HOLE) if not v else (f"{min(v):.{nd}f}", f"{max(v):.{nd}f}")

    def pol(fab, k, field):
        return (res[fab]["policies"].get(k) or {}).get(field)

    # ---- abstract, contribution (3), conclusion, Section 5.3: a rule's own records against that rule
    own = [f"tbl_{k}-{k}" for k in RULES]
    lo, hi = rng([c(f, k, "pct") for f in FABS for k in own])
    M.add("recGainLo", lo, "gain of a rule's own-records table over the rule, %: lowest of the three rules on both scenarios")
    M.add("recGainHi", hi, "... highest")

    # ---- Section 5.2: the table fitted from the full-batch records (2% started) against the control limit, the residual-only table, the rules
    x = c("HVLM", "learner-clock")
    M.add("dClockH", HOLE if x is None else num(abs(x)), "table fitted from the full-batch records (2% started) - control limit, HVLM, unsigned")
    M.add("ciClockH", ci(c("HVLM", "learner-clock", "lo"), c("HVLM", "learner-clock", "hi")))
    x = c("LVHM", "learner-clock")
    M.add("dClockL", HOLE if x is None else num(abs(x)), "table from the full-batch records - control limit, LVHM, unsigned")
    M.add("ciClockL", ci(c("LVHM", "learner-clock", "lo"), c("LVHM", "learner-clock", "hi")))
    for f, t in (("HVLM", "H"), ("LVHM", "L")):
        M.add("dResidClock" + t, sgn(c(f, "resid-clock")), "residual-only table - control limit")
        M.add("ciResidClock" + t, ci(c(f, "resid-clock", "lo"), c(f, "resid-clock", "hi")))
    for f, t in (("HVLM", "H"), ("LVHM", "L")):
        x = c(f, "learner-resid")
        M.add("dResid" + t, HOLE if x is None else num(abs(x)), "table fitted from the full-batch records (2% started) - residual-only table, unsigned")
        M.add("ciResid" + t, ci(c(f, "learner-resid", "lo"), c(f, "learner-resid", "hi")))
    for f, t in (("HVLM", "H"), ("LVHM", "L")):
        ag = (res[f]["tables"].get("resid") or {}).get("agree_with_learner")
        M.add("residDiffer" + t, HOLE if ag is None else f"{100 * (1 - ag):.0f}",
              "free decisions at which the table fitted from the full-batch records (2% started) and the residual-only table take different actions, %")
    lo, hi = rng([c(f, f"learner-{k}", "pct") for f in FABS for k in RULES])
    M.add("pctRulesLo", lo, "table fitted from the full-batch records (2% started) over the three rules, %: lowest of both scenarios")
    M.add("pctRulesHi", hi, "... highest")
    w = [(c(f, f"learner-{k}", "wins"), c(f, f"learner-{k}", "n")) for f in FABS for k in RULES if c(f, f"learner-{k}", "n")]
    M.add("winsRulesMin", str(min(x for x, _ in w)) if w else HOLE, "fewest wins of the table fitted from the full-batch records over a rule, both scenarios")
    M.add("winsRulesEvery", "yes" if w and all(x == n for x, n in w) else "no",
          "whether the table fitted from the full-batch records completes more than each rule on every seed")
    # scrap location (policies run by batch_fire.py only: the default, the three rules, the control limit, the tables)
    loc = [pol(f, k, "scrapped_other") for f in FABS for k in TABLE1]
    loc = [x for x in loc if x is not None]
    M.add("scrElseLo", f"{min(loc):.0f}" if loc else HOLE,
          "lots scrapped per day at other tools than furnaces, over the policies of the policies table: the lowest")
    M.add("scrElseHi", f"{max(loc):.0f}" if loc else HOLE, "... the highest")
    for f, t in (("HVLM", "H"), ("LVHM", "L")):
        M.add("scrFurnDef" + t, num(pol(f, "default", "scrapped_furnace"), 1), "scrapped per day at furnaces, the full-batch rule")
        M.add("scrFurnLearn" + t, num(pol(f, "learner", "scrapped_furnace"), 1), "... the table fitted from the full-batch records (2% started)")
    lo, hi = rng([pol(f, k, "scrapped_furnace") for f in FABS for k in RULES], 1)
    M.add("scrFurnRulesLo", lo, "scrapped per day at furnaces under the three rules, lowest of both scenarios")
    M.add("scrFurnRulesHi", hi, "... highest")
    lo, hi = rng([pol(f, k, "underfull_per_day") for f in FABS for k in RULES])
    M.add("ufRulesLo", lo, "under-full loads per day of the three rules, lowest of both scenarios")
    M.add("ufRulesHi", hi, "... highest")
    TBL = tuple(f"tbl_{k}" for k in RULES)
    lo, hi = rng([pol(f, k, "underfull_per_day") for f in FABS for k in TBL])
    M.add("ufTblLo", lo, "under-full loads per day of the tables fitted from the three rules' records, lowest")
    M.add("ufTblHi", hi, "... highest")
    lo, hi = rng([pol(f, k, "scrapped_furnace") for f in FABS for k in TBL], 1)
    M.add("scrFurnTblLo", lo, "scrapped per day at furnaces under the tables fitted from the three rules' records, lowest")
    M.add("scrFurnTblHi", hi, "... highest")
    w = [(c(f, f"tbl_{k}-{k}", "wins"), c(f, f"tbl_{k}-{k}", "n")) for f in FABS for k in RULES if c(f, f"tbl_{k}-{k}", "n")]
    M.add("winsOwnMin", str(min(x for x, _ in w)) if w else HOLE, "fewest wins of a table over its own rule, the six cases")
    M.add("winsOwnEvery", "yes" if w and all(x == n for x, n in w) else "no",
          "whether each table completes more than its rule on every seed (the text says so)")
    # the six cases, table against its own rule, as relative quantities (Section 5.2 quotes these instead of
    # reading the cells of the policies table aloud)
    red = [100 * (1 - pol(f, f"tbl_{k}", "scrapped_furnace") / pol(f, k, "scrapped_furnace"))
           for f in FABS for k in RULES
           if pol(f, f"tbl_{k}", "scrapped_furnace") is not None and pol(f, k, "scrapped_furnace")]
    M.add("scrFurnRedLo", f"{min(red):.0f}" if red else HOLE,
          "reduction of the lots scrapped per day at furnaces, a table against its own rule, %: lowest of the six cases")
    M.add("scrFurnRedHi", f"{max(red):.0f}" if red else HOLE, "... highest")
    tot = [100 * (1 - pol(f, f"tbl_{k}", "scrapped") / pol(f, k, "scrapped"))
           for f in FABS for k in RULES
           if pol(f, f"tbl_{k}", "scrapped") is not None and pol(f, k, "scrapped")]
    M.add("scrTotRedLo", f"{min(tot):.0f}" if tot else HOLE,
          "reduction of the lots scrapped per day in all, a table against its own rule, %: lowest of the six cases")
    M.add("scrTotRedHi", f"{max(tot):.0f}" if tot else HOLE, "... highest")
    ratio = [pol(f, k, "underfull_per_day") / pol(f, f"tbl_{k}", "underfull_per_day")
             for f in FABS for k in RULES
             if pol(f, k, "underfull_per_day") is not None and pol(f, f"tbl_{k}", "underfull_per_day")]
    M.add("ufRatioLo", f"{min(ratio):.0f}" if ratio else HOLE,
          "under-full loads per day of a rule over those of its own table: lowest of the six cases")
    M.add("ufRatioHi", f"{max(ratio):.0f}" if ratio else HOLE, "... highest")
    cyc = [abs(pol(f, f"tbl_{k}", "cycle_p50_days") - pol(f, k, "cycle_p50_days")) for f in FABS for k in RULES
           if pol(f, f"tbl_{k}", "cycle_p50_days") is not None and pol(f, k, "cycle_p50_days") is not None]
    M.add("cycleDiffMax", f"{max(cyc):.1f}" if cyc else HOLE,
          "largest change of the median cycle time, a table against its own rule, days, the six cases")

    # ---- Section 5.3: the tables fitted from the rules' records
    ag = [100 * res[f]["records"][k]["agree_with_learner"] for f in FABS for k in ("timeout", "mbs")
          if k in res[f]["records"] and res[f]["records"][k].get("agree_with_learner") is not None]
    lo, hi = rng(ag, 1)
    M.add("agreeLo", lo, "free decisions at which the timeout and minimum-batch tables take the action of the table fitted from the full-batch records (2% started), %")
    M.add("agreeHi", hi)
    d = [c(f, f"tbl_{k}-clock") for f in FABS for k in ("timeout", "mbs")]
    d = [x for x in d if x is not None]
    M.add("dRecClockLo", num(min(d)) if d else HOLE,
          "timeout and minimum-batch tables - control limit, lowest of the four (signed value without sign if positive)")
    M.add("dRecClockHi", num(max(d)) if d else HOLE, "... highest")
    M.add("recClockAllMore", "yes" if d and min(d) > 0 else "no", "whether all four are positive (the text says 'more')")
    for f, t in (("HVLM", "H"), ("LVHM", "L")):
        M.add("dNachClock" + t, sgn(c(f, "tbl_nach-clock")), "table from NACH's records - control limit")
        M.add("ciNachClock" + t, ci(c(f, "tbl_nach-clock", "lo"), c(f, "tbl_nach-clock", "hi")))
        x = c(f, "tbl_nach-clock")
        M.add("dNachClockAbs" + t, HOLE if x is None else num(abs(x)), "... unsigned (the text says fewer/more)")
        x = c(f, "resid-clock")
        M.add("dResidClockAbs" + t, HOLE if x is None else num(abs(x)), "residual-only table - control limit, unsigned")
    d = [c(f, f"tbl_{k}-learner") for f in FABS for k in ("timeout", "mbs")]
    d = [x for x in d if x is not None]
    M.add("dRecLearnLo", sgn(min(d)) if d else HOLE, "timeout and minimum-batch tables - the table fitted from the full-batch records, lowest of the four")
    M.add("dRecLearnHi", sgn(max(d)) if d else HOLE, "... highest")


def numbers(res, comment="", with_prose=True):
    M = Macros()
    systematic(res, M)
    if with_prose:
        M.rem()
        M.rem("the macros of the present text (paper/sections), read from the numbers above")
        prose(res, M)
    return comment + "\n".join(M.lines) + "\n", M


# ---------------------------------------------------------------- plain text

def text_summary(res):
    out, N = [], n_seeds(res)
    m = res["meta"]
    out.append(f"{m['mode']} results of {m['generated']}: seeds {m['seeds'][0]}-{m['seeds'][1]}, "
               f"{m['runs_present']} of {m['runs_expected']} runs" + ("" if m.get("finished", True) else "  [NOT FINISHED]"))
    for d in m.get("deviations", []):
        out.append("  deviation: " + d)
    f = lambda x, s="{:.2f}": "--" if x is None else s.format(x)
    pv = lambda x: "--" if x is None else (f"{x:.3f}" if x >= 0.001 else f"{x:.1e}")
    for fab in FABS:
        P, C, R = res[fab]["policies"], res[fab]["comparisons"], res[fab]["records"]
        out.append(f"\n{fab}  policies table")
        out.append(f"  {'policy':36s} {'n':>3s} {'compl':>6s} {'scrap':>6s} {'under':>6s} {'cycle':>5s} | {'learner - policy':>24s} {'wins':>6s} {'sign p':>7s}")
        for heading, names in GROUPS:
            out.append(f"  [{heading}]")
            for k in names:
                p, c = P.get(k), C.get(f"learner-{k}")
                if p is None:
                    continue
                uf, run = p["underfull_per_day"], p.get("underfull_per_day_run")
                ufs = f(uf, "{:.1f}") if uf is not None or run is None else f(run, "{:.1f}") + "*"
                line = (f"  {p['label'].replace('$', ''):36s} {p['n']:3d} {f(p['completed']):>6s} {f(p['scrapped']):>6s} "
                        f"{ufs:>6s} {f(p['cycle_p50_days'], '{:.1f}'):>5s} | ")
                if c and c["n"] and k != "learner":
                    cis = "" if c["lo"] is None else f"[{c['lo']:.2f}, {c['hi']:.2f}]"
                    line += (f"{c['mean']:+6.2f} {cis:>17s} {c['wins']:>3d}/{c['wins'] + c['losses']:<2d} {pv(c['p_sign']):>7s}"
                             + (f"  Holm {pv(c['p_holm'])}" if c.get("p_holm") is not None else "")
                             + (f"  (n {c['n']})" if c["n"] < N else ""))
                out.append(line)
        out.append("  (* under-full loads per day over all 360 days: BC and PPO have no window count)")
        out.append(f"{fab}  records table (the last row is printed against the policy that made its records)")
        out.append(f"  {'records of':30s} {'rule':>6s} {'table':>6s} {'gain%':>6s} {'table - rule':>26s} {'wins':>6s} {'cells':>6s} {'same%':>6s}")
        for key in RECORD_ROWS:
            r = R.get(key)
            if r is None:
                continue
            rule, table, c = P.get(r["rule"]), P.get(r["table"]), C.get(r["comparison"]) or {}
            ag = r.get("agree_with_learner")
            cis = "" if c.get("lo") is None else f"[{c['lo']:.2f}, {c['hi']:.2f}]"
            wins = f"{c['wins']}/{c['wins'] + c['losses']}" if c.get("n") else "--"
            same = "--" if key == "default" or ag is None else f"{100 * ag:.1f}"
            name = rule["label"].replace("$", "")
            out.append(f"  {name:30s} {f(rule['completed']):>6s} {f(table['completed']):>6s} "
                       f"{f(c.get('pct'), '{:.1f}'):>6s} {f(c.get('mean'), '{:+.2f}'):>7s} {cis:>18s} "
                       f"{wins:>6s} {r['cells_both']:>3d}/{r['cells']:<2d} {same:>6s}")
        out.append(f"{fab}  other paired differences (A - B, completed lots per day)")
        for key, c in C.items():
            if key.startswith("learner-") and key.split("-")[1] in TABLE1 or key in [R[k]["comparison"] for k in R]:
                continue
            cis = "" if c["lo"] is None else f"[{c['lo']:.2f}, {c['hi']:.2f}]"
            out.append(f"  {key:22s} n {c['n']:2d} {f(c['mean'], '{:+.2f}'):>6s} {cis:>17s} {c['wins']:>3d}/{c['wins'] + c['losses']:<2d} "
                       f"p {pv(c['p_sign'])}")
        cl = res[fab].get("claims")
        if cl:
            c2 = cl["C2"]
            out.append(f"{fab}  claims (PROTOCOL_confirm.md): "
                       f"C1 {', '.join(k.split('-')[1] + ' ' + str(v['holds']) for k, v in cl['C1'].items())}; "
                       f"C2 non-inferior {c2['noninferior']} (lower end {f(c2['lo'], '{:+.2f}')} against -{c2['margin']}), "
                       f"at least as many {c2['at_least_as_many']}, more {c2['more']}, control limit more {c2['control_limit_more']}; "
                       f"C3 {', '.join(k.split('-')[1] + ' ' + str(v['holds']) for k, v in cl['C3'].items())}; "
                       f"C4 {cl['C4']['learner-resid']['holds']}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--results", default=RESULTS, help="a results file of confirm_report.py")
    ap.add_argument("--out", default=None, help="directory for policies.tex and numbers.tex (default: paper/tables)")
    ap.add_argument("--no-prose-macros", action="store_true", help="numbers.tex without the macros of the present text")
    a = ap.parse_args()
    if not os.path.exists(a.results):
        sys.exit(f"no results file {a.results}: run confirm_report.py first (while the block runs it writes "
                 f"results_partial.json, which is rendered with --results and --out)")
    with open(a.results, encoding="utf-8") as f:
        res = json.load(f)
    m = res["meta"]
    if a.out is None and not (m["mode"] == "confirm" and m.get("block", True) and m.get("finished", True)):
        what = ("the development record" if m["mode"] != "confirm" else
                "an unfinished block" if m.get("block", True) else "runs from another directory")
        sys.exit(f"{a.results} holds {what}; name the directory with --out to render it "
                 f"(paper/tables is written only from the finished block)")
    out = a.out or OUT
    os.makedirs(out, exist_ok=True)
    comment = header(res, os.path.abspath(a.results))
    ntext, M = numbers(res, comment, not a.no_prose_macros)
    files = {"policies.tex": policies_table(res, comment), "numbers.tex": ntext}
    print(text_summary(res))
    print()
    for name, text in files.items():
        p = os.path.join(out, name)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote", p + (f"  ({len(M.names)} macros)" if name == "numbers.tex" else ""))


if __name__ == "__main__":
    main()
