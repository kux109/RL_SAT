#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

// =================================================================================
// CDCL Solver Implementation
// =================================================================================

struct Clause {
  vector<int> lits;
  bool learnt = false;
  float lbd = 0;
};

enum VarValue { UNDEF = -1, FALSE_VAL = 0, TRUE_VAL = 1 };

struct VarData {
  VarValue value = UNDEF;
  int level = -1;
  int reason_cls_idx = -1; // -1 means decision or no reason
  float activity = 0.0;
};

// Heap for VSIDS
class VarHeap {
  vector<int> heap;            // stores var indices
  vector<int> pos;             // var -> index in heap
  const vector<VarData> &vars; // reference to activity

public:
  VarHeap(const vector<VarData> &v) : vars(v) {}

  void resize(int n_vars) { pos.resize(n_vars + 1, -1); }

  // Helper functions
  int left(int i) { return 2 * i + 1; }
  int right(int i) { return 2 * i + 2; }
  int parent(int i) { return (i - 1) / 2; }

  bool in_heap(int var) { return pos[var] != -1; }

  void insert(int var) {
    if (in_heap(var))
      return;
    heap.push_back(var);
    pos[var] = heap.size() - 1;
    sift_up(pos[var]);
  }

  void remove(int var) {
    if (!in_heap(var))
      return;
    int idx = pos[var];
    int last_var = heap.back();
    heap.pop_back();

    if (idx != (int)heap.size()) { // If we didn't remove the last element
      heap[idx] = last_var;
      pos[last_var] = idx;
      // We moved the last element to `idx`. It might need to go up or down.
      sift_up(idx);
      sift_down(idx);
    }
    pos[var] = -1;
  }

  int remove_max() {
    if (heap.empty())
      return 0;
    int max_var = heap[0];
    remove(max_var);
    return max_var;
  }

  void update(int var) {
    if (in_heap(var)) {
      sift_up(pos[var]);
      sift_down(pos[var]);
    }
  }

  void sift_up(int i) {
    while (i > 0) {
      int p = parent(i);
      if (vars[heap[i]].activity > vars[heap[p]].activity) {
        swap_nodes(i, p);
        i = p;
      } else {
        break;
      }
    }
  }

  void sift_down(int i) {
    int size = heap.size();
    while (true) {
      int l = left(i);
      int r = right(i);
      int largest = i;
      if (l < size && vars[heap[l]].activity > vars[heap[largest]].activity)
        largest = l;
      if (r < size && vars[heap[r]].activity > vars[heap[largest]].activity)
        largest = r;
      if (largest != i) {
        swap_nodes(i, largest);
        i = largest;
      } else {
        break;
      }
    }
  }

  void swap_nodes(int i, int j) {
    swap(heap[i], heap[j]);
    pos[heap[i]] = i;
    pos[heap[j]] = j;
  }

  bool empty() const { return heap.empty(); }
};

// =================================================================================
// Linear Algebra Helper (Minimal dependency-free implementation)
// =================================================================================
struct Vector {
  vector<double> data;
  Vector(int size, double val = 0.0) : data(size, val) {}
  double &operator[](int i) { return data[i]; }
  const double &operator[](int i) const { return data[i]; }
  int size() const { return data.size(); }
};

struct Matrix {
  int rows, cols;
  vector<vector<double>> data;

  Matrix(int r, int c, double val = 0.0)
      : rows(r), cols(c), data(r, vector<double>(c, val)) {}

  static Matrix identity(int size) {
    Matrix res(size, size);
    for (int i = 0; i < size; i++)
      res.data[i][i] = 1.0;
    return res;
  }

  vector<double> &operator[](int i) { return data[i]; }
  const vector<double> &operator[](int i) const { return data[i]; }

  // Minimal Matrix-Vector Multiply
  Vector dot(const Vector &v) const {
    assert(cols == v.size());
    Vector res(rows);
    for (int i = 0; i < rows; i++) {
      for (int j = 0; j < cols; j++) {
        res[i] += data[i][j] * v[j];
      }
    }
    return res;
  }

  // Sherman-Morrison Update: (A + uv^T)^-1 = A^-1 - (A^-1 u v^T A^-1) / (1 +
  // v^T A^-1 u) Here we update A_inv with new feature vector x: A <- A + xx^T
  void update_inverse(const Vector &x) {
    int d = rows;
    // Compute z = A_inv * x
    Vector z = this->dot(x);

    // Compute factor = 1 + x^T * z
    double factor = 1.0;
    for (int i = 0; i < d; i++)
      factor += x[i] * z[i];

    // Update A_inv: A_inv -= (z * z^T) / factor
    for (int i = 0; i < d; i++) {
      for (int j = 0; j < d; j++) {
        data[i][j] -= (z[i] * z[j]) / factor;
      }
    }
  }
};

