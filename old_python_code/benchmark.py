import subprocess
import glob
import os
import csv
import re
import time
import argparse
import sys
from typing import Dict, List, Any

def parse_result_line(line: str) -> Dict[str, Any]:
    # Expected format: Result: SAT/UNSAT, time=X.XXXXs, conflicts=Y, decisions=Z, propagations=W
    data = {}
    if "Result:" not in line:
        return data
    
    parts = line.split(',')
    for part in parts:
        part = part.strip()
        if part.startswith("Result:"):
            data['status'] = part.split(':')[1].strip()
        elif part.startswith("time="):
            data['time'] = float(part.split('=')[1].replace('s', ''))
        elif part.startswith("conflicts="):
            data['conflicts'] = int(part.split('=')[1])
    return data

def get_avg_metrics_from_csv(csv_path: str) -> Dict[str, float]:
    metrics = {
        'avg_lbd': [],
        'glue_ratio': [],
        'restart_rate': []
    }
    
    if not os.path.exists(csv_path):
        return {}

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    if 'feat_avg_lbd' in row: metrics['avg_lbd'].append(float(row['feat_avg_lbd']))
                    if 'feat_glue_ratio' in row: metrics['glue_ratio'].append(float(row['feat_glue_ratio']))
                    if 'feat_rest_rate' in row: metrics['restart_rate'].append(float(row['feat_rest_rate']))
                except ValueError:
                    continue
    except Exception:
        return {}
        
    avg_metrics = {}
    for k, v in metrics.items():
        if v:
            avg_metrics[k] = sum(v) / len(v)
        else:
            avg_metrics[k] = 0.0
    return avg_metrics

def run_solver(mode: str, cnf_path: str, log_path: str, timeout: int = 60) -> Dict[str, Any]:
    cmd = [
        "python3", "run_solver.py",
        "--mode", mode,
        "--cnf", cnf_path,
        "--log", log_path
    ]
    if mode == "baseline":
        cmd.extend(["--heuristic", "vsids"]) 

    result_data = {'status': 'TIMEOUT', 'time': timeout, 'conflicts': 0}
    
    try:
        # Run process
        process = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout
        )
        # Parse stdout
        for line in process.stdout.splitlines():
            parsed = parse_result_line(line)
            if parsed:
                result_data.update(parsed)
                
    except subprocess.TimeoutExpired:
        print(f"  > {mode.upper()} Timed out after {timeout}s")
        result_data['status'] = 'TIMEOUT'
        
    # Get metrics from CSV even if timeout (as logs are flushed)
    csv_metrics = get_avg_metrics_from_csv(log_path)
    result_data.update(csv_metrics)
    
    # Cleanup log
    if os.path.exists(log_path):
        os.remove(log_path)
        
    return result_data

class DualLogger:
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def main():
    parser = argparse.ArgumentParser(description="Benchmark BL vs RL Solvers")
    parser.add_argument("--dir", type=str, default="test_cnfs", help="Directory containing .cnf files")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds per instance")
    args = parser.parse_args()

    # Setup Logging
    result_dir = "result"
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    log_file = os.path.join(result_dir, "results-log.txt")
    # Redirect stdout to DualLogger
    original_stdout = sys.stdout
    sys.stdout = DualLogger(log_file)

    files = glob.glob(os.path.join(args.dir, "*.cnf"))
    files.sort()
    
    if not files:
        print(f"No .cnf files found in {args.dir}")
        return

    print(f"Found {len(files)} instances. Running benchmark (Timeout: {args.timeout}s)...")
    print(f"Logging results to: {log_file}")
    print("-" * 100)
    print(f"{'Instance':<20} | {'Mode':<5} | {'Status':<7} | {'Time(s)':<8} | {'Conflicts':<9} | {'Avg LBD':<7} | {'Glue%':<5} | {'Rest%':<5}")
    print("-" * 100)

    results = []

    for cnf_file in files:
        basename = os.path.basename(cnf_file)
        
        # Run Baseline
        bl_res = run_solver("baseline", cnf_file, "temp_bl.csv", args.timeout)
        print(f"{basename:<20} | {'BL':<5} | {bl_res.get('status', 'N/A'):<7} | {bl_res.get('time', 0):<8.4f} | {bl_res.get('conflicts', 0):<9} | {bl_res.get('avg_lbd', 0):<7.2f} | {bl_res.get('glue_ratio', 0):<5.2f} | {bl_res.get('restart_rate', 0):<5.2f}")
        
        # Run RL
        rl_res = run_solver("rl", cnf_file, "temp_rl.csv", args.timeout)
        print(f"{'':<20} | {'RL':<5} | {rl_res.get('status', 'N/A'):<7} | {rl_res.get('time', 0):<8.4f} | {rl_res.get('conflicts', 0):<9} | {rl_res.get('avg_lbd', 0):<7.2f} | {rl_res.get('glue_ratio', 0):<5.2f} | {rl_res.get('restart_rate', 0):<5.2f}")
        print("-" * 100)

        results.append({
            'instance': basename,
            'bl_time': bl_res.get('time'),
            'rl_time': rl_res.get('time'),
            'bl_status': bl_res.get('status'),
            'rl_status': rl_res.get('status')
        })

    # Summary
    wins_bl = sum(1 for r in results if r['bl_time'] < r['rl_time'] and r['bl_status'] != 'TIMEOUT')
    wins_rl = sum(1 for r in results if r['rl_time'] < r['bl_time'] and r['rl_status'] != 'TIMEOUT')
    
    print("\nSummary:")
    print(f"Baseline Faster: {wins_bl}")
    print(f"RL Faster:       {wins_rl}")

if __name__ == "__main__":
    main()
