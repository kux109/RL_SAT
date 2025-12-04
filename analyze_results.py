#!/usr/bin/env python3
"""
Analyze benchmark results and compute comparative statistics.
"""
import argparse
import pandas as pd
import sys


def analyze_results(csv_path: str):
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return

    if df.empty:
        print("No results found")
        return

    print("=" * 70)
    print(f"Benchmark Analysis: {csv_path}")
    print("=" * 70)

    # Overall stats per mode
    print("\n### Per-Mode Summary ###")
    for mode in df['mode'].unique():
        mode_df = df[df['mode'] == mode]
        solved = mode_df[mode_df['status'].isin(['SAT', 'UNSAT'])]
        timeouts = mode_df[mode_df['status'] == 'TIMEOUT']
        errors = mode_df[~mode_df['status'].isin(['SAT', 'UNSAT', 'TIMEOUT'])]
        
        print(f"\n{mode.upper()}:")
        print(f"  Total instances: {len(mode_df)}")
        print(f"  Solved: {len(solved)} ({len(solved)/len(mode_df)*100:.1f}%)")
        print(f"  Timeouts: {len(timeouts)}")
        print(f"  Errors: {len(errors)}")
        
        if not solved.empty:
            print(f"  Avg time (solved): {solved['time'].mean():.2f}s")
            print(f"  Median time (solved): {solved['time'].median():.2f}s")
            print(f"  Avg conflicts: {solved['conflicts'].mean():.0f}")
            print(f"  Avg decisions: {solved['decisions'].mean():.0f}")
            print(f"  Avg propagations: {solved['propagations'].mean():.0f}")

    # Instance-by-instance comparison
    if 'rl' in df['mode'].values and 'baseline' in df['mode'].values:
        print("\n### RL vs Baseline (Instance-by-Instance) ###")
        
        rl_df = df[df['mode'] == 'rl'].set_index('instance')
        baseline_df = df[df['mode'] == 'baseline'].set_index('instance')
        
        common_instances = set(rl_df.index) & set(baseline_df.index)
        
        if not common_instances:
            print("No common instances between RL and baseline")
            return
        
        rl_wins = 0
        baseline_wins = 0
        ties = 0
        speedups = []
        
        print(f"\n{'Instance':<30} {'RL Time':<12} {'Base Time':<12} {'Speedup':<10} {'Winner'}")
        print("-" * 80)
        
        for instance in sorted(common_instances):
            rl_row = rl_df.loc[instance]
            base_row = baseline_df.loc[instance]
            
            rl_solved = rl_row['status'] in ['SAT', 'UNSAT']
            base_solved = base_row['status'] in ['SAT', 'UNSAT']
            
            if rl_solved and base_solved:
                speedup = base_row['time'] / rl_row['time']
                speedups.append(speedup)
                if speedup > 1.05:
                    winner = 'RL'
                    rl_wins += 1
                elif speedup < 0.95:
                    winner = 'Baseline'
                    baseline_wins += 1
                else:
                    winner = 'Tie'
                    ties += 1
                print(f"{instance:<30} {rl_row['time']:>10.2f}s {base_row['time']:>10.2f}s {speedup:>8.2f}x {winner}")
            elif rl_solved:
                rl_wins += 1
                print(f"{instance:<30} {rl_row['time']:>10.2f}s {'TIMEOUT':>12} {'--':>10} RL")
            elif base_solved:
                baseline_wins += 1
                print(f"{instance:<30} {'TIMEOUT':>12} {base_row['time']:>10.2f}s {'--':>10} Baseline")
            else:
                ties += 1
                print(f"{instance:<30} {'TIMEOUT':>12} {'TIMEOUT':>12} {'--':>10} Both timeout")
        
        print("\n### Head-to-Head Summary ###")
        print(f"RL wins: {rl_wins}")
        print(f"Baseline wins: {baseline_wins}")
        print(f"Ties: {ties}")
        
        if speedups:
            avg_speedup = sum(speedups) / len(speedups)
            median_speedup = sorted(speedups)[len(speedups)//2]
            print(f"\nAverage speedup (RL vs baseline): {avg_speedup:.2f}x")
            print(f"Median speedup: {median_speedup:.2f}x")
            print(f"Best speedup: {max(speedups):.2f}x")
            print(f"Worst speedup: {min(speedups):.2f}x")


def main():
    parser = argparse.ArgumentParser(description="Analyze benchmark results")
    parser.add_argument('results_csv', type=str, help='Path to benchmark results CSV')
    args = parser.parse_args()
    
    analyze_results(args.results_csv)


if __name__ == '__main__':
    main()