// =================================================================================
// LinUCB Bandit Implementation
// =================================================================================
class LinUCB {
  int n_arms;
  int n_features;
  double alpha;
  vector<Matrix> A_inv; // Inverse of covariance matrix per arm
  vector<Vector> b;     // Reward history per arm

public:
  LinUCB(int arms, int features, double alpha_val = 0.1)
      : n_arms(arms), n_features(features), alpha(alpha_val) {
    for (int i = 0; i < n_arms; i++) {
      A_inv.push_back(Matrix::identity(n_features));
      b.push_back(Vector(n_features, 0.0));
    }
  }

  // Returns arm index
  int select(const Vector &context) {
    int best_arm = -1;
    double max_ucb = -1e9;

    for (int a = 0; a < n_arms; a++) {
      // Theta = A_inv * b
      Vector theta = A_inv[a].dot(b[a]);

      // Expected Reward = theta^T * x
      double mean = 0.0;
      for (int i = 0; i < n_features; i++)
        mean += theta[i] * context[i];

      // Variance = x^T * A_inv * x
      double var = 0.0;
      Vector temp = A_inv[a].dot(context);
      for (int i = 0; i < n_features; i++)
        var += context[i] * temp[i];

      double ucb = mean + alpha * sqrt(var);

      if (ucb > max_ucb) {
        max_ucb = ucb;
        best_arm = a;
      }
    }
    return best_arm;
  }

  void update(int arm, const Vector &context, double reward) {
    // Update b
    for (int i = 0; i < n_features; i++) {
      b[arm][i] += reward * context[i];
    }
    // Update A_inv
    A_inv[arm].update_inverse(context);
  }
};

class Solver {
public:
  int n_vars;
  vector<Clause> clauses;
  vector<VarData> var_data;
  vector<vector<int>> watches; // lit -> list of clause indices

  // Assignments
  vector<int> trail;
  vector<int> trail_lim; // decision levels
  int q_head = 0;        // propagation queue head

  // Statistics / VSIDS
  double var_inc = 1.0;
  double var_decay = 0.95;
  long long conflicts = 0;

  // RL Components
  bool use_rl = false;
  LinUCB *agent = nullptr;
  int current_epoch_start = 0;
  int epoch_size = 500; // Same as Python
  int current_arm = 0;  // 0 = VSIDS, 1 = JW (Simplified for C++)

  // Metrics for Features
  float lbd_avg = 0.0;
  float glue_ratio = 0.0;
  int recent_lbd_sum = 0;
  int lbd_count = 0;

  // Epoch Stats (for RL Reward)
  int epoch_lbd_sum = 0;
  int epoch_lbd_count = 0;
  int epoch_glue_count = 0;

  VarHeap order_heap;

  Solver() : n_vars(0), order_heap(var_data) {}

  ~Solver() {
    if (agent)
      delete agent;
  }

  void init_rl() {
    use_rl = true;
    // 5 Features: [Bias, LBD_Avg, Glue_Ratio, Decision_Depth, Trail_Util]
    agent = new LinUCB(2, 5, 0.5);
  }

  Vector get_features() {
    Vector f(5);
    f[0] = 1.0; // Bias
    f[1] = (lbd_count > 0) ? (float)recent_lbd_sum / lbd_count : 0.0;
    f[2] = glue_ratio; // Need to track this in update
    f[3] = (n_vars > 0) ? (float)trail_lim.size() / n_vars : 0.0;
    f[4] = (n_vars > 0) ? (float)trail.size() / n_vars : 0.0;
    return f;
  }

  int lit_to_idx(int lit) { return (lit > 0) ? (lit) : (-lit + n_vars); }
  // ^ Wait, standard mapping: 1..N -> 1..N, -1..-N -> N+1..2N?
  // Let's use standard: lit > 0 -> 2*(v-1), lit < 0 -> 2*(v-1)+1
  int to_int(int lit) {
    int v = abs(lit);
    return (lit > 0) ? 2 * (v - 1) : 2 * (v - 1) + 1;
  }
  int to_lit(int l) {
    int v = (l / 2) + 1;
    return (l % 2 == 0) ? v : -v;
  }

  void resize_vars(int n) {
    n_vars = n;
    var_data.resize(n + 1);
    watches.resize(2 * n);
    order_heap.resize(n);
    for (int i = 1; i <= n; i++) {
      order_heap.insert(i);
    }
  }

