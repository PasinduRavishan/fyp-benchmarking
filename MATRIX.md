# Benchmarking Matrix (generated from results.csv — do not edit)

Values are means over 10 stock runs (protocol in runs/). `canonical` = our metric definitions (directed SM, interface-count IFN, fixed-bounds NED); `chgnn-repo` = the released metric.py variants (undirected SM, cross-edge IFN, relative NED). Copy the variant your matrix column expects — the published numbers in each paper may mix variants (see runs/ notes).

## CHGNN × acme
*dataset commit: `bundled@f94803e` · date: 2026-07-12*

| metric | canonical | chgnn-repo | published |
|---|---|---|---|
| SM ↑ | 0.1420 | 0.2052 | 0.214 |
| ICP ↓ | 0.3743 | — | — |
| IFN ↓ | 2.83 | 6.55 | 2.5 |
| NED ↑ | 0.803 | 0.561 | 0.738 |
| BCP ↓ | 2.0731 | — | — |
| CHM ↑ | — | — | — |
| CHD ↑ | — | — | — |

- *canonical*: mean of 10 unseeded stock runs; spread in runs/chgnn_acme_reproducibility.md; published IFN matches THIS variant; CHM/CHD N/A: released acme data has no param/return types; BCP use case = entrypoint from released callgraph.dot annotations
- *chgnn-repo*: mean of 10 unseeded stock runs; undirected SM / relative NED / cross-edge IFN per released metric.py; published SM matches THIS variant

## CHGNN × jpetstore
*dataset commit: `ebbd98ae92271c8dfa951d2fef518ba12877bf53` · date: 2026-07-12*

| metric | canonical | chgnn-repo | published |
|---|---|---|---|
| SM ↑ | 0.1716 | 0.2905 | — |
| ICP ↓ | 0.2224 | — | — |
| IFN ↓ | 1.98 | 2.68 | — |
| NED ↑ | 0.986 | 1.000 | — |
| BCP ↓ | 0.7945 | — | — |
| CHM ↑ | 0.4701 | — | — |
| CHD ↑ | 0.3063 | — | — |

- *canonical*: mean of 10 stock runs; first filled cell; protocol+seeds in runs/chgnn_jpetstore_repro.md; BCP use case = web entrypoint (reachability); CHM/CHD over cross-partition calls from extractor calls.csv
- *chgnn-repo*: mean of 10 stock runs; undirected SM / relative NED / cross-edge IFN per released metric.py

