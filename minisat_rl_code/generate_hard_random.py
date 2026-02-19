
import random
import os
import argparse

def generate_random_3sat(n_vars, ratio, filename):
    """
    Generates a Random 3-SAT instance at the Phase Transition (Ratio ~4.26).
    These are statistically the 'hardest' random instances for CDCL.
    """
    n_clauses = int(n_vars * ratio)
    clauses = []
    
    variables = list(range(1, n_vars + 1))
    
    for _ in range(n_clauses):
        # Pick 3 distinct variables
        c_vars = random.sample(variables, 3)
        # Assign random polarity
        clause = [v if random.random() > 0.5 else -v for v in c_vars]
        clauses.append(clause)
        
    with open(filename, 'w') as f:
        f.write(f"p cnf {n_vars} {n_clauses}\n")
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="datasets/hard_random", help="Output directory")
    parser.add_argument("--count", type=int, default=20, help="Number of instances")
    parser.add_argument("--vars", type=int, default=300, help="Number of variables (default 300)")
    args = parser.parse_args()
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    print(f"Generating {args.count} Random 3-SAT instances (N={args.vars}, Ratio=4.26) in {args.out}...")
    
    for i in range(args.count):
        fname = os.path.join(args.out, f"rnd_3sat_n{args.vars}_{i}.cnf")
        generate_random_3sat(args.vars, 4.26, fname)
        
    print("Done.")

if __name__ == "__main__":
    main()


