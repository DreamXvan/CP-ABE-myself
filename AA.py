import random
import numpy as np

from algo import RTrapGen, SamplePre
from config import attr, q, f, V, m
from util import *


class AA:
    '''
    Authority
    '''

    def __init__(self) -> None:
        # secret linear map P (paper: P_tau).  Its coefficients must be bounded,
        # otherwise y = P.z is huge and the noise e.y would swallow the message.
        self._C = np.array(gauss_int(m*f*V), dtype=object).reshape(m, f, V)
    def AASetup(self):
        self.A, self._T = RTrapGen()

        self.b_plus = np.array([gen_multiple_polynomials(m)
                               for _ in range(attr)], dtype=object)
        self.b_minus = np.array([gen_multiple_polynomials(m)
                                for _ in range(attr)], dtype=object)

    def _P(self, z):
        '''
        z has shape (V,)
        C has shape (m, f, V)
        returns P = C @ z, of shape (m * f)
        '''
        return np.dot(self._C, z)

    def S(self):
        '''
        attributes given to the user
        '''
        X = random.getrandbits(attr)
        self.X = np.array([1 & X >> i for i in range(attr)])
        return self.X

    def SecretKey(self, E):
        delta = E
        self._SK = np.zeros((attr + 1, m, f), dtype=object)

        for i in range(attr):
            z = np.array(gauss_int(V), dtype=object)
            y = self._P(z)
            self._SK[i] = y

            n = poly_dotprod(self.b_plus[i], y) if self.X[i] == 1 else poly_dotprod(
                self.b_minus[i], y)

            # Delta_tau = E(tau) - sum_i n_{tau,i}   (must accumulate!)
            delta = poly_add(delta, -1 * n)

        # y_{tau,A_tau} <- RSamplePre(A_tau, T_{A_tau}, Delta_tau, sigma, sigma_s)
        self._SK[attr] = SamplePre(self.A, self._T, delta)

    def Decrypt(self, cipher, F, W):
        '''
        per-authority decryption share Theta_tau = Theta_{tau,0} + sum_i [Theta_{tau,i,1} + Theta_{tau,i,2}]

        The scalar vector g is the reconstruction vector of the LSSS matrix F,
        i.e. sum_i g_i F_i = (1, 0, ..., 0).  F is built in User.Encrypt so that
        its first row already spans the shared secret, hence g = e_1.
        '''
        g = np.zeros(attr, dtype=object)
        g[0] = 1

        L = poly_dotprod(cipher['c_A'], self._SK[attr])

        for i in range(attr):
            L = poly_add(L, g[i]*cipher['c_{0}_2'.format(i)])

            if W[i] == 1:
                L1 = poly_dotprod(cipher['c_{0}_1'.format(i)], self._SK[i])
                L = poly_add(L, L1)
            elif self.X[i] == 1:
                L1 = poly_dotprod(cipher['c_plus_{0}_1'.format(i)], self._SK[i])
                L = poly_add(L, L1)
            else:
                L1 = poly_dotprod(cipher['c_minus_{0}_1'.format(i)], self._SK[i])
                L = poly_add(L, L1)

        return L
