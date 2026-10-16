# helpers
import numpy as np
from config import *
from util import *


def RTrapGen():
    """
    Ring trap generation.

    Outputs (A, T) with A in R_q^m of the form

        A = ( 1, a, h_0 - a.r_0 - e_0, ..., h_{k-1} - a.r_{k-1} - e_{k-1} )

    and the trapdoor T = (r, e) in R_q^k x R_q^k.  r and e are drawn from the
    bounded discrete Gaussian (they were uniform in [0, q) before, which made
    the preimages produced by SamplePre arbitrarily long).
    """
    a = gen_polynomial()
    r = gauss_multiple_polynomials(k)
    e = gauss_multiple_polynomials(k)

    one = np.zeros(f, dtype=object)
    one[-1] = 1                                     # constant polynomial 1
    A = np.array([one, a], dtype=object)
    b_rows = np.array([(np.array([0]*(f-1) + [h[i]], dtype=object) - poly_op(a, r[i], e[i]))
                       for i in range(k)], dtype=object)

    A = np.concatenate((A, b_rows))
    T = (r, e)

    return A, T


def _digits(value):
    """
    centered base-b digits of a single coefficient, i.e. value = sum_i d_i b^i
    """
    ds = []
    for _ in range(k):
        d = value % b
        if d > b // 2:
            d -= b
        ds.append(d)
        value = (value - d) // b
    assert value == 0, 'gadget is too short to represent the target'

    return ds


def SamplePre(A, T, delta):
    """
    RSamplePre(A, T_A, delta, sigma, sigma_s): return a short y in R_q^m with

        A . y = delta

    Using the gadget decomposition delta = sum_i h_i d_i one gets

        y = ( sum_i e_i d_i , sum_i r_i d_i , d_0, ..., d_{k-1} )

    which satisfies A . y = delta exactly and stays short because r, e and the
    digits d_i are all bounded.
    """
    r, e = T

    D = np.zeros((k, f), dtype=object)
    for j, c in enumerate(delta):
        D[:, j] = _digits(int(c))

    y = np.zeros((m, f), dtype=object)
    y[2:] = D
    y[1] = poly_dotprod(r, D)
    y[0] = poly_dotprod(e, D)

    return y
