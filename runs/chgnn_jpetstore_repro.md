# CHGNN × JPetStore — first matrix cell (10 runs)

**Date:** 2026-07-12 · **Runner:** Pasindu Ravishan
**Tool:** `tools/chgnn` @ `f94803e` (conda `CHGNN`, osx-64/Rosetta)
**Dataset:** `mybatis/jpetstore-6` @ `ebbd98ae92271c8dfa951d2fef518ba12877bf53`
**Pipeline:** extractor (24 classes, 61 edges) → `adapters/chgnn_adapter.py`
(configs in `adapters/configs/jpetstore/`) → 10 × stock
`python Graph.py --model=AE_EGCN_Separate --data=jpetstore --code=with_edge_loss`
→ scored with `metrics/` (both variants). Protocol identical to
`runs/chgnn_acme_reproducibility.md`.

## Adapter inputs (documented decisions)

- **Entrypoints (4):** the concrete Stripes ActionBeans (Account/Cart/Catalog/Order).
- **db map:** 7 MyBatis mappers → their tables with CRUD read off the real mapper
  interfaces (e.g. AccountMapper→account CRU, OrderMapper→orders CR).
- **Seeds (4 clusters, semi-supervised — CHGNN requires seeds):** account-res +
  AccountService · catalog tables + CatalogService · Cart + CartActionBean ·
  order tables + OrderService. This mirrors the acme seed style (one datastore
  group + its service per cluster) and JPetStore's classic 4-service split.
- Synthesized class-level callgraph.dot (one `.call` node per class; per-entrypoint
  annotations over CALL-reachable sets); `node_dimension` = 2·(24+7)+4 = 66.

## Per-run results

| run | sizes | SM canon | SM chgnn | IFN canon | IFN chgnn | NED canon | NED chgnn | ICP canon |
|-----|-------|----------|----------|-----------|-----------|-----------|-----------|-----------|
| 1 | 4/6/8/11 | 0.1562 | 0.2492 | 2.25 | 3.25 | 0.862 | 1.000 | 0.2857 |
| 2 | 5/7/8/9 | 0.1733 | 0.2875 | 2.00 | 2.50 | 1.000 | 1.000 | 0.2041 |
| 3 | 5/7/8/9 | 0.1733 | 0.2875 | 2.00 | 2.50 | 1.000 | 1.000 | 0.2041 |
| 4 | 5/7/8/9 | 0.1733 | 0.2875 | 2.00 | 2.50 | 1.000 | 1.000 | 0.2041 |
| 5 | 5/6/7/11 | 0.1826 | 0.3190 | 1.75 | 2.50 | 1.000 | 1.000 | 0.2041 |
| 6 | 5/6/7/11 | 0.1826 | 0.3190 | 1.75 | 2.50 | 1.000 | 1.000 | 0.2041 |
| 7 | 6/7/8/8 | 0.1610 | 0.2854 | 2.00 | 3.00 | 1.000 | 1.000 | 0.2449 |
| 8 | 5/6/8/10 | 0.1575 | 0.2634 | 2.25 | 3.00 | 1.000 | 1.000 | 0.2653 |
| 9 | 5/7/8/9 | 0.1733 | 0.2875 | 2.00 | 2.50 | 1.000 | 1.000 | 0.2041 |
| 10 | 5/6/7/11 | 0.1826 | 0.3190 | 1.75 | 2.50 | 1.000 | 1.000 | 0.2041 |

## Summary (n = 10)

| metric | variant | mean | min | max | stdev |
|--------|---------|------|-----|-----|-------|
| SM | canonical | 0.1716 | 0.1562 | 0.1826 | 0.0101 |
| SM | chgnn-repo | 0.2905 | 0.2492 | 0.3190 | 0.0234 |
| IFN | canonical | 1.98 | 1.75 | 2.25 | 0.18 |
| IFN | chgnn-repo | 2.68 | 2.50 | 3.25 | 0.29 |
| NED | canonical | 0.986 | 0.862 | 1.000 | 0.044 |
| NED | chgnn-repo | 1.000 | 1.000 | 1.000 | 0.000 |
| ICP | canonical | 0.222 | 0.204 | 0.286 | 0.031 |

## Observations

- Far more stable than acme (SM stdev 0.010 vs 0.052): the smaller graph plus
  4 seed groups over 31 nodes constrain the solution space; several runs converge
  to identical partitions.
- Partitions are architecturally coherent — the Account vertical (bean, service,
  mapper, table) lands in one cluster in every run we inspected.
- No published CHGNN×JPetStore numbers exist (this is an empty matrix cell —
  the reason this project exists). The published_* columns are blank in results.csv.
- Our variant reimplementations matched the released `metric.py` on all 10 runs.
