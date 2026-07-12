"""Adapter: our extractor output (nodes.csv + edges.csv) -> CHGNN input dataset.

Generates a complete data_layer/utilities/data/{name}_AE_EGCN_Separate/ folder:
    temp/inter_class_usage.json   from CALL+FIELD weights, EXTENDS, IMPLEMENTS
    temp/callgraph.dot            synthesized class-level "method" graph with
                                  entrypoint annotations (one fake method
                                  {Class}.call per class); per entrypoint E,
                                  every CALL edge inside E's reachable set is
                                  emitted with E's annotation
    temp/service.json             one entry per entrypoint class
    temp/db.json                  from a {class: {table: "CRUD"}} map
    custom/seeds.txt              copied from --seeds
    custom/ignore_classes.txt     empty
    custom/gcnconfig_{code}.json  from --template, with num_clusters =
                                  #seed lines and node_dimension =
                                  2*(#classes + #tables) + #entrypoints

Usage:
    python3 adapters/chgnn_adapter.py --nodes n.csv --edges e.csv \
        --entrypoints eps.txt --db-map dbmap.json --seeds seeds.txt \
        --template <acme gcnconfig> --out <chgnn data dir> [--code with_edge_loss]
"""

import argparse
import csv
import json
import os
from collections import defaultdict


def load_nodes(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()][1:]  # skip header


def load_edges(path):
    with open(path, newline="") as f:
        return [
            (r["src"], r["dst"], r["type"], int(float(r["weight"])))
            for r in csv.DictReader(f)
        ]


def build_icu(nodes, edges):
    """inter_class_usage.json: CALL+FIELD weights as usage counts,
    EXTENDS -> superClass, IMPLEMENTS -> implementedInterfaces."""
    used = defaultdict(lambda: defaultdict(int))
    used_by = defaultdict(lambda: defaultdict(int))
    super_class = {}
    interfaces = defaultdict(list)
    node_set = set(nodes)

    for src, dst, etype, w in edges:
        if src not in node_set or dst not in node_set:
            continue
        # every edge type counts as usage: CHGNN's own acme data lists all
        # EXTENDS/IMPLEMENTS targets in the usage counts too, and classes
        # with a zero usage row (pure inheritance parents) NaN the GCN
        used[src][dst] += w
        used_by[dst][src] += w
        if etype == "EXTENDS":
            super_class[src] = dst
        elif etype == "IMPLEMENTS":
            interfaces[src].append(dst)

    return {
        n: {
            "name": n,
            "usedClassesToCount": dict(used[n]),
            "usedByClassesToCount": dict(used_by[n]),
            "type": "both",
            "superClass": super_class.get(n, "java.lang.Object"),
            "implementedInterfaces": sorted(interfaces[n]),
        }
        for n in nodes
    }


def _ep_annotation(entry_class):
    short = entry_class.split(".")[-1]
    return ("{type: web, method: GET, uri: [/%s], entry: %s, "
            "entrydisplayname: %s.call}" % (short, short, short))


# edge types that carry call-graph reachability: real calls plus FIELD (DI
# wiring - frameworks inject the field, then dispatch through it, and e.g.
# Spring Data repositories receive no project-level CALL edges at all)
_LINK_TYPES = ("CALL", "FIELD")


def reachable(edges, root):
    """Classes reachable from root via CALL/FIELD edges (root included)."""
    out = defaultdict(set)
    for src, dst, etype, _ in edges:
        if etype in _LINK_TYPES:
            out[src].add(dst)
    seen = {root}
    stack = [root]
    while stack:
        for nxt in out[stack.pop()] - seen:
            seen.add(nxt)
            stack.append(nxt)
    return seen


def build_callgraph_dot(nodes, edges, entrypoints):
    lines = ["digraph {", "rankdir=LR", "node[shape=plaintext]"]
    for ep_class in entrypoints:
        ann = _ep_annotation(ep_class)
        lines.append('"%s.call" -> "[%s] %s.call"' % (ep_class, ann, ep_class))
        reach = reachable(edges, ep_class)
        for src, dst, etype, _ in edges:
            if etype in _LINK_TYPES and src in reach and dst in reach:
                lines.append('"[%s] %s.call" -> "[%s] %s.call"'
                             % (ann, src, ann, dst))
    lines.append("}")
    return "\n".join(lines) + "\n"


def build_service_json(entrypoints):
    return [
        {
            "service_entry_name": _ep_annotation(ep),
            "class_method_name": ["%s.call" % ep],
        }
        for ep in entrypoints
    ]


def build_db_json(db_map):
    """db_map: {class_fqn: {table_name: "CRUD letters"}} -> db.json entries."""
    entries = []
    for cls, tables in db_map.items():
        for table, crud in tables.items():
            for letter in crud:
                entries.append({
                    "service_name": "%s.call" % cls,
                    "db_name": table,
                    "crud": letter,
                })
    return entries


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nodes", required=True)
    p.add_argument("--edges", required=True)
    p.add_argument("--entrypoints", required=True,
                   help="file with one entrypoint class FQN per line")
    p.add_argument("--db-map", required=True,
                   help="json: {class_fqn: {table: 'CRUD letters'}}")
    p.add_argument("--seeds", required=True, help="seeds.txt to copy")
    p.add_argument("--ignore", default=None,
                   help="optional ignore_classes.txt to copy (classes CHGNN "
                        "should drop, e.g. structurally isolated ones)")
    p.add_argument("--template", required=True, help="gcnconfig json to adapt")
    p.add_argument("--out", required=True, help="{name}_AE_EGCN_Separate dir")
    p.add_argument("--code", default="with_edge_loss")
    args = p.parse_args(argv)

    nodes = load_nodes(args.nodes)
    edges = load_edges(args.edges)
    with open(args.entrypoints) as f:
        entrypoints = [line.strip() for line in f if line.strip()]
    with open(args.db_map) as f:
        db_map = json.load(f)
    with open(args.seeds) as f:
        seed_lines = [line for line in f if line.strip()]
    with open(args.template) as f:
        config = json.load(f)

    tables = sorted({t for tabs in db_map.values() for t in tabs})

    os.makedirs(os.path.join(args.out, "temp"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "custom"), exist_ok=True)

    def write(rel, content):
        path = os.path.join(args.out, rel)
        with open(path, "w") as f:
            f.write(content)

    write("temp/inter_class_usage.json", json.dumps(build_icu(nodes, edges), indent=1))
    write("temp/callgraph.dot", build_callgraph_dot(nodes, edges, entrypoints))
    write("temp/service.json", json.dumps(build_service_json(entrypoints), indent=1))
    write("temp/db.json", json.dumps(build_db_json(db_map), indent=1))
    write("custom/seeds.txt", "".join(seed_lines))
    ignore = ""
    if args.ignore:
        with open(args.ignore) as f:
            ignore = f.read()
    write("custom/ignore_classes.txt", ignore)

    config["code"] = "_" + args.code
    config["num_clusters"] = len(seed_lines)
    # INH and PCC are (classes+resources) wide, EP is one column per entrypoint
    config["node_dimension"] = 2 * (len(nodes) + len(tables)) + len(entrypoints)
    write("custom/gcnconfig_%s.json" % args.code, json.dumps(config, indent=1))

    print("classes=%d tables=%d entrypoints=%d num_clusters=%d node_dimension=%d"
          % (len(nodes), len(tables), len(entrypoints), config["num_clusters"],
             config["node_dimension"]))


if __name__ == "__main__":
    main()
