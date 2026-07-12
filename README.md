# FYP Benchmarking Harness

Benchmarking harness for **microservice decomposition methods**, built by a 4-person
final-year project team at the University of Moratuwa as groundwork for **SemLeiden**,
our own decomposition method.

## What this does

Existing decomposition methods (CHGNN, CoGCN, FoSCI, MAGNET, …) were each evaluated
in their papers on only a handful of Java monoliths. We fill in the missing cells of
the benchmarking matrix: run each **method** on **datasets** its paper did *not* test
on, and score the resulting partitions with a single, unified metrics implementation
so numbers are comparable across methods.

## Repository structure

```
fyp-benchmarking/
├── datasets/     # cloned monolith apps (each pinned to a recorded commit)
├── tools/        # cloned method implementations
├── extractor/    # our JavaParser-based structural graph extractor (planned)
├── adapters/     # per-tool input format converters (planned)
├── metrics/      # unified metric calculator — single source of truth ✅
├── outputs/      # partitions produced, named {method}_{dataset}.json
├── runs/         # logs per run
└── results.csv   # method, dataset, dataset_commit, SM, ICP, IFN, NED, ...
```

## Metrics module (`metrics/`)

Computes the four standard decomposition-quality metrics, using the canonical
formulations from Jin et al., TSE 2021 (as used in the CHGNN / CoGCN / Mono2Micro
literature):

| Metric | Meaning | Better |
|--------|---------|--------|
| **SM** | Structural Modularity — intra-partition cohesion minus inter-partition coupling, on unweighted structural edges | higher |
| **ICP** | Inter-Call Percentage — fraction of CALL-edge *weight* crossing partition boundaries | lower |
| **IFN** | Interface Number — mean number of classes per partition that receive calls from outside it | lower |
| **NED** | Non-Extreme Distribution — fraction of classes in reasonably-sized partitions (default bounds 5 ≤ size ≤ 20, configurable) | higher |

### Usage

```bash
python3 -m metrics.metrics partition.json edges.csv [--ned-lo 5 --ned-hi 20]
```

- `partition.json`: `{"com.example.SomeClass": 0, "com.example.Other": 1, ...}`
- `edges.csv`: columns `src,dst,type,weight` with `type ∈ {CALL, EXTENDS, IMPLEMENTS, FIELD}`

Output is a JSON object with `SM`, `ICP`, `IFN`, `NED`. Also usable as a library
(`from metrics.metrics import compute_all`).

Implementation notes:
- SM counts edges of **all types, unweighted**; ICP and IFN use **CALL edges only**
  (ICP weighted, IFN as a set of callee classes).
- Edges touching classes absent from the partition are ignored (some tools drop classes).

### Tests

```bash
python3 -m pytest metrics/tests/ -v
```

15 unit tests built around a tiny hand-computed 5-class / 2-partition example —
the full hand calculation is in the docstring of `metrics/tests/test_metrics.py`.

## Status

- [x] **Phase A** — repo skeleton + metrics module + unit tests
- [x] Phase A gate — our SM/NED reproduce `tools/chgnn/metric.py` **exactly** (1e-12) on
      the real acme run output (pinned regression fixture in `metrics/tests/fixtures/`).
      Findings: CHGNN treats the graph as undirected (`sm(..., undirected=True)`), uses a
      *relative* NED variant (`ned_relative`, bounds avg±50% — not the fixed [5,20]), and
      its `get_IFN` counts cross-edges per partition, not interface classes (7.0 vs our
      canonical 3.0 on acme) — record both variants when filling cells.
- [x] **Phase B** — JavaParser structural extractor (`extractor/`, Maven, 8 unit tests on a
      known-truth fixture) + JPetStore validation: 24 classes, 61 edges, layering spot-checks
      pass (`outputs/graphs/jpetstore/`). Build `mvn package`, run
      `java -jar target/extractor-0.1.0.jar <java-repo> <out-dir>` → `nodes.csv` + `edges.csv`
      in the metrics module's format. Dataset commits pinned in `datasets/COMMITS.csv`.
- [x] **Phase C** — CHGNN stock run → adapter → first matrix cell (CHGNN × JPetStore)
  - [x] CHGNN cloned (`tools/chgnn` @ `f94803e`), env built (conda `CHGNN`, osx-64 under
        Rosetta), stock acme run reproduced (`runs/chgnn_acme_stock.log`)
  - [x] Reproducibility study: 10 stock acme runs, both metric variants
        (`runs/chgnn_acme_reproducibility.md`). CHGNN is unseeded — single runs are not
        meaningful; cells report means over 10 runs. Paper's SM matches the repo's
        undirected variant, but paper's IFN matches the *canonical* definition, not the
        released `metric.py`.
  - [x] **First matrix cell filled: CHGNN × JPetStore** — extractor → `chgnn_adapter.py`
        → 10 runs → both metric variants in `results.csv`
        (`runs/chgnn_jpetstore_repro.md`). SM 0.172 canonical / 0.291 chgnn-repo,
        IFN 1.98, NED 0.99, ICP 0.22 (means, n=10).
- [ ] **Phase D** — scale across datasets and remaining methods

## Team

Final Year Project, Dept. of Computer Science & Engineering, University of Moratuwa.
