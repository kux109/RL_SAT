from typing import List, Optional, Dict
import time
import math
import sys
from pathlib import Path

# Add parent directories to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'core_files'))
sys.path.insert(0, str(project_root / 'heuristics'))
sys.path.insert(0, str(project_root / 'bandit'))
sys.path.insert(0, str(project_root / 'utils'))

from cdcl_core import CDCLCore
from heuristics import HeuristicStrategy, VSIDSStrategy, JWStrategy, DLISStrategy, RandomStrategy
from bandit import LinUCB
from logging_utils import CSVLogger


class CDCLSolverRL(CDCLCore):
    def __init__(self, num_vars: int, clauses: List[List[int]]):
        super().__init__(num_vars, clauses)
        self.heuristics: List[HeuristicStrategy] = [VSIDSStrategy(), JWStrategy(), DLISStrategy(), RandomStrategy()]
        self.heuristic_names = [h.name for h in self.heuristics]
        self.agent: Optional[LinUCB] = None
        self.current_arm: int = 0
        self.last_context: Optional[List[float]] = None
        self.last_arm: Optional[int] = None
        self.epoch_size = 50
        self.epoch_start_conflicts = 0
        self.epoch_start_time = time.time()
        self.epoch_start_decisions = 0
        self.epoch_start_props = 0
        self.restart_interval = 200
        # logging
        self.logger = None
        self.epoch_index = 0

    def feature_context(self, since_conflicts: int, since_decisions: int, since_props: int, since_time: float) -> List[float]:
        if self.recent_lbd:
            avg_lbd = sum(self.recent_lbd) / len(self.recent_lbd)
            var_lbd = sum((x - avg_lbd) ** 2 for x in self.recent_lbd) / len(self.recent_lbd)
            glue_ratio = sum(1 for x in self.recent_lbd if x <= 2) / len(self.recent_lbd)
        else:
            avg_lbd = 0.0
            var_lbd = 0.0
            glue_ratio = 0.0
        conf_rate = (since_conflicts / max(1e-3, since_time))
        max_act = max(self.activity[1:], default=1.0)
        mean_act = sum(self.activity[1:]) / max(1, self.num_vars)
        std_act = math.sqrt(max(0.0, sum((a - mean_act) ** 2 for a in self.activity[1:]) / max(1, self.num_vars)))
        mean_act_n = mean_act / max(1e-9, max_act)
        std_act_n = std_act / max(1e-9, max_act)
        total_clauses = len(self.clauses)
        learned = max(0, total_clauses - self.orig_clause_count)
        learned_ratio = learned / max(1, total_clauses)
        clause_var_ratio = total_clauses / max(1, self.num_vars)
        restarts_rate = (self.restarts) / max(1, self.conflicts)
        prop_rate = (since_props / max(1, since_decisions))
        sat_ratio = self.satisfied_ratio()
        feats = [
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
        return feats

    def maybe_restart(self):
        if self.restart_interval <= 0:
            return
        if self.conflicts > 0 and self.conflicts % self.restart_interval == 0 and self.decision_level > 0:
            self.backtrack(0)
            self.restarts += 1

    def pick_branch_literal(self) -> Optional[int]:
        lit = self.heuristics[self.current_arm].decide(self)
        if lit is not None:
            return lit
        v = self.pick_first_unassigned()
        if v is None:
            return None
        if self.phase[v] is not None:
            return v if self.phase[v] else -v
        return v

    def _compute_epoch_reward(self, d_conf: int, d_dec: int, d_prop: int, prev_avg_lbd: float, curr_avg_lbd: float, solved: bool) -> float:
        r = 1.0 / (1.0 + d_conf)
        r += 0.01 * (d_prop / max(1, d_dec))
        if prev_avg_lbd > 0 and curr_avg_lbd > 0:
            r += 0.05 * max(0.0, (prev_avg_lbd - curr_avg_lbd) / prev_avg_lbd)
        if solved:
            r += 1.0
        return r

    def _end_epoch_update(self, final: bool = False):
        if self.agent is None or self.last_context is None or self.last_arm is None:
            return
        d_conf = self.conflicts - self.epoch_start_conflicts
        d_dec = self.decisions - self.epoch_start_decisions
        d_prop = self.propagations - self.epoch_start_props
        curr_avg_lbd = (sum(self.recent_lbd) / len(self.recent_lbd)) if self.recent_lbd else 0.0
        prev_avg_lbd = curr_avg_lbd
        reward = self._compute_epoch_reward(d_conf, d_dec, d_prop, prev_avg_lbd, curr_avg_lbd, solved=final)
        self.agent.update(self.last_arm, self.last_context, reward)
        # log row
        if self.logger is not None:
            row = {
                'epoch': self.epoch_index,
                'heuristic': self.heuristic_names[self.current_arm],
                'reward': reward,
                'd_conflicts': d_conf,
                'd_decisions': d_dec,
                'd_propagations': d_prop,
                'avg_lbd': curr_avg_lbd,
                'conflicts': self.conflicts,
                'decisions': self.decisions,
                'propagations': self.propagations,
                'restarts': self.restarts,
            }
            # add context features with names c0..cN
            for i, v in enumerate(self.last_context):
                row[f'c{i}'] = v
            self.logger.log(row)
        self.epoch_index += 1

    def _start_new_epoch(self):
        self.epoch_start_conflicts = self.conflicts
        self.epoch_start_time = time.time()
        self.epoch_start_decisions = self.decisions
        self.epoch_start_props = self.propagations
        ctx = self.feature_context(0, 0, 0, 1e-3)
        arm = self.agent.select(ctx) if self.agent is not None else 0
        self.current_arm = arm
        self.last_arm = arm
        self.last_context = ctx

    def solve(self) -> bool:
        self.add_watches()
        last_log = time.time()
        init_context = self.feature_context(0, 0, 0, 1e-3)
        dim = len(init_context)
        self.agent = LinUCB(n_arms=len(self.heuristics), dim=dim, alpha=0.3)
        self.current_arm = 0
        self.last_context = init_context
        self.last_arm = self.current_arm
        self._start_new_epoch()

        while True:
            conflict = self.propagate()
            if conflict is not None:
                self.conflicts += 1
                now = time.time()
                if self.conflicts % 50 == 0 or now - last_log > 2:
                    print(f"[RL] lvl={self.decision_level} conf={self.conflicts} dec={self.decisions} prop={self.propagations} rest={self.restarts} heur={self.heuristic_names[self.current_arm]}")
                    last_log = now
                if self.decision_level == 0:
                    print('[RL] UNSAT at level 0')
                    self._end_epoch_update(final=True)
                    return False
                learnt, bt = self.analyze_conflict(conflict)
                self.backtrack(bt)
                self.clauses.append(learnt)
                # notify JW
                for h in self.heuristics:
                    if isinstance(h, JWStrategy):
                        h.notify_clause_added(self, learnt)
                # watch
                self.watch_literal(learnt, learnt[0])
                if len(learnt) > 1:
                    self.watch_literal(learnt, learnt[1])
                self.enqueue(learnt[0], learnt)
                self.maybe_restart()
                if (self.conflicts - self.epoch_start_conflicts) >= self.epoch_size:
                    self._end_epoch_update()
                    self._start_new_epoch()
            else:
                lit = self.pick_branch_literal()
                if lit is None:
                    print(f"[RL] SAT after {self.conflicts} conflicts")
                    self._end_epoch_update(final=True)
                    return True
                self.decision_level += 1
                self.trail_limits.append(len(self.trail))
                self.enqueue(lit, None)
                if time.time() - last_log > 2:
                    print(f"[RL] new lvl={self.decision_level} heur={self.heuristic_names[self.current_arm]}")
                    last_log = time.time()
