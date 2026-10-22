import random

import numpy as np

import config as cfg
from algo import RSamplePre, RTrapGen
from util import (gen_multiple_polynomials, gaussian_bound, poly_add,
                  poly_dotprod, reconstruction_coefficients)


class AA:
    '''Authority; Decrypt returns its contribution Lambda_theta, not plaintext.'''

    def __init__(self, theta=1):
        if theta not in range(1, cfg.N + 1):
            raise ValueError('Authority identity must be in 1..N')
        self.theta = theta
        self._C = np.array([
            [[random.randint(-cfg.key_coefficient_bound, cfg.key_coefficient_bound)
              for _ in range(cfg.V)] for _ in range(cfg.f)]
            for _ in range(cfg.m)
        ], dtype=object)

    def AASetup(self):
        self.A, self._T = RTrapGen()
        self.b_plus = np.array([gen_multiple_polynomials(cfg.m)
                                for _ in range(cfg.attr)], dtype=object)
        self.b_minus = np.array([gen_multiple_polynomials(cfg.m)
                                 for _ in range(cfg.attr)], dtype=object)

    def _P(self, z):
        return self._C @ z

    def S(self, attributes=None):
        '''Issue a positive/negative attribute vector for this user's key.'''
        if hasattr(self, '_SK'):
            raise ValueError('Attributes are fixed after key issuance; use a new AA user instance')
        if attributes is None:
            attributes = [random.getrandbits(1) for _ in range(cfg.attr)]
        attributes = np.asarray(attributes, dtype=object)
        if attributes.shape != (cfg.attr,) or not np.all(np.isin(attributes, [0, 1])):
            raise ValueError('Attributes must be an attr-length binary vector')
        self._X = attributes.copy()
        return self.X

    @property
    def X(self):
        # Callers cannot silently change the attribute labels attached to a key.
        return self._X.copy()

    def SecretKey(self, E):
        delta = np.asarray(E, dtype=object).copy()
        if delta.shape != (cfg.f,):
            raise ValueError('A Shamir share must contain f coefficients')
        self._SK = np.zeros((cfg.attr + 1, cfg.m, cfg.f), dtype=object)
        for i in range(cfg.attr):
            # Deliberate short-key completion of the paper's underspecified P(z).
            z = np.array([random.randint(-cfg.key_input_bound, cfg.key_input_bound)
                          for _ in range(cfg.V)], dtype=object)
            y = self._P(z)
            self._SK[i] = y
            public = self.b_plus[i] if self._X[i] else self.b_minus[i]
            delta = poly_add(delta, -poly_dotprod(public, y))
        self._SK[cfg.attr] = RSamplePre(self.A, self._T, delta)
        return self._SK.copy()

    def reconstruction(self, cipher):
        policy = np.asarray(cipher['W'], dtype=object)
        if policy.shape != (cfg.attr,):
            raise ValueError('Policy must contain attr signed literals')
        if not np.all(np.isin(policy, [-1, 0, 1])):
            raise ValueError('Policy literals must be -1, 0 or 1')
        if np.any((policy == 1) & (self._X != 1)) or np.any((policy == -1) & (self._X != 0)):
            raise PermissionError('User attributes do not satisfy the signed AND policy')
        matrix = np.asarray(cipher['F'], dtype=object)
        if matrix.shape != (cfg.attr, cfg.m):
            raise ValueError('LSSS matrix must have shape (attr, m)')
        return reconstruction_coefficients(matrix)

    def noise_bound(self, g):
        '''Coefficient bound for this authority, using the actual signed keys.'''
        key_norm = sum(abs(int(value)) for value in self._SK.flat)
        return gaussian_bound() * (key_norm + sum(abs(int(value)) for value in g))

    def Decrypt(self, cipher):
        '''Compute paper V-E's Lambda_theta after checking policy and LSSS.'''
        if cipher['theta'] != self.theta:
            raise ValueError('Ciphertext and authority identities differ')
        g = self.reconstruction(cipher)
        value = poly_dotprod(cipher['c_A'], self._SK[cfg.attr])
        for i in range(cfg.attr):
            value = poly_add(value, int(g[i]) * cipher[f'c_{i}_2'])
            if cipher['W'][i] != 0:
                component = cipher[f'c_{i}_1']
            elif self._X[i]:
                component = cipher[f'c_plus_{i}_1']
            else:
                component = cipher[f'c_minus_{i}_1']
            value = poly_add(value, poly_dotprod(component, self._SK[i]))
        return value
