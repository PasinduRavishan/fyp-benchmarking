# CHGNN × DayTrader + PlantsByWebSphere (authors' bundled inputs, 10 runs each)

**Date:** 2026-07-13 · **Runner:** Pasindu Ravishan · **Tool:** `tools/chgnn` @ `f94803e`
**Protocol:** identical to `runs/chgnn_acme_reproducibility.md` — 10 × stock
`Graph.py --model=AE_EGCN_Separate --data={pbw|dayTrader} --code=with_edge_loss`,
scored with `metrics/` in both variants. Inputs are the **authors' bundled**
datasets (their static analysis, their seeds; dayTrader: 6 clusters, pbw: 5).
Raw logs/partitions/result files in `runs/chgnn_{pbw,dayTrader}_repro/`.

## Summary (means, n=10)

| dataset | variant | SM | ICP | IFN | NED | BCP |
|---------|---------|-----|-----|-----|-----|-----|
| pbw | canonical | 0.1625 | 0.5052 | 3.88 | 0.869 | 2.5881 |
| pbw | chgnn-repo | 0.2674 | — | 10.26 | 0.858 | — |
| dayTrader | canonical | 0.0883 | 0.5636 | 5.53 | 0.507 | 4.4972 |
| dayTrader | chgnn-repo | 0.1632 | — | 25.05 | 0.555 | — |

Stdevs: pbw SM ±0.019/±0.020, dayTrader SM ±0.008/±0.011; full stats in the
analysis output. CHM/CHD are N/A for both (bundled data has method names but
no parameter/return types). BCP use case = entrypoint labels parsed from the
bundled callgraph.dot (pbw: 75 labeled classes, dayTrader: 176).

## Comparison with the authors' own recorded runs (dayTrader)

`custom/results.txt` in the bundled dayTrader folder records 5 of the authors'
own with_edge_loss runs:

| metric (authors' name) | authors' range | our matching variant | our range (n=10) | verdict |
|------------------------|----------------|----------------------|------------------|---------|
| Interface Count | 5.67–6.67 | IFN **canonical** | 4.83–6.50 | **aligns** — and is far from released `get_IFN` (23–27), reinforcing the acme finding that authors reported canonical-style IFN, not their released code's |
| NED | 0.484–0.634 | NED (both variants) | 0.39–0.67 | **aligns** |
| Structural Modularity | 0.014–0.056 | neither | canonical 0.079–0.100, undirected 0.144–0.177 | **does not align** — open question; their recorded SM is below anything we can produce from these partitions with either formulation. Possibly computed on a different graph (e.g. including the transaction.json layer) or an earlier code state. Not tuned away; recorded as a finding. |

## Notes

- dayTrader is the largest graph so far (~176 labeled classes, node_dimension
  436); runs took ~10 min each vs ~2.5 min for the small apps.
- pbw's released `get_IFN` (10.26) vs canonical (3.88) again shows the
  cross-edge-vs-interface-count gap scales with graph density.
- `dataset_commit` is recorded as `bundled@f94803e` — these cells measure
  CHGNN on the *authors' preparation* of these apps, not on a pinned source
  checkout of ours.
