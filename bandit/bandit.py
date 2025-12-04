import math
from typing import List
import random


class LinUCB:
    def __init__(self, n_arms: int, dim: int, alpha: float = 0.3):
        self.n_arms = n_arms
        self.dim = dim
        self.alpha = alpha
        self.A_inv = [self._eye(dim) for _ in range(n_arms)]
        self.b = [[0.0 for _ in range(dim)] for _ in range(n_arms)]

    def _eye(self, n: int) -> List[List[float]]:
        return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    def _mat_vec(self, M: List[List[float]], v: List[float]) -> List[float]:
        return [sum(M[i][j] * v[j] for j in range(self.dim)) for i in range(self.dim)]

    def _dot(self, a: List[float], b: List[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def _quad(self, A: List[List[float]], x: List[float]) -> float:
        Ax = self._mat_vec(A, x)
        return self._dot(x, Ax)

    def select(self, x: List[float]) -> int:
        scores = []
        for a in range(self.n_arms):
            theta = self._mat_vec(self.A_inv[a], self.b[a])
            exploit = self._dot(theta, x)
            explore = self.alpha * math.sqrt(max(1e-12, self._quad(self.A_inv[a], x)))
            scores.append(exploit + explore)
        max_score = max(scores)
        best = [i for i, s in enumerate(scores) if s == max_score]
        return random.choice(best)

    def update(self, arm: int, x: List[float], reward: float):
        Ainv = self.A_inv[arm]
        # Sherman–Morrison
        Ainv_x = self._mat_vec(Ainv, x)
        denom = 1.0 + self._dot(x, Ainv_x)
        for i in range(self.dim):
            for j in range(self.dim):
                Ainv[i][j] -= (Ainv_x[i] * Ainv_x[j]) / max(1e-12, denom)
        self.b[arm] = [self.b[arm][i] + reward * x[i] for i in range(self.dim)]