  void parse_dimacs(string filename) {
    ifstream infile(filename);
    if (!infile) {
      cerr << "Error opening " << filename << endl;
      exit(1);
    }
    string line;
    while (getline(infile, line)) {
      if (line.empty() || line[0] == 'c')
        continue;
      if (line[0] == 'p') {
        stringstream ss(line);
        string temp;
        int nc;
        ss >> temp >> temp >> n_vars >> nc;
        resize_vars(n_vars);
        continue;
      }
      vector<int> lits;
      stringstream ss(line);
      int lit;
      while (ss >> lit) {
        if (lit == 0)
          break;
        lits.push_back(lit);
      }
      if (!lits.empty())
        add_clause(lits);
    }
  }

  void add_clause(vector<int> &lits) {
    Clause c;
    c.lits = lits;
    clauses.push_back(c);
    int c_idx = clauses.size() - 1;

    if (lits.empty()) {
      cout << "UNSAT (empty clause)" << endl;
      exit(0);
    }

    if (lits.size() == 1) {
      // Unit clause at level 0
      enqueue(lits[0]);
    } else {
      // Watch two literals
      watches[to_int(lits[0])].push_back(c_idx);
      watches[to_int(lits[1])].push_back(c_idx);
    }
  }

  // Returns false if conflict
  bool enqueue(int lit, int reason_cls = -1) {
    int v = abs(lit);
    if (var_data[v].value != UNDEF) {
      return (var_data[v].value == (lit > 0 ? TRUE_VAL : FALSE_VAL));
    }

    var_data[v].value = (lit > 0) ? TRUE_VAL : FALSE_VAL;
    var_data[v].level = trail_lim.size(); // Current decision level
    var_data[v].reason_cls_idx = reason_cls;
    trail.push_back(lit);
    return true;
  }

  // Returns conflict clause index, or -1 if none
  int propagate() {
    int conflict_cls = -1;
    while (q_head < (int)trail.size()) {
      int p = trail[q_head++]; // Literal that is TRUE
      int false_lit = -p;      // The literal that became FALSE

      // Inspect watches for this false literal
      // We are watching `l`, which is false. We need to find a new watch or
      // propagate.
      int idx = to_int(false_lit);
      vector<int> &ws = watches[idx];

      for (int i = 0; i < (int)ws.size(); i++) {
        int c_idx = ws[i];
        Clause &c = clauses[c_idx];

        // Ensure false_lit is at c[1]
        if (to_int(c.lits[0]) == idx) {
          swap(c.lits[0], c.lits[1]);
        }

        // If 0th literal is already true, clause is satisfied
        int v0 = abs(c.lits[0]);
        VarValue val0 = var_data[v0].value;
        if (val0 != UNDEF) {
          bool is_true =
              (c.lits[0] > 0) ? (val0 == TRUE_VAL) : (val0 == FALSE_VAL);
          if (is_true) {
            // Clause satisfied, keep watching
            continue;
          }
        }

        // Look for replacement watch
        bool found = false;
        for (int k = 2; k < (int)c.lits.size(); k++) {
          int lit_k = c.lits[k];
          int vk = abs(lit_k);
          VarValue val_k = var_data[vk].value;
          // Need non-false literal
          if (val_k == UNDEF || ((lit_k > 0) == (val_k == TRUE_VAL))) {
            swap(c.lits[1], c.lits[k]);
            watches[to_int(c.lits[1])].push_back(c_idx);

            // Remove from current watch list
            ws[i] = ws.back();
            ws.pop_back();
            i--; // Revisit this index
            found = true;
            break;
          }
        }

        if (!found) {
          // No replacement. c[0] must be implied or conflict.
          if (val0 == UNDEF) {
            // Propagate c[0]
            enqueue(c.lits[0], c_idx);
          } else {
            // Conflict: c[0] is FALSE, c[1] is FALSE (that's `p`)
            // And we couldn't find any other TRUE/UNDEF literal.
            conflict_cls = c_idx;
            // DO NOT return immediately, we might want to clear q?
            // Actually standard is return immediately.
            return conflict_cls;
          }
        }
      }
    }
    return -1;
  }

