import os
import glob
import re
import csv
import argparse

def parse_cobol_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    content = "".join(lines)
    
    # Extract PROGRAM-ID
    prog_match = re.search(r'PROGRAM-ID\.\s*([A-Za-z0-9_-]+)', content, re.IGNORECASE)
    if not prog_match:
        return None
    
    prog_name = prog_match.group(1).upper()
    
    # Extract variables and their VALUE string literals
    # e.g., 77 LGACDB02 PIC X(8) VALUE 'LGACDB02'
    var_values = {}
    val_matches = re.finditer(r'(?:01|77|05|10)\s+([A-Za-z0-9_-]+)\s+.*?VALUE\s+[\'\"]([A-Za-z0-9_-]+)[\'\"]', content, re.IGNORECASE)
    for vm in val_matches:
        var_name = vm.group(1).upper()
        var_val = vm.group(2).upper()
        var_values[var_name] = var_val

    # Extract EXEC CICS LINK / XCTL
    cics_calls = []
    link_matches = re.finditer(r'EXEC\s+CICS\s+(?:LINK|XCTL)\s+PROGRAM\s*\(\s*([A-Za-z0-9_\-\'\"]+)\s*\)', content, re.IGNORECASE)
    for lm in link_matches:
        raw_target = lm.group(1).strip().strip('\'"').upper()
        if raw_target in var_values:
            target = var_values[raw_target]
        else:
            target = raw_target
        cics_calls.append(target)

    # Extract CALL statements
    call_matches = re.finditer(r'\bCALL\s+[\'\"]([A-Za-z0-9_-]+)[\'\"]', content, re.IGNORECASE)
    for cm in call_matches:
        cics_calls.append(cm.group(1).upper())

    # Extract COPY statements (copybooks)
    copybooks = []
    copy_matches = re.finditer(r'\bCOPY\s+([A-Za-z0-9_-]+)', content, re.IGNORECASE)
    for cpm in copy_matches:
        copybooks.append(cpm.group(1).upper())

    return {
        'program': prog_name,
        'filepath': filepath,
        'var_values': var_values,
        'cics_calls': cics_calls,
        'copybooks': copybooks,
        'content': content
    }

def main():
    parser = argparse.ArgumentParser(description="COBOL Graph Extractor")
    parser.add_argument("repo_path", help="Path to COBOL repository")
    parser.add_argument("output_dir", help="Output directory for CSV files")
    args = parser.parse_args()

    cbl_files = glob.glob(os.path.join(args.repo_path, "**/*.cbl"), recursive=True)
    
    programs = []
    for f in cbl_files:
        p_info = parse_cobol_file(f)
        if p_info:
            programs.append(p_info)

    nodes = set(p['program'] for p in programs)
    prog_map = {p['program']: p for p in programs}

    edges_map = {} # (src, dst, type) -> weight

    def add_edge(src, dst, etype, weight=1):
        if not src or not dst or src == dst:
            return
        if src not in nodes or dst not in nodes:
            return
        key = (src, dst, etype)
        edges_map[key] = edges_map.get(key, 0) + weight

    methods_list = []
    method_calls_list = []

    for p in programs:
        src = p['program']
        
        # 1. CICS / COBOL CALL edges
        for target in p['cics_calls']:
            if target in nodes:
                add_edge(src, target, "CALL", 1)
                method_calls_list.append({
                    "srcClass": src,
                    "srcMethod": "main",
                    "dstClass": target,
                    "dstMethod": "main"
                })

        # 2. Check string mentions of program names in code (additional calls or data references)
        for other_prog in nodes:
            if other_prog == src:
                continue
            # Check if program name appears as literal or variable in file
            matches = len(re.findall(r'\b' + re.escape(other_prog) + r'\b', p['content']))
            if matches > 0:
                add_edge(src, other_prog, "CALL", matches)
                method_calls_list.append({
                    "srcClass": src,
                    "srcMethod": "main",
                    "dstClass": other_prog,
                    "dstMethod": "main"
                })

        methods_list.append({
            "class": src,
            "method": "main",
            "returnType": "void",
            "parameters": ""
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
