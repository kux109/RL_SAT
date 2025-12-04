#!/usr/bin/env python3
"""
Analyze benchmark results (pandas-free version).
"""
import sys
import csv
from collections import defaultdict

def load_csv(path):
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            r['time'] = float(r['time'])
            r['conflicts'] = int(r['conflicts'])
            r['decisions'] = int(r['decisions'])
            r['propagations'] = int(r['propagations'])
            rows.append(r)
    return rows

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_simple.py <results.csv>")
        sys.exit(1)
    
    rows = load_csv(sys.argv[1])
    
    print("="*60)
    print("BENCHMARK ANALYSIS")
    print("="*60)
    
    # Per-mode summary
    by_mode = defaultdict(list)
    for r in rows:
        by_mode[r['mode']].append(r)
    
    for mode, mode_rows in by_mode.items():
        solved = [r for r in mode_rows if r['status'] in ['SAT', 'UNSAT']]
        print(f"\n{mode.upper()}:")
        print(f"  Total: {len(mode_rows)}")
        print(f"  Solved: {len(solved)} ({len(solved)/len(mode_rows)*100:.1f}%)")
        
        if solved:
            times = [r['time'] for r in solved]
            conflicts = [r['conflicts'] for r in solved]
            print(f"  Mean time: {sum(times)/len(times):.4f}s")
            print(f"  Mean conflicts: {sum(conflicts)/len(conflicts):.0f}")
    
    # Head-to-head
    by_instance = defaultdict(dict)
    for r in rows:
        by_instance[r['instance']][r['mode']] = r
    
    print("\n" + "="*60)
    print("HEAD-TO-HEAD")
    print("="*60)
    
    rl_wins = base_wins = ties = 0
    speedups = []
    
    for inst in sorted(by_instance.keys()):
        if 'rl' not in by_instance[inst] or 'baseline' not in by_instance[inst]:
            continue
        
        rl = by_instance[inst]['rl']
        base = by_instance[inst]['baseline']
        
        print(f"\n{inst}:")
        print(f"  RL:       {rl['status']:8s} {rl['time']:7.4f}s conf={rl['conflicts']:5d}")
        print(f"  Baseline: {base['status']:8s} {base['time']:7.4f}s conf={base['conflicts']:5d}")
        
        rl_ok = rl['status'] in ['SAT', 'UNSAT']
        base_ok = base['status'] in ['SAT', 'UNSAT']
        
        if rl_ok and not base_ok:
            rl_wins += 1
            print("  Winner: RL")
        elif base_ok and not rl_ok:
            base_wins += 1
            print("  Winner: Baseline")
        elif rl_ok and base_ok:
            if rl['time'] < base['time'] * 0.95:
                rl_wins += 1
                speedup = base['time'] / rl['time']
                speedups.append(speedup)
                print(f"  Winner: RL ({speedup:.2f}x speedup)")
            elif base['time'] < rl['time'] * 0.95:
                base_wins += 1
                print("  Winner: Baseline")
            else:
                ties += 1
                print("  Tie")
        else:
            ties += 1
            print("  Tie (both timeout)")
    
    print("\n" + "="*60)
    print(f"RL wins: {rl_wins}, Baseline wins: {base_wins}, Ties: {ties}")
    if speedups:
        print(f"Avg speedup (RL faster): {sum(speedups)/len(speedups):.2f}x")

if __name__ == '__main__':
    main()
