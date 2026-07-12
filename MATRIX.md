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

## CHGNN × acmeair
*dataset commit: `f16122729873ef0449ea276dfb2d2a1d45bebb40` · date: 2026-07-13*

| metric | canonical | chgnn-repo | published |
|---|---|---|---|
| SM ↑ | 0.0683 | 0.1544 | — |
| ICP ↓ | 0.3759 | — | — |
| IFN ↓ | 5.43 | 12.88 | — |
| NED ↑ | 0.652 | 0.844 | — |
| BCP ↓ | 1.0813 | — | — |
| CHM ↑ | 0.3469 | — | — |
| CHD ↑ | 0.1824 | — | — |

- *canonical*: mean of 10 stock runs; OUR full pipeline (extractor+adapter); NOT comparable to paper's acme (different AcmeAir variant: 84 vs 38 classes); protocol in runs/chgnn_tier2_pipeline.md
- *chgnn-repo*: mean of 10 stock runs; undirected SM / relative NED / cross-edge IFN per released metric.py

## CHGNN × daytrader
*dataset commit: `bundled@f94803e` · date: 2026-07-13*

| metric | canonical | chgnn-repo | published |
|---|---|---|---|
| SM ↑ | 0.0883 | 0.1632 | — |
| ICP ↓ | 0.5636 | — | — |
| IFN ↓ | 5.53 | 25.05 | — |
| NED ↑ | 0.507 | 0.555 | — |
| BCP ↓ | 4.4972 | — | — |
| CHM ↑ | — | — | — |
| CHD ↑ | — | — | — |

- *canonical*: mean of 10 stock runs on authors' bundled inputs; authors' own results.txt (5 runs): IFN 5.7-6.7 matches THIS IFN variant and NED 0.48-0.63 matches; their recorded SM 0.014-0.056 is below both our variants - open question
- *chgnn-repo*: mean of 10 stock runs; undirected SM / relative NED / cross-edge IFN per released metric.py

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

## CHGNN × plantsbywebsphere
*dataset commit: `bundled@f94803e` · date: 2026-07-13*

| metric | canonical | chgnn-repo | published |
|---|---|---|---|
| SM ↑ | 0.1625 | 0.2674 | — |
| ICP ↓ | 0.5052 | — | — |
| IFN ↓ | 3.88 | 10.26 | — |
| NED ↑ | 0.869 | 0.858 | — |
| BCP ↓ | 2.5881 | — | — |
| CHM ↑ | — | — | — |
| CHD ↑ | — | — | — |

- *canonical*: mean of 10 stock runs on authors' bundled pbw inputs; CHM/CHD N/A (no signatures in bundled data); BCP from callgraph.dot entrypoint labels
- *chgnn-repo*: mean of 10 stock runs; undirected SM / relative NED / cross-edge IFN per released metric.py

## CHGNN × spring-petclinic
*dataset commit: `51045d1648dad955df586150c1a1a6e22ef400c2` · date: 2026-07-13*

| metric | canonical | chgnn-repo | published |
|---|---|---|---|
| SM ↑ | 0.1787 | 0.2616 | — |
| ICP ↓ | 0.1702 | — | — |
| IFN ↓ | 1.67 | 2.30 | — |
| NED ↑ | 0.971 | 0.867 | — |
| BCP ↓ | 0.7420 | — | — |
| CHM ↑ | 0.7000 | — | — |
| CHD ↑ | 0.7429 | — | — |

- *canonical*: mean of 10 stock runs; OUR full pipeline; 6 isolated bootstrap/config classes excluded via ignore_classes.txt; sparse-graph caveat in runs/chgnn_tier2_pipeline.md
- *chgnn-repo*: mean of 10 stock runs; undirected SM / relative NED / cross-edge IFN per released metric.py

