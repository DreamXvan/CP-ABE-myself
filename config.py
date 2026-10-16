import math
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
k = math.floor(math.log(q, b) + 1)
m = k + 2

# gadget vector g = (1, b, b^2, ..., b^(k-1)) of the G-lattice, used both by
# RTrapGen and by the base-b digit decomposition inside SamplePre
h = [b ** i for i in range(k)]

# Bounded (truncated) discrete Gaussian: every sampled coefficient lies in
# [-BOUND, BOUND], which makes the decryption error bound computable.
SIGMA = 1.0
BOUND = 2

# q does not fit into a machine word, so every coefficient is kept as a
# Python integer (numpy object dtype).
u = np.array([random.randrange(0, q) for _ in range(f)], dtype=object)

# total number of attributes
# [10, 15, 20, 25]
attr = 10

V = 10
