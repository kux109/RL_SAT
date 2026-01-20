# Context-Aware Heuristic Selection in a Lightweight CDCL SAT Solver

This repository contains a small, self-contained CDCL SAT solver with two modes:

- RL mode: Contextual bandit (LinUCB) dynamically selects among multiple branching heuristics per conflict epoch.
- Baseline mode: Standard CDCL with a single fixed heuristic (e.g., VSIDS or JW) and no RL.

The goal is to support research on context-aware online learning for heuristic selection without relying on Kissat.

## Project structure

- `cdcl_core.py` — Core CDCL machinery (assignments, propagation, conflict analysis, VSIDS bumps, LBD stats).
- `heuristics.py` — Heuristic strategies: VSIDS, JW (Jeroslow–Wang), DLIS, Random.
- `bandit.py` — LinUCB contextual bandit for arm selection and online updates.
- `cdcl_rl.py` — RL-enabled solver using `cdcl_core` and `bandit` to switch heuristics per epoch using context features.
- `cdcl_baseline.py` — Baseline solver using a single heuristic without any RL.
- `run_solver.py` — CLI to run either RL or baseline solvers on a DIMACS file.
- `cdcl.py` — Legacy entry that now calls RL solver for backward compatibility (kept so existing invocations work).

## How it works (high-level flow)

1. CDCL core initializes watches and begins the decide–propagate–analyze loop.
2. On each conflict:
   - First-UIP conflict analysis produces a learned clause and a backtrack level.
   - VSIDS bumps are applied to variables in the learned clause.
   - LBD (glue) metric of the learned clause is computed and recorded for statistics.
   - The learned clause is added and watched; asserting literal is enqueued.
   - Optional restarts periodically backtrack to level 0.
3. Branching decisions use a heuristic’s `decide()` to pick a literal with phase saving.

RL mode only:
- The solver maintains an epoch of fixed conflict length. At the end of each epoch:
  - Extract a context vector from solver state (LBD stats, conflict/propagation rates, activity stats, clause DB dynamics, restart rate, satisfied-clause ratio, etc.).
  - LinUCB selects the heuristic arm for the next epoch.
  - A reward is computed favoring fewer conflicts, more propagation/decision, and lower LBD, and the bandit is updated online.

## Detailed API overview

- `CDCLCore` (cdcl_core.py):
  - `add_watches()`: Initialize two-watched-literal scheme for all clauses.
  - `propagate()`: Perform Boolean Constraint Propagation; returns a conflicting clause if any, otherwise None. Enqueues units with reasons.
  - `analyze_conflict(conflict_clause) -> (learnt_clause, backtrack_level)`: Standard 1-UIP analysis; also computes and stores LBD, applies VSIDS bumps.
  - `backtrack(level)`: Undo assignments beyond `level`.
  - `enqueue(lit, reason)`: Assign a literal with an optional reason; updates decision/propagation counters and phase saving.
  - `compute_lbd(clause)`: Count unique decision levels in the clause.
  - `is_satisfied(clause)`: Check if a clause is satisfied by current assignments.
  - `pick_first_unassigned()`: Fallback variable selection if a heuristic returns None.
  - Tracks: `conflicts`, `decisions`, `propagations`, `restarts`, `activity` (VSIDS), `recent_lbd`.

- `heuristics.py`:
  - `VSIDSStrategy.decide(solver)`: Highest-activity unassigned var with phase saving.
  - `JWStrategy`: Jeroslow–Wang literal weights; updated when new learned clauses are added.
  - `DLISStrategy`: Counts occurrences of literals in currently unsatisfied clauses.
  - `RandomStrategy`: First unassigned variable with random or saved phase.

- `bandit.py`:
  - `LinUCB(n_arms, dim, alpha)`: Maintains per-arm inverse Gram matrices and reward vectors; `select(context)` picks arm, `update(arm, context, reward)` updates parameters using Sherman–Morrison.

- `cdcl_rl.py`:
  - `CDCLSolverRL`: Extends `CDCLCore`; holds multiple heuristics, LinUCB agent, epoch accounting.
  - `feature_context(...)`: Builds the context vector the agent uses.
  - `solve()`: CDCL loop augmented with epoch handling and bandit updates.

- `cdcl_baseline.py`:
  - `CDCLSolverBaseline(heuristic='vsids')`: Same CDCL loop but with a single fixed heuristic and no RL.

## Run it

- RL mode (default) with built-in tiny CNF:

```bash
python3 run_solver.py --mode rl
```

- RL mode on a DIMACS file with custom epoch and restart intervals:

```bash
python3 run_solver.py --mode rl --cnf path/to/instance.cnf --epoch 200 --restart 400
```

- Baseline mode with VSIDS:

```bash
python3 run_solver.py --mode baseline --heuristic vsids --cnf path/to/instance.cnf
```

- Baseline mode with JW:

```bash
python3 run_solver.py --mode baseline --heuristic jw --cnf path/to/instance.cnf
```

The CLI prints summary metrics (time, conflicts, decisions, propagations). Use these to compare RL vs baseline.

## Tuning & Extensions

- Adjust exploration via `alpha` in `bandit.py`.
- Change epoch size and restart interval via CLI flags or attributes.
- Add/remove features in `CDCLSolverRL.feature_context()`.
- Replace periodic restart with Luby schedule.
- Implement clause database reduction; feed deletion counts into features.

## Caveats

- This is a compact educational solver; not optimized for large or industrial SAT instances.
- DLIS is naive (clause scans). Consider caching if needed.
- LBD reward uses the current average as a proxy; you can store per-epoch values to compute deltas exactly.

## Minimal example (programmatic)

```python
from run_solver import parse_dimacs
from cdcl_rl import CDCLSolverRL

cnf = """
c Example
p cnf 3 2
1 -2 0
-1 2 3 0
"""
num_vars, clauses = parse_dimacs(cnf)
solver = CDCLSolverRL(num_vars, clauses)
solver.epoch_size = 50
sat = solver.solve()
print("SAT" if sat else "UNSAT")
```