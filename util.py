import math
import operator
import random

import numpy as np

import config as cfg


_rng = random.SystemRandom()


def gen_polynomial():
    """Sample a uniform R_q polynomial, in descending coefficient order."""
    return np.array([_rng.randrange(cfg.q) for _ in range(cfg.f)], dtype=object)


def gen_multiple_polynomials(m):
    return np.array([gen_polynomial() for _ in range(m)],
                    dtype=object).reshape(m, cfg.f)


def _coefficients(poly):
    values = np.asarray(poly, dtype=object)
    if values.ndim != 1:
        raise ValueError('a polynomial must be a one-dimensional coefficient vector')
    return np.array([operator.index(value) for value in values], dtype=object)


def poly_mod(exp):
    """Reduce exactly modulo (q, x^f + 1), padding to f coefficients."""
    values = _coefficients(exp)
    result = np.zeros(cfg.f, dtype=object)
    for degree, value in enumerate(reversed(values)):
        quotient, remainder = divmod(degree, cfg.f)
        result[-remainder - 1] += -value if quotient % 2 else value
    return result % cfg.q


def poly_add(s1, s2):
    return (poly_mod(s1) + poly_mod(s2)) % cfg.q


def poly_mul(s1, s2):
    left = np.trim_zeros(poly_mod(s1), 'f')
    right = np.trim_zeros(poly_mod(s2), 'f')
    if not len(left) or not len(right):
        return np.zeros(cfg.f, dtype=object)
    return poly_mod(np.convolve(left, right))


def poly_dotprod(s1, s2):
    if len(s1) != len(s2):
        raise ValueError('polynomial vectors must have equal lengths')
    result = np.zeros(cfg.f, dtype=object)
    for left, right in zip(s1, s2):
        result = poly_add(result, poly_mul(left, right))
    return result


def poly_op(a, s1, s2):
    return poly_add(poly_mul(a, s1), s2)


def centered(poly):
    """Return the signed representatives in [-q//2, q//2]."""
    reduced = poly_mod(poly)
    return np.array([value - cfg.q if value > cfg.q // 2 else value
                     for value in reduced], dtype=object)


def gaussian_bound(sigma=None):
    sigma = cfg.noise_sigma if sigma is None else sigma
    if not math.isfinite(sigma) or sigma < 0:
        raise ValueError('Gaussian sigma must be finite and nonnegative')
    return math.ceil(cfg.gaussian_tail * sigma)


def sample_small_polynomial(sigma=None):
    """Sample finite discrete weights exp(-pi*x^2/sigma^2).

    Support is truncated at gaussian_tail*sigma and weights use floating point.
    This prototype sampler has no cryptographic distribution guarantee.
    """
    sigma = cfg.noise_sigma if sigma is None else sigma
    bound = gaussian_bound(sigma)
    if sigma == 0:
        return np.zeros(cfg.f, dtype=object)
    support = range(-bound, bound + 1)
    weights = [math.exp(-math.pi * (value / sigma)**2) for value in support]
    return np.array(_rng.choices(support, weights=weights, k=cfg.f), dtype=object)


def sample_small_polynomials(count, sigma=None):
    return np.array([sample_small_polynomial(sigma) for _ in range(count)],
                    dtype=object).reshape(count, cfg.f)


def Lagrange(theta):
    """Exact reconstruction weight at zero for all authority IDs 1..N."""
    if not 1 <= theta <= cfg.N:
        raise ValueError('authority ID must be in 1..N')
    return (-1 if theta % 2 == 0 else 1) * math.comb(cfg.N, theta)


def reconstruction_coefficients(F, available=None):
    """Solve sum_i g_i F_i = (1,0,...) over F_q.

    F contains scalar field coefficients. available contains zero-based row
    indices. Return one centered coefficient per row, zero for unavailable rows.
    """
    matrix = np.asarray(F, dtype=object)
    if matrix.ndim != 2 or not all(matrix.shape):
        raise ValueError('the sharing matrix must have nonempty rows and columns')
    row_count, columns = matrix.shape
    rows = list(range(row_count)) if available is None else list(available)
    if len(set(rows)) != len(rows) or any(not 0 <= row < row_count for row in rows):
        raise ValueError('available rows must be distinct valid row indices')
    # Transpose to solve F_available^T g = e_1 by modular elimination.
    equations = [[operator.index(matrix[row, column]) % cfg.q for row in rows]
                 + [1 if column == 0 else 0] for column in range(columns)]
    pivots = []
    pivot_row = 0
    for variable in range(len(rows)):
        chosen = next((index for index in range(pivot_row, columns)
                       if equations[index][variable]), None)
        if chosen is None:
            continue
        equations[pivot_row], equations[chosen] = equations[chosen], equations[pivot_row]
        inverse = pow(equations[pivot_row][variable], -1, cfg.q)
        equations[pivot_row] = [(value * inverse) % cfg.q
                                for value in equations[pivot_row]]
        for index in range(columns):
            if index != pivot_row:
                multiplier = equations[index][variable]
                equations[index] = [(value - multiplier * pivot) % cfg.q
                                    for value, pivot in zip(equations[index],
                                                            equations[pivot_row])]
        pivots.append((pivot_row, variable))
        pivot_row += 1
        if pivot_row == columns:
            break
    if any(not any(equation[:-1]) and equation[-1] for equation in equations):
        raise ValueError('available sharing rows cannot reconstruct the secret')
    result = np.zeros(row_count, dtype=object)
    for equation, variable in pivots:
        value = equations[equation][-1]
        result[rows[variable]] = value - cfg.q if value > cfg.q // 2 else value
    return result
