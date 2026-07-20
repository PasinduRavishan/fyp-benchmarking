import os
import glob
import re
import csv
import argparse

def parse_cs_file(filepath):
    with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
        content = f.read()

    ns_match = re.search(r'namespace\s+([A-Za-z0-9_.]+)', content)
    namespace = ns_match.group(1) if ns_match else "WebApplication1"

    class_matches = re.finditer(r'(?:public|protected|private|internal)?\s*(?:partial\s+)?(class|interface|struct)\s+([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_.,\s]+))?', content)
    
    classes = []
    for match in class_matches:
        kind = match.group(1)
        name = match.group(2)
        bases_str = match.group(3)
        fqn = f"{namespace}.{name}"
        
        if name in ('and', 'Test', 'UnitTest1', 'DodawanieProduktu', 'DodawanieWpisu') or not fqn.startswith("WebApplication1."):
            continue

        bases = []
        if bases_str:
            for b in bases_str.split(','):
                b_clean = b.strip().split()[-1]
                if b_clean:
                    bases.append(b_clean)
        
        classes.append({
            'fqn': fqn,
            'name': name,
            'kind': kind,
            'bases': bases,
            'namespace': namespace,
            'content': content
        })
    return classes

def main():
    parser = argparse.ArgumentParser(description="C# Graph Extractor")
    parser.add_argument("repo_path", help="Path to C# repository")
    parser.add_argument("output_dir", help="Output directory for CSV files")
    args = parser.parse_args()

    cs_files = glob.glob(os.path.join(args.repo_path, "**/*.cs"), recursive=True)
    
    all_classes = []
    for f in cs_files:
        if "AssemblyInfo.cs" in f or "SeleniumTests" in f:
            continue
        all_classes.extend(parse_cs_file(f))

    nodes = set()
    name_to_fqns = {}
    for c in all_classes:
        fqn = c['fqn']
        nodes.add(fqn)
        name_to_fqns.setdefault(c['name'], set()).add(fqn)

    def resolve_type(type_name, current_ns):
        type_name = re.sub(r'<.*?>', '', type_name).strip()
        type_name = type_name.replace('[]', '').strip()

        if not type_name:
            return None

        if type_name in nodes:
            return type_name

        fqn_in_ns = f"{current_ns}.{type_name}"
        if fqn_in_ns in nodes:
            return fqn_in_ns

        if type_name in name_to_fqns:
            candidates = name_to_fqns[type_name]
            if len(candidates) == 1:
                return list(candidates)[0]
            for cand in candidates:
                if cand.startswith(current_ns):
                    return cand
            return list(candidates)[0]
        return None

    edges_map = {}

    def add_edge(src, dst, etype, weight=1):
        if not src or not dst or src == dst:
            return
        if src not in nodes or dst not in nodes:
            return
        key = (src, dst, etype)
        edges_map[key] = edges_map.get(key, 0) + weight

    methods_list = []
    method_calls_list = []

    for c in all_classes:
        src = c['fqn']
        current_ns = c['namespace']
        content = c['content']

        for base_name in c['bases']:
            dst = resolve_type(base_name, current_ns)
            if dst:
                etype = "IMPLEMENTS" if base_name.startswith("I") and len(base_name) > 1 and base_name[1].isupper() else "EXTENDS"
                add_edge(src, dst, etype, 1)

        field_matches = re.finditer(r'(?:public|protected|private|internal)\s+(?:static\s+)?([A-Za-z0-9_<>,?\s]+?)\s+([A-Za-z0-9_]+)\s*(?:;|\{)', content)
        for fm in field_matches:
            type_str = fm.group(1).strip()
            for word in re.findall(r'\b[A-Za-z0-9_]+\b', type_str):
                dst = resolve_type(word, current_ns)
                if dst:
                    add_edge(src, dst, "FIELD", 1)

        new_matches = re.finditer(r'new\s+([A-Za-z0-9_]+)\s*\(', content)
        for nm in new_matches:
            type_name = nm.group(1)
            dst = resolve_type(type_name, current_ns)
            if dst:
                add_edge(src, dst, "CALL", 1)
                method_calls_list.append({
                    "srcClass": src,
                    "srcMethod": "unknown",
                    "dstClass": dst,
                    "dstMethod": "<init>"
                })

        method_matches = re.finditer(r'(?:public|protected|private|internal)\s+(?:virtual|override|async|static\s+)?([A-Za-z0-9_<>,?\s]+?)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)', content)
        for mm in method_matches:
            ret_type = mm.group(1).strip()
            m_name = mm.group(2)
            params_str = mm.group(3)

            if m_name in ('if', 'for', 'while', 'switch', 'catch', 'using', 'lock'):
                continue

            params = [p.strip().split()[0] for p in params_str.split(',') if p.strip()] if params_str else []
            methods_list.append({
                "class": src,
                "method": m_name,
                "returnType": ret_type,
                "parameters": ";".join(params)
            })

            for p in params:
                for word in re.findall(r'\b[A-Za-z0-9_]+\b', p):
                    dst = resolve_type(word, current_ns)
                    if dst:
                        add_edge(src, dst, "FIELD", 1)

        for target_class in all_classes:
            dst = target_class['fqn']
            tname = target_class['name']
            if dst == src:
                continue

            var_pattern = r'\b' + re.escape(tname) + r'\b|\b_' + re.escape(tname[0].lower() + tname[1:]) + r'\b'
            call_matches = len(re.findall(var_pattern, content))
            if call_matches > 0:
                add_edge(src, dst, "CALL", call_matches)
                method_calls_list.append({
                    "srcClass": src,
                    "srcMethod": "unknown",
                    "dstClass": dst,
                    "dstMethod": "call"
                })

    os.makedirs(args.output_dir, exist_ok=True)
    
    sorted_nodes = sorted(list(nodes))
    nodes_path = os.path.join(args.output_dir, "nodes.csv")
    with open(nodes_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["class"])
        for n in sorted_nodes:
            writer.writerow([n])

    edges_path = os.path.join(args.output_dir, "edges.csv")
    with open(edges_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["src", "dst", "type", "weight"])
        for (src, dst, etype), count in sorted(edges_map.items()):
            writer.writerow([src, dst, etype, count])

    methods_path = os.path.join(args.output_dir, "methods.csv")
    with open(methods_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["class", "method", "returnType", "parameters"])
        writer.writeheader()
        writer.writerows(methods_list)

    method_calls_path = os.path.join(args.output_dir, "method_calls.csv")
    with open(method_calls_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["srcClass", "srcMethod", "dstClass", "dstMethod"])
        writer.writeheader()
        writer.writerows(method_calls_list)

    print(f"Extracted {len(sorted_nodes)} nodes and {len(edges_map)} unique edges.")
    print(f"Saved to {args.output_dir}")

if __name__ == "__main__":
    main()
