# RL-CDCL SAT Solver: How to Run

## 🏛️ Code Architecture Overview

Your project has **two main solvers** that both use a shared core engine:

```
                    USER CODE
                (Scripts/Experiments)
                        │
        ┌───────────────┴───────────────┐
        │                               │
    BASELINE MODE                   RL MODE
    (Fixed Heuristic)           (Adaptive Learning)
        │                               │
   cdcl_baseline.py              cdcl_rl.py
        │                               │
    ├─ cdcl_core.py              ├─ cdcl_core.py
    ├─ heuristics.py             ├─ heuristics.py
    └─ ONE fixed heuristic       ├─ bandit.py (LinUCB)
       (VSIDS/JW/DLIS/Random)    └─ ADAPTIVE heuristic selection
```

### **Component Breakdown:**

| File | Purpose |
|------|---------|
| `cdcl_core.py` | The CDCL engine - core SAT solving logic (propagation, conflict analysis, learning) |
| `heuristics.py` | 4 branching strategies: VSIDS, JW, DLIS, Random |
| `bandit.py` | LinUCB contextual bandit - learns which heuristic works best |
| `cdcl_baseline.py` | Baseline solver using ONE fixed heuristic throughout |
| `cdcl_rl.py` | RL solver that adaptively picks heuristics based on problem context |
| `run_solver.py` | CLI to run single instances |
| `run_experiments.py` | Batch runner to compare RL vs Baseline |

---

## 🚀 Quick Start - Run Single Instance

### **Run Baseline with Fixed Heuristic**

```bash
python3 run_solver.py --mode baseline --heuristic vsids --cnf test_cnfs/simple1.cnf
```

**Available heuristics:** `vsids`, `jw`, `dlis`, `random`

**Examples:**
```bash
python3 run_solver.py --mode baseline --heuristic jw --cnf test_cnfs/medium1.cnf
python3 run_solver.py --mode baseline --heuristic dlis --cnf test_cnfs/medium1.cnf
```

### **Run RL with Adaptive Learning**

```bash
python3 run_solver.py --mode rl --cnf test_cnfs/simple1.cnf
```

**With custom parameters:**
```bash
python3 run_solver.py --mode rl --cnf test_cnfs/simple1.cnf --epoch 50 --restart 200
```

- `--epoch 50` = Switch heuristic every 50 conflicts
- `--restart 200` = Restart search every 200 conflicts

### **Example Output**

```
Result: SAT, time=2.34s, conflicts=1523, decisions=342, propagations=8904
```

---

## 📊 Batch Experiments - Compare RL vs Baseline

Run comprehensive experiments that test both solvers on all instances:

```bash
python3 run_experiments.py --cnf-dir test_cnfs/ --timeout 30 --output results.csv
```

**Parameters:**
- `--cnf-dir test_cnfs/` = Directory with CNF files
- `--timeout 30` = Max 30 seconds per instance
- `--output results.csv` = Save raw results
- `--epoch 50` = Conflicts per epoch (default: 50)
- `--restart 200` = Conflicts per restart (default: 200)

### **Output Files**

1. `experiment_results.csv` - Raw solver statistics
2. `comparison_results_vsids.csv` - RL vs Baseline comparison

### **What You Get**

**Console output shows:**
```
Total instances: 10
Both solved: 8
RL only solved: 1
Baseline only solved: 0
Neither solved: 1

TIME ANALYSIS:
RL avg time:          2.34s (median: 1.89s)
Baseline avg time:    3.21s (median: 2.45s)
Speedup (baseline/rl) avg: 1.37x

RL faster on 6/8 instances
RL slower on 2/8 instances

[Per-instance detailed results...]
```

---

## 🧪 Workflow Examples

### **Example 1: Quick Test on One Instance**

```bash
# Test RL
python3 run_solver.py --mode rl --cnf test_cnfs/medium1.cnf

# Test Baseline with VSIDS
python3 run_solver.py --mode baseline --heuristic vsids --cnf test_cnfs/medium1.cnf

# Compare outputs
```

### **Example 2: Compare All Heuristics on One Instance**

```bash
python3 run_solver.py --mode baseline --heuristic vsids --cnf test_cnfs/medium1.cnf
python3 run_solver.py --mode baseline --heuristic jw --cnf test_cnfs/medium1.cnf
python3 run_solver.py --mode baseline --heuristic dlis --cnf test_cnfs/medium1.cnf
python3 run_solver.py --mode baseline --heuristic random --cnf test_cnfs/medium1.cnf
python3 run_solver.py --mode rl --cnf test_cnfs/medium1.cnf
```

### **Example 3: Full Benchmark Suite**

```bash
# Run experiments with longer timeout for harder instances
python3 run_experiments.py \
    --cnf-dir test_cnfs/ \
    --timeout 60 \
    --epoch 50 \
    --restart 200 \
    --output thesis_results.csv
```

---

## 📈 Understanding the Results

### **Key Metrics Compared:**

- **Time:** Wallclock time to solve (in seconds)
- **Conflicts:** Number of conflicts encountered
- **Decisions:** Number of branching decisions made
- **Propagations:** Number of unit propagations
- **Status:** SAT, UNSAT, or TIMEOUT

### **Interpreting the Speedup:**

- **Speedup > 1.0x** = RL is faster than baseline ✅
- **Speedup = 1.0x** = Both equally fast
- **Speedup < 1.0x** = Baseline is faster ❌

### **What You're Measuring:**

Your thesis answers: **"Can adaptive heuristic selection (RL) beat fixed heuristics on SAT problems?"**

---

## 📂 Test Instances

Located in `test_cnfs/` folder:

- `simple1.cnf`, `tiny_sat.cnf` - Trivial (for quick tests)
- `unsat1.cnf` - Unsatisfiable instance
- `medium1.cnf` - `medium7.cnf` - Medium difficulty (your benchmarks)

---

## 🔧 Customization

### **Change Context Features**

Edit `cdcl_rl.py` in `feature_context()` method to add/remove features the bandit learns from.

### **Change Reward Function**

Edit `_compute_epoch_reward()` in `cdcl_rl.py` to weight conflicts, propagations, and LBD differently.

### **Change Exploration Parameter**

In `cdcl_rl.py`, modify `LinUCB` alpha:
```python
self.agent = LinUCB(n_arms=len(self.heuristics), dim=dim, alpha=0.3)
```
- Higher alpha = more exploration
- Lower alpha = more exploitation

---

## 💡 Tips

1. **Start small:** Test on simple instances first with short timeouts
2. **Use alternating runs:** Run RL first sometimes, Baseline first other times (reduces bias)
3. **Multiple runs:** Run experiments several times and average results
4. **Diverse instances:** Test on easy, medium, and hard instances
5. **Log learning:** Use `--log` in `run_solver.py` to see per-epoch heuristic selection

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Timeout on all instances | Increase `--timeout` (e.g., 300 for 5 min) |
| Script errors | Check CNF file format: `p cnf N M` header required |
| RL not learning | Try different `--epoch` and `--restart` values |
| Need faster results | Use smaller instances or shorter timeouts for testing |

---

## 📋 Common Commands Cheat Sheet

```bash
# Single instance - Baseline
python3 run_solver.py --mode baseline --heuristic vsids --cnf test_cnfs/simple1.cnf

# Single instance - RL
python3 run_solver.py --mode rl --cnf test_cnfs/simple1.cnf

# Batch experiments
python3 run_experiments.py --cnf-dir test_cnfs/ --timeout 30 --output results.csv

# Analyze results
python3 analyze_simple.py results.csv
```

---

**Ready to run experiments for your thesis! 🚀**
