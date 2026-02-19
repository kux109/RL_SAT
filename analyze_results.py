import json
import os
import glob
import sys

# Path to results
RESULTS_DIR = "minisat_rl_code/results"

def analyze():
    print("=== RL Agent Activity Analysis ===\n")
    
    files = glob.glob(os.path.join(RESULTS_DIR, "*.json"))
    if not files:
        print("No result files found.")
        return

    total_instances_all = 0
    total_identical_conflicts = 0

    for fpath in files:
        with open(fpath, 'r') as f:
            data = json.load(f)
        
        fname = os.path.basename(fpath)
        dataset = data.get("meta", {}).get("input_directory", "unknown").split("/")[-1]
        results = data.get("results", [])
        
        n_total = len(results)
        n_identical = 0
        n_rl_better = 0
        n_bl_better = 0
        
        if n_total == 0: continue

        for r in results:
            bl_c = r["baseline"].get("conflicts", -1)
            rl_c = r["rl"].get("conflicts", -1)
            
            # Count identical conflicts (Solver took exact same path)
            if bl_c == rl_c and bl_c != -1:
                n_identical += 1
            elif rl_c < bl_c and rl_c != -1:
                n_rl_better += 1
            elif bl_c < rl_c and bl_c != -1:
                n_bl_better += 1
        
        total_instances_all += n_total
        total_identical_conflicts += n_identical
        
        identical_rate = (n_identical / n_total) * 100
        print(f"File: {fname} (Dataset: {dataset})")
        print(f"  Instances: {n_total}")
        print(f"  Identical Conflicts: {n_identical} ({identical_rate:.1f}%)")
        print(f"  BL Better Conflicts: {n_bl_better}")
        print(f"  RL Better Conflicts: {n_rl_better}")
        print("-" * 40)

    if total_instances_all > 0:
        global_rate = (total_identical_conflicts / total_instances_all) * 100
        print(f"\nOVERALL: {global_rate:.1f}% of instances have IDENTICAL conflict counts.")
        if global_rate > 90:
            print("CONCLUSION: The RL Agent is effectively INACTIVE or making no difference in search trajectory.")
        elif global_rate > 50:
            print("CONCLUSION: The RL Agent has minimal impact.")
        else:
            print("CONCLUSION: The RL Agent is active.")
    else:
        print("No instances to analyze.")

if __name__ == "__main__":
    analyze()
