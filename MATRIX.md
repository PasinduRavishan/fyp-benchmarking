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

## FoSCI × acmeair
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0456 | — |
| ICP ↓ | 0.0608 | — |
| IFN ↓ | 0.6667 | — |
| NED ↑ | 0.2143 | — |
| BCP ↓ | 1.3143 | — |
| CHM ↑ | 0.8517 | — |
| CHD ↑ | 0.7780 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × autocare-nepal
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0244 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.0000 | — |
| BCP ↓ | 0.5142 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × bearboard
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0897 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.7647 | — |
| BCP ↓ | 1.4509 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=8)

## FoSCI × compiere-330
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0065 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.0251 | — |
| BCP ↓ | 3.6189 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × daytrader
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0019 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.0000 | — |
| BCP ↓ | 0.5584 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × diet-app
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.2277 | — |
| ICP ↓ | 0.3046 | — |
| IFN ↓ | 1.7500 | — |
| NED ↑ | 0.7083 | — |
| BCP ↓ | 1.5752 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × genapp
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0774 | — |
| ICP ↓ | 0.1481 | — |
| IFN ↓ | 0.4286 | — |
| NED ↑ | 0.6452 | — |
| BCP ↓ | 1.1296 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=7)

## FoSCI × jforum
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0020 | — |
| ICP ↓ | 0.0001 | — |
| IFN ↓ | 0.9167 | — |
| NED ↑ | 0.0000 | — |
| BCP ↓ | 0.6263 | — |
| CHM ↑ | 0.9384 | — |
| CHD ↑ | 0.9197 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × jpetstore
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.1526 | — |
| ICP ↓ | 0.0888 | — |
| IFN ↓ | 2.2500 | — |
| NED ↑ | 0.7500 | — |
| BCP ↓ | 1.6786 | — |
| CHM ↑ | 0.8214 | — |
| CHD ↑ | 0.6245 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=4)

## FoSCI × pharmacy
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0255 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.1356 | — |
| BCP ↓ | 0.7768 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × plantsbywebsphere
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0612 | — |
| ICP ↓ | 0.1333 | — |
| IFN ↓ | 0.7778 | — |
| NED ↑ | 0.0000 | — |
| BCP ↓ | 0.8095 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=9)

## FoSCI × pos-system
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0377 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.0000 | — |
| BCP ↓ | 0.8305 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=8)

## FoSCI × roller
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0518 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 1.5833 | — |
| NED ↑ | 0.0217 | — |
| BCP ↓ | 1.1202 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

## FoSCI × spring-petclinic
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0203 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.7600 | — |
| BCP ↓ | 0.8747 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=6)

## FoSCI × train-ticket
*dataset commit: `master@pinned` · date: 2026-07-29*

| metric | canonical | published |
|---|---|---|
| SM ↑ | 0.0512 | — |
| ICP ↓ | 0.0000 | — |
| IFN ↓ | 0.0000 | — |
| NED ↑ | 0.0796 | — |
| BCP ↓ | 2.5755 | — |
| CHM ↑ | 1.0000 | — |
| CHD ↑ | 1.0000 | — |

- *canonical*: FoSCI multi-sourced feature space clustering (K=12)

