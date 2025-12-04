# Benchmark Infrastructure - Quick Start

## Overview
Your benchmark infrastructure is now fully operational! You have:

1. **benchmark_runner.py** - Runs multiple CNF instances with both RL and baseline modes
2. **analyze_simple.py** - Analyzes results and computes comparative statistics (no dependencies)
3. **test_cnfs/** - Sample CNF instances for testing

## Quick Test Run

```bash
# Run benchmark on test instances (use longer timeout for real experiments)
python3 benchmark_runner.py --cnf-dir test_cnfs/ --output results.csv --timeout 60

# Analyze results
python3 analyze_simple.py results.csv
```

## Next Steps for Your Thesis

### 1. Get Real Benchmark Instances
Download standard SAT benchmarks:
- **SATLIB**: http://www.cs.ubc.ca/~hoos/SATLIB/benchm.html
- **SAT Competition**: http://www.satcompetition.org/
- Start with: 3-SAT random instances, industrial benchmarks, crafted instances

### 2. Run Systematic Experiments

```bash
# Example: Run on SATLIB benchmarks with 5 minute timeout
python3 benchmark_runner.py \
    --cnf-dir satlib_instances/ \
    --output satlib_results.csv \
    --timeout 300 \
    --epoch 50 \
    --restart 200
```

### 3. Parameter Tuning
Key hyperparameters to experiment with:
- `--epoch`: Conflicts per epoch (try 25, 50, 100, 200)
- `--restart`: Conflicts between restarts (try 100, 200, 500)
- LinUCB alpha in `bandit.py` (try 0.1, 0.3, 0.5, 1.0)
- Reward weights in `cdcl_rl.py`

### 4. Thesis Experiments

**Experiment 1: Basic Performance Comparison**
- Run RL vs baseline on 50-100 SAT instances
- Compare solve rates, times, conflicts
- Create plots showing speedup distributions

**Experiment 2: Learning Behavior**
- Analyze per-epoch CSV logs from `cdcl_rl.py`
- Show how heuristic selection evolves over epochs
- Plot reward trends to show learning

**Experiment 3: Ablation Study**
- Remove/change context features one at a time
- Show which features matter most
- Compare different reward functions

**Experiment 4: Different Instance Types**
- Test on random 3-SAT, industrial, crafted instances
- Show RL adapts better to different problem structures

### 5. Visualization Ideas

```python
# Example: Plot speedup distribution
import matplotlib.pyplot as plt

speedups = []  # compute from analyze_simple.py output
plt.hist(speedups, bins=20)
plt.xlabel('Speedup (RL vs Baseline)')
plt.ylabel('# Instances')
plt.title('RL Performance Distribution')
plt.savefig('speedup_dist.png')
```

### 6. Write-Up Structure

**Section 1: Introduction**
- Motivation: Why contextual bandits for SAT?
- Contributions: Context-aware heuristic selection

**Section 2: Background**
- CDCL algorithm
- Heuristics (VSIDS, JW, DLIS)
- LinUCB contextual bandits

**Section 3: Approach**
- Context features (11 features explained)
- Reward design
- Epoch-based learning

**Section 4: Implementation**
- Architecture (cdcl_core, heuristics, bandit, etc.)
- Baseline comparison methodology

**Section 5: Experiments**
- Benchmark setup
- Results: solve rates, speedups, learning curves
- Ablation studies

**Section 6: Discussion**
- When does RL help? (complex instances)
- Feature importance analysis
- Limitations and future work

**Section 7: Conclusion**
- Summary of contributions
- Empirical validation

## Current Status

✅ Complete implementation with modular architecture
✅ RL solver with LinUCB bandit and 11 context features
✅ Baseline solver for fair comparison
✅ Epoch-based logging infrastructure
✅ Automated benchmark harness with timeout handling
✅ Statistical analysis tools

🔄 Next: Run experiments on real benchmarks
🔄 Next: Generate plots for thesis
🔄 Next: Write up results

## Tips for Good Experiments

1. **Use diverse instances**: Mix easy/hard, SAT/UNSAT, different structures
2. **Multiple runs**: Run 3-5 times and report mean ± std dev
3. **Fair comparison**: Same epoch structure for both RL and baseline
4. **Appropriate timeouts**: 5-10 minutes for medium instances, 30-60 min for hard ones
5. **Document everything**: Keep notes on hyperparameters and results
6. **Version control**: Commit code before major experiments

## Troubleshooting

**Problem**: prop=0 in solver output (no propagations)
**Solution**: Instance might be too hard or have structural issues. Try different instances.

**Problem**: Timeout too short
**Solution**: Increase `--timeout` parameter (e.g., 300 for 5 minutes)

**Problem**: RL not learning
**Solution**: Try different epoch sizes, adjust reward weights, check feature normalization

## Example Full Workflow

```bash
# 1. Download SATLIB instances
wget http://www.cs.ubc.ca/~hoos/SATLIB/Benchmarks/SAT/RND3SAT/uf50-218.tar.gz
tar -xzf uf50-218.tar.gz
mkdir satlib_uf50/
mv uf50-*.cnf satlib_uf50/

# 2. Run benchmark
python3 benchmark_runner.py \
    --cnf-dir satlib_uf50/ \
    --output satlib_uf50_results.csv \
    --timeout 120 \
    --epoch 50 \
    --restart 200

# 3. Analyze
python3 analyze_simple.py satlib_uf50_results.csv > satlib_uf50_analysis.txt

# 4. Check per-epoch logs for learning behavior
ls logs_*_epoch*.csv

# 5. Create plots (write your own plotting script)
python3 plot_results.py satlib_uf50_results.csv
```

Good luck with your thesis! 🎓
