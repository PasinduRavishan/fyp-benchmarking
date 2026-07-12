"""Adapter: our extractor output (nodes.csv + edges.csv) -> CoGCN input dataset (struct.csv + content.csv).

Usage:
    python adapters/cogcn_adapter.py --nodes outputs/graphs/spring-petclinic/nodes.csv \
        --edges outputs/graphs/spring-petclinic/edges.csv \
        --out tools/cogcn/cogcn/data/apps/spring-petclinic/
"""

import argparse
import csv
import os
import numpy as np


def load_nodes(path):
    with open(path) as f:
        # Skip header "class"
        return [line.strip() for line in f if line.strip()][1:]


def load_edges(path):
    with open(path, newline="") as f:
        return [
            (r["src"], r["dst"], r["type"], float(r["weight"]))
            for r in csv.DictReader(f)
        ]


def get_reachable_classes(entrypoint, call_edges_dict):
    visited = {entrypoint}
    queue = [entrypoint]
    while queue:
        curr = queue.pop(0)
        for nxt in call_edges_dict.get(curr, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return visited


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nodes", required=True, help="Path to nodes.csv")
    p.add_argument("--edges", required=True, help="Path to edges.csv")
    p.add_argument("--out", required=True, help="Target directory for struct.csv and content.csv")
    args = p.parse_args(argv)

    nodes = sorted(load_nodes(args.nodes))
    edges = load_edges(args.edges)
    n_nodes = len(nodes)
    node_to_idx = {node: i for i, node in enumerate(nodes)}

    # 1. Identify entrypoints
    entrypoints = sorted([n for n in nodes if n.lower().endswith("controller")])
    n_entrypoints = len(entrypoints)
    ep_to_idx = {ep: i for i, ep in enumerate(entrypoints)}

    print(f"Loaded {n_nodes} nodes, {len(edges)} edges. Found {n_entrypoints} entrypoints:")
    for ep in entrypoints:
        print(f"  - {ep}")

    # 2. Build directed CALL graph for reachability
    call_edges_dict = {}
    for src, dst, etype, _ in edges:
        if etype == "CALL":
            call_edges_dict.setdefault(src, []).append(dst)

    # 3. Find reachable classes for each entrypoint
    reachable = {}
    for ep in entrypoints:
        reachable[ep] = get_reachable_classes(ep, call_edges_dict)

    # 4. Map each class to the set of entrypoints that reach it
    class_eps = {}
    for cls in nodes:
        class_eps[cls] = {ep for ep in entrypoints if cls in reachable.get(ep, set())}

    # 5. Build Content Matrix (features)
    # Dimension: N (coupling) + E (entrypoint reachability) + N (inheritance) = 2N + E
    feat_dim = 2 * n_nodes + n_entrypoints
    features = np.zeros((n_nodes, feat_dim), dtype=float)

    # Inheritance mapping
    inheritance_edges = {}
    for src, dst, etype, _ in edges:
        if etype in ("EXTENDS", "IMPLEMENTS"):
            inheritance_edges.setdefault(src, set()).add(dst)

    for i, cls_i in enumerate(nodes):
        eps_i = class_eps[cls_i]
        len_eps_i = len(eps_i)

        # A. Class Coupling: columns 0 to N-1
        for j, cls_j in enumerate(nodes):
            if len_eps_i > 0:
                eps_j = class_eps[cls_j]
                intersect = len(eps_i.intersection(eps_j))
                features[i, j] = intersect / len_eps_i

        # B. Entrypoint reachability: columns N to N+E-1
        for ep in eps_i:
            ep_idx = ep_to_idx[ep]
            features[i, n_nodes + ep_idx] = 1.0 / len_eps_i

        # C. Inheritance: columns N+E to 2N+E-1
        for dst in inheritance_edges.get(cls_i, []):
            if dst in node_to_idx:
                j = node_to_idx[dst]
                features[i, n_nodes + n_entrypoints + j] = 1.0

    # 6. Build Structure Matrix (directed adjacency matrix)
    adj = np.zeros((n_nodes, n_nodes), dtype=int)
    for src, dst, _, _ in edges:
        if src in node_to_idx and dst in node_to_idx:
            i = node_to_idx[src]
            j = node_to_idx[dst]
            if i != j:  # ignore self loops
                adj[i, j] = 1

    # 7. Write to output CSV files
    os.makedirs(args.out, exist_ok=True)
    
    struct_path = os.path.join(args.out, "struct.csv")
    np.savetxt(struct_path, adj, fmt="%d", delimiter=",")
    
    content_path = os.path.join(args.out, "content.csv")
    # For content.csv, match the baseline formatting
    np.savetxt(content_path, features, fmt="%.12g", delimiter=",")

    print(f"Successfully wrote {struct_path} (shape {adj.shape}) and {content_path} (shape {features.shape})")


if __name__ == "__main__":
    main()
