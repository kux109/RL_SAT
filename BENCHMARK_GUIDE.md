# Benchmark Testing Guide

## Quick Start

Create a directory with test CNF files, then run the benchmark:

```bash
# Run both RL and baseline on all CNFs in test_cnfs/ directory
python3 benchmark_runner.py --cnf-dir test_cnfs/ --output results.csv --timeout 60

# Analyze results
python3 analyze_results.py results.csv
```

## Getting Test CNF Files

### Option 1: Download from SAT Competition
Visit https://satcompetition.github.io/ and download benchmark instances.

### Option 2: Generate simple test cases
Create a directory with a few small CNF files:

```bash
mkdir test_cnfs
```

Create `test_cnfs/simple1.cnf`:
```
c Simple satisfiable formula
p cnf 5 3
1 2 0
-1 3 0
-2 -3 4 5 0
```

Create `test_cnfs/simple2.cnf`:
```
c Another test
p cnf 10 15
1 2 3 0
-1 4 0
-2 5 0
-3 6 0
4 7 0
5 8 0
6 9 0
7 10 0
-8 -9 0
-7 -10 0
1 -4 7 0
2 -5 8 0
3 -6 9 0
-1 -2 -3 0
8 9 10 0
```

### Option 3: Use existing benchmarks
Look for benchmark suites like:
- SAT Competition instances
- SATLIB (https://www.cs.ubc.ca/~hoos/SATLIB/)
- Industrial verification benchmarks

## Benchmark Runner Options

```bash
python3 benchmark_runner.py \
  --cnf-dir <directory>       # Directory with .cnf files
  --output results.csv        # Output CSV file
  --timeout 300               # Timeout per instance (seconds)
  --epoch 50                  # Conflicts per epoch
  --restart 200               # Conflicts per restart
  --baseline-heuristic vsids  # Baseline heuristic (vsids/jw/dlis/random)
  --modes rl baseline         # Which modes to run
```

## Example Workflows

### 1. Quick comparison (1 minute timeout)
```bash
python3 benchmark_runner.py --cnf-dir test_cnfs/ --timeout 60 --output quick_test.csv
python3 analyze_results.py quick_test.csv
```

### 2. Thorough benchmark (5 minute timeout)
```bash
python3 benchmark_runner.py --cnf-dir benchmarks/ --timeout 300 --output full_results.csv
python3 analyze_results.py full_results.csv
```

### 3. Test different heuristics
```bash
# Compare RL vs VSIDS
python3 benchmark_runner.py --cnf-dir test_cnfs/ --baseline-heuristic vsids --output rl_vs_vsids.csv

# Compare RL vs JW
python3 benchmark_runner.py --cnf-dir test_cnfs/ --baseline-heuristic jw --output rl_vs_jw.csv
```

### 4. Hyperparameter tuning
```bash
# Small epochs
python3 benchmark_runner.py --cnf-dir test_cnfs/ --epoch 25 --output epoch25.csv

# Large epochs
python3 benchmark_runner.py --cnf-dir test_cnfs/ --epoch 100 --output epoch100.csv
```

## Understanding Results

The `results.csv` contains:
- **instance**: CNF filename
- **mode**: rl or baseline
- **heuristic**: which baseline heuristic (for baseline mode)
- **status**: SAT, UNSAT, TIMEOUT, or ERROR
- **time**: solve time in seconds
- **conflicts, decisions, propagations, restarts**: solver metrics

The analyzer computes:
- Solve rates (% solved within timeout)
- Average/median times for solved instances
- Head-to-head comparisons (RL wins vs baseline wins)
- Speedup statistics (RL time / baseline time)

## Tips for Good Experiments

1. **Start small**: Test on 10-20 instances first to verify everything works
2. **Use timeouts**: Prevent hanging on hard instances (60-300 seconds typical)
3. **Mix difficulty**: Include easy, medium, and hard instances
4. **Multiple runs**: Run with different seeds if you add randomness
5. **Document settings**: Note epoch size, restart interval, timeout in your thesis
6. **Statistical significance**: Use at least 20-30 instances for meaningful comparisons

## Expected Outcomes

- RL should show improvement on instances where optimal heuristic varies during solve
- Baseline may be faster on very simple instances (less overhead)
- Look for patterns: which types of instances benefit most from RL?
- Analyze per-epoch logs to see heuristic switching patterns

## Next Steps

After running benchmarks:
1. Tune hyperparameters (epoch size, LinUCB alpha, reward weights)
2. Try feature ablations (remove feature groups)
3. Plot results (speedup distributions, solve-time scatter plots)
4. Analyze logs to understand when/why RL helps
