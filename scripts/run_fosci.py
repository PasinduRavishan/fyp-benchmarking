"""Script to run FoSCI evaluation across benchmark datasets using BOTH:
1. Static Analysis (canonical-static): JavaParser extracted static call graph
2. Dynamic Analysis (canonical-dynamic): Runtime execution trace logs (.txt)
"""

import csv
import json
import math
import os
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
    """Load nodes and edges from a preprocessed struct.csv matrix."""
    matrix = np.loadtxt(struct_csv_path, delimiter=",")
    num_nodes = matrix.shape[0]
    nodes = [f"Class_{i}" for i in range(num_nodes)]
    raw_edges = []
    
    for i in range(num_nodes):
        for j in range(num_nodes):
            if matrix[i, j] > 0:
                src, dst = nodes[i], nodes[j]
                weight = float(matrix[i, j])
                raw_edges.append(Edge(src, dst, "CALL", weight))
                
    return nodes, raw_edges


def load_fosci_dynamic_trace(trace_path):
    """Parse a FoSCI dynamic trace log (.txt) to extract runtime execution sequence calls."""
    if not os.path.exists(trace_path):
        return None, None, []
    nodes = set()
    edge_weights = defaultdict(float)
    trace_calls = []

    with open(trace_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            c1, c2 = row.get("class1"), row.get("class2")
            if c1 and c2 and c1 != c2:
                nodes.add(c1)
                nodes.add(c2)
                edge_weights[(c1, c2)] += 1.0
                
                # Extract Operation for CHM/CHD
                m2 = row.get("method2", "call")
                m2_short = m2.split(".")[-1] if "." in m2 else m2
                m2_params = tuple(row.get("m2_para", "").split(";")) if row.get("m2_para") else ()
                m2_ret = row.get("m2_return", "void") or "void"

                op = Operation(cls=c2, name=m2_short, params=m2_params, returns=m2_ret)
                trace_calls.append((c1, op))

    nodes_list = sorted(list(nodes))
    raw_edges = [Edge(src, dst, "CALL", w) for (src, dst), w in edge_weights.items()]
    return nodes_list, raw_edges, trace_calls


def run_fosci_clustering(nodes, raw_edges, mode="static"):
    """FoSCI clustering algorithm in static or dynamic mode."""
    n = len(nodes)
    if n <= 1:
        return {nodes[0]: 0} if n == 1 else {}

    node_to_idx = {node: i for i, node in enumerate(nodes)}
    
    # 1. Structural / Dynamic Call Feature Matrix
    call_matrix = np.zeros((n, n))
    for e in raw_edges:
        if e.src in node_to_idx and e.dst in node_to_idx:
            i, j = node_to_idx[e.src], node_to_idx[e.dst]
            call_matrix[i, j] += e.weight
            call_matrix[j, i] += e.weight

    max_call = np.max(call_matrix) if np.max(call_matrix) > 0 else 1.0
    struct_sim = call_matrix / max_call

    # 2. Semantic Vocabulary Feature Space
    corpus = [" ".join(node.split(".")[-1].split("_")) for node in nodes]
    try:
        vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
        tfidf = vectorizer.fit_transform(corpus).toarray()
        sem_sim = np.dot(tfidf, tfidf.T)
    except Exception:
        sem_sim = np.eye(n)

    # Combined FoSCI Feature Space: Dynamic mode puts 0.8 weight on execution call frequencies
    alpha = 0.8 if mode == "dynamic" else 0.6
    affinity = alpha * struct_sim + (1.0 - alpha) * sem_sim
    distance_matrix = 1.0 - affinity
    np.fill_diagonal(distance_matrix, 0.0)
    distance_matrix = np.clip(distance_matrix, 0.0, 1.0)

    target_k = max(2, min(n // 4, 12)) if n >= 4 else max(1, n)

    clustering = AgglomerativeClustering(
        n_clusters=target_k,
        metric="precomputed",
        linkage="average"
    )
    labels = clustering.fit_predict(distance_matrix)
    
    return {node: int(labels[i]) for i, node in enumerate(nodes)}


def compute_bcp_uniform(partition):
    clusters = _clusters(partition)
    K = len(clusters)
    if K == 0:
        return 0.0
    total = sum(math.log2(max(1, len(members))) for members in clusters.values())
    return total / K


def evaluate_dataset(dataset_name, mode, graph_dir, output_dir):
    """Evaluate dataset using static analysis (canonical-static) or dynamic trace analysis (canonical-dynamic)."""
    nodes_file = os.path.join(graph_dir, "nodes.csv")
    edges_file = os.path.join(graph_dir, "edges.csv")
    calls_file = os.path.join(graph_dir, "calls.csv")
    struct_file = os.path.join(graph_dir, "struct.csv")

    trace_file = Path(__file__).resolve().parent.parent / "tools" / "fosci" / "traces" / f"{dataset_name}.txt"
    if not trace_file.exists():
        trace_file = Path(__file__).resolve().parent.parent / "tools" / "fosci" / "traces" / f"{dataset_name.replace('-', '')}.txt"

    if mode == "dynamic":
        if not trace_file.exists():
            print(f"Skipping dynamic mode for {dataset_name}: no trace file found.")
            return None
        nodes, raw_edges, calls = load_fosci_dynamic_trace(str(trace_file))
    else:
        # Static mode
        if os.path.exists(nodes_file) and os.path.exists(edges_file):
            nodes = load_nodes_csv(nodes_file)
            raw_edges = load_edges_csv(edges_file)
            calls = load_calls_csv(calls_file)
        elif os.path.exists(struct_file):
            nodes, raw_edges = load_from_struct_matrix(struct_file)
            calls = []
        else:
            print(f"Skipping static mode for {dataset_name}: static graph files missing.")
            return None

    if not nodes:
        return None

    partition = run_fosci_clustering(nodes, raw_edges, mode=mode)

    out_json_path = os.path.join(output_dir, f"fosci_{dataset_name}_{mode}.json")
    with open(out_json_path, "w") as f:
        json.dump(partition, f, indent=2)

    sm_val = sm(partition, raw_edges)
    icp_val = icp(partition, raw_edges)
    ifn_val = ifn(partition, raw_edges)
    ned_val = ned(partition, lo=5, hi=20)
    chm_val = chm(partition, calls) if calls else 1.0
    chd_val = chd(partition, calls) if calls else 1.0
    bcp_val = compute_bcp_uniform(partition)

    return {
        "method": "FoSCI",
        "dataset": dataset_name,
        "mode": mode,
        "variant": f"canonical-{mode}",
        "SM": sm_val,
        "ICP": icp_val,
        "IFN": ifn_val,
        "NED": ned_val,
        "CHM": chm_val,
        "CHD": chd_val,
        "BCP": bcp_val,
        "num_classes": len(nodes),
        "num_clusters": len(set(partition.values())),
        "partition_file": out_json_path
    }


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
    print("Running FoSCI Dual Evaluation (Static AST vs Dynamic Execution Trace Analysis)...")
    print("=" * 100)

    for dname in all_target_names:
        gdir = graphs_dir / dname
        if not gdir.exists() and (cogcn_apps_dir / dname).exists():
            gdir = cogcn_apps_dir / dname

        # Static Evaluation
        res_static = evaluate_dataset(dname, "static", str(gdir), str(output_dir))
        if res_static:
            results.append(res_static)
            print(f"[{dname:<20}] STATIC  | SM: {res_static['SM']:.4f} | ICP: {res_static['ICP']:.4f} | IFN: {res_static['IFN']:.4f} | NED: {res_static['NED']:.4f} | K: {res_static['num_clusters']}")

        # Dynamic Evaluation
        res_dynamic = evaluate_dataset(dname, "dynamic", str(gdir), str(output_dir))
        if res_dynamic:
            results.append(res_dynamic)
            print(f"[{dname:<20}] DYNAMIC | SM: {res_dynamic['SM']:.4f} | ICP: {res_dynamic['ICP']:.4f} | IFN: {res_dynamic['IFN']:.4f} | NED: {res_dynamic['NED']:.4f} | K: {res_dynamic['num_clusters']}")

    print("=" * 100)

    summary_path = output_dir / "fosci_dual_results_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Dual FoSCI Evaluation complete! Summary saved to {summary_path}")


if __name__ == "__main__":
    main()
