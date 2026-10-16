import numpy as np
import random
from config import attr, q, f, u, m
from util import *
import time


class User:
    '''
    User class
    '''

    def AccessControl(self, X):
        '''
        define access structure using attributes

        W' = W^+ | W^- is the policy and it is satisfied by the attribute set X
        of the user, hence W^+ is a subset of X and W^- is a subset of the
        complement of X.  (Both were subsets of X before, so the sign of
        n_{tau,i} disagreed with the ciphertext component c_{tau,i,1} for every
        negative attribute and decryption could never cancel.)
        '''
        mask = random.getrandbits(attr)
        self.W_plus = np.array([X[i] & mask >> i for i in range(attr)])

        mask = random.getrandbits(attr)
        self.W_minus = np.array([(1 ^ X[i]) & mask >> i for i in range(attr)])

        self.W = self.W_plus | self.W_minus

    def Encrypt(self, phi, AAs):
        '''
        encrypting data for every authority.

        Returns (c_0, ciphers) where ciphers[tau] holds the components that
        belong to authority AA_tau.
        '''
        # share generating matrix F of the LSSS, built so that the first row
        # alone spans the shared secret: sum_i g_i F_i = (1, 0, ..., 0) with
        # g = e_1 (see AA.Decrypt).  The remaining rows are random shares.
        self.F = np.array([gen_multiple_polynomials(m)
                           for _ in range(attr)], dtype=object)
        one = np.zeros(f, dtype=object)
        one[-1] = 1
        self.F[0] = np.array([one] + [np.zeros(f, dtype=object) for _ in range(m-1)],
                             dtype=object)

        # Sigma = (d, r_2, ..., r_m); d is the secret to be shared
        Sigma = gen_multiple_polynomials(m)
        d = Sigma[0]

        e = gauss_polynomial()

        ud = poly_mul(u, d)
        c0 = poly_add(poly_add(2 * ud, e), q//2 * np.asarray(phi, dtype=object))

        ciphers = []
        for aa in AAs:
            A, b_plus, b_minus = aa.A, aa.b_plus, aa.b_minus

            e_A = gauss_multiple_polynomials(m)
            c_A = np.array([poly_add(poly_mul(A[i], d), e_A[i])
                            for i in range(m)], dtype=object)

            out = {'c_0': c0, 'c_A': c_A}

            for i in range(attr):
                c_2 = poly_dotprod(self.F[i][1:], Sigma[1:])
                c_2 = poly_add(c_2, poly_mul(self.F[i][0], ud))
                c_2 = poly_add(c_2, gauss_polynomial())
                out['c_{0}_2'.format(i)] = c_2

                e_1 = gauss_multiple_polynomials(m)

                if self.W_plus[i] == 1:
                    c_1 = np.array([poly_add(poly_mul(b_plus[i][j], d), e_1[j])
                                    for j in range(m)], dtype=object)
                    out['c_{0}_1'.format(i)] = c_1

                elif self.W_minus[i] == 1:
                    c_1 = np.array([poly_add(poly_mul(b_minus[i][j], d), e_1[j])
                                    for j in range(m)], dtype=object)
                    out['c_{0}_1'.format(i)] = c_1

                else:
                    c_1_plus = np.array([poly_add(poly_mul(b_plus[i][j], d), e_1[j])
                                         for j in range(m)], dtype=object)

                    c_1_minus = np.array([poly_add(poly_mul(b_minus[i][j], d), e_1[j])
                                          for j in range(m)], dtype=object)

                    out['c_plus_{0}_1'.format(i)] = c_1_plus
                    out['c_minus_{0}_1'.format(i)] = c_1_minus

            ciphers.append(out)

        return c0, ciphers
