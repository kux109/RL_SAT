# Chapter 1: Introduction

## 1.1 The Boolean Satisfiability Problem (SAT)
The Boolean Satisfiability Problem (SAT) stands as one of the most fundamental challenges in computer science. Defined as the problem of determining whether there exists an interpretation that satisfies a given Boolean formula, SAT was the first problem proved to be NP-complete by the Cook-Levin theorem in 1971. Despite its theoretical hardness, SAT has evolved from an academic curiosity into a pragmatic workhorse for modern industry. From verifying the correctness of microprocessors and optimizing railway schedules to solving complex cryptographic challenges and dependency management in software repositories, the ability to solve massive SAT instances is a cornerstone of automated reasoning.

The core of the problem is deceptive in its simplicity: given a formula in Conjunctive Normal Form (CNF)—a conjunction of clauses, where each clause is a disjunction of literals—can we assign truth values (True/False) to the variables such that the entire formula evaluates to True? In practice, modern instances contain millions of variables and clauses, creating a search space of magnitude $2^{1000000}$ that renders naive brute-force approaches impossible.

## 1.2 The Evolution of Solvers: From DPLL to CDCL
For decades, the Davis-Putnam-Logemann-Loveland (DPLL) algorithm provided the framework for complete SAT solvers via backtracking search. However, the true revolution occurred in the late 1990s with the advent of **Conflict-Driven Clause Learning (CDCL)**.

CDCL solvers, exemplified by engines like **MiniSat**, transformed the landscape by treating "failure" as "learning." Instead of simply backtracking when a conflict arises (i.e., when a variable must be both True and False simultaneously), CDCL solvers analyze the conflict graph to deduce the root cause. They then learn a new "conflict clause" that prevents the solver from ever exploring that specific invalid subtree again. This mechanism, combined with **Non-Chronological Backtracking** (jumping back multiple levels) and **Lazy Data Structures** (Two-Watched Literals), allowed solvers to handle industrial instances of unprecedented scale.

## 1.3 The Heuristic Bottleneck
While CDCL provided the architecture for success, the "brain" of the solver lies in its branching heuristic: deciding *which* variable to pick next. For over two years, the dominant standard has been **VSIDS (Variable State Independent Decaying Sum)**.

VSIDS operates on a simple principle of "activity": variables involved in recent conflicts are prioritized. This focus on "locality" allows the solver to hammer away at the most difficult parts of the problem until they are resolved. However, VSIDS—and its variants like CHB or LRB—are fundamentally **static** (or slowly decaying) and **context-agnostic**. They apply the same logic regardless of the search state.
*   **The Problem:** On "Heavy-Tail" hard random instances, static heuristics often guide the solver into deep, fruitless subtrees (local minima) from which it takes millions of steps to recover. The solver effectively "hallucinates" that it is making progress, unaware that it is traversing a Refutation Proof that is exponentially large.

## 1.4 The Opportunity: Reinforcement Learning (RL)
This stagnation is a decision-making problem. If we view the SAT solver as an agent navigating a state space (the assignment stack), and the "solved instance" as the goal, the parallel with **Reinforcement Learning (RL)** becomes evident.

Why RL? Traditional heuristics are manually engineered "rules of thumb." RL offers the promise of **data-driven decision making**, where an agent learns to map the internal state of the solver (The Context) to the optimal branching decision (The Action). While Offline Learning (training a Neural Network on millions of instances) has shown promise (e.g., NeuroSAT), it suffers from massive overhead and lack of generalization. The gap lies in **Online Learning**: can an agent learn *during* the solving of a single instance?

## 1.5 Research Problem: Context-Aware Dynamic Strategy Selection
Existing attempts to make solvers dynamic (e.g., KISSAT's Multi-Armed Bandits) often employ "Context-Free" learning. They track which heuristic wins more often but ignore *why*. They fail to ask: "Is the solver currently in a deep search phase? Are the learned clauses high-quality (low LBD) or garbage?"

**This thesis addresses the lack of Context-Awareness in dynamic SAT solvers.** We posit that a solver requires a meta-cognitive layer—a controller that monitors the "health" of the search process in real-time. By observing features like the **Literal Block Distance (LBD)** distribution and **Glue Clause** generation rates, an agent should be able to detect stagnation and intervene.

## 1.6 Proposed Approach: Contextual Bandits in MiniSat
We introduce a hybrid framework integrating **Linear Upper Confidence Bound (LinUCB)** bandits directly into the decision loop of **MiniSat 2.2**. Our approach diverges from standard methods by formulating the problem as **Epoch-Based Strategy Selection**:
1.  **State Representation:** Every 500 conflicts (an Epoch), we extract a feature vector summarizing the search trajectory.
2.  **Action Space:** The agent chooses between:
    *   **Exploitation (Arm 0):** The standard VSIDS heuristic.
    *   **Exploration (Arm 1 - "Polarity Flipping"):** A novel strategy that selects the most active variable but forces its value to the *opposite* of its saved phase. This acts as a "smart perturbation," kicking the solver out of local attractors.
3.  **Reward Signal:** A composite function penalizing long conflict chains and rewarding the discovery of "Glue Clauses" (clauses that connect distant search regions).

## 1.7 Thesis Contributions
This work makes the following contributions to the field of Automated Reasoning:
1.  **Native Integration:** We provide a robust, low-overhead C++ implementation of Contextual Bandits within the legacy MiniSat codebase, demonstrating that modern ML components can coexist with highly-optimized solver loops.
2.  **Algorithmic Novelty:** We identify **Polarity Flipping** as a highly effective exploration primitive for escaping local minima in random 3-SAT instances.
3.  **Empirical Validation:** We demonstrate that our context-aware agent achieves a **55% win rate** against the unmodified baseline on the challenging `uf250` dataset, with speedups of up to **22x** on specific instances, effectively "rescuing" searches that otherwise timeout.

## 1.8 Thesis Organization
The remainder of this thesis is organized as follows... [To be continued]
