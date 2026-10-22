import numpy as np

import config as cfg
from util import gen_multiple_polynomials, poly_add


def Setup():
    """Evaluate ONE degree-(N-1) Shamir polynomial with E(0) = u."""
    G = gen_multiple_polynomials(cfg.N - 1)
    shares = []
    for theta in range(1, cfg.N + 1):
        value = cfg.u.copy()
        for degree, coefficient in enumerate(G, 1):
            value = poly_add(value, theta**degree * coefficient)
        shares.append(value)
    return np.array(shares, dtype=object)
