# all channel operations are simulated here

from KGC import *
from AA import *
from User import *
from config import N, f, attr, b, m
import time


def label(en, zh):
    '''
    bilingual output: the original English wording stays in place and the
    Chinese translation is appended, so that the layout is unchanged
    '''
    return '{0}（{1}）'.format(en, zh)


def boolean(value):
    return label(str(value), '是' if value else '否')


def timeit(code, title):
    st = time.time()
    res = code()
    end = time.time()
    t = round(end - st, 2)
    print(title, '-', t, '(s)')
    return res


print(label('Sampling profile', '采样方式') + ': ' + label('bounded', '有界'))
print(label('Parameters', '参数') + ': N={0}, f={1}, attr={2}, b={3}, m={4}'.format(
    N, f, attr, b, m))

aas = [AA() for _ in range(N)]
user = User()

E = timeit(lambda: Setup(), label('Setup', '系统初始化'))
timeit(lambda: [aa.AASetup() for aa in aas], label('AASetup', '授权机构初始化'))

# all authorities share the same attribute universe in this simulation
X = aas[0].S()
for aa in aas:
    aa.X = X

timeit(lambda: [aa.SecretKey(E[tau]) for tau, aa in enumerate(aas)],
       label('KeyGen', '用户密钥生成'))

user.AccessControl(X)
msg = random.getrandbits(f)
phi = np.array([1 & msg >> i for i in range(f)])

print(label('Guaranteed coefficient error bound', '保证的系数误差上界') + ':',
      guaranteed_error_bound())

c_0, ciphers = timeit(lambda: user.Encrypt(phi, aas), label('Encryption', '加密'))

thetas = timeit(lambda: [aa.Decrypt(ciphers[tau], user.F, user.W)
                         for tau, aa in enumerate(aas)],
                label('Decryption', '解密'))

# phi' = c_0 - sum_tau L_tau * Theta_tau
phi_prime = c_0
for tau in range(N):
    phi_prime = poly_add(phi_prime, -1 * (Lagrange(tau+1) * thetas[tau]))

# centered representatives, phi_i = 0 if |phi'_i| < q/4 else 1
centered = [int(x) if x <= q//2 else int(x) - q for x in phi_prime]
recovered = np.array([1 if abs(x) >= q//4 else 0 for x in centered])

# the error has to be measured mod q: phi'_i = (q//2).phi_i + error, and the
# centered representative of (q//2).1 = (q-1)/2 is positive while the one of
# (q+1)/2 is negative, so a plain subtraction would report an error of ~q.
error = []
for i in range(f):
    diff = (int(phi_prime[i]) - (q//2) * int(phi[i])) % q
    if diff > q//2:
        diff -= q
    error.append(abs(diff))
observed = max(error)
recovered_bits = int(sum(1 for i in range(f) if recovered[i] == phi[i]))
success = bool(np.array_equal(recovered, phi))

print(label('Recovered bits', '正确恢复的比特数') + ': {0}/{1}'.format(recovered_bits, f))
print(label('Observed error max', '实测最大误差') + ': {0}'.format(observed))
print(label('Error below q/4', '误差小于 q/4') + ': ' + boolean(observed < q//4))
print(label('Plaintext recovered', '明文恢复成功') + ': ' + boolean(success))
