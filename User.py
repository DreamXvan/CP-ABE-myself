import random

import numpy as np

import config as cfg
from util import (Lagrange, centered, gaussian_bound, gen_multiple_polynomials,
                  poly_add, poly_mul, sample_small_polynomial,
                  sample_small_polynomials)


class User:
    '''Data owner and recipient for the paper's signed AND policy subset.'''

    def AccessControl(self, X=None, policy=None):
        '''policy[theta-1, i]: +1 present, -1 absent, 0 wildcard.'''
        if policy is None:
            attributes = np.asarray(X, dtype=object)
            if attributes.shape != (cfg.N, cfg.attr) or not np.all(np.isin(attributes, [0, 1])):
                raise ValueError('Attributes must have shape (N, attr) and be binary')
            policy = np.array([
                [(1 if bit else -1) if random.getrandbits(1) else 0 for bit in row]
                for row in attributes
            ], dtype=object)
        policy = np.asarray(policy, dtype=object)
        if policy.shape != (cfg.N, cfg.attr) or not np.all(np.isin(policy, [-1, 0, 1])):
            raise ValueError('Policy must have shape (N, attr) with literals -1, 0, 1')
        self.W = policy.copy()
        self.W_plus = (policy == 1)
        self.W_minus = (policy == -1)
        self.F = []
        for row in policy:
            required = list(np.flatnonzero(row))
            # A wildcard row carries ud for the always-true local policy.
            if not required:
                required = [0]
            if len(required) > cfg.m:
                raise ValueError('Signed AND policy requires at most m literals per authority')
            matrix = np.zeros((cfg.attr, cfg.m), dtype=object)
            matrix[required[0], 0] = 1
            # Chain shares telescope; all required rows sum to (1, 0, ..., 0).
            for j in range(len(required) - 1):
                matrix[required[j], j + 1] = 1
                matrix[required[j + 1], j + 1] = -1
            self.F.append(matrix)

    def Encrypt(self, phi, A, b_plus, b_minus):
        phi = np.asarray(phi, dtype=object)
        if phi.shape != (cfg.f,) or not np.all(np.isin(phi, [0, 1])):
            raise ValueError('Plaintext must be an f-length binary vector')
        if len(A) != cfg.N or len(b_plus) != cfg.N or len(b_minus) != cfg.N:
            raise ValueError('Encryption requires all N public authority keys')
        Sigma = gen_multiple_polynomials(cfg.m)
        d = Sigma[0]
        ud = poly_mul(cfg.u, d)
        c0 = poly_add(poly_add(2 * ud, sample_small_polynomial()), (cfg.q // 2) * phi)
        out = {'c_0': c0, 'authorities': []}
        for index in range(cfg.N):
            errors = sample_small_polynomials(cfg.m)
            part = {
                'theta': index + 1,
                'c_A': np.array([poly_add(poly_mul(a, d), e)
                                 for a, e in zip(A[index], errors)], dtype=object),
                'F': self.F[index].copy(), 'W': self.W[index].copy(),
            }
            for i in range(cfg.attr):
                # F is a scalar F_q matrix, as in the paper's LSSS definition.
                c2 = int(self.F[index][i, 0]) * ud
                for j in range(1, cfg.m):
                    if self.F[index][i, j]:
                        c2 = poly_add(c2, int(self.F[index][i, j]) * Sigma[j])
                part[f'c_{i}_2'] = poly_add(c2, sample_small_polynomial())
                if self.W_plus[index, i]:
                    choices = [(f'c_{i}_1', b_plus[index][i])]
                elif self.W_minus[index, i]:
                    choices = [(f'c_{i}_1', b_minus[index][i])]
                else:
                    choices = [(f'c_plus_{i}_1', b_plus[index][i]),
                               (f'c_minus_{i}_1', b_minus[index][i])]
                for name, public in choices:
                    # Positive and negative branches use independent errors.
                    errors = sample_small_polynomials(cfg.m)
                    part[name] = np.array([poly_add(poly_mul(b, d), e)
                                           for b, e in zip(public, errors)], dtype=object)
            out['authorities'].append(part)
        return out

    def noise_bound(self, authorities, parts=None):
        '''Check the deterministic budget before encryption or on ciphertext data.'''
        if parts is None:
            parts = [{'theta': i + 1, 'F': matrix, 'W': self.W[i]}
                     for i, matrix in enumerate(self.F)]
        identities = [aa.theta for aa in authorities]
        expected = list(range(1, cfg.N + 1))
        if sorted(identities) != expected or sorted(part['theta'] for part in parts) != expected:
            raise ValueError('Decryption requires each of the N authorities exactly once')
        by_identity = {aa.theta: aa for aa in authorities}
        bound = gaussian_bound()
        for part in parts:
            aa = by_identity[part['theta']]
            g = aa.reconstruction(part)
            bound += abs(Lagrange(aa.theta)) * aa.noise_bound(g)
        # One unit of margin also covers encoding a bit as floor(q/2).
        if 4 * (bound + 1) >= cfg.q:
            raise ValueError('Noise bound is too large for correct q/4 decoding')
        return bound

    def Decrypt(self, cipher, authorities):
        parts = cipher['authorities']
        bound = self.noise_bound(authorities, parts)
        by_identity = {aa.theta: aa for aa in authorities}
        residual = np.asarray(cipher['c_0'], dtype=object).copy()
        self.last_noise_bound = bound
        for part in parts:
            aa = by_identity[part['theta']]
            residual = poly_add(residual, -Lagrange(aa.theta) * aa.Decrypt(part))
        residual = centered(residual)
        self.last_residual = residual.copy()
        return np.array([int(4 * abs(int(value)) >= cfg.q) for value in residual], dtype=object)
