import os
import subprocess
import json
import time
import argparse
import sys

# Configuration
# Assumes the minisat binary is at ./minisat/core/minisat relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MINISAT_BIN = os.path.join(BASE_DIR, "minisat", "core", "minisat")
TIMEOUT = 30  # seconds

def parse_minisat_output(output):
    """
    Parses MiniSat stdout to extract metrics.
    """
    stats = {
        "status": "UNKNOWN",
        "time": None,
        "conflicts": None,
        "restarts": None
    }
    
    # Status detection
    if "SATISFIABLE" in output:
        stats["status"] = "SAT"
    elif "UNSATISFIABLE" in output:
        stats["status"] = "UNSAT"
    elif "INDETERMINATE" in output:
        stats["status"] = "INDET"
    
    # Parse lines for stats
    for line in output.split('\n'):
        if line.startswith("conflicts"):
            try:
                # Format: conflicts : 1234  ( 1234 /sec)
                parts = line.split(":")
                val = parts[1].split("(")[0].strip()
                stats["conflicts"] = int(val)
            except: pass
        elif line.startswith("restarts"):
            try:
                # Format: restarts : 12
                parts = line.split(":")
                stats["restarts"] = int(parts[1].strip())
            except: pass
        elif line.startswith("CPU time"):
            try:
                # Format: CPU time : 0.123 s
                parts = line.split(":")
                val = parts[1].replace("s", "").strip()
                stats["time"] = float(val)
            except: pass

    return stats

def run_solver(cnf_path, use_rl=False, rl_step=100):
    """
    Runs MiniSat on a single CNF file.
    """
    cmd = [MINISAT_BIN]
    if use_rl:
        cmd.append("-rl")
        cmd.append(f"-rl-step={rl_step}")
    
    cmd.append(cnf_path)
    
    start_time = time.time()
    try:
        # Run with timeout
        proc = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=TIMEOUT
        )
        return parse_minisat_output(proc.stdout)
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "time": TIMEOUT, "conflicts": -1, "restarts": -1}
    except Exception as e:
        return {"status": f"ERROR: {str(e)}", "time": 0, "conflicts": -1, "restarts": -1}

def main():
    parser = argparse.ArgumentParser(description="Simple MiniSat Benchmark Script")
    parser.add_argument("input_dir", help="Directory containing .cnf files to benchmark")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.exists(input_dir):
        print(f"Error: Directory '{input_dir}' does not exist.")
        sys.exit(1)

    if not os.path.exists(MINISAT_BIN):
        print(f"Error: MiniSat binary not found at {MINISAT_BIN}")
        print("Please compile MiniSat first.")
        sys.exit(1)

    # 1. Gather all CNF files
    cnf_files = []
    print(f"Searching for .cnf files in {input_dir}...")
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.endswith(".cnf"):
                cnf_files.append(os.path.join(root, f))
    
    cnf_files.sort()
    total_files = len(cnf_files)
    print(f"Found {total_files} CNF files.")
    
    if total_files == 0:
        print("No CNF files found. Exiting.")
        sys.exit(0)

    # 2. Run Benchmarks
    results = []
    
    # Summary Counters
    summary = {
        "total": 0,
        "baseline_wins": 0,
        "rl_wins": 0,
        "ties": 0
    }

    print("\nStarting Benchmark Run...")
    print(f"{'Instance':<40} | {'BL Time':<10} | {'RL Time':<10} | {'Winner':<10}")
    print("-" * 80)

    for i, cnf_path in enumerate(cnf_files):
        instance_name = os.path.basename(cnf_path)
        
        # Print valid row prefix
        print(f"{instance_name:<40} | ", end="", flush=True)
        
        # Run Baseline
        res_bl = run_solver(cnf_path, use_rl=False)
        print("...", end="", flush=True) # visual feedback
        
        # Run RL
        res_rl = run_solver(cnf_path, use_rl=True, rl_step=100)
        
        # Determine Winner (Lower Time preferred for SAT solvers, if both solved)
        bl_time = res_bl.get("time") or float('inf')
        rl_time = res_rl.get("time") or float('inf')
        
        winner = "TIE"
        if res_bl["status"] in ["SAT", "UNSAT"] and res_rl["status"] not in ["SAT", "UNSAT"]:
            winner = "BASELINE"
        elif res_rl["status"] in ["SAT", "UNSAT"] and res_bl["status"] not in ["SAT", "UNSAT"]:
            winner = "RL"
        elif res_bl["status"] == res_rl["status"] and res_bl["status"] in ["SAT", "UNSAT"]:
            if bl_time < rl_time:
                winner = "BASELINE"
            elif rl_time < bl_time:
                winner = "RL"
        
        # Update summary
        summary["total"] += 1
        if winner == "BASELINE":
            summary["baseline_wins"] += 1
        elif winner == "RL":
            summary["rl_wins"] += 1
        else:
            summary["ties"] += 1

        # Clear visual feedback and print result
        sys.stdout.write("\b\b\b") 
        val_bl = f"{bl_time:>9.4f}s" if bl_time != float('inf') else "  TIMEOUT "
        val_rl = f"{rl_time:>9.4f}s" if rl_time != float('inf') else "  TIMEOUT "
        print(f"{val_bl} | {val_rl} | {winner}")

        # Record detailed entry
        results.append({
            "instance": instance_name,
            "path": cnf_path,
            "baseline": res_bl,
            "rl": res_rl,
            "winner": winner
        })

    # 3. Save Results
    # Format: result-HH-MM.json
    RESULTS_DIR = os.path.join(BASE_DIR, "results")
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    timestamp_str = time.strftime("%d-%m-%Y-%H-%M")
    output_filename = f"result-{timestamp_str}.json"
    output_path = os.path.join(RESULTS_DIR, output_filename)
    
    # Save JSON
    final_data = {
        "meta": {
            "input_directory": input_dir,
            "date": time.strftime("%Y-%m-%d"),
            "time": timestamp_str
        },
        "summary": summary,
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(final_data, f, indent=4)

    print("-" * 80)
    print(f"Benchmark completed. Results saved to: {output_path}")
    print("\n=== SUMMARY ===")
    print(f"Total Instances: {summary['total']}")
    print(f"Baseline Wins:   {summary['baseline_wins']}")
    print(f"RL Wins:         {summary['rl_wins']}")
    print(f"Ties:            {summary['ties']}")
    print("===============")

if __name__ == "__main__":
    main()