  // 1-UIP Analysis with LBD calculation
  void analyze(int conflict_cls, vector<int> &learnt_clause,
               int &backtrack_lvl) {
    int path_c = 0;
    int p = -1;

    learnt_clause.clear();
    learnt_clause.push_back(0);

    int index = trail.size() - 1;
    vector<bool> seen(n_vars + 1, false);
    int c_idx = conflict_cls;

    do {
      if (c_idx != -1) {
        Clause &c = clauses[c_idx];
        for (int lit : c.lits) {
          int v = abs(lit);
          var_data[v].activity += var_inc;
          if (order_heap.in_heap(v))
            order_heap.update(v);

          if (lit == p)
            continue;

          if (!seen[v] && var_data[v].level > 0) {
            seen[v] = true;
            if (var_data[v].level >= (int)trail_lim.size()) {
              path_c++;
            } else {
              learnt_clause.push_back(lit);
            }
          }
        }
      }
      while (!seen[abs(trail[index])])
        index--;
      p = trail[index--];
      seen[abs(p)] = false;
      path_c--;
      c_idx = var_data[abs(p)].reason_cls_idx;
    } while (path_c > 0);

    learnt_clause[0] = -p;

    // Compute LBD
    int lbd = 0;
    set<int> levels;
    for (int lit : learnt_clause)
      levels.insert(var_data[abs(lit)].level);
    lbd = levels.size();

    // Update Stats
    recent_lbd_sum += lbd;
    lbd_count++; // Total learned clauses

    // Epoch Stats
    epoch_lbd_sum += lbd;
    epoch_lbd_count++;

    if (lbd <= 2) {
      glue_ratio++; // Tracking low LBD clauses as 'glue'
      epoch_glue_count++;
    }

    var_inc *= (1.0 / var_decay);

    backtrack_lvl = 0;
    if (learnt_clause.size() > 1) {
      int max_lvl = 0;
      for (size_t i = 1; i < learnt_clause.size(); i++) {
        int lvl = var_data[abs(learnt_clause[i])].level;
        if (lvl > max_lvl)
          max_lvl = lvl;
      }
      backtrack_lvl = max_lvl;
    }
  }

  void backtrack(int level) {
    while ((int)trail_lim.size() > level) {
      int limit = trail_lim.back();
      trail_lim.pop_back();
      while ((int)trail.size() > limit) {
        int lit = trail.back();
        trail.pop_back();
        int v = abs(lit);
        var_data[v].value = UNDEF;
        var_data[v].reason_cls_idx = -1;
        var_data[v].level = -1;
        order_heap.insert(v);
      }
    }
    q_head = trail.size();
  }

  // Heuristics
  int pick_jw() {
    // Jeroslow-Wang (Static/Dynamic) - Simplified Dynamic One-Sided
    // Just pick literal with max count in open clauses (approx)
    // For efficiency, we'll just use VSIDS but picking the 'least' active?
    // No, C++ implementation of full JW is expensive (O(Clauses)).
    // Let's implement a random exploration or alternate VSIDS (e.g., Min VSIDS)
    // as 'Arm 1'. Better: Use 'Random' as Arm 1 for proof of concept? Or
    // simple: Pick unassigned var with max occurrences (needs a count array).
    // Let's settle for: Arm 0 = VSIDS, Arm 1 = Random (to allow valid
    // comparison to Python "Random" baseline) OR better: Arm 1 = Pick Oldest
    // Activity (Anti-VSIDS) to see if exploring old variables helps?

    // Standard RL paper approach: VSIDS vs LRB or VSIDS vs Random.
    // Let's do Random for stability.
    int v = rand() % n_vars + 1;
    while (var_data[v].value != UNDEF) {
      v = rand() % n_vars + 1;
    }
    return v;
  }

  int restarts = 0;    // Class member now
  int step_size = 500; // Default epoch size

  // Luby Sequence: 1, 1, 2, 1, 1, 2, 4, 1...
  // Optimized to use int arithmetic
  int luby(int x) {
    int size, seq;
    for (size = 1, seq = 0; size < x + 1; seq++, size = 2 * size + 1)
      ;
    while (size - 1 != x) {
      size = (size - 1) >> 1;
      seq--;
      x = x % size;
    }
    return 1 << seq; // Equivalent to pow(2, seq) but integer
  }

  void print_stats() {
    float avg_lbd = (lbd_count > 0) ? (float)recent_lbd_sum / lbd_count : 0.0;
    float glue = (lbd_count > 0) ? (float)glue_ratio / lbd_count : 0.0;
    cout << "c STATS Conflicts=" << conflicts << " Restarts=" << restarts
         << " LBD=" << avg_lbd << " Glue=" << glue << endl;
  }

