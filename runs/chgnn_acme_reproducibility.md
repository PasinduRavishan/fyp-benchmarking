# CHGNN × acme: reproducibility study (10 runs)

**Date:** 2026-07-12 · **Runner:** Pasindu Ravishan · **Tool:** `tools/chgnn` @ `f94803e`
**Env:** conda `CHGNN` (authors' pinned environment.yml, osx-64 under Rosetta 2)
**Command (unchanged, stock):**
`python Graph.py --model=AE_EGCN_Separate --data=acme --code=with_edge_loss`

## Why this study

The CHGNN paper reports for acme: **SM = 0.214, IFN = 2.5, NED = 0.738**. Our first
reproduced run gave SM = 0.2016, IFN(repo) = 7.0, NED(repo) = 0.583. Since our metrics
module reproduces the released `metric.py` *exactly* (1e-12, pinned regression test),
the divergence must come from the partitions themselves. We ran the stock experiment
10 times and scored every run under both metric variants.

## Non-determinism: confirmed

The released code fixes **no random seeds**:

- no `torch.manual_seed` / `np.random.seed` / `random.seed` anywhere in the repo;
- `"rngseed": 0` in `gcnconfig_with_edge_loss.json` is dead config — no code reads it;
- `KMeans(n_clusters=K, n_init=5)` (`NN_Models/Losses/kmeans.py:43`) omits `random_state`.

Weight initialization *and* the final clustering are stochastic; every run yields a
different partition (cluster size profiles below range from 3/9/11/13 to 2/3/5/26).

## Per-run results

Variants: **canonical** = our module's defaults (directed SM per Jin et al.; IFN =
interface classes per partition; NED = fixed bounds [5,20]). **chgnn-repo** = the
released `metric.py` (undirected SM; IFN = cross-edges/K; NED relative, avg±50%),
computed by running the authors' own code on each result file. Our reimplementations
(`sm(undirected=True)`, `ned_relative`) matched `metric.py` on all 10 runs.

| run | cluster sizes | SM canon | SM chgnn | IFN canon | IFN chgnn | NED canon | NED chgnn | ICP canon |
|-----|--------------|----------|----------|-----------|-----------|-----------|-----------|-----------|
| 1 | 3/9/11/13 | 0.1072 | 0.1684 | 2.50 | 7.00 | 0.917 | 0.917 | 0.3919 |
| 2 | 3/5/12/16 | 0.1238 | 0.1837 | 2.75 | 7.25 | 0.917 | 0.472 | 0.4054 |
| 3 | 4/4/13/15 | 0.1093 | 0.1764 | 3.25 | 7.25 | 0.778 | 0.583 | 0.4324 |
| 4 | 4/7/9/16 | 0.1079 | 0.1834 | 2.25 | 6.75 | 0.889 | 0.556 | 0.3784 |
| 5 | 2/3/5/26 | 0.1996 | 0.2157 | 3.50 | 4.50 | 0.139 | 0.139 | 0.2703 |
| 6 | 3/4/14/15 | 0.1404 | 0.2046 | 2.25 | 6.50 | 0.806 | 0.500 | 0.3514 |
| 7 | 5/8/11/12 | 0.1005 | 0.1888 | 3.00 | 7.50 | 1.000 | 1.000 | 0.4324 |
| 8 | 3/4/12/17 | 0.1427 | 0.2098 | 3.00 | 6.00 | 0.806 | 0.444 | 0.3514 |
| 9 | 2/2/15/17 | 0.2660 | 0.2981 | 2.75 | 6.00 | 0.889 | 0.000 | 0.3378 |
| 10 | 4/9/9/14 | 0.1223 | 0.2231 | 3.00 | 6.75 | 0.889 | 1.000 | 0.3919 |

## Summary vs published (n = 10)

| metric | variant | mean | min | max | stdev | published | published within range? |
|--------|---------|------|-----|-----|-------|-----------|------------------------|
| SM | canonical | 0.1420 | 0.1005 | 0.2660 | 0.0523 | 0.214 | yes |
| SM | chgnn-repo | **0.2052** | 0.1684 | 0.2981 | 0.0372 | **0.214** | **yes — near mean** |
| IFN | canonical | **2.83** | 2.25 | 3.50 | 0.41 | **2.5** | **yes — near mean** |
| IFN | chgnn-repo | 6.55 | 4.50 | 7.50 | 0.88 | 2.5 | **no — far outside** |
| NED | canonical | 0.803 | 0.139 | 1.000 | 0.242 | 0.738 | yes |
| NED | chgnn-repo | 0.561 | 0.000 | 1.000 | 0.338 | 0.738 | yes (huge spread) |
| ICP | canonical | 0.374 | 0.270 | 0.432 | 0.049 | — | — |

## Interface/use-case metrics (added 2026-07-12, same 10 partitions)

- **BCP: mean 2.0731 (min 1.9741, max 2.1698, stdev 0.0572).** Use case =
  entrypoint; class labels parsed from the released callgraph.dot annotations
  (73 labeled classes).
- **CHM / CHD: N/A.** The released acme data contains method names but no
  parameter or return types, so message- and domain-level operation similarity
  cannot be computed. Recorded as N/A per the workflow rule (a finding, not a
  failure).

## Conclusions

1. **The paper's SM (0.214) is consistent with the repo's undirected SM variant**
   (mean 0.2052, published value inside [0.168, 0.298] and within 0.25 stdev of the
   mean). The canonical directed SM (mean 0.142) is a noticeably different quantity.
2. **IFN: the paper almost certainly used the canonical interface-count definition,
   NOT the released `metric.py`.** Published 2.5 sits inside our canonical range
   [2.25, 3.5] (mean 2.83), while the released `get_IFN` (cross-edges/K) never went
   below 4.5 in 10 runs (mean 6.55). The released metric code and the paper's IFN
   are different metrics.
3. **NED is too high-variance to discriminate** (both variants' ranges span the
   published 0.738); cluster-size profiles vary run to run, and NED is a pure
   function of sizes.
4. **Single-run numbers from CHGNN are not meaningful** — unseeded training and
   clustering produce e.g. SM(canonical) from 0.10 to 0.27. Benchmarking cells for
   CHGNN should report the mean over a fixed number of stock runs (we used 10) with
   this protocol referenced, and the spread kept in `runs/`.

We did NOT tune anything to match published numbers. The reproducible quantity with
a documented protocol (10 stock runs, means, both metric variants) is our result;
the divergence pattern above is itself a finding.

## Artifacts

- `runs/chgnn_acme_repro/run_{1..10}.log` — training logs
- `runs/chgnn_acme_repro/clusters_{1..10}.json` — raw partitions
- `runs/chgnn_acme_repro/result_{1..10}.json` — converted result files scored above
- `results.csv` — two rows (canonical / chgnn-repo variant means)
