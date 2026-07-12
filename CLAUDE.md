# CLAUDE.md — FYP Benchmarking Harness

## What this project is
We are a 4-person final-year project team (University of Moratuwa) building SemLeiden,
a microservice decomposition method. Before that, we must fill a benchmarking matrix:
run existing decomposition METHODS on DATASETS (Java monoliths) that their original
papers did NOT test on, and compute standard metrics on the resulting partitions.
Papers' own published numbers are already in our spreadsheet; we only fill EMPTY cells.

## Repo structure to create
fyp-benchmarking/
├── datasets/          # cloned monolith apps (pin each to a commit, record it)
├── tools/             # cloned method implementations
├── extractor/         # OUR JavaParser-based structural graph extractor
├── adapters/          # per-tool input format converters
├── metrics/           # OUR unified metric calculator (single source of truth)
├── outputs/           # partitions produced, named {method}_{dataset}.json
├── results.csv        # method, dataset, dataset_commit, SM, ICP, IFN, NED, BCP, date, runner
└── runs/              # logs per run

## The metrics module (metrics/) — BUILD THIS FIRST
Input: (a) partition JSON: {"class.FullName": cluster_id, ...}
       (b) structural graph: edges.csv with columns src,dst,type,weight
Output: SM, ICP, IFN, NED (and optionally MQ, Silhouette, BCP where inputs allow).

Canonical definitions (from Jin et al., TSE 2021 "Service Candidate Identification
from Monolithic Systems Based on Execution Traces" — the formulations used by
CHGNN/CoGCN/Mono2Micro literature):

- SM (Structural Modularity): SM = (1/K) * Σ_k (μ_k / N_k²)  −  (1/(K(K−1)/2)) * Σ_{i<j} (σ_{i,j} / (2·N_i·N_j))
  where K = #partitions, μ_k = #edges inside partition k, N_k = #classes in k,
  σ_{i,j} = #edges between partitions i and j. Higher is better.
- ICP (Inter-Call Percentage): fraction of call-edge weight crossing partition
  boundaries over total call-edge weight. Lower is better.
- IFN (Interface Number): IFN = (1/K) * Σ_k |interfaces(k)| where an interface of
  partition k is a class in k that receives calls from OUTSIDE k. Lower is better.
- NED (Non-Extreme Distribution): NED = 1 − (#classes in partitions of "extreme"
  size / total classes), where a partition is non-extreme if 5 ≤ size ≤ 20
  (standard bounds in this literature). Higher is better.

IMPORTANT: also read tools/chgnn/metric.py after cloning CHGNN — cross-check our
implementation against theirs. VALIDATION GATE: our metrics run on CHGNN's published
partitions must reproduce the paper's numbers (within rounding) before we fill ANY cell.
NOTE: our team's Google Doc has metric formulation screenshots per-tool
(Mono2Micro / CoGCN / Magnet variants) — if a tool's paper defines a metric variant
differently, record BOTH values and flag the discrepancy in results.csv notes.
Also see https://arxiv.org/pdf/2402.08481 (last year's FYP metric definitions).

## The extractor (extractor/) — BUILD SECOND
JavaParser-based CLI: input = path to a Java repo; output = nodes.csv (class FQNs)
+ edges.csv (src,dst,type,weight) with type ∈ {CALL, EXTENDS, IMPLEMENTS, FIELD}.
This doubles as Stage 1 of our own method later, so keep it clean and tested.
Validate on JPetStore (smallest app) by manually spot-checking known relationships.

## Methods (tools/) in priority order
1. CHGNN   — github.com/Alex-Mathai-98/Monolith-to-Microservices
             RUNNABLE: conda env create -f environment.yml; conda activate CHGNN;
             python Graph.py --model=AE_EGCN_Separate --data=acme --code=with_edge_loss
             Ships a working 'acme' example — run it UNCHANGED first, then study its
             Nodes/, Edges/, data_layer/ formats and write adapters/chgnn_adapter.py.
2. CoGCN   — github.com/utkd/cogcn (same IBM lineage as CHGNN, likely similar format)
3. FoSCI   — github.com/wj86/FoSCI (check the fosci-wrap release)
4. MAGNET  — github.com/magnetmicro/MAGNET (Docker-based, self-contained)
5. VAE-C   — github.com/rokinmaharjan/benchmarking-monolith-to-microservices
             NOTE: this is itself a benchmarking harness — inspect it early, it may
             already provide runners/adapters for several methods and save us work.
6. MonoEmbed — figshare.com/articles/dataset/MonoEmbed-EMSE25-RP/28373498
             (implementation + ME-LLM2Vec-340K weights; likely needs GPU; do last)
7. MicroMiner — Google Drive folder (manual download; inspect format first)
NOT RUNNABLE: Mono2Micro (IBM proprietary, repo is data-only — but its
datasets_runtime/ folder has INPUT+OUTPUT data for FoSCI/CoGCN/Bunch/MEM on
acmeair/daytrader/jpetstore/plants → check for FREE pre-computed partitions we can
score directly before running anything).

## Datasets (datasets/) — clone and pin commits
AcmeAir           github.com/acmeair/acmeair
Spring-PetClinic  github.com/spring-projects/spring-petclinic
PlantsByWebSphere github.com/WASdev/sample.plantsbywebsphere
DayTrader         github.com/WASdev/sample.daytrader7
JPetStore         github.com/mybatis/jpetstore-6
JForum            github.com/jforum
FXML-POS          github.com/BONY-SL/Point-Of-Sales-System-JAVAFX
SpringBlog        github.com/Raysmond/SpringBlog
Apache Roller     github.com/apache/roller
GenApp            github.com/cicsdev/cics-genapp
Missing repos (find or mark N/A): DietApp, Bearboard, student-information-system,
Compiere, Pharmacy.
CAUTION: papers pin specific commits (e.g. MonoEmbed pins AcmeAir @ f161227).
Record the commit for every clone in results.csv.

## Workflow per (method, dataset) cell
1. Clone+build dataset → 2. Run extractor → 3. Run adapter → 4. Run tool →
5. Score with OUR metrics module → 6. Append row to results.csv + log in runs/.
A cell may legitimately be "N/A (incompatible)" — record why (e.g. trace-based
tool on a desktop JavaFX app). That is a finding, not a failure.

## Build order
Phase A: repo skeleton + metrics module + its unit tests + validation gate.
Phase B: extractor + JPetStore validation.
Phase C: CHGNN stock acme run → chgnn adapter → CHGNN×JPetStore end-to-end (first cell).
Phase D: scale across datasets for CHGNN, then add methods in priority order.
