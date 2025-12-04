from typing import List, Optional
import math


class CDCLCore:
    def __init__(self, num_vars: int, clauses: List[List[int]]):
        self.num_vars = num_vars
        self.clauses = clauses
        self.assignments = [None] * (num_vars + 1)
        self.level = [0] * (num_vars + 1)
        self.reason = [None] * (num_vars + 1)
        self.trail: List[int] = []
        self.trail_limits: List[int] = []
        self.decision_level = 0
        self.watched_literals = [[] for _ in range(2 * num_vars + 1)]
        # stats and helper structures
        self.activity = [0.0] * (num_vars + 1)
        self.act_inc = 1.0
        self.act_decay = 0.95
        self.phase = [None] * (num_vars + 1)
        self.conflicts = 0
        self.decisions = 0
        self.propagations = 0
        self.restarts = 0
        self.orig_clause_count = len(clauses)
        self.recent_lbd: List[int] = []
        self.lbd_window = 100

    def literal_to_index(self, lit: int) -> int:
        return lit + self.num_vars

    def watch_literal(self, clause: List[int], lit: int):
        self.watched_literals[self.literal_to_index(lit)].append(clause)

    def add_watches(self):
        for clause in self.clauses:
            if len(clause) > 0:
                self.watch_literal(clause, clause[0])
                if len(clause) > 1:
                    self.watch_literal(clause, clause[1])

    def bump_activity(self, clause: List[int]):
        for lit in clause:
            v = abs(lit)
            self.activity[v] += self.act_inc
        self.act_inc /= self.act_decay
        if max(self.activity[1:], default=0.0) > 1e100:
            for i in range(1, self.num_vars + 1):
                self.activity[i] *= 1e-100

    def enqueue(self, lit: int, reason: Optional[List[int]]):
        var = abs(lit)
        val = lit > 0
        if self.assignments[var] is not None:
            return self.assignments[var] == val
        self.assignments[var] = val
        self.reason[var] = reason
        self.level[var] = self.decision_level
        self.trail.append(lit)
        self.phase[var] = val
        if reason is None:
            self.decisions += 1
        else:
            self.propagations += 1
        return True

    def is_satisfied(self, clause: List[int]) -> bool:
        for lit in clause:
            val = self.assignments[abs(lit)]
            if val is not None and ((lit > 0 and val) or (lit < 0 and not val)):
                return True
        return False

    def propagate(self) -> Optional[List[int]]:
        queue_idx = 0
        while queue_idx < len(self.trail):
            lit = self.trail[queue_idx]
            neg_lit = -lit
            watch_list = self.watched_literals[self.literal_to_index(neg_lit)]
            i = 0
            while i < len(watch_list):
                clause = watch_list[i]
                if self.is_satisfied(clause):
                    i += 1
                    continue
                found_replacement = False
                other_lit = None
                if len(clause) > 1:
                    for l in clause:
                        if l != neg_lit:
                            other_lit = l
                            break
                for lit2 in clause:
                    if lit2 == neg_lit:
                        continue
                    val = self.assignments[abs(lit2)]
                    if val is None or (lit2 > 0 and val) or (lit2 < 0 and not val):
                        watch_list[i] = watch_list[-1]
                        watch_list.pop()
                        self.watch_literal(clause, lit2)
                        found_replacement = True
                        break
                if not found_replacement:
                    if other_lit is not None and self.assignments[abs(other_lit)] is None:
                        if not self.enqueue(other_lit, clause):
                            return clause
                        i += 1
                        continue
                    return clause
                else:
                    i += 1
            queue_idx += 1
        return None

    def backtrack(self, level: int):
        while self.trail and self.level[abs(self.trail[-1])] > level:
            var = abs(self.trail.pop())
            self.assignments[var] = None
            self.reason[var] = None
            self.level[var] = 0
        self.decision_level = level

    def pick_first_unassigned(self) -> Optional[int]:
        for v in range(1, self.num_vars + 1):
            if self.assignments[v] is None:
                return v
        return None

    def analyze_conflict(self, conflict_clause: List[int]):
        learnt_clause: List[int] = []
        seen = set()
        counter = 0
        current_level = self.decision_level
        backtrack_level = 0
        idx = len(self.trail) - 1

        for lit in conflict_clause:
            var = abs(lit)
            if self.level[var] == 0:
                continue
            if var not in seen:
                seen.add(var)
                if self.level[var] == current_level:
                    counter += 1
                else:
                    backtrack_level = max(backtrack_level, self.level[var])
                learnt_clause.append(lit)

        while counter > 1:
            lit = self.trail[idx]
            var = abs(lit)
            if var in seen:
                if self.reason[var] is not None:
                    for l in self.reason[var]:
                        u = abs(l)
                        if u not in seen and self.level[u] > 0:
                            if self.level[u] == current_level:
                                counter += 1
                            else:
                                backtrack_level = max(backtrack_level, self.level[u])
                            learnt_clause.append(l)
                    counter -= 1
                seen.remove(var)
            idx -= 1

        lbd = self.compute_lbd(learnt_clause)
        self.recent_lbd.append(lbd)
        if len(self.recent_lbd) > self.lbd_window:
            self.recent_lbd.pop(0)
        self.bump_activity(learnt_clause)
        return learnt_clause, backtrack_level

    def compute_lbd(self, clause: List[int]) -> int:
        levels = set()
        for lit in clause:
            levels.add(self.level[abs(lit)])
        return len(levels)

    def satisfied_ratio(self) -> float:
        sat = 0
        for c in self.clauses:
            if self.is_satisfied(c):
                sat += 1
        return sat / max(1, len(self.clauses))
