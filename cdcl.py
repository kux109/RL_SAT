from typing import List, Optional, Tuple
from typing import List, Optional, Tuple
import time

from run_solver import parse_dimacs
from cdcl_rl import CDCLSolverRL


def cdcl_solver(dimacs_input: str) -> bool:
    n, c = parse_dimacs(dimacs_input)
    solver = CDCLSolverRL(n, c)
    return solver.solve()


def parse_dimacs_legacy(dimacs: str):
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
            if lits[-1] == 0:
                lits.pop()
            clauses.append(lits)
    return num_vars, clauses

def cdcl_solver_legacy(dimacs_input: str) -> bool:
    num_vars, clauses = parse_dimacs_legacy(dimacs_input)
    solver = CDCLSolverRL(num_vars, clauses)
    return solver.solve()

# Example DIMACS CNF to test
example_dimacs = '''
c This is a comment line
p cnf 3 2
1 -2 0
-1 2 3 0
'''

if __name__ == '__main__':
    start_time = time.time()
    result = cdcl_solver(example_dimacs)
    elapsed_time = time.time() - start_time
    print(f'SAT result: {"SAT" if result else "UNSAT"}, Time: {elapsed_time:.6f} seconds')
