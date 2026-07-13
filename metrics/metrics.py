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


@dataclass(frozen=True)
class Operation:
    """A callee method: owning class FQN, name, parameter types, return type."""
    cls: str
    name: str
    params: tuple
    returns: str


# Type-name tokens that are not domain terms (JDK/primitive noise for CHD).
_NON_DOMAIN = {
    "void", "int", "long", "short", "byte", "float", "double", "boolean",
    "char", "string", "list", "map", "set", "collection", "object",
    "integer", "optional", "iterable",
}


def _published_ops(partition, calls):
    """Operations of each partition invoked from OUTSIDE it.
    calls: iterable of (caller_class, Operation)."""
    ops = {cid: set() for cid in set(partition.values())}
    for caller, op in calls:
        ci, cj = partition.get(caller), partition.get(op.cls)
        if ci is None or cj is None or ci == cj:
            continue
        ops[cj].add(op)
    return ops


def _pairwise_mean(ops, similarity):
    """Mean of similarity over unordered op pairs; 1.0 below 2 ops (a
    single-operation or unpublished interface is vacuously cohesive)."""
    ops = sorted(ops, key=lambda o: (o.cls, o.name, o.params, o.returns))
    if len(ops) < 2:
        return 1.0
    pairs = list(combinations(ops, 2))
    return sum(similarity(a, b) for a, b in pairs) / len(pairs)


