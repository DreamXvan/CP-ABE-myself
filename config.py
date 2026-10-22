import numpy as np
import random

# number of authorities
N = 3

# f is degree of polynomial
v = 9
f = 1 << v

# large prime number
q = 1461501637330902918203684832716283019655932564481

b = 17
# Exact base-b digit length; logarithms can round at powers.
k = 1
while b**k <= q:
    k += 1
m = k + 2

h = [b**i for i in range(k)]

# Correctness-prototype parameters; see docs/algorithm-notes.md.
sigma = 2
sigma_s = 3
noise_sigma = 2
gaussian_tail = 6
key_coefficient_bound = 1
key_input_bound = 1

u = np.array([random.randrange(0, q) for _ in range(f)], dtype=object)

# total number of attributes
# [10, 15, 20, 25]
attr = 10

V = 10
