from util import *
from config import u, N


def Setup():
    '''
    E(x) = u + sum_{I=1}^{N-1} G_I x^I, evaluated at x = 1, ..., N.

    The constant term of E is u itself, so the G_0 coefficient is *not* used:
    otherwise sum_tau L_tau E(tau) = u + G_0 instead of E(0) = u and the
    Lagrange reconstruction in Decryption would not cancel the 2.u.d term.
    '''
    G = gen_multiple_polynomials(N)

    def E(x):
        res = np.array(u, dtype=object)
        for I in range(1, N):
            res = poly_add(res, np.array(G[I], dtype=object) * x**I)

        return res

    return np.array([E(i) for i in range(1, N+1)], dtype=object)
