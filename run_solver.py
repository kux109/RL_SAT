import argparse
import time
from typing import Tuple

from cdcl_rl import CDCLSolverRL
from cdcl_baseline import CDCLSolverBaseline
from logging_utils import CSVLogger


def parse_dimacs(dimacs: str) -> Tuple[int, list[list[int]]]:
    lines = dimacs.splitlines()
    num_vars = 0
    clauses = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('c'):
            continue
        if line.startswith('p'):
            parts = line.split()
            num_vars = int(parts[2])
        else:
            lits = list(map(int, line.split()))
            if len(lits) > 0 and lits[-1] == 0:
                lits.pop()
            if lits:
                clauses.append(lits)
    return num_vars, clauses


def parse_dimacs_file(path: str) -> Tuple[int, list[list[int]]]:
    with open(path, 'r') as f:
        return parse_dimacs(f.read())


def main():
    parser = argparse.ArgumentParser(description="CDCL SAT Solver (RL and Baseline)")
    parser.add_argument('--mode', choices=['rl', 'baseline'], default='rl', help='Run RL-enabled solver or baseline')
    parser.add_argument('--heuristic', choices=['vsids', 'jw', 'dlis', 'random'], default='vsids', help='Baseline heuristic (ignored in RL mode)')
    parser.add_argument('--cnf', type=str, help='Path to DIMACS CNF file')
    parser.add_argument('--epoch', type=int, default=50, help='Conflicts per epoch (RL or baseline logging)')
    parser.add_argument('--restart', type=int, default=200, help='Conflicts per restart')
    parser.add_argument('--log', type=str, default=None, help='CSV file to log per-epoch metrics')
    args = parser.parse_args()

    example_dimacs = '''
c Example
p cnf 3 2
1 -2 0
-1 2 3 0
'''

    if args.cnf:
        n, cls = parse_dimacs_file(args.cnf)
    else:
        n, cls = parse_dimacs(example_dimacs)

    if args.mode == 'rl':
        solver = CDCLSolverRL(n, cls)
        solver.epoch_size = args.epoch
        solver.restart_interval = args.restart
    else:
        solver = CDCLSolverBaseline(n, cls, heuristic=args.heuristic)
        solver.restart_interval = args.restart
        solver.epoch_size = args.epoch

    # optional logging: build fieldnames based on context length
    if args.log:
        # probe context dimension
        if args.mode == 'rl':
            ctx = solver.feature_context(0, 0, 0, 1e-3)
        else:
            ctx = solver.feature_context(0, 0, 0, 0.0)
        fieldnames = [
            'epoch', 'heuristic', 'reward', 'd_conflicts', 'd_decisions', 'd_propagations',
            'avg_lbd', 'conflicts', 'decisions', 'propagations', 'restarts'
        ] + [f'c{i}' for i in range(len(ctx))]
        solver.logger = CSVLogger(args.log, fieldnames)

    t0 = time.time()
    sat = solver.solve()
    dt = time.time() - t0
    print(f"Result: {'SAT' if sat else 'UNSAT'}, time={dt:.4f}s, conflicts={solver.conflicts}, decisions={solver.decisions}, propagations={solver.propagations}")


if __name__ == '__main__':
    main()
