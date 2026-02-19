
import json
import os
import re
import matplotlib.pyplot as plt
import glob
import sys

# Ensure output directory exists
OUTPUT_DIR = "minisat_rl_code/Final_results"
if not os.path.exists(OUTPUT_DIR):
    print(f"Error: {OUTPUT_DIR} not found.")
    sys.exit(1)

# Set Matplotlib theme for academic/publication quality
plt.style.use('ggplot')
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
plt.rcParams['figure.dpi'] = 300
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['lines.linewidth'] = 2.0

def parse_json_benchmark(filepath):
    """
    Parses a benchmark JSON file.
    Returns: dataset_name, data_list
    """
    dataset_name = os.path.basename(filepath).replace(".json", "").replace("result-", "")
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    parsed_data = []
    for entry in data.get("results", []):
        parsed_data.append({
            "instance": entry.get("instance"),
            "bl_time": entry["baseline"]["time"],
            "rl_time": entry["rl"]["time"],
            "bl_status": entry["baseline"]["status"],
            "rl_status": entry["rl"]["status"],
            "bl_conflicts": entry["baseline"]["conflicts"],
            "rl_conflicts": entry["rl"]["conflicts"]
        })
    return dataset_name, parsed_data

def plot_cactus(dataset_name, data):
    """
    Generates a Cactus Plot (Solved Instances vs Time).
    """
    bl_times = sorted([d["bl_time"] for d in data if d["bl_status"] == "SAT"])
    rl_times = sorted([d["rl_time"] for d in data if d["rl_status"] == "SAT"])
    
    plt.figure(figsize=(10, 6))
    
    # Plot lines with improved styling
    plt.plot(range(1, len(bl_times) + 1), bl_times, 
             label='Baseline (MiniSat)', color='#e74c3c', linestyle='-', marker='o', markersize=4, markevery=5)
    plt.plot(range(1, len(rl_times) + 1), rl_times, 
             label='RL-Augmented', color='#2ecc71', linestyle='--', marker='s', markersize=4, markevery=5)
    
    plt.xlabel("Number of Solved Instances")
    plt.ylabel("Time (s) [Log Scale]")
    plt.title(f"Cactus Plot: {dataset_name}")
    plt.legend(fancybox=True, framealpha=0.9, loc='lower right')
    plt.grid(True, which="both", ls="-", alpha=0.3)
    plt.yscale('log')
    
    plt.tight_layout()
    output_path = os.path.join(OUTPUT_DIR, f"{dataset_name}_cactus.png")
    plt.savefig(output_path)
    plt.close()
    print(f"Saved {output_path}")

def plot_scatter(dataset_name, data):
    """
    Generates a Scatter Plot (BL Time vs RL Time).
    """
    bl_vals = []
    rl_vals = []
    
    # Filter out timeouts for scatter plot to keep it clean
    valid_data = [d for d in data if d["bl_status"] != "TIMEOUT" and d["rl_status"] != "TIMEOUT"]
    
    for d in valid_data:
        bl_vals.append(d["bl_time"])
        rl_vals.append(d["rl_time"])

    if not bl_vals:
        return

    plt.figure(figsize=(8, 8))
    
    # Use different markers/colors for wins
    colors = ['#2ecc71' if r < b else '#e74c3c' for b, r in zip(bl_vals, rl_vals)]
    
    plt.scatter(bl_vals, rl_vals, c=colors, alpha=0.7, edgecolors='k', s=60, zorder=3)
    
    # Diagonal line (y=x)
    max_val = max(max(bl_vals), max(rl_vals))
    plt.plot([0, max_val], [0, max_val], 'k--', alpha=0.5, zorder=2, label="Equal Performance")
    
    plt.xlabel("Baseline Time (s)")
    plt.ylabel("RL Agent Time (s)")
    plt.title(f"Performance Comparison: {dataset_name}")
    
    # Add annotation for regions
    plt.text(max_val*0.8, max_val*0.1, "RL Win Region", fontsize=10, color='#2ecc71', fontweight='bold', ha='center',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))
    plt.text(max_val*0.2, max_val*0.9, "Baseline Win Region", fontsize=10, color='#e74c3c', fontweight='bold', ha='center',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

    plt.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    
    output_path = os.path.join(OUTPUT_DIR, f"{dataset_name}_scatter.png")
    plt.savefig(output_path)
    plt.close()
    print(f"Saved {output_path}")

def parse_ablation_text(filepath):
    """
    Parses an ablation text file to extract summary table.
    """
    filename = os.path.basename(filepath).replace(".txt", "")
    configs = []
    avg_times = []
    solved_counts = []
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    start_idx = -1
    for i, line in enumerate(lines):
        if "ABLATION RESULTS SUMMARY" in line:
            start_idx = i + 2
            break
            
    if start_idx == -1:
        return None, None, None, None
        
    for line in lines[start_idx:]:
        if "|" not in line: continue
        if "---" in line: continue
        
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4: continue
        
        configs.append(parts[0])
        try:
            solved_counts.append(int(parts[1]))
            avg_times.append(float(parts[2]))
        except ValueError:
            continue
            
    return filename, configs, solved_counts, avg_times

def plot_ablation(dataset_name, configs, solved, times):
    """
    Generates Bar Charts for Ablation Study using Matplotlib.
    """
    # 1. Avg Time Chart
    plt.figure(figsize=(10, 6))
    x_pos = range(len(configs))
    colors = ['#95a5a6', '#3498db', '#f39c12', '#e74c3c', '#9b59b6']
    
    bars = plt.bar(x_pos, times, color=colors[:len(configs)], edgecolor='black', alpha=0.8)
    
    plt.title(f"Ablation Study - Average Solve Time: {dataset_name}")
    plt.xlabel("") 
    plt.ylabel("Average Time (s)")
    plt.xticks(x_pos, configs, rotation=25, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.4)
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.01 * max(times), 
                 f"{height:.2f}s", ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    output_path_time = os.path.join(OUTPUT_DIR, f"{dataset_name}_ablation_time.png")
    plt.savefig(output_path_time)
    plt.close()
    print(f"Saved {output_path_time}")
    
    # 2. Solved Count Chart
    plt.figure(figsize=(10, 6))
    bars = plt.bar(x_pos, solved, color='#2ecc71', edgecolor='black', alpha=0.8)
    
    plt.title(f"Ablation Study - Solved Instances: {dataset_name}")
    plt.xlabel("")
    plt.ylabel("Solved Instances")
    plt.xticks(x_pos, configs, rotation=25, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.4)

    # Add value labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1, 
                 str(int(height)), ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    output_path_solved = os.path.join(OUTPUT_DIR, f"{dataset_name}_ablation_solved.png")
    plt.savefig(output_path_solved)
    plt.close()
    print(f"Saved {output_path_solved}")

def main():
    json_files = glob.glob(os.path.join(OUTPUT_DIR, "*.json"))
    for jf in json_files:
        name, data = parse_json_benchmark(jf)
        if data:
            plot_cactus(name, data)
            plot_scatter(name, data)
            
    txt_files = glob.glob(os.path.join(OUTPUT_DIR, "ablation-*.txt"))
    for tf in txt_files:
        name, configs, solved, times = parse_ablation_text(tf)
        if name and configs:
            plot_ablation(name, configs, solved, times)

if __name__ == "__main__":
    main()
