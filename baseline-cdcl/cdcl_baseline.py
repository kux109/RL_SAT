from typing import List, Optional
import time
import sys
from pathlib import Path

# Add parent directories to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'core_files'))
sys.path.insert(0, str(project_root / 'heuristics'))
sys.path.insert(0, str(project_root / 'utils'))

from cdcl_core import CDCLCore
from heuristics import HeuristicStrategy, VSIDSStrategy, JWStrategy, DLISStrategy, RandomStrategy
from logging_utils import CSVLogger


class CDCLSolverBaseline(CDCLCore):
    def __init__(self, num_vars: int, clauses: List[List[int]], heuristic: str = "vsids"):
        super().__init__(num_vars, clauses)
        self.heuristic_name = heuristic.lower()
        if self.heuristic_name == "vsids":
            self.heuristic: HeuristicStrategy = VSIDSStrategy()
        elif self.heuristic_name == "jw":
            self.heuristic = JWStrategy()
        elif self.heuristic_name == "dlis":
            self.heuristic = DLISStrategy()
        elif self.heuristic_name == "random":
            self.heuristic = RandomStrategy()
        else:
            self.heuristic = VSIDSStrategy()
        self.restart_interval = 200
        # logging
        self.logger = None
        self.epoch_size = 50
        self.epoch_start_conflicts = 0
        self.epoch_start_decisions = 0
        self.epoch_start_props = 0
        self.epoch_index = 0

    def feature_context(self, since_conflicts: int, since_decisions: int, since_props: int, since_time: float) -> List[float]:
        # reuse logic similar to RL solver for logging comparability
        if self.recent_lbd:
            avg_lbd = sum(self.recent_lbd) / len(self.recent_lbd)
            var_lbd = sum((x - avg_lbd) ** 2 for x in self.recent_lbd) / len(self.recent_lbd)
            glue_ratio = sum(1 for x in self.recent_lbd if x <= 2) / len(self.recent_lbd)
        else:
            avg_lbd = 0.0
            var_lbd = 0.0
            glue_ratio = 0.0
        # since_time not tracked here; set conf_rate proxy to 0
        conf_rate = 0.0
        max_act = max(self.activity[1:], default=1.0)
        mean_act = sum(self.activity[1:]) / max(1, self.num_vars)
        std_act = (sum((a - mean_act) ** 2 for a in self.activity[1:]) / max(1, self.num_vars)) ** 0.5
        mean_act_n = mean_act / max(1e-9, max_act)
        std_act_n = std_act / max(1e-9, max_act)
        total_clauses = len(self.clauses)
        learned = max(0, total_clauses - self.orig_clause_count)
        learned_ratio = learned / max(1, total_clauses)
        clause_var_ratio = total_clauses / max(1, self.num_vars)
        restarts_rate = (self.restarts) / max(1, self.conflicts)
        prop_rate = (since_props / max(1, since_decisions)) if since_decisions > 0 else 0.0
        sat_ratio = self.satisfied_ratio()
        return [
            min(1.0, avg_lbd / 20.0),
            min(1.0, var_lbd / 100.0),
            glue_ratio,
            min(1.0, conf_rate / 100.0),
            min(1.0, mean_act_n),
            min(1.0, std_act_n),
            learned_ratio,
            min(1.0, clause_var_ratio / 10.0),
            min(1.0, restarts_rate),
            min(1.0, prop_rate / 100.0),
            sat_ratio,
        ]

    def maybe_restart(self):
        if self.restart_interval <= 0:
            return
        if self.conflicts > 0 and self.conflicts % self.restart_interval == 0 and self.decision_level > 0:
            self.backtrack(0)
            self.restarts += 1

    def pick_branch_literal(self) -> Optional[int]:
        lit = self.heuristic.decide(self)
        if lit is not None:
            return lit
        v = self.pick_first_unassigned()
        if v is None:
            return None
        if self.phase[v] is not None:
            return v if self.phase[v] else -v
        return v

    def solve(self) -> bool:
        self.add_watches()
        last_log = time.time()
        # baseline epoch init
        self.epoch_start_conflicts = self.conflicts
        self.epoch_start_decisions = self.decisions
        self.epoch_start_props = self.propagations
        while True:
            conflict = self.propagate()
            if conflict is not None:
                self.conflicts += 1
                now = time.time()
                if self.conflicts % 50 == 0 or now - last_log > 2:
                    print(f"[BASE:{self.heuristic_name}] lvl={self.decision_level} conf={self.conflicts} dec={self.decisions} prop={self.propagations} rest={self.restarts}")
                    last_log = now
                if self.decision_level == 0:
                    print('[BASE] UNSAT at level 0')
                    # finalize epoch logging
                    self._log_epoch(final=True)
                    return False
                learnt, bt = self.analyze_conflict(conflict)
                self.backtrack(bt)
                self.clauses.append(learnt)
                if isinstance(self.heuristic, JWStrategy):
                    self.heuristic.notify_clause_added(self, learnt)
                self.watch_literal(learnt, learnt[0])
                if len(learnt) > 1:
                    self.watch_literal(learnt, learnt[1])
                self.enqueue(learnt[0], learnt)
                self.maybe_restart()
                # baseline epoch step
                if (self.conflicts - self.epoch_start_conflicts) >= self.epoch_size:
                    self._log_epoch()
            else:
                lit = self.pick_branch_literal()
                if lit is None:
                    print(f"[BASE:{self.heuristic_name}] SAT after {self.conflicts} conflicts")
                    self._log_epoch(final=True)
                    return True
                self.decision_level += 1
                self.trail_limits.append(len(self.trail))
                self.enqueue(lit, None)
                if time.time() - last_log > 2:
                    print(f"[BASE:{self.heuristic_name}] new lvl={self.decision_level}")
                    last_log = time.time()

    def _log_epoch(self, final: bool = False):
        if self.logger is None:
            # reset counters anyway
            self.epoch_start_conflicts = self.conflicts
            self.epoch_start_decisions = self.decisions
            self.epoch_start_props = self.propagations
            return
        d_conf = self.conflicts - self.epoch_start_conflicts
        d_dec = self.decisions - self.epoch_start_decisions
        d_prop = self.propagations - self.epoch_start_props
        ctx = self.feature_context(d_conf, d_dec, d_prop, 0.0)
        row = {
            'epoch': self.epoch_index,
            'heuristic': self.heuristic_name,
            'reward': '',
            'd_conflicts': d_conf,
            'd_decisions': d_dec,
            'd_propagations': d_prop,
            'avg_lbd': (sum(self.recent_lbd) / len(self.recent_lbd)) if self.recent_lbd else 0.0,
            'conflicts': self.conflicts,
            'decisions': self.decisions,
            'propagations': self.propagations,
            'restarts': self.restarts,
        }
        for i, v in enumerate(ctx):
            row[f'c{i}'] = v
        self.logger.log(row)
        self.epoch_index += 1
        # reset epoch counters
        self.epoch_start_conflicts = self.conflicts
        self.epoch_start_decisions = self.decisions
        self.epoch_start_props = self.propagations
