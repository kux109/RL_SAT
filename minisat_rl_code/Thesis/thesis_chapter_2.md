# Chapter 2: Literature Review

This chapter surveys the evolution of heuristic management in SAT solvers, tracing the trajectory from static decision rules to modern data-driven approaches. We categorize the existing literature into four distinct phases: Classical Foundations, Dynamic Heuristics, Deep Learning approaches, and the emerging field of Lightweight Reinforcement Learning.

## 2.1 Foundations of Modern CDCL
The architecture of modern Conflict-Driven Clause Learning (CDCL) solvers rests on the seminal work of the **MiniSat** solver (Eén & Sörensson, 2003) [1]. MiniSat established the "minimalist" yet highly efficient framework of 1-UIP conflict analysis, two-watched literal propagation, and rapid restarts that defines the current state of the art.

The core decision engine of these solvers is the **VSIDS (Variable State Independent Decaying Sum)** heuristic, introduced in the **Chaff** solver (Moskewicz et al., 2001) [2]. VSIDS prioritizes variables involved in recent conflicts, leveraging the principle of "locality" to focus the search on difficult sub-problems. Despite its success, VSIDS is fundamentally static; its decay rates and prioritization logic are fixed parameters that do not adapt to structural changes in the search space.

Recognizing the need for metrics beyond raw activity, Audemard and Simon (2009) introduced **Literal Block Distance (LBD)** in the **Glucose** solver [3]. LBD measures the quality of learned clauses based on the number of decision levels they span. This metric provided the first "contextual" signal that search progress could be quantified, a concept foundational to our work.

## 2.2 Dynamic Heuristics and Multi-Strategy Solvers
As the diversity of SAT benchmarks grew, it became evident that no single heuristic dominates across all problem classes. This led to the development of dynamic strategy switching.

Biere et al. (2020) demonstrated in **CaDiCaL** and **Kissat** [4] that alternating between "Stable" (VSIDS-focused) and "Focused" (VMTF-focused) search phases significantly improves robustness. Similarly, Cherif et al. (2021) proposed combining VSIDS and **CHB (Conflict History Based)** heuristics using restart triggers [5]. These approaches effectively employ a "Round Robin" or "Time-Triggered" strategy switching mechanism.

While effective, these methods are largely **context-agnostic**. The switch between heuristics is determined by fixed conflict counts or simple timers, rather than an intelligent assessment of the solver's internal state. They do not "learn" which heuristic is appropriate for the *current* difficulty of the problem.

## 2.3 Deep Learning in SAT: The "Heavy" Alternative
Recent advances in Deep Learning have spurred attempts to replace human-designed heuristics entirely with Neural Networks.

Guo (2023) provides a comprehensive survey of these methods [6], highlighting graph-based representations. Notably, **NeuroSAT** (Selsam et al., 2018) and subsequent work by Kurin et al. (2020) [7] formulated SAT as a Graph Neural Network (GNN) problem, attempting to learn branching heuristics via Q-Learning on the clause-variable graph. Yolcu and Póczos (2019) applied similar Reinforcement Learning techniques to Local Search heuristics [8].

However, these approaches face a critical **Inference Bottleneck**. A GNN forward pass is orders of magnitude slower than a single variable propagation in a C++ solver. As noted by Kurin [7], while GNNs can minimize the *number of decisions*, the wall-clock time is often uncompetitive for industrial scale problems. This limitation motivates our shift toward *lightweight* feature-based learning.

## 2.4 Reinforcement Learning in CDCL
The middle ground between static heuristics and heavy Deep RL lies in lightweight, online Reinforcement Learning.

Li et al. (2024) recently explored this direction by applying RL to the **Reset (Restart) Policy** of CDCL solvers [9]. Their agent learns when to restart the search based on runtime features, demonstrating that online learning can outperform static Luby restarts.

Our work extends this philosophy to the **Branching Heuristic**. We utilize the **LinUCB (Linear Upper Confidence Bound)** algorithm (Li et al., 2010) [10], which models the decision problem as a Contextual Bandit. Unlike the neural approaches, LinUCB performs matrix updates that are computationally inexpensive ($< 0.1\%$ overhead), allowing it to be integrated directly into the inner loop of a high-frequency solver like MiniSat.

## 2.5 Summary and Research Gap
The literature reveals a clear dichotomy: solvers are either **fast but static** (Standard CDCL), **dynamic but blind** (Round-Robin MABs), or **intelligent but slow** (GNN-based SAT).

There exists a gap for a system that is **Fast, Intelligent, and State-Aware**. This thesis addresses that gap by integrating lightweight, context-aware bandits into the branching loop, allowing the solver to dynamically select strategies (like Polarity Flipping) based on real-time features (LBD, Glues) without incurring the cost of deep neural networks.