  bool solve() {
    if (use_rl && !agent)
      init_rl();
    current_arm = 0;

    // Use configured step size
    epoch_size = step_size;

    // Restart Parameters
    int restart_base = 100;
    long long conflicts_at_last_restart = 0;
    long long limit = restart_base * luby(restarts + 1);

    while (true) {
      if (use_rl && conflicts - current_epoch_start >= epoch_size) {
        // Calculate Epoch Metrics
        int epoch_confl = conflicts - current_epoch_start;
        float epoch_avg_lbd = (epoch_lbd_count > 0)
                                  ? (float)epoch_lbd_sum / epoch_lbd_count
                                  : 0.0;
        float epoch_glue_rate =
            (epoch_confl > 0) ? (float)epoch_glue_count / epoch_confl : 0.0;

        // Reward Shaping: Maximize Glue, Minimize LBD, Minimize Conflicts
        // Base reward: -0.1 per conflict (Penalty for slowness)
        // Bonus: +100 per Glue clause found
        // Penalty: -1 per point of Average LBD
        float reward = -(float)epoch_confl * 0.01;
        reward += (epoch_glue_count * 50.0);
        reward -= (epoch_avg_lbd * 2.0);

        // Clip reward for stability
        if (reward < -10.0)
          reward = -10.0;
        if (reward > 10.0)
          reward = 10.0;

        Vector ctx = get_features();
        ctx[2] = epoch_glue_rate;
        agent->update(current_arm, ctx, reward);

        // Adaptive Restart Strategy (The "Cook" - Force restarts if LBD is bad)
        // If local search is producing bad clauses (High LBD), generic restarts
        // might be too slow. RL actively kills the path.
        if (epoch_avg_lbd > 4.0 || epoch_glue_count == 0) {
          backtrack(0);
          restarts++;
          // Reset Luby limit
          limit = restart_base * luby(restarts + 1);
          conflicts_at_last_restart = conflicts;
        }

        // Select new arm
        current_arm = agent->select(ctx);

        // Reset Epoch Stats
        current_epoch_start = conflicts;
        epoch_lbd_sum = 0;
        epoch_lbd_count = 0;
        epoch_glue_count = 0;

        if (epoch_size >= 100)
          print_stats();
      }

      int conflict = propagate();
      if (conflict != -1) {
        if (trail_lim.empty())
          return false;
        vector<int> learnt_clause;
        int bt_level;
        analyze(conflict, learnt_clause, bt_level);
        backtrack(bt_level);
        add_clause(learnt_clause);
        enqueue(learnt_clause[0], clauses.size() - 1);
        conflicts++;

        // Periodically print stats (Every 1000 conflicts for better
        // validability on timeouts)
        if (conflicts % 1000 == 0)
          print_stats();

        if (conflicts - conflicts_at_last_restart >= limit) {
          conflicts_at_last_restart = conflicts;
          restarts++;
          backtrack(0);
          limit = restart_base * luby(restarts + 1);
        }
      } else {
        int next_var;
        // Arm 0: VSIDS (Default, False)
        // Arm 1: VSIDS (Flip, True)
        if (!use_rl || current_arm == 0) {
          next_var = order_heap.remove_max();
          if (next_var == 0)
            return true;
          trail_lim.push_back(trail.size());
          enqueue(-next_var); // Default: Try FALSE
        } else {
          next_var = order_heap.remove_max();
          if (next_var == 0)
            return true;
          trail_lim.push_back(trail.size());
          enqueue(next_var); // RL Exploration: Try TRUE
        }
      }
    }
  }
};

int main(int argc, char **argv) {
  if (argc < 2) {
    cerr << "Usage: ./solver <cnf_file> [--rl] [--step N]" << endl;
    return 1;
  }
  string filename = argv[1];
  bool use_rl = false;
  int step = 500;

  for (int i = 2; i < argc; i++) {
    string arg = argv[i];
    if (arg == "--rl")
      use_rl = true;
    else if (arg == "--step" && i + 1 < argc) {
      step = atoi(argv[i + 1]);
      i++;
    }
  }

  Solver s;
  s.step_size = step;
  if (use_rl)
    s.init_rl();

  cout << "c Solving " << filename << (use_rl ? " with RL" : " (Baseline)")
       << " Step=" << step << "..." << endl;

  auto start = chrono::high_resolution_clock::now();
  s.parse_dimacs(filename);
  bool sat = s.solve();
  auto end = chrono::high_resolution_clock::now();

  // Final Stats (Standard Output Format)
  cout << "s " << (sat ? "SATISFIABLE" : "UNSATISFIABLE") << endl;
  cout << "c Time: " << chrono::duration<double>(end - start).count() << endl;
  cout << "c Conflicts: " << s.conflicts << endl;
  cout << "c Restarts: " << s.restarts << endl;

  s.print_stats(); // Print final LBD/Glue line

  return 0;
}
