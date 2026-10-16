import math
import random
from fractions import Fraction

import numpy as np

from config import q, f, N, b, k, m, V, attr, SIGMA, BOUND

####################################

# Bounded discrete Gaussian sampling
#
# The paper only says that the noise is drawn from a discrete Gaussian
# D_{R,sigma} and never fixes its range.  We therefore use a *truncated*
# discrete Gaussian: every sampled coefficient lies in [-BOUND, BOUND].
# This keeps the decryption error bounded and computable.

_support = None
_weights = None


def _gauss_table():
    global _support, _weights
    if _support is None:
        _support = list(range(-BOUND, BOUND + 1))
        w = [math.exp(-(x * x) / (2.0 * SIGMA * SIGMA)) for x in _support]
        s = float(sum(w))
        _weights = [x / s for x in w]
    return _support, _weights


def gauss_int(n=1):
    """
    n coefficients drawn from the bounded discrete Gaussian
    """
    support, weights = _gauss_table()
    return random.choices(support, weights=weights, k=n)


def gauss_polynomial():
    """
    random polynomial of R_q with bounded discrete Gaussian coefficients
    """
    return np.array(gauss_int(f), dtype=object)


def gauss_multiple_polynomials(m):
    return np.array([gauss_polynomial() for _ in range(m)], dtype=object)


def gen_polynomial():
    """
    generate a random polynomial with
    - degree: f
    - range: [0, q-1]

    belongs to R_q
    """
    return np.array([random.randrange(0, q) for _ in range(f)], dtype=object)


def gen_multiple_polynomials(m):
    return np.array([gen_polynomial() for _ in range(m)], dtype=object)

####################################

# Polynomial operations
#
# q ~ 1.46e48 does not fit into a 64 bit integer, so every coefficient is
# carried as a Python int (numpy object dtype).


def poly_mod(exp):
    """
    expression (mod (x^f + 1))
    """
    res = np.asarray(exp, dtype=object) % q
    m = len(res)
    if m < f:
        # np.polyadd drops leading zeros, which would shift every coefficient
        res = np.concatenate((np.zeros(f - m, dtype=object), res))
        m = f
    for i in range(0, m-f):
        d = res[i]
        res[i] -= d
        res[i + f] -= d
    res = res[-f:] % q
    return res


def poly_add(s1, s2):
    """
        t = s1 + s2
    """
    return poly_mod(np.polyadd(np.asarray(s1, dtype=object),
                               np.asarray(s2, dtype=object)))


def poly_mul(s1, s2):
    """
        t = s1 * s2
    """
    return poly_mod(np.convolve(np.asarray(s1, dtype=object),
                                np.asarray(s2, dtype=object)))


def poly_dotprod(s1, s2):
    """
        t = s1[0]*s2[0] + s1[1]*s2[1] ... + s1[m-1]*s2[m-1]
    """
    n = np.zeros(f, dtype=object)
    for a, b in zip(s1, s2):
        n = poly_add(n, poly_mul(a, b))

    return n


def poly_op(a, s1, s2):
    """
        t = a * s1 + s2
    """
    return poly_mod(np.polyadd(np.convolve(np.asarray(s1, dtype=object),
                                           np.asarray(a, dtype=object)), s2))

####################################

# Lagrange Polynomial


def lagrange_ratio(theta):
    """
    Lagrange coefficient L_theta evaluated at 0, kept as an exact rational
    """
    num, den = 1, 1
    for i in range(1, N+1):
        if i != theta:
            num *= -i
            den *= (theta - i)

    return Fraction(num, den)


def Lagrange(theta):
    """
    Lagrange coefficient L_theta(0) as an element of Z_q (q is prime)
    """
    ratio = lagrange_ratio(theta)

    return (ratio.numerator % q) * pow(ratio.denominator % q, -1, q) % q

####################################

# Decryption error


def guaranteed_error_bound():
    """
    Analytic upper bound, per coefficient, of the decryption error

        e' - sum_tau L_tau * (e_{tau,A}.y_{tau,A}
                              + sum_i (e_{tau,i,1}.y_{tau,i} + g_i.e_{tau,i,2}))

    Correctness of the scheme only needs this bound to stay below q/4.
    """
    digit = b // 2                          # |centered base-b digit|
    y_a = k * f * BOUND * digit             # bound on ||y_{tau,A}||_inf
    y_i = f * V * BOUND * BOUND             # bound on ||y_{tau,i}||_inf
    lag = math.ceil(sum(abs(lagrange_ratio(t)) for t in range(1, N+1)))

    per_authority = (m * f * BOUND * y_a        # e_{tau,A} . y_{tau,A}
                     + attr * f * BOUND * y_i   # e_{tau,i,1} . y_{tau,i}
                     + attr * BOUND)            # g_i . e_{tau,i,2}

    return lag * per_authority + BOUND          # + e~
