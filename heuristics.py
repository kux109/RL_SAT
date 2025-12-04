from typing import List, Optional
import random


class HeuristicStrategy:
    name: str = "base"

    def decide(self, solver) -> Optional[int]:
        raise NotImplementedError


class RandomStrategy(HeuristicStrategy):
    name = "random"

    def decide(self, solver) -> Optional[int]:
        for v in range(1, solver.num_vars + 1):
            if solver.assignments[v] is None:
                if solver.phase[v] is not None:
                    return v if solver.phase[v] else -v
                return v if random.random() < 0.5 else -v
        return None


class VSIDSStrategy(HeuristicStrategy):
    name = "vsids"

    def decide(self, solver) -> Optional[int]:
        best_v = None
        best_act = -1.0
        for v in range(1, solver.num_vars + 1):
            if solver.assignments[v] is None:
                act = solver.activity[v]
                if act > best_act:
                    best_act = act
                    best_v = v
        if best_v is None:
            return None
        if solver.phase[best_v] is not None:
            return best_v if solver.phase[best_v] else -best_v
        return best_v


class JWStrategy(HeuristicStrategy):
    name = "jw"

    def __init__(self):
        self.pos_w = None
        self.neg_w = None

    def ensure(self, solver):
        if self.pos_w is None or len(self.pos_w) != solver.num_vars + 1:
            self.pos_w = [0.0] * (solver.num_vars + 1)
            self.neg_w = [0.0] * (solver.num_vars + 1)
            self.recompute_weights(solver)

    def recompute_weights(self, solver):
        self.pos_w = [0.0] * (solver.num_vars + 1)
        self.neg_w = [0.0] * (solver.num_vars + 1)
        for c in solver.clauses:
            k = max(1, len(c))
            w = 2.0 ** (-k)
            for lit in c:
                if lit > 0:
                    self.pos_w[abs(lit)] += w
                else:
                    self.neg_w[abs(lit)] += w

    def notify_clause_added(self, solver, clause: List[int]):
        self.ensure(solver)
        k = max(1, len(clause))
        w = 2.0 ** (-k)
        for lit in clause:
            if lit > 0:
                self.pos_w[abs(lit)] += w
            else:
                self.neg_w[abs(lit)] += w

    def decide(self, solver) -> Optional[int]:
        self.ensure(solver)
        best_v = None
        best_score = -1.0
        best_sign = True
        for v in range(1, solver.num_vars + 1):
            if solver.assignments[v] is not None:
                continue
            pos = self.pos_w[v]
            neg = self.neg_w[v]
            if pos >= neg:
                score = pos
                sign = True
            else:
                score = neg
                sign = False
            if score > best_score:
                best_score = score
                best_v = v
                best_sign = sign
        if best_v is None:
            return None
        if solver.phase[best_v] is not None:
            return best_v if solver.phase[best_v] else -best_v
        return best_v if best_sign else -best_v


class DLISStrategy(HeuristicStrategy):
    name = "dlis"

    def decide(self, solver) -> Optional[int]:
        best_lit = None
        best_count = -1
        for v in range(1, solver.num_vars + 1):
            if solver.assignments[v] is not None:
                continue
            pos_c = 0
            neg_c = 0
            for c in solver.clauses:
                if solver.is_satisfied(c):
                    continue
                if v in map(abs, c):
                    if v in c:
                        pos_c += 1
                    if -v in c:
                        neg_c += 1
            if pos_c >= neg_c:
                count = pos_c
                lit = v
            else:
                count = neg_c
                lit = -v
            if count > best_count:
                best_count = count
                best_lit = lit
        return best_lit
