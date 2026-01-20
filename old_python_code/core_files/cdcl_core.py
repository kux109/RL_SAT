from typing import List, Optional
import math
from heap import VarOrderHeap

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
        
        # Initialize Heap with all variables (initially unassigned)
        self.var_heap = VarOrderHeap(self.activity)
        self.var_heap.rebuild(list(range(1, num_vars + 1)))

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
            if self.var_heap.in_heap(v):
                self.var_heap.update(v)
        self.act_inc /= self.act_decay
        if max(self.activity[1:], default=0.0) > 1e100:
            for i in range(1, self.num_vars + 1):
                self.activity[i] *= 1e-100
            # after rescaling, heap order is preserved relative to each other, 
            # but scores change. Technically might strictly not valid if precision lost?
            # Rebuilding is safe but expensive. Sifting down all might be needed?
            # Usually strict relative order is preserved so heap property holds.

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
        # Remove from heap as it is now assigned
        self.var_heap.remove(var)
        
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
            # Add back to heap as it is unassigned
            self.var_heap.insert(var)
        self.decision_level = level

    def pick_first_unassigned(self) -> Optional[int]:
        # Fallback if heuristic returns None, or used by Random
        for v in range(1, self.num_vars + 1):
            if self.assignments[v] is None:
                return v
        return None

    def analyze_conflict(self, conflict_clause: List[int]):
        learnt_clause: List[int] = []
        if self.decision_level == 0:
            return [], -1
        
        seen = [False] * (self.num_vars + 1)
        counter = 0
        p = None
        
        clause_to_process = conflict_clause
        idx = len(self.trail) - 1
        
        while True:
            # Bump activity for variables in the clause being processed
            if clause_to_process:
                self.bump_activity(clause_to_process)
                
            for lit in clause_to_process:
                var = abs(lit)
                if not seen[var] and self.level[var] > 0:
                    seen[var] = True
                    if self.level[var] == self.decision_level:
                        counter += 1
                    else:
                        learnt_clause.append(lit)
            
            # Select next literal to resolve
            while True:
                p = self.trail[idx]
                var = abs(p)
                idx -= 1
                if seen[var]:
                    break
            
            seen[var] = False
            counter -= 1
            if counter == 0:
                break
            
            # Resolve with reason clause
            reason_clause = self.reason[var]
            if reason_clause is not None:
                # reason_clause includes the literal 'p' itself, or we implicitly know it implies p.
                # In standard CDCL implementation, reason vector usually contains the literals that implied p.
                # We need all literals from reason_clause EXCEPT p (or those that falsify p).
                # The current implementation of propagate stores the whole clause as reason.
                # So we process the whole clause. 'seen' check handles duplicates.
                clause_to_process = reason_clause
            else:
                # Should not happen if counter > 0
                break

        # p is the UIP. Add -p to learnt clause
        # The learnt clause must contain the negation of the UIP literal
        # p is the literal in the trail (could be positive or negative)
        # We need to add the literal that falsifies the UIP in the clause
        # If p is in trail, it is true. We add -p.
        learnt_clause.insert(0, -p)
        
        # Compute backtrack level
        if len(learnt_clause) == 1:
            backtrack_level = 0
        else:
            # Find max level among other literals
            max_lvl = 0
            for lit in learnt_clause[1:]:
                lvl = self.level[abs(lit)]
                if lvl > max_lvl:
                    max_lvl = lvl
            backtrack_level = max_lvl

        lbd = self.compute_lbd(learnt_clause)
        self.recent_lbd.append(lbd)
        if len(self.recent_lbd) > self.lbd_window:
            self.recent_lbd.pop(0)
            
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
