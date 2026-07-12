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
- [ ] Phase A gate — validate metrics against CHGNN's published partitions/numbers
- [ ] **Phase B** — JavaParser structural extractor + JPetStore validation
- [ ] **Phase C** — CHGNN stock run → adapter → first matrix cell (CHGNN × JPetStore)
- [ ] **Phase D** — scale across datasets and remaining methods

## Team

Final Year Project, Dept. of Computer Science & Engineering, University of Moratuwa.
