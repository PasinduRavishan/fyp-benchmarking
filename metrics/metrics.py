"""Unified metric calculator: SM, ICP, IFN, NED.

Canonical formulations from Jin et al., TSE 2021 (as used by the
CHGNN / CoGCN / Mono2Micro literature). See CLAUDE.md.

Inputs:
    partition: {class_fqn: cluster_id}
    edges: list of Edge(src, dst, type, weight)
"""

import csv
import json
import math
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    type: str
    weight: float = 1.0


def _clusters(partition):
    """Map cluster_id -> set of classes."""
    clusters = {}
    for cls, cid in partition.items():
        clusters.setdefault(cid, set()).add(cls)
    return clusters


def sm(partition, edges, undirected=False):
    """Structural Modularity. Edge COUNTS (unweighted), all edge types.

    SM = (1/K) * sum_k(mu_k / N_k^2)
         - (1/(K(K-1)/2)) * sum_{i<j}(sigma_ij / (2 * N_i * N_j))

    undirected=True reproduces CHGNN's metric.py (validated on its acme
    run): edges collapse to unordered pairs (self-loops dropped), each
    intra pair counts TWICE in mu_k, each cross pair ONCE in sigma_ij.
    """
    clusters = _clusters(partition)
    K = len(clusters)

    if undirected:
        pairs = {frozenset((e.src, e.dst)) for e in edges if e.src != e.dst}
        edges = [Edge(*sorted(p), "UND", 1.0) for p in pairs]

    mu = {cid: 0 for cid in clusters}          # intra-edge counts
    sigma = {}                                  # {frozenset({i,j}): count}
    for e in edges:
        ci, cj = partition.get(e.src), partition.get(e.dst)
        if ci is None or cj is None:
            continue
        if ci == cj:
            mu[ci] += 2 if undirected else 1
        else:
            key = frozenset((ci, cj))
            sigma[key] = sigma.get(key, 0) + 1

    intra = sum(mu[cid] / len(members) ** 2 for cid, members in clusters.items()) / K

    if K < 2:
        return intra

    n_pairs = K * (K - 1) / 2
    inter = sum(
        sigma.get(frozenset((i, j)), 0) / (2 * len(clusters[i]) * len(clusters[j]))
        for i, j in combinations(clusters, 2)
    ) / n_pairs
    return intra - inter


def icp(partition, edges):
    """Inter-Call Percentage: crossing CALL-edge weight / total CALL-edge
    weight. Lower is better. Returns 0.0 if there are no call edges."""
    total = 0.0
    crossing = 0.0
    for e in edges:
        if e.type != "CALL":
            continue
        ci, cj = partition.get(e.src), partition.get(e.dst)
        if ci is None or cj is None:
            continue
        total += e.weight
        if ci != cj:
            crossing += e.weight
    return crossing / total if total else 0.0


def ifn(partition, edges):
    """Interface Number: IFN = (1/K) * sum_k |interfaces(k)|, where an
    interface of partition k is a class in k receiving CALL edges from
    outside k. Lower is better."""
    clusters = _clusters(partition)
    interfaces = set()
    for e in edges:
        if e.type != "CALL":
            continue
        ci, cj = partition.get(e.src), partition.get(e.dst)
        if ci is None or cj is None or ci == cj:
            continue
        interfaces.add(e.dst)
    return len(interfaces) / len(clusters)


def ned(partition, lo=5, hi=20):
    """Non-Extreme Distribution: 1 - (#classes in extreme-sized partitions /
    total classes). A partition is non-extreme if lo <= size <= hi
    (standard bounds in this literature: [5, 20]). Higher is better."""
    clusters = _clusters(partition)
    total = len(partition)
    extreme = sum(
        len(members) for members in clusters.values()
        if not lo <= len(members) <= hi
    )
    return 1 - extreme / total


def ned_relative(partition, eps=0.5):
    """CHGNN's NED variant (tools/chgnn/metric.py get_ned): a partition is
    non-extreme if floor(avg*(1-eps)) <= size <= ceil(avg*(1+eps)), where
    avg is the mean partition size. Differs from the fixed-bounds ned()
    above — record both when scoring (see CLAUDE.md)."""
    clusters = _clusters(partition)
    sizes = [len(m) for m in clusters.values()]
    avg = sum(sizes) / len(sizes)
    lo, hi = math.floor(avg * (1 - eps)), math.ceil(avg * (1 + eps))
    return sum(s for s in sizes if lo <= s <= hi) / len(partition)


def load_partition_json(path):
    """Load {class_fqn: cluster_id} from a partition JSON file."""
    with open(path) as f:
        return json.load(f)


def load_edges_csv(path):
    """Load edges.csv with columns src,dst,type,weight into Edge list."""
    with open(path, newline="") as f:
        return [
            Edge(row["src"], row["dst"], row["type"], float(row["weight"]))
            for row in csv.DictReader(f)
        ]


def compute_all(partition, edges, ned_lo=5, ned_hi=20):
    """Compute all metrics; returns {"SM": ..., "ICP": ..., "IFN": ..., "NED": ...}."""
    return {
        "SM": sm(partition, edges),
        "ICP": icp(partition, edges),
        "IFN": ifn(partition, edges),
        "NED": ned(partition, lo=ned_lo, hi=ned_hi),
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute SM/ICP/IFN/NED for a partition against a structural graph."
    )
    parser.add_argument("partition_json", help="partition file: {class_fqn: cluster_id}")
    parser.add_argument("edges_csv", help="edges.csv with columns src,dst,type,weight")
    parser.add_argument("--ned-lo", type=int, default=5)
    parser.add_argument("--ned-hi", type=int, default=20)
    args = parser.parse_args(argv)

    result = compute_all(
        load_partition_json(args.partition_json),
        load_edges_csv(args.edges_csv),
        ned_lo=args.ned_lo,
        ned_hi=args.ned_hi,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
