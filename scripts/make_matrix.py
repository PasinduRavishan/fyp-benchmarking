"""Render results.csv as MATRIX.md — a per-cell grid that mirrors the team's
benchmarking matrix doc, one block per (method, dataset) with both metric
variants side by side and the published reference values where known.

Usage: python3 scripts/make_matrix.py   (from repo root; rewrites MATRIX.md)
"""

import csv
from collections import defaultdict

METRICS = ["SM", "ICP", "IFN", "NED", "BCP", "CHM", "CHD"]
ARROWS = {"SM": "↑", "ICP": "↓", "IFN": "↓", "NED": "↑",
          "BCP": "↓", "CHM": "↑", "CHD": "↑"}


def main():
    cells = defaultdict(list)
    with open("results.csv", newline="") as f:
        for row in csv.DictReader(f):
            cells[(row["method"], row["dataset"])].append(row)

    out = ["# Benchmarking Matrix (generated from results.csv — do not edit)",
           "",
           "Values are means over 10 stock runs (protocol in runs/). "
           "`canonical` = our metric definitions (directed SM, interface-count IFN, "
           "fixed-bounds NED); `chgnn-repo` = the released metric.py variants "
           "(undirected SM, cross-edge IFN, relative NED). Copy the variant your "
           "matrix column expects — the published numbers in each paper may mix "
           "variants (see runs/ notes).",
           ""]

    for (method, dataset), rows in sorted(cells.items()):
        commit = rows[0]["dataset_commit"]
        out.append(f"## {method} × {dataset}")
        out.append(f"*dataset commit: `{commit}` · date: {rows[0]['date']}*")
        out.append("")
        header = "| metric | " + " | ".join(r["metric_variant"] for r in rows) + " | published |"
        out.append(header)
        out.append("|" + "---|" * (len(rows) + 2))
        for m in METRICS:
            vals = [r.get(m, "") or "—" for r in rows]
            pub = rows[0].get(f"published_{m}", "") or "—"
            out.append(f"| {m} {ARROWS[m]} | " + " | ".join(vals) + f" | {pub} |")
        out.append("")
        for r in rows:
            if r["notes"]:
                out.append(f"- *{r['metric_variant']}*: {r['notes']}")
        out.append("")

    with open("MATRIX.md", "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"MATRIX.md: {len(cells)} cells")


if __name__ == "__main__":
    main()
