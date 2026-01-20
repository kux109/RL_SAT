#ifndef LinUCB_h
#define LinUCB_h

#include <cassert>
#include <cmath>
#include <cstdlib>
#include <vector>

namespace Minisat {

// =================================================================================
// Linear Algebra Helper (Minimal dependency-free implementation)
// =================================================================================
struct Vector {
  std::vector<double> data;
  Vector(int size, double val = 0.0) : data(size, val) {}
  double &operator[](int i) { return data[i]; }
  const double &operator[](int i) const { return data[i]; }
  int size() const { return data.size(); }
};

struct Matrix {
  int rows, cols;
  std::vector<std::vector<double>> data;

  Matrix(int r, int c, double val = 0.0)
      : rows(r), cols(c), data(r, std::vector<double>(c, val)) {}

  static Matrix identity(int size) {
    Matrix res(size, size);
    for (int i = 0; i < size; i++)
      res.data[i][i] = 1.0;
    return res;
  }

  std::vector<double> &operator[](int i) { return data[i]; }
  const std::vector<double> &operator[](int i) const { return data[i]; }

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
  std::vector<Matrix> A_inv; // Inverse of covariance matrix per arm
  std::vector<Vector> b;     // Reward history per arm

public:
  LinUCB(int arms, int features, double alpha_val = 0.5)
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
    if (arm < 0 || arm >= n_arms)
      return;
    // Update b
    for (int i = 0; i < n_features; i++) {
      b[arm][i] += reward * context[i];
    }
    // Update A_inv
    A_inv[arm].update_inverse(context);
  }
};

} // namespace Minisat

#endif
