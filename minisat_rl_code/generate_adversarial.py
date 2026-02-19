import random
import os
import argparse

def generate_masked_unsat(n_traps, n_backbone, filename):
    """
    Generates a 'Masked UNSAT' instance.
    
    Logic:
    1. Generate a Random 3-SAT core on 'n_traps' variables with Ratio=4.3.
       This is likely UNSAT or very hard.
    2. 'Mask' this core by adding a 'Backbone' literal to every clause.
       Clause becomes: (t1 v t2 v t3 v BackboneVar).
    3. Properties:
       - Traps (t): HIGH Activity (appear in every clause).
       - Backbone (b): LOW Activity (appear sparsely, e.g., 1 per 20 clauses).
       - Solution: Setting Backbone=TRUE satisfies clauses instantly.
       - Trap: VSIDS picks 't' vars, dives into UNSAT core, thrashing forever.
    """
    
    clauses = []
    
    # 1. Variables
    # Traps: 1 .. n_traps
    # Backbone: n_traps+1 .. n_traps+n_backbone
    trap_start = 1
    backbone_start = n_traps + 1
    
    traps = list(range(trap_start, trap_start + n_traps))
    backbone = list(range(backbone_start, backbone_start + n_backbone))
    
    # 2. Generate Random 3-SAT Core (Ratio 4.3 for Hardness/UNSAT)
    m_clauses = int(4.3 * n_traps)
    
    for _ in range(m_clauses):
        # Random 3-clause from Traps
        c = random.sample(traps, 3)
        lits = [x if random.random() > 0.5 else -x for x in c]
        
        # 3. Add Backbone Mask
        # We distribute backbone vars across clauses.
        # To keep backbone activity LOW, we rotate them slowly or randomly.
        # But we must ensure EVERY clause is covered if we want Backbone=True to be a solution.
        b_var = random.choice(backbone)
        
        # Add 'b_var' (Positive) to clause.
        # So (t1 v t2 v t3 v b_var).
        # If b_var = TRUE, clause is satisfied.
        lits.append(b_var)
        
        clauses.append(lits)
        
    # 4. Optional: Force Backbone to be "Hidden" by adding dummy constraints?
    # No, low activity is the disguise.
    # If n_backbone is small (e.g., 10) vs n_traps (1000), 
    # n_backbone vars appear m_clauses/10 times.
    # n_traps vars appear m_clauses*3/1000 times.
    # Activity Ratio = (m/10) vs (3m/1000) = 0.1m vs 0.003m.
    # Wait, Backbone activity would be HIGHER if we simply append them?
    # Ah! If we append a backbone var to EVERY clause, they appear M/n_backbone times.
    # If N_backbone is small, they appear A LOT.
    # WE NEED N_BACKBONE TO BE LARGE OR APPEAR RARELY?
    # If they appear rarely, some clauses remain UNSAT 3-clauses? No.
    # To mask *every* clause, we must add a backbone literal to every clause.
    # To keep Backbone activity LOW, we need N_Backbone >> N_Traps?
    # No, we want Traps to have high activity.
    
    # Correction:
    # We want Traps to appear OFTEN. (Ratio 4.3 clauses per var).
    # We want Backbone to appear SELDOM.
    # But we need Backbone to cover M clauses.
    # So if M = 4300 (for N=1000).
    # To make Backbone rare, we need say 4300 Backbone vars each appearing once?
    # Then N_total = 5300.
    # Trap Activity = 4.3 * 3 = 12.
    # Backbone Activity = 1.
    # YES!
    # So N_Backbone should be roughly equal to M (number of clauses) if we want activity=1.
    # Or N_Backbone = M / k.
    
    # Revised Config:
    # N_Traps = 200 (Hard Core)
    # M_Clauses = 860
    # N_Backbone = 860 (Each backbone var covers 1 clause).
    # Result:
    # Trap Activity ~12.
    # Backbone Activity ~1.
    # VSIDS picks Traps.
    # Solver thrashes in 200-var UNSAT core.
    # Real solution: Set all 860 Backbone vars to True.
    
    # Let's parameterize based on this.
    
    real_backbone_size = len(clauses) # One unique backbone var per clause?
    # Or reuse them slightly? Let's assume unique for max stealth.
    
    # Re-generate backbone based on clause count
    backbone = list(range(backbone_start, backbone_start + len(clauses)))
    
    final_clauses = []
    for i, c in enumerate(clauses):
        b = backbone[i]
        c[-1] = b # Replace the placeholder b_var with unique b
        final_clauses.append(c)
        
    n_vars_total = backbone[-1]
    
    with open(filename, 'w') as f:
        f.write(f"p cnf {n_vars_total} {len(final_clauses)}\n")
        for c in final_clauses:
            f.write(" ".join(map(str, c)) + " 0\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="datasets/adversarial", help="Output directory")
    parser.add_argument("--count", type=int, default=10, help="Number of instances")
    parser.add_argument("--hard", action="store_true", help="Generate extra hard instances")
    args = parser.parse_args()
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    print(f"Generating {args.count} adversarial instances in {args.out}...")
    
    for i in range(args.count):
        if args.hard:
            n_traps = 500  # Harder Random Core
        else:
            n_traps = 200  # Standard Hard Core
            
        fname = os.path.join(args.out, f"adv_mask_n{n_traps}_{i}.cnf")
        # Pass a dummy backbone size initially, it gets recalculated based on clauses
        generate_masked_unsat(n_traps, 100, fname)
        
    print("Done.")

if __name__ == "__main__":
    main()
