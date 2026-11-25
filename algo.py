import numpy as np

import config as cfg
from util import (centered, gen_polynomial, poly_add, poly_dotprod, poly_mod,
                  poly_op, sample_small_polynomials)


def RTrapGen():
    """Construct A with the short trapdoor satisfying A[e;r;I] = h."""
    a = gen_polynomial()
    r = sample_small_polynomials(cfg.k, cfg.sigma)
    e = sample_small_polynomials(cfg.k, cfg.sigma)
    one = poly_mod([1])
    gadget_blocks = [poly_add([cfg.h[index]], -poly_op(a, r[index], e[index]))
                     for index in range(cfg.k)]
    public = np.array([one, a] + gadget_blocks, dtype=object)
    return public, (r, e)


def RSamplePre(A, T, target):
    """Exact-preimage prototype using the paper's gadget/trapdoor identity.

    This samples a short disturbance and uses base-b digit decomposition for Y.
    It is NOT a GPV discrete Gaussian coset sampler: neither the distribution of
    Y nor that of the output is the Gaussian distribution claimed in the paper.
    """
    public = np.asarray(A, dtype=object)
    r, e = (np.asarray(part, dtype=object) for part in T)
    if public.shape != (cfg.m, cfg.f) or r.shape != (cfg.k, cfg.f) or e.shape != r.shape:
        raise ValueError('public vector or trapdoor dimensions do not match parameters')
    disturbance = sample_small_polynomials(cfg.m, cfg.sigma_s)
    residual = poly_add(target, -poly_dotprod(public, disturbance))
    digits = np.zeros((cfg.k, cfg.f), dtype=object)
    for column in range(cfg.f):
        value = int(residual[column])
        for index in range(cfg.k):
            value, digits[index, column] = divmod(value, cfg.b)
        if value:
            raise ValueError('the configured base-b gadget is too short for q')
    result = disturbance.copy()
    result[0] = poly_add(disturbance[0], poly_dotprod(e, digits))
    result[1] = poly_add(disturbance[1], poly_dotprod(r, digits))
    for index in range(cfg.k):
        result[index + 2] = poly_add(disturbance[index + 2], digits[index])
    result = np.array([centered(poly) for poly in result], dtype=object)
    if not np.array_equal(poly_dotprod(public, result), poly_mod(target)):
        raise ValueError('trapdoor preimage verification failed')
    return result
