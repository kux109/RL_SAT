import random
import os
import argparse

def generate_k_sat(n_vars, n_clauses, k=3):
    clauses = []
    for _ in range(n_clauses):
        clause = set()
        while len(clause) < k:
            var = random.randint(1, n_vars)
            sign = random.choice([1, -1])
            lit = var * sign
            # Avoid tautologies (x and -x in same clause) and duplicates
            if -lit not in clause:
                clause.add(lit)
        clauses.append(list(clause))
    return clauses

def write_dimacs(clauses, n_vars, filename):
    with open(filename, 'w') as f:
        f.write(f"c Random 3-SAT Generated Instance\n")
        f.write(f"p cnf {n_vars} {len(clauses)}\n")
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")

def main():
    parser = argparse.ArgumentParser(description="Generate Random 3-SAT Instances")
    parser.add_argument("--vars", type=int, default=75, help="Number of variables")
    parser.add_argument("--count", type=int, default=10, help="Number of instances to generate")
    parser.add_argument("--out", type=str, default="generated_cnfs", help="Output directory")
    args = parser.parse_args()

    # Phase transition ratio for 3-SAT is approx 4.26
    n_clauses = int(args.vars * 4.26)
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    print(f"Generating {args.count} instances with {args.vars} variables and ~{n_clauses} clauses...")
    
    for i in range(args.count):
        clauses = generate_k_sat(args.vars, n_clauses)
        filename = os.path.join(args.out, f"rnd_{args.vars}_{i}.cnf")
        write_dimacs(clauses, args.vars, filename)
        
    print(f"Done. Saved to {args.out}/")

if __name__ == "__main__":
    main()
