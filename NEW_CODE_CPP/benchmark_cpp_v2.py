import os
import sys
import subprocess
import glob
import time
import argparse
import csv

def parse_output(output_str):
    """
    Parses the stdout from the C++ solver.
    """
    status = "UNKNOWN"
    time_s = 0.0
    conflicts = 0
    restarts = 0
    lbd = 0.0
    glue = 0.0
    
    lines = output_str.strip().split('\n')
    for line in lines:
        if line.startswith("s SAT") or line == "SAT":
            status = "SAT"
        elif line.startswith("s UNSAT") or line == "UNSAT":
            status = "UNSAT"
        elif line.startswith("c Time:"):
            try: time_s = float(line.split()[2])
            except: pass
        elif line.startswith("c Conflicts:"):
            try: conflicts = int(line.split()[2])
            except: pass
        elif line.startswith("c Restarts:"):
            try: restarts = int(line.split()[2])
            except: pass
        elif line.startswith("c STATS"):
            # Format: c STATS Conflicts=123 Restarts=5 LBD=4.5 Glue=0.1
            try:
                parts = line.split()
                for p in parts:
                    if "Restarts=" in p: restarts = int(p.split("=")[1])
                    if "LBD=" in p: lbd = float(p.split("=")[1])
                    if "Glue=" in p: glue = float(p.split("=")[1])
            except: pass
                
    return status, time_s, conflicts, restarts, lbd, glue

def run_solver(binary_path, cnf_file, use_rl=False, timeout=30):
    cmd = [binary_path, cnf_file]
    if use_rl:
        cmd.append("--rl")
        
    try:
        # Use Popen to capture partial output if timeout happens
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True
        )
        try:
            stdout, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, _ = process.communicate()
            return "TIMEOUT", timeout, 0, 0, 0.0, 0.0 # Return empty or partial stats if you want partial parsing
            # Actually, let's parse stdout anyway to get partial stats!
            st, t, c, r, l, g = parse_output(stdout)
            return "TIMEOUT", timeout, c, r, l, g

        return parse_output(stdout)
        
    except Exception as e:
        print(f"Error running {cmd}: {e}")
        return "ERROR", 0.0, 0, 0, 0.0, 0.0

def main():
    parser = argparse.ArgumentParser(description="Benchmark C++ Baseline vs RL Solver")
    parser.add_argument("--dir", required=True, help="Directory containing .cnf files")
    parser.add_argument("--solver", default="./solver", help="Path to compiled solver binary")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout per instance in seconds")
    parser.add_argument("--output", default="benchmark_results_detailed.txt", help="Output log file")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of instances (0 = all)")
    
    args = parser.parse_args()
    
    cnf_files = sorted(glob.glob(os.path.join(args.dir, "*.cnf")))
    if not cnf_files:
        print(f"No .cnf files found in {args.dir}")
        return
        
    if args.limit > 0:
        cnf_files = cnf_files[:args.limit]

    print(f"Found {len(cnf_files)} instances. Running benchmark (Timeout: {args.timeout}s)...")
    
    # Header for printing
    header_fmt = "{:<25} | {:<4} | {:<7} | {:<8} | {:<9} | {:<5} | {:<5} | {:<5}"
    header = header_fmt.format("Instance", "Mode", "Stat", "Time", "Confl", "Rest", "LBD", "Glue")
    print("-" * 90)
    print(header)
    print("-" * 90)
    
    results = []
    
    for f in cnf_files:
        basename = os.path.basename(f)
        
        # Run Baseline
        st1, t1, c1, r1, l1, g1 = run_solver(args.solver, f, use_rl=False, timeout=args.timeout)
        print(header_fmt.format(basename, "BL", st1, f"{t1:.4f}", c1, r1, f"{l1:.2f}", f"{g1:.2f}"))
        
        # Run RL
        st2, t2, c2, r2, l2, g2 = run_solver(args.solver, f, use_rl=True, timeout=args.timeout)
        print(header_fmt.format("", "RL", st2, f"{t2:.4f}", c2, r2, f"{l2:.2f}", f"{g2:.2f}"))
        print("-" * 90)
        
        results.append({
            "instance": basename,
            "bl": [st1, t1, c1, r1, l1, g1],
            "rl": [st2, t2, c2, r2, l2, g2]
        })

    # Summary
    # bl_wins = ... (omitted for brevity)
    
    # Write full log
    with open(args.output, "w") as f:
        f.write(header + "\n")
        f.write("-" * 90 + "\n")
        for r in results:
            d1, d2 = r['bl'], r['rl']
            f.write(header_fmt.format(r['instance'], "BL", d1[0], f"{d1[1]:.4f}", d1[2], d1[3], f"{d1[4]:.2f}", f"{d1[5]:.2f}") + "\n")
            f.write(header_fmt.format("", "RL", d2[0], f"{d2[1]:.4f}", d2[2], d2[3], f"{d2[4]:.2f}", f"{d2[5]:.2f}") + "\n")
            f.write("-" * 90 + "\n")
        
    print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    main()