def _jaccard(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def chm(partition, calls):
    """Cohesion at Message level: mean over partitions of the mean pairwise
    f_msg = (Jaccard(returns) + Jaccard(params))/2 over the partition's
    externally-invoked operations. Range [0,1], higher is better."""
    def f_msg(a, b):
        return (_jaccard({a.returns}, {b.returns}) + _jaccard(a.params, b.params)) / 2

    ops = _published_ops(partition, calls)
    return sum(_pairwise_mean(o, f_msg) for o in ops.values()) / len(ops)


def _terms(op):
    """Domain terms of an operation signature: camelCase tokens of the method
    name plus simple names of param/return types, minus JDK/primitive noise."""
    import re

    words = []
    names = [op.name] + [p.split(".")[-1] for p in op.params]
    names.append(op.returns.split(".")[-1])
    for name in names:
        words.extend(re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", name))
    return {w.lower() for w in words} - _NON_DOMAIN


def chd(partition, calls):
    """Cohesion at Domain level: like chm but f_dom = Jaccard of the domain
    terms in the operation signatures. Range [0,1], higher is better."""
    def f_dom(a, b):
        return _jaccard(_terms(a), _terms(b))

    ops = _published_ops(partition, calls)
    return sum(_pairwise_mean(o, f_dom) for o in ops.values()) / len(ops)


def bcp(partition, class_usecases, log=math.log):
    """Business Context Purity: mean over partitions of the entropy of a
    uniform distribution over the partition's use cases, i.e. log(m_i) with
    m_i = |union of use-case labels of member classes| (0 if no labels).
    Natural log by default. Lower is better."""
    clusters = _clusters(partition)
    total = 0.0
    for members in clusters.values():
        labels = set()
        for c in members:
            labels |= set(class_usecases.get(c, ()))
        total += log(len(labels)) if labels else 0.0
    return total / len(clusters)


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


def load_methods_csv(path):
    """Loads methods.csv with columns class,method,returnType,parameters."""
    methods_by_class = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cls = row["class"]
            method_name = row["method"]
            ret_type = row["returnType"]
            params = row["parameters"].split(";") if row["parameters"] else []
            methods_by_class.setdefault(cls, []).append({
                "name": method_name,
                "returnType": ret_type,
                "parameters": params
            })
    return methods_by_class


def load_method_calls_csv(path):
    """Loads method_calls.csv with columns srcClass,srcMethod,dstClass,dstMethod."""
    calls = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            calls.append({
                "srcClass": row["srcClass"],
                "srcMethod": row["srcMethod"],
                "dstClass": row["dstClass"],
                "dstMethod": row["dstMethod"]
            })
    return calls


def jaccard(set_a, set_b):
    if not set_a and not set_b:
        return 1.0
    union = set_a.union(set_b)
    if not union:
        return 1.0
    return len(set_a.intersection(set_b)) / len(union)


# Stop words and framework keywords for CHD
STOP_WORDS = {
    'a', 'an', 'the', 'of', 'in', 'to', 'for', 'with', 'by', 'on', 'at', 'and', 'or', 'not', 'is', 'are', 'was', 'were',
    'void', 'string', 'int', 'double', 'float', 'boolean', 'list', 'set', 'map', 'get', 'set', 'impl', 'class', 'object',
    'java', 'org', 'com', 'spring', 'framework', 'samples', 'petclinic', 'util', 'lang', 'http', 'api'
}


def split_words(s):
    import re
    # Split camelCase, snake_case, dots, etc.
    tokens = re.split(r'[^a-zA-Z0-9]', s)
    words = []
    for token in tokens:
        # Split camelCase
        camel_split = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)', token)
        for w in camel_split:
            words.append(w.lower())
        if not camel_split and token:
            words.append(token.lower())
    return words


def get_domain_terms(method_info):
    terms = set()
    terms.update(split_words(method_info.get('name', '')))
    terms.update(split_words(method_info.get('returnType', '')))
    for param in method_info.get('parameters', []):
        terms.update(split_words(param))
    terms = {t for t in terms if t not in STOP_WORDS and len(t) > 1}
    return terms


def compute_chm_chd(partition, methods_by_class, method_calls):
    """Compute CHM (Cohesion at Message level) and CHD (Cohesion at Domain level)."""
    # Map each (class, method) to its method_info
    method_registry = {}
    for cls, m_list in methods_by_class.items():
        for m in m_list:
            method_registry[(cls, m['name'])] = m

    clusters = _clusters(partition)
    N = len(clusters)
    if N == 0:
        return 0.0, 0.0

    # Group external calls by callee class's partition
    external_calls_by_cluster = {}
    for mc in method_calls:
        src_c, dst_c = mc['srcClass'], mc['dstClass']
        ci, cj = partition.get(src_c), partition.get(dst_c)
        if ci is not None and cj is not None and ci != cj:
            external_calls_by_cluster.setdefault(cj, set()).add((dst_c, mc['dstMethod']))

    chm_sum = 0.0
    chd_sum = 0.0

    for cj, members in clusters.items():
        O_j = list(external_calls_by_cluster.get(cj, set()))
        if len(O_j) <= 1:
            chm_sum += 1.0
            chd_sum += 1.0
            continue

        sigs = []
        for cls, m_name in O_j:
            info = method_registry.get((cls, m_name))
            if info is None:
                info = {'name': m_name, 'returnType': 'void', 'parameters': []}
            sigs.append(info)

        chm_pairs_sum = 0.0
        chd_pairs_sum = 0.0
        num_pairs = len(sigs) * (len(sigs) - 1) / 2

        for idx1, idx2 in combinations(range(len(sigs)), 2):
            sig1, sig2 = sigs[idx1], sigs[idx2]

            # CHM calculation
            ret1 = {sig1['returnType']} if sig1['returnType'] != 'void' else set()
            ret2 = {sig2['returnType']} if sig2['returnType'] != 'void' else set()
            par1 = set(sig1['parameters'])
            par2 = set(sig2['parameters'])

            f_msg = 0.5 * (jaccard(ret1, ret2) + jaccard(par1, par2))
            chm_pairs_sum += f_msg

            # CHD calculation
            terms1 = get_domain_terms(sig1)
            terms2 = get_domain_terms(sig2)
            f_dom = jaccard(terms1, terms2)
            chd_pairs_sum += f_dom

        chm_sum += chm_pairs_sum / num_pairs
        chd_sum += chd_pairs_sum / num_pairs

    return chm_sum / N, chd_sum / N


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


def compute_bcp(partition, edges, entrypoints=None):
    """Compute Business Cohesion of Partition (BCP). Returns uniform and entropy variants."""
    if entrypoints is None:
        entrypoints = [cls for cls in partition.keys() if cls.lower().endswith('controller') or cls.lower().endswith('action') or cls.lower().endswith('rest')]

    call_edges_dict = {}
    for e in edges:
        if e.type == "CALL":
            call_edges_dict.setdefault(e.src, []).append(e.dst)

    reachable_classes = {}
    for ep in entrypoints:
        reachable_classes[ep] = get_reachable_classes(ep, call_edges_dict)

    class_use_cases = {}
    for cls in partition.keys():
        class_use_cases[cls] = {ep for ep in entrypoints if cls in reachable_classes.get(ep, set())}

    clusters = _clusters(partition)
    M = len(clusters)
    if M == 0:
        return 0.0, 0.0

    bcp_uniform_sum = 0.0
    bcp_entropy_sum = 0.0

    for cid, members in clusters.items():
        partition_use_cases = set()
        use_case_counts = {}
        for m in members:
            ucs = class_use_cases.get(m, set())
            partition_use_cases.update(ucs)
            for uc in ucs:
                use_case_counts[uc] = use_case_counts.get(uc, 0) + 1

        m_i = len(partition_use_cases)
        if m_i <= 1:
            # log(1) = 0
            continue

        # Uniform entropy (as per paper screenshot: log2(m_i))
        bcp_uniform_sum += math.log2(m_i)

        # Non-uniform entropy
        total_mappings = sum(use_case_counts.values())
        bcp_i_non_uniform = 0.0
        if total_mappings > 0:
            for uc in partition_use_cases:
                p_j = use_case_counts[uc] / total_mappings
                bcp_i_non_uniform -= p_j * math.log2(p_j)
        bcp_entropy_sum += bcp_i_non_uniform

    return bcp_uniform_sum / M, bcp_entropy_sum / M


def compute_all(partition, edges, methods_by_class=None, method_calls=None, ned_lo=5, ned_hi=20):
    """Compute all metrics; returns {"SM": ..., "ICP": ..., "IFN": ..., "NED": ...}."""
    res = {
        "SM": sm(partition, edges),
        "ICP": icp(partition, edges),
        "IFN": ifn(partition, edges),
        "NED": ned(partition, lo=ned_lo, hi=ned_hi),
    }
    if methods_by_class is not None and method_calls is not None:
        chm, chd = compute_chm_chd(partition, methods_by_class, method_calls)
        res["CHM"] = chm
        res["CHD"] = chd

    # BCP can always be computed if we have edges (and automatically identify controller entrypoints)
    bcp_uni, bcp_ent = compute_bcp(partition, edges)
    res["BCP_uniform"] = bcp_uni
    res["BCP_entropy"] = bcp_ent

    return res


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute SM/ICP/IFN/NED/CHM/CHD/BCP for a partition against a structural graph."
    )
    parser.add_argument("partition_json", help="partition file: {class_fqn: cluster_id}")
    parser.add_argument("edges_csv", help="edges.csv with columns src,dst,type,weight")
    parser.add_argument("methods_csv", nargs="?", default=None, help="methods.csv with columns class,method,returnType,parameters")
    parser.add_argument("method_calls_csv", nargs="?", default=None, help="method_calls.csv with columns srcClass,srcMethod,dstClass,dstMethod")
    parser.add_argument("--ned-lo", type=int, default=5)
    parser.add_argument("--ned-hi", type=int, default=20)
    args = parser.parse_args(argv)

    partition = load_partition_json(args.partition_json)
    edges = load_edges_csv(args.edges_csv)

    methods_by_class = None
    if args.methods_csv:
        methods_by_class = load_methods_csv(args.methods_csv)

    method_calls = None
    if args.method_calls_csv:
        method_calls = load_method_calls_csv(args.method_calls_csv)

    result = compute_all(
        partition,
        edges,
        methods_by_class=methods_by_class,
        method_calls=method_calls,
        ned_lo=args.ned_lo,
        ned_hi=args.ned_hi,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
