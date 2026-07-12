# CHGNN × AcmeAir (f161227) + Spring-PetClinic (51045d1) — full-pipeline cells (10 runs each)

**Date:** 2026-07-13 · **Runner:** Pasindu Ravishan · **Tool:** `tools/chgnn` @ `f94803e`
**Pipeline:** OUR extractor → `adapters/chgnn_adapter.py` (final semantics: inheritance
counts as usage; FIELD edges carry callgraph reachability; isolated classes excludable
via `--ignore`) → 10 × stock `Graph.py --model=AE_EGCN_Separate --code=with_edge_loss`
→ scored with `metrics/`, both variants + CHM/CHD/BCP.
Configs: `adapters/configs/{acmeair,spring-petclinic}/`. Raw artifacts:
`runs/chgnn_{acmeair,springpetclinic}_repro/`.

These are the first cells where the ENTIRE pipeline is ours (extraction, adapter,
metrics). An earlier AcmeAir batch run under pre-fix adapter semantics was discarded
(never recorded) when the PetClinic NaN debugging changed the adapter; both datasets
were rerun under the final semantics.

## Summary (means, n=10)

| dataset | variant | SM | ICP | IFN | NED | BCP | CHM | CHD |
|---------|---------|-----|-----|-----|-----|-----|-----|-----|
| acmeair | canonical | 0.0683 | 0.3759 | 5.43 | 0.652 | 1.0813 | 0.3469 | 0.1824 |
| acmeair | chgnn-repo | 0.1544 | — | 12.88 | 0.844 | — | — | — |
| spring-petclinic | canonical | 0.1787 | 0.1702 | 1.67 | 0.971 | 0.7420 | 0.7000 | 0.7429 |
| spring-petclinic | chgnn-repo | 0.2616 | — | 2.30 | 0.867 | — | — | — |

## Notes and caveats

- **AcmeAir ≠ paper's acme.** The CHGNN authors analyzed the mongo-refactored
  AcmeAir variant (38 classes); f161227 (MonoEmbed's pin) is the morphia/wxs
  monolith (84 classes). Do not compare this cell to CHGNN's published acme row.
- **PetClinic caveats:** sparse graph (44 edges/25 classes; Spring hides calls
  in the framework); 6 isolated bootstrap/config classes excluded via
  ignore_classes.txt (they crash CHGNN with NaN and carry no structural signal);
  visits have no repository in this version (persist via the Owner aggregate).
  High CHM/CHD partly reflects the tiny interface surface (few cross-partition
  operations per boundary).
- **AcmeAir quality drop is real:** SM 0.068 / ICP 0.38 / NED 0.65 on 84 classes
  vs PetClinic's 25 — consistent with the DayTrader pattern (CHGNN quality
  degrades with app size).
- BCP use case = web entrypoint (CALL+FIELD reachability); AcmeAir 6 entrypoints,
  PetClinic 4 (Welcome/Crash excluded as isolated).
- Debugging record for the adapter fixes: see commit "Adapter fixes from
  PetClinic NaN debugging" — root cause was a seed group entirely dropped in
  preprocessing (empty k-means center = NaN) because Spring Data repositories
  get no project-level CALL edges.
