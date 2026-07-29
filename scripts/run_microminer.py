"""Script to run MicroMiner evaluation across benchmark datasets and calculate quality metrics.
Computes SM, ICP, IFN, NED, CHM, CHD, BCP_uniform (log2 usecase count entropy), and BCP_entropy (Shannon entropy).
"""

import csv
import json
import math
import os
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.microminer.microminer import MicroMiner
from metrics.metrics import (
    load_edges_csv,
    Operation,
    Edge,
    _clusters,
    sm,
    icp,
    ifn,
    ned,
    chm,
    chd,
)


def load_nodes_csv(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()][1:]  # skip header


def load_calls_csv(path):
    if not os.path.exists(path):
        return []
    calls = []
    with open(path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for r in reader:
            params = tuple(r["params"].split(";")) if r.get("params") else ()
            op = Operation(
                cls=r["callee"],
                name=r.get("method", "call"),
                params=params,
                returns=r.get("returns", "void")
            )
            calls.append((r["caller"], op))
    return calls


def load_from_struct_matrix(struct_csv_path):
    """Load nodes and edges from a preprocessed struct.csv adjacency matrix."""
    matrix = np.loadtxt(struct_csv_path, delimiter=",")
    num_nodes = matrix.shape[0]
    nodes = [f"Class_{i}" for i in range(num_nodes)]
    edges = []
    raw_edges = []
    
    for i in range(num_nodes):
        for j in range(num_nodes):
            if matrix[i, j] > 0:
                src, dst = nodes[i], nodes[j]
                weight = float(matrix[i, j])
                edges.append((src, dst, "CALL", weight))
                raw_edges.append(Edge(src, dst, "CALL", weight))
                
    return nodes, edges, raw_edges


def load_entrypoints(nodes):
    """Find entrypoint controller classes from nodes."""
    entrypoints = set()
    for n in nodes:
        name_lower = n.split(".")[-1].lower()
        if any(k in name_lower for k in ["controller", "action", "resource", "endpoint", "servlet"]):
            entrypoints.add(n)
    if not entrypoints:
        entrypoints = set(nodes[:max(1, len(nodes) // 5)])
    return entrypoints


def compute_bcp_metrics(partition, nodes, raw_edges):
    """Computes BCP_uniform (log2(m_i)) and BCP_entropy (-sum p_j log2(p_j))."""
    eps = load_entrypoints(nodes)
    adj = defaultdict(set)
    for e in raw_edges:
        if e.type in ("CALL", "FIELD"):
            adj[e.src].add(e.dst)

    class_usecases = defaultdict(set)
    for ep in eps:
        visited = set()
        queue = [ep]
        while queue:
            curr = queue.pop(0)
            if curr not in visited:
                visited.add(curr)
                class_usecases[curr].add(ep)
                for nxt in adj[curr]:
                    if nxt not in visited:
                        queue.append(nxt)

    clusters = _clusters(partition)
    bcp_uniform_sum = 0.0
    bcp_entropy_sum = 0.0

    for cid, members in clusters.items():
        all_labels = set()
        uc_counts = defaultdict(int)
        for c in members:
            labels = class_usecases.get(c, set())
            all_labels |= labels
            for l in labels:
                uc_counts[l] += 1
        
        m_i = len(all_labels)
        bcp_uniform_sum += math.log2(m_i) if m_i > 0 else 0.0

        total_counts = sum(uc_counts.values())
        if total_counts > 0:
            ent = 0.0
            for cnt in uc_counts.values():
                p = cnt / total_counts
                ent -= p * math.log2(p)
            bcp_entropy_sum += ent

    K = len(clusters)
    return (bcp_uniform_sum / K) if K > 0 else 0.0, (bcp_entropy_sum / K) if K > 0 else 0.0


def run_dataset(dataset_name, graph_dir, output_dir):
    nodes_file = os.path.join(graph_dir, "nodes.csv")
    edges_file = os.path.join(graph_dir, "edges.csv")
    calls_file = os.path.join(graph_dir, "calls.csv")
    struct_file = os.path.join(graph_dir, "struct.csv")

    if os.path.exists(nodes_file) and os.path.exists(edges_file):
        nodes = load_nodes_csv(nodes_file)
        raw_edges = load_edges_csv(edges_file)
        edges_tuples = [(e.src, e.dst, e.type, e.weight) for e in raw_edges]
    elif os.path.exists(struct_file):
        nodes, edges_tuples, raw_edges = load_from_struct_matrix(struct_file)
    else:
        print(f"Skipping {dataset_name}: graph files missing.")
        return None

    # Run MicroMiner algorithm
    mm = MicroMiner(nodes=nodes, edges=edges_tuples)
    partition = mm.run()

    # Save partition JSON
    out_json_path = os.path.join(output_dir, f"microminer_{dataset_name}.json")
    with open(out_json_path, "w") as f:
        json.dump(partition, f, indent=2)

    # Compute metrics
    sm_val = sm(partition, raw_edges)
    icp_val = icp(partition, raw_edges)
    ifn_val = ifn(partition, raw_edges)
    ned_val = ned(partition, lo=5, hi=20)

    # Advanced interface/cohesion metrics
    calls = load_calls_csv(calls_file)
    chm_val = chm(partition, calls) if calls else 1.0
    chd_val = chd(partition, calls) if calls else 1.0

    # Business Cohesion of Partition (BCP) - both uniform and Shannon entropy variants
    bcp_uniform, bcp_entropy = compute_bcp_metrics(partition, nodes, raw_edges)

    result = {
        "method": "MicroMiner",
        "dataset": dataset_name,
        "SM": sm_val,
        "ICP": icp_val,
        "IFN": ifn_val,
        "NED": ned_val,
        "CHM": chm_val,
        "CHD": chd_val,
        "BCP": bcp_uniform,
        "BCP_uniform": bcp_uniform,
        "BCP_entropy": bcp_entropy,
        "num_classes": len(nodes),
        "num_clusters": len(set(partition.values())),
        "partition_file": out_json_path
    }
    return result


def main():
    benchmarking_dir = Path(__file__).resolve().parent.parent
    graphs_dir = benchmarking_dir / "outputs" / "graphs"
    output_dir = benchmarking_dir / "outputs"

    cogcn_apps_dir = benchmarking_dir / "tools" / "cogcn" / "cogcn" / "data" / "apps"

    all_target_names = [
        "acmeair", "autocare-nepal", "bearboard", "compiere-330", "daytrader",
        "diet-app", "genapp", "jforum", "jpetstore", "pharmacy",
        "plantsbywebsphere", "pos-system", "roller", "spring-petclinic",
        "springblog", "train-ticket"
    ]

    results = []
    print("=" * 100)
    print(f"Running MicroMiner Evaluation on all target datasets (with BCP Uniform & Shannon Entropy)...")
    print("=" * 100)

    for dname in all_target_names:
        gdir = graphs_dir / dname
        if not gdir.exists() and (cogcn_apps_dir / dname).exists():
            gdir = cogcn_apps_dir / dname

        res = run_dataset(dname, str(gdir), str(output_dir))
        if res:
            results.append(res)
            print(f"[{dname:<20}] SM: {res['SM']:.4f} | ICP: {res['ICP']:.4f} | IFN: {res['IFN']:.4f} | NED: {res['NED']:.4f} | BCP_uni: {res['BCP_uniform']:.4f} | BCP_ent: {res['BCP_entropy']:.4f}")

    print("=" * 100)

    # Save summary results JSON
    summary_path = output_dir / "microminer_results_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results summary saved to {summary_path}")


if __name__ == "__main__":
    main()
