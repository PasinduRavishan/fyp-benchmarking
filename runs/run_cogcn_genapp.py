import os
import sys
import json
import csv
import numpy as np
import torch
import random

# Add paths
sys.path.append(os.path.abspath("tools/cogcn/cogcn"))
sys.path.append(os.path.abspath("metrics"))

from model import GCNAE
from optimizer import compute_structure_loss, compute_attribute_loss, update_o1, update_o2
from utils import load_data_cma, preprocess_graph
from kmeans import Clustering

import metrics as metrics_mod

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def run_single_seed(dataset_dir, nodes, k=6, seed=0, preepochs=350, epochs=300, lr=0.01, lambda1=0.1, lambda2=0.1, lambda3=0.8, hidden1=64, hidden2=32, dropout=0.2):
    set_seed(seed)
    
    adj, features = load_data_cma(dataset_dir)
    n_nodes, feat_dim = features.shape

    # preprocess graph
    adj_norm = preprocess_graph(adj)

    model = GCNAE(feat_dim, hidden1, hidden2, dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    gamma = 0.98
    schedule_update_interval = 400
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=gamma)

    init_value = [1./n_nodes] * n_nodes
    o_1 = torch.FloatTensor(init_value)
    o_2 = torch.FloatTensor(init_value)

    lossfn = torch.nn.MSELoss(reduction='none')

    l1 = lambda1 / (lambda1 + lambda2)
    l2 = lambda2 / (lambda1 + lambda2)

    kmeans = Clustering(k)

    # Pretrain
    for epoch in range(preepochs):
        model.train()
        optimizer.zero_grad()
        recon, embed = model(features, adj_norm)

        structure_loss = compute_structure_loss(adj_norm, embed, o_1)
        attribute_loss = compute_attribute_loss(lossfn, features, recon, o_2)

        loss = l1 * structure_loss + l2 * attribute_loss
        loss.backward()
        optimizer.step()

    # Init clusters
    recon, embed = model(features, adj_norm)
    kmeans.cluster(embed)

    # Main train
    for epoch in range(epochs):
        o_1 = update_o1(adj_norm, embed)
        o_2 = update_o2(features, recon)

        if (epoch+1) % schedule_update_interval == 0:
            scheduler.step()

        model.train()
        optimizer.zero_grad()
        recon, embed = model(features, adj_norm)
        kmeans.cluster(embed)

        structure_loss = compute_structure_loss(adj_norm, embed, o_1)
        attribute_loss = compute_attribute_loss(lossfn, features, recon, o_2)
        clustering_loss = kmeans.get_loss(embed)

        loss = (lambda1 * structure_loss) + (lambda2 * attribute_loss) + (lambda3 * clustering_loss)
        loss.backward()
        optimizer.step()

    membership = kmeans.get_membership()
    partition = {node: int(membership[i]) for i, node in enumerate(nodes)}
    return partition

def main():
    dataset_name = "genapp"
    data_dir = f"tools/cogcn/cogcn/data/apps/{dataset_name}"
    nodes_csv = f"outputs/graphs/{dataset_name}/nodes.csv"
    edges_csv = f"outputs/graphs/{dataset_name}/edges.csv"
    methods_csv = f"outputs/graphs/{dataset_name}/methods.csv"
    method_calls_csv = f"outputs/graphs/{dataset_name}/method_calls.csv"

    # Load nodes
    with open(nodes_csv) as f:
        nodes = [line.strip() for line in f if line.strip()][1:]

    edges = metrics_mod.load_edges_csv(edges_csv)
    methods_by_class = metrics_mod.load_methods_csv(methods_csv) if os.path.exists(methods_csv) else None
    method_calls = metrics_mod.load_method_calls_csv(method_calls_csv) if os.path.exists(method_calls_csv) else None

    k = 6
    n_runs = 10
    all_results = []
    partitions = []

    print(f"--- Running CoGCN on {dataset_name} with K={k} for {n_runs} seeds ---")

    for seed in range(n_runs):
        partition = run_single_seed(data_dir, nodes, k=k, seed=seed)
        partitions.append(partition)
        
        res = metrics_mod.compute_all(partition, edges, methods_by_class, method_calls)
        all_results.append(res)
        print(f"Seed {seed}: SM={res['SM']:.4f}, ICP={res['ICP']:.4f}, IFN={res['IFN']:.4f}, NED={res['NED']:.4f}, CHM={res.get('CHM',0):.4f}, CHD={res.get('CHD',0):.4f}, BCP_uni={res.get('BCP_uniform',0):.4f}, BCP_ent={res.get('BCP_entropy',0):.4f}")

    # Save best partition JSON (seed 0 or best SM)
    best_idx = 0
    os.makedirs("outputs", exist_ok=True)
    out_json = f"outputs/cogcn_{dataset_name}.json"
    with open(out_json, "w") as f:
        json.dump(partitions[best_idx], f, indent=2)
    print(f"Saved partition JSON to {out_json}")

    # Compute summary statistics
    metrics_keys = ["SM", "ICP", "IFN", "NED", "CHM", "CHD", "BCP_uniform", "BCP_entropy"]
    means = {}
    std_devs = {}

    for key in metrics_keys:
        vals = [r[key] for r in all_results if key in r]
        means[key] = float(np.mean(vals))
        std_devs[key] = float(np.std(vals))

    # Generate Markdown Report
    report_lines = [
        f"# CoGCN 10-Run Reproducibility Report for `{dataset_name}`",
        "",
        f"This report records the individual metrics and aggregate statistics for 10 runs of CoGCN with different random seeds (0-9) on the `{dataset_name}` dataset using $K = {k}$ clusters.",
        "",
        "## Individual Runs",
        "",
        "| Run | Seed | SM | ICP | IFN | NED | CHM | CHD | BCP_uni | BCP_ent |",
        "|-----|------|----|-----|-----|-----|-----|-----|---------|---------|"
    ]

    for i, r in enumerate(all_results):
        report_lines.append(
            f"| {i+1} | {i} | {r['SM']:.4f} | {r['ICP']:.4f} | {r['IFN']:.2f} | {r['NED']:.4f} | {r.get('CHM',0):.4f} | {r.get('CHD',0):.4f} | {r.get('BCP_uniform',0):.4f} | {r.get('BCP_entropy',0):.4f} |"
        )

    report_lines.extend([
        "",
        "## Summary Statistics (Mean & Std Dev)",
        "",
        "| Metric | Mean | Std Dev |",
        "|--------|------|---------|"
    ])

    for key in metrics_keys:
        report_lines.append(f"| {key} | {means[key]:.4f} | {std_devs[key]:.4f} |")

    report_md_path = f"runs/cogcn_{dataset_name}_reproducibility.md"
    with open(report_md_path, "w") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"Saved reproducibility report to {report_md_path}")

    # Output CSV row
    commit_hash = "f6f3f4b2580d31b7d8dcc31ce3e3676f4cceaaaa"
    date_str = "2026-07-20"
    runner = "Antigravity"
    notes = f"mean of 10 runs; CHM={means['CHM']:.3f} CHD={means['CHD']:.3f} BCP_entropy={means['BCP_entropy']:.3f}; Test drivers and entrypoints; K={k}"
    
    csv_row = f"CoGCN,{dataset_name},{commit_hash},canonical,{means['SM']:.4f},{means['ICP']:.4f},{means['IFN']:.4f},{means['NED']:.4f},{means['BCP_entropy']:.4f},,,,,{date_str},{runner},{notes}"
    print("\n--- RESULTS.CSV ROW TO APPEND ---")
    print(csv_row)

if __name__ == "__main__":
    main()
