from typing import List, Dict, Optional

class VarOrderHeap:
    def __init__(self, activity: List[float]):
        self.activity = activity  # Reference to solver.activity
        self.heap: List[int] = [] # Stores variable indices
        self.var_to_pos: Dict[int, int] = {} # Maps variable -> position in heap

    def parent(self, i: int) -> int:
        return (i - 1) // 2

    def left(self, i: int) -> int:
        return 2 * i + 1

    def right(self, i: int) -> int:
        return 2 * i + 2

    def in_heap(self, var: int) -> bool:
        return var in self.var_to_pos

    def swap(self, i: int, j: int):
        v1 = self.heap[i]
        v2 = self.heap[j]
        self.heap[i], self.heap[j] = v2, v1
        self.var_to_pos[v1] = j
        self.var_to_pos[v2] = i

    def sift_up(self, i: int):
        while i > 0:
            p = self.parent(i)
            # Max-heap based on activity
            if self.activity[self.heap[i]] > self.activity[self.heap[p]]:
                self.swap(i, p)
                i = p
            else:
                break

    def sift_down(self, i: int):
        size = len(self.heap)
        while True:
            l = self.left(i)
            r = self.right(i)
            largest = i
            if l < size and self.activity[self.heap[l]] > self.activity[self.heap[largest]]:
                largest = l
            if r < size and self.activity[self.heap[r]] > self.activity[self.heap[largest]]:
                largest = r
            if largest != i:
                self.swap(i, largest)
                i = largest
            else:
                break

    def insert(self, var: int):
        if var in self.var_to_pos:
            return
        self.heap.append(var)
        i = len(self.heap) - 1
        self.var_to_pos[var] = i
        self.sift_up(i)

    def remove_max(self) -> int:
        if not self.heap:
            return 0
        root = self.heap[0]
        last = self.heap.pop()
        if self.heap:
            self.heap[0] = last
            self.var_to_pos[last] = 0
            del self.var_to_pos[root]
            self.sift_down(0)
        else:
            del self.var_to_pos[root]
        return root

    def remove(self, var: int):
        if var not in self.var_to_pos:
            return
        idx = self.var_to_pos[var]
        last = self.heap.pop()
        del self.var_to_pos[var]
        if idx < len(self.heap):
            self.heap[idx] = last
            self.var_to_pos[last] = idx
            self.sift_up(idx)
            self.sift_down(idx)

    def update(self, var: int):
        if var in self.var_to_pos:
            self.sift_up(self.var_to_pos[var])
            self.sift_down(self.var_to_pos[var])

    def rebuild(self, variables: List[int]):
        self.heap = []
        self.var_to_pos = {}
        for v in variables:
            self.insert(v)
