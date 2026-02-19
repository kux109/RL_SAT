
import os
import subprocess
import json
import time
import argparse
import statistics
from pathlib import Path

# Configurations to test
CONFIGS = {
    "Baseline (MiniSat)": [],
    "RL_Full_Context": ["-rl"],
    "RL_No_Glue": ["-rl", "-rl-no-glue"],
    "RL_No_LBD": ["-rl", "-rl-no-lbd"],
    "RL_Context_Blind": ["-rl", "-rl-dummy"]
}

def parse_output(output):
    """Extracts CPU time and conflicts from MiniSat output."""
    time_taken = None
    conflicts = None
    result = "UNKNOWN"
    
    for line in output.splitlines():
        if "CPU time" in line:
            try:
                time_taken = float(line.split(":")[1].replace("s", "").strip())
            except: pass
        if "conflicts" in line and ":" in line:
            try:
                parts = line.split(":")
                val = parts[1].strip().split()[0]
                conflicts = int(val)
            except: pass
        if "SATISFIABLE" in line:
            result = "SAT"
        if "UNSATISFIABLE" in line:
            result = "UNSAT"
            
    return result, time_taken, conflicts

def run_solver(solver_path, cnf_path, flags):
    cmd = [solver_path] + flags + [cnf_path]
    print(f"Running: {' '.join(cmd)}")
    try:
        start = time.time()
        # Run with timeout of 60s per instance for ablation
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = proc.stdout
        result, cpu_time, conflicts = parse_output(output)
        if cpu_time is None:
            cpu_time = time.time() - start # Fallback
            
        return {
            "result": result,
            "time": cpu_time,
            "conflicts": conflicts,
            "timeout": False
        }
    except subprocess.TimeoutExpired:
        return {
            "result": "TIMEOUT",
            "time": 60.0,
            "conflicts": -1,
            "timeout": True
        }
    except Exception as e:
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Run RL-SAT Ablation Study")
    parser.add_argument("--cnf", required=True, help="Path to CNF file or directory")
    parser.add_argument("--solver", default="./minisat/core/minisat", help="Path to minisat binary")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of instances (0=all)")
    parser.add_argument("--output", default="ablation_summary.txt", help="Output text file")
    args = parser.parse_args()

    # Resolve paths
    solver_path = Path(args.solver).resolve()
    if not solver_path.exists():
        print(f"Error: Solver not found at {solver_path}")
        return

    files = []
    p = Path(args.cnf).resolve()
    if p.is_dir():
        files = list(p.rglob("*.cnf"))
        files.sort()
    else:
        files = [p]
    
    if args.limit > 0:
        files = files[:args.limit]
        print(f"Limiting to first {args.limit} files.")

    results = {cfg: {"total_time": 0, "solved": 0, "conflicts": []} for cfg in CONFIGS}
    
    # Log to file and stdout
    def log(msg):
        print(msg)
        with open(args.output, "a") as f:
            f.write(msg + "\n")

    # Clear previous log
    with open(args.output, "w") as f:
        f.write("=== RL-SAT Ablation Study Log ===\n\n")

    # Run
    for cnf in files:
        log(f"\n--- Benchmarking: {cnf.name} ---")
        for cfg_name, flags in CONFIGS.items():
            res = run_solver(str(solver_path), str(cnf), flags)
            
            # Store
            if res.get("timeout"):
                log(f"  [{cfg_name}] TIMEOUT")
            else:
                log(f"  [{cfg_name}] {res['result']} in {res['time']:.4f}s ({res['conflicts']} confl)")
                results[cfg_name]["solved"] += 1
                results[cfg_name]["total_time"] += res["time"]
                if res["conflicts"]:
                    results[cfg_name]["conflicts"].append(res["conflicts"])

    # Summary
    log("\n\n=== ABLATION RESULTS SUMMARY ===")
    log(f"{'Configuration':<25} | {'Solved':<8} | {'Avg Time':<10} | {'Avg Confl':<10}")
    log("-" * 65)
    
    for cfg, data in results.items():
        n = max(1, data["solved"]) # Avoid div/0 if none solved
        avg_time = data["total_time"] / n
        avg_confl = statistics.mean(data["conflicts"]) if data["conflicts"] else 0
        log(f"{cfg:<25} | {data['solved']:<8} | {avg_time:<10.4f} | {avg_confl:<10.1f}")
        
    with open("ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)
        log("\nFull results saved to ablation_results.json")

if __name__ == "__main__":
    main()
