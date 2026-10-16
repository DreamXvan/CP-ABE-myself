# change.md — 对原代码的修改记录

本文档记录为了让本项目能够按照论文
*An Efficient and Secure Post-Quantum Multi-Authority Ciphertext-Policy Attribute-Based
Encryption Method Using Lattice*（以下简称"论文"）所描述的算法**正确运行**，对原代码所做的
全部修改。每条记录给出：**修改位置**、**修改原因**、**修改内容**，以及**对应的论文依据**。

修改遵循 `karpathy-guidelines`：只改与"让算法正确运行"直接相关的代码，不做顺手重构，
不改动无关格式与注释，新代码保持原有命名与风格。

---

## 0. 问题总览

原始代码在 `python main.py` 时直接崩溃：

```
OverflowError: int too big to convert      # User.py:44  c0 = poly_add(poly_add(2 * ud, e), q//2 * phi)
```

即使绕过该异常，算法在数学上也**不可能正确解密**。共定位到 8 类缺陷：

| # | 缺陷 | 后果 |
|---|------|------|
| 1 | `q ≈ 1.46e48` 远超 int64，但所有系数都用 `np.array(...)` 默认 int64 存储 | `OverflowError`，无法运行 |
| 2 | `config.h = [b << (i-1) ...]`（应为 `b ** (i-1)`）| gadget 向量不是 b 的幂，无法表示 $\mathbb{Z}_q$ 中的元素 |
| 3 | 密钥/噪声全部均匀取自 $[0,q)$ | 噪声量级 ~q/2 ≫ q/4，解密必然失败 |
| 4 | `AA.SecretKey` 中 `delta = poly_add(E, -1*n)` 覆盖而非累加 | $\Delta_\tau$ 错误 |
| 5 | `SK[attr]` 直接取随机多项式，未使用陷门 | $A_\tau y_{\tau,A_\tau} \ne \Delta_\tau$ |
| 6 | 未构造满足 $\sum_i g_i F_i=(1,0,\dots,0)$ 的 LSSS 矩阵 | $c_{\tau,i,2}$ 无法重构 $u\cdot d$ |
| 7 | `AccessControl` 使 $W^-\subseteq S$ | 负极性属性的 $b$ 符号与密钥不一致 |
| 8 | 只模拟 1 个授权机构，且拉格朗日系数用浮点数 | 无法完成 $\sum_\tau L_\tau\Theta_\tau$ 重构 |

---

## 1. `config.py`

### 1.1 gadget 向量改为 $b$ 的幂 — 【缺陷 2】

- **位置**：`config.py:19`
- **原因**：论文的 G-lattice gadget 为 $g=(1,b,b^2,\dots,b^{k-1})$，其中
  $k=\lfloor\log_b q\rfloor+1$ 是 $q$ 的 base-$b$ 位数。原式 `b << (i-1)` 得到的是
  $(b,2b,4b,\dots)$，只覆盖到 $b\cdot2^{k-1}\approx9.3\times10^{12}$，与 $q\approx1.46\times10^{48}$
  相差 36 个数量级，`SamplePre` 无法表示目标向量 $\Delta_\tau$。
- **修改**：
  ```diff
  - h = [b << (i-1) for i in range(1, k+1)]
  + # gadget vector g = (1, b, b^2, ..., b^(k-1)) of the G-lattice, used both by
  + # RTrapGen and by the base-b digit decomposition inside SamplePre
  + h = [b ** i for i in range(k)]
  ```
- **依据**：论文 §V-B（AASetup）"AA_τ first runs the ring trap generation algorithm RTrapGen"；
  §IV-D "Gaussian Preimage Sampling"（$G$-lattice 上的原像采样）。

### 1.2 新增有界采样参数 — 【缺陷 3】

- **位置**：`config.py:21-23`（原"Gaussian Params"注释处）
- **原因**：论文只说噪声来自离散高斯 $\mathcal{D}_{R,\sigma}$，未给出范围与 $\sigma$；
  均匀采样会使噪声量级达 $q/2$。需要一个**有硬界**的采样profile，才能给出可计算的解密误差上界。
- **修改**：新增
  ```python
  SIGMA = 1.0   # 截断离散高斯的 σ
  BOUND = 2     # 每个系数的硬界 |coeff| <= BOUND
  ```
- **依据**：论文 §IV-B "Discrete Gaussian"；详见 `采样与噪声方案分析.md`。

### 1.3 `u` 使用 Python 大整数 — 【缺陷 1】

- **位置**：`config.py:25`
- **原因**：$q>2^{63}$，int64 溢出。
- **修改**：
  ```diff
  - u = np.array([random.randrange(0, q) for _ in range(f)])
  + u = np.array([random.randrange(0, q) for _ in range(f)], dtype=object)
  ```
- **依据**：论文 §V-A（Setup）$u \xleftarrow{R} R_q$。

---

## 2. `util.py`

### 2.1 新增有界离散高斯采样器 — 【缺陷 3】

- **位置**：`util.py` 新增 `_gauss_table()` / `gauss_int()` / `gauss_polynomial()` / `gauss_multiple_polynomials()`
- **原因**：需要"系数落在 $[-BOUND, BOUND]$ 内"的采样器，且要能批量生成以控制耗时。
- **修改**：截断离散高斯，权重 $w_x=\exp(-x^2/2\sigma^2),\ x\in[-BOUND,BOUND]$，归一化后用
  `random.choices` 采样。
- **依据**：论文 §IV-B。

### 2.2 多项式系数改为 object dtype — 【缺陷 1】

- **位置**：`gen_polynomial()`、`gen_multiple_polynomials()`
- **原因**：同 1.3，所有承载 $\mathbb{Z}_q$ 系数的数组都必须是 Python 大整数。
- **修改**：`np.array(..., dtype=object)`。

### 2.3 `poly_mod` 增加长度保护

- **位置**：`poly_mod()`
- **原因**：`np.polyadd` 会**自动去掉首部零系数**，若结果首项恰为 0（mod q），数组长度会
  小于 `f`，导致 `res[-f:]` 与折叠循环整体错位。
- **修改**：`if m < f: 左侧补零至长度 f`。
- **说明**：这是防御性修复，不改变正常路径的结果。

### 2.4 `poly_add` / `poly_mul` 强制 object dtype

- **位置**：`poly_add()`、`poly_mul()`、`poly_op()`
- **原因**：原实现中 `np.polyadd([0], j)`、`np.convolve(...)` 在混合 dtype 下可能回退到
  int64 并溢出。
- **修改**：统一用 `np.asarray(x, dtype=object)` 后再运算。

### 2.5 `poly_dotprod` 去掉 Python 级累加循环

- **位置**：`poly_dotprod()`
- **原因**：原实现先构造 `n_poly` 列表再逐个 `poly_add`，在 $m=42$ 时多余地物化了中间数组。
- **修改**：改为单次循环累加，语义完全等价（仍为 $\sum_j s_1[j]s_2[j]$）。

### 2.6 拉格朗日系数改为模 $q$ 精确整数 — 【缺陷 8】

- **位置**：`Lagrange()`，新增 `lagrange_ratio()`
- **原因**：原实现返回 Python `float`（如 3.0、-3.0）。`float * object_array` 会把整型系数
  变成浮点数，$\mathbb{Z}_q$ 上的运算失去精确性；且 $N$ 较大时浮点误差不可接受。
- **修改**：用 `Fraction` 计算精确有理数，再取模 $q$ 的乘法逆元：
  ```python
  return (ratio.numerator % q) * pow(ratio.denominator % q, -1, q) % q
  ```
  $N=3$ 时得到 $L_1=3,\ L_2=q-3\ (\equiv-3),\ L_3=1$，且 $\sum L_\tau \equiv 1 \pmod q$。
- **依据**：论文 §V-E 中 $L_\tau$ 为拉格朗日多项式。

### 2.7 新增解密误差上界 — 【缺陷 3】

- **位置**：`guaranteed_error_bound()`
- **原因**：需要把"采样有界"转换成"可验证的正确性条件"，即论文 §V-E 的 $|\phi'_i|<q/4$。
- **修改**：按 3.3 节推导的公式给出解析上界（详见 `采样与噪声方案分析.md` 第 4 节）。

---

## 3. `algo.py`

### 3.1 `RTrapGen` 的 $r,e$ 改为有界采样 — 【缺陷 3】

- **位置**：`RTrapGen()`，对应原 `algo.py:9-10`
- **原因**：原代码注释即为 `# TODO: gaussian distribution`。$r,e$ 若均匀取自 $[0,q)$，
  则由陷门产生的原像 $y_{\tau,A_\tau}=(\sum_i e_i d_i,\ \sum_i r_i d_i, d_0,\dots)$
  的系数会达到 $q$ 量级，噪声 $e_{\tau,A}\cdot y_{\tau,A}$ 直接吞掉明文。
- **修改**：
  ```diff
  - r = gen_multiple_polynomials(k) # TODO: gaussian distribution
  - e = gen_multiple_polynomials(k)
  + r = gauss_multiple_polynomials(k)
  + e = gauss_multiple_polynomials(k)
  ```
  同时把常量多项式 1 的构造显式化（`one[-1] = 1`，保持"降幂"约定）并统一 dtype。

### 3.2 新增 `SamplePre`（论文的 `RSamplePre`）— 【缺陷 5】

- **位置**：`algo.py` 新增 `_digits()` 与 `SamplePre()`
- **原因**：原代码 `AA.SecretKey` 中 `self._SK[attr] = gen_multiple_polynomials(m)` 是**随机**多项式，
  完全未使用 $A_\tau$ 与陷门 $T_{A_\tau}$，因此 $A_\tau y_{\tau,A_\tau}\ne\Delta_\tau$，
  解密时 $\Theta_{\tau,0}$ 无法还原 $\Delta_\tau\cdot d$。README 也标注 `TrapGen (proxy to be replaced)`。
- **修改**：实现基于 base-$b$ gadget 分解的原像采样。设
  $A_\tau=(1,\ a,\ h_0-ar_0-e_0,\dots,h_{k-1}-ar_{k-1}-e_{k-1})$，
  对 $\Delta_\tau=\sum_i h_i d_i$ 取中心化 base-$b$ 数字 $d_i\in[-\lfloor b/2\rfloor,\lfloor b/2\rfloor]$，令
  $$
  y_{\tau,A_\tau}=\Big(\textstyle\sum_i e_i d_i,\ \sum_i r_i d_i,\ d_0,\dots,d_{k-1}\Big)
  $$
  则
  $A_\tau y_{\tau,A_\tau}=y_0+a y_1+\sum_i(h_i-ar_i-e_i)d_i=\Delta_\tau$
  **精确成立**，且各分量因 $r,e,d_i$ 有界而保持很短。
- **依据**：论文 §IV-D（Gaussian Preimage Sampling）、§V-C（KeyGen 中
  $\Delta_\tau=E(\tau)-\sum_i n_{\tau,i}$ 后运行 `RSamplePre`）。
- **备注**：论文的 `RSamplePre` 还含"扰动向量 $l'$"以实现高斯分布；本项目为**确定性**原像，
  差异与取舍见 `采样与噪声方案分析.md` §5。

---

## 4. `KGC.py`

### 4.1 `E(x)` 不再使用 $G_0$ 项 — 【缺陷 8】

- **位置**：`Setup()`
- **原因**：论文定义 $E(x)=u+\sum_{I=1}^{N-1}G_Ix^I$，常数项就是 $u$。原实现用
  `X = [[x^0,...,x^{N-1}]]` 与 `G[0]` 相乘，等价于 $E(x)=u+G_0+\sum_{I\ge1}G_Ix^I$，于是
  $$\sum_\tau L_\tau E(\tau)=\Big(\sum_\tau L_\tau\Big)(u+G_0)=u+G_0\ne E(0)=u$$
  解密时 $2ud$ 项无法被抵消（$N=3$ 时误差达 $3G_0$ 量级）。
- **修改**：从 $I=1$ 开始累加，常数项直接用 `u`。
- **依据**：论文 §V-A。

---

## 5. `AA.py`

### 5.1 秘密线性映射 $P_\tau$ 改为有界采样 — 【缺陷 3】

- **位置**：`__init__` 中的 `self._C`
- **原因**：$y_{\tau,i}=P_\tau z_i$ 会出现在噪声项 $e_{\tau,i,1}\cdot y_{\tau,i}$ 中。若 $P_\tau$
  均匀取自 $R_q$，即使 $z_i$ 很小，$y_{\tau,i}$ 仍是 $q$ 量级，噪声必然溢出 $q/4$。
- **修改**：`self._C` 用有界离散高斯采样（形状 $(m,f,V)$ 不变），并把生成方式改为一次
  `random.choices(m*f*V)` 后 reshape，避免三重 Python 循环。
- **依据**：论文 §V-B 中 $P_\tau$ 是 ASK（授权机构秘密），其分布论文未指定，属于任务 2 的缺失项。

### 5.2 `SecretKey` 累加 $\Delta_\tau$ — 【缺陷 4】

- **位置**：`SecretKey()`，对应原 `AA.py:55`
- **原因**：原式为
  ```python
  delta = poly_add(E, -1 * n)     # 每次迭代都覆盖 delta
  ```
  循环结束后只剩 $\Delta_\tau=E(\tau)-n_{\tau,h_\tau}$，丢失了前面所有 $n_{\tau,i}$。
  论文要求 $\Delta_\tau=E(\tau)-\sum_{i=1}^{h_\tau}n_{\tau,i}$。
- **修改**：
  ```diff
  - delta = poly_add(E, -1 * n)
  + # Delta_tau = E(tau) - sum_i n_{tau,i}   (must accumulate!)
  + delta = poly_add(delta, -1 * n)
  ```

### 5.3 用户随机量 $z_i$ 改为有界采样 — 【缺陷 3】

- **位置**：`SecretKey()` 中 `z`
- **原因**：原式 `random.randrange(0, q)` 使 $z_i$ 均匀分布在 $\mathbb{Z}_q^V$，$y_{\tau,i}$ 随之巨大。
- **修改**：`z = np.array(gauss_int(V), dtype=object)`。
- **依据**：论文 §V-C "AA_τ picks $(z_{1,i},\dots,z_{V,i})$ uniformly at random from $(\mathbb{Z}_q)^V$"
  ——该表述正是任务 2 指出的"采样范围描述不足"，实际必须取有界分布。

### 5.4 `SK[attr]` 改用 `SamplePre` — 【缺陷 5】

- **位置**：`SecretKey()` 末行，对应原 `AA.py:57`
- **修改**：
  ```diff
  - self._SK[attr] = gen_multiple_polynomials(m)
  + # y_{tau,A_tau} <- RSamplePre(A_tau, T_{A_tau}, Delta_tau, sigma, sigma_s)
  + self._SK[attr] = SamplePre(self.A, self._T, delta)
  ```

### 5.5 `Decrypt` 返回单个机构的解密份额 $\Theta_\tau$ — 【缺陷 8】

- **位置**：`Decrypt()`
- **原因**：论文 §V-E 的解密是 $\phi'=c_0-\sum_{\tau\in[N]}L_\tau\Theta_\tau$，需要**全部 $N$ 个
  授权机构**的份额。原代码只有一个 `AA` 实例、且用 `Lagrange(1) * L` 乘单个份额，
  数学上等价于假设所有 $\Theta_\tau$ 相同，无法成立。
- **修改**：`Decrypt` 只负责计算本机构的
  $\Theta_\tau=\Theta_{\tau,0}+\sum_i[\Theta_{\tau,i,1}+\Theta_{\tau,i,2}]$
  并返回；跨机构的拉格朗日合并移到 `main.py`。同时把重构向量明确写为 $g=e_1$（与
  `User.Encrypt` 构造的 $F$ 对应），并删去原来 `phi -= Lagrange(1) * L` 与阈值判定。
- **依据**：论文 §V-E 步骤 1)、2) 与最后一步。

---

## 6. `User.py`

### 6.1 `AccessControl` 修正正/负极性 — 【缺陷 7】

- **位置**：`AccessControl()`，对应原 `User.py:13-23`
- **原因**：论文中 $W'=W^+\cup W^-$，$W^+$ 为策略中要求"具备"的属性、$W^-$ 为要求"不具备"的属性；
  而 `KeyGen` 中 $n_{\tau,i}$ 在 $x_i\in S$ 时用 $b^+$、否则用 $b^-$。
  原实现令 $W^+$ 与 $W^-$ **都**是 $X$ 的子集，即 $W^-\subseteq S$，于是对每个负极性属性，
  密文分量用的是 $b^-$、而密钥用的是 $b^+$，$\Theta_{\tau,i,1}$ 里多出
  $(b^--b^+)\cdot y_{\tau,i}\cdot d$ 量级的项，解密结果完全是随机值（实测 257/512）。
- **修改**：
  ```diff
  - self.W = np.array([X[i] & mask >> i for i in range(attr)])
  - mask = random.getrandbits(attr)
  - self.W_plus = np.array([self.W[i] & mask >> i for i in range(attr)])
  - self.W_minus = np.array([self.W[i] & (1 ^ self.W_plus[i]) for i in range(attr)])
  + mask = random.getrandbits(attr)
  + self.W_plus = np.array([X[i] & mask >> i for i in range(attr)])
  + mask = random.getrandbits(attr)
  + self.W_minus = np.array([(1 ^ X[i]) & mask >> i for i in range(attr)])
  + self.W = self.W_plus | self.W_minus
  ```
  即 $W^+\subseteq X$、$W^-\subseteq\Omega\setminus X$，策略由用户的属性集满足。

### 6.2 构造满足重构条件的 LSSS 矩阵 $F$ — 【缺陷 6】

- **位置**：`Encrypt()` 开头（原无此逻辑）
- **原因**：论文要求取 $g_i\in\{0,1\}$ 使 $\sum_i g_iF_i=(1,0,\dots,0)$。原代码 $F$ 与 $g$ 都是
  随机的（`g = random.getrandbits(attr)`），$\sum_i g_ic_{\tau,i,2}$ 中的
  $u\cdot d$ 项无法被重构，且会引入 $\sum_j r_j(\sum_i g_iF_{i,j})$ 这种 $q$ 量级的杂项。
- **修改**：令 $F$ 的第 0 行为 $(1,0,\dots,0)$、其余行为随机 $R_q^m$；解密侧取 $g=e_1$，
  于是 $\sum_i g_iF_i=F_0=(1,0,\dots,0)$ 精确成立。`main.py` 中已加不变量校验。
- **依据**：论文 §V-D、§V-E "take $\{g_i\in\{0,1\}\}$ such that $\sum_i g_iF_i=(1,0,\dots,0)$"。
- **说明**：本仿真采用"策略中全部属性均需满足"的访问结构，其 1 列共享矩阵的每一行都能独立
  张成共享秘密，因此重构向量取单行即可；这也使 $\sum_{j\ge2}F_{i,j}r_j$ 项在重构中不出现
  （$F$ 的其余行仍作为随机份额随密文一同传输，保持论文 $ct$ 的完整形式）。

### 6.3 噪声改为有界采样 + 支持多授权机构 — 【缺陷 3 / 8】

- **位置**：`Encrypt()`
- **原因**：(a) 所有 $e$ 原为 `gen_polynomial()`（均匀 $[0,q)$），噪声必然溢出；
  (b) 原函数只接受单个机构的 $(A,b^+,b^-)$，无法生成论文中面向 $N$ 个机构的密文。
- **修改**：
  - `e`、$e_{\tau,A}$、$e_{\tau,i,1}$、$e_{\tau,i,2}$ 全部改用 `gauss_polynomial()` /
    `gauss_multiple_polynomials(m)`；
  - 签名改为 `Encrypt(phi, AAs)`，返回 `(c_0, ciphers)`，`ciphers[tau]` 为该机构的密文分量；
  - `c_0` 中的 $\lfloor q/2\rfloor\phi$ 显式转成 object dtype，修掉 `OverflowError`；
  - 各分量键名（`c_A`、`c_{i}_2`、`c_{i}_1`、`c_plus_{i}_1`、`c_minus_{i}_1`）保持原样。
- **依据**：论文 §V-D。

---

## 7. `main.py`

- **位置**：整文件（原 34 行）
- **原因**：(a) 只创建 1 个 `AA`，与 $N=3$ 不符；(b) 缺少论文 §V-E 的
  $\phi'=c_0-\sum_\tau L_\tau\Theta_\tau$ 重构；(c) 缺少截图所示的正确性诊断输出；
  (d) 需要按任务 4 输出中英文双语。
- **修改**：
  1. `aas = [AA() for _ in range(N)]`，`AASetup`/`SecretKey` 对全部机构执行，`E[tau]` 即 $E(\tau+1)$；
  2. 三个机构共用同一属性全集（`aa.X = X`）；
  3. `Setup` → `AASetup` → `KeyGen` → `Encryption` → `Decryption` 的计时保持不变；
  4. 解密按 $\phi'=c_0-\sum_{\tau}L_\tau\Theta_\tau$ 合并，再用论文阈值
     $|\phi'_i|<q/4$ 判定比特；
  5. 输出 `Guaranteed coefficient error bound` / `Recovered bits` / `Observed error max` /
     `Error below q/4` / `Plaintext recovered` 五项诊断；
  6. **误差按模 $q$ 的圆周距离度量**（见下）；
  7. 所有英文标签改为中英文双语（任务 4）。
- **关键细节——误差度量**：$q$ 为奇数，$\lfloor q/2\rfloor=(q-1)/2$，因此
  $\phi'_i=(\lfloor q/2\rfloor\phi_i+\text{noise})\bmod q$ 的中心化代表在
  $\text{noise}=+1$ 时会从 $+(q-1)/2$ 跳到 $-(q-1)/2$，直接相减会报出 $\approx q$ 的"误差"。
  故误差取
  $$\mathrm{err}_i=\Big|\,\mathrm{center}\big((\phi'_i-\lfloor q/2\rfloor\phi_i)\bmod q\big)\Big|$$
  这也是论文用 $|\phi'_i|<q/4$（只比较绝对值）而非符号判定的原因。

---

## 8. 验证结果

修改后 `python main.py` 可完整运行并正确解密：

```
Sampling profile（采样方式）: bounded（有界）
Parameters（参数）: N=3, f=512, attr=10, b=17, m=42
Setup（系统初始化） - 0.0 (s)
AASetup（授权机构初始化） - 3.73 (s)
KeyGen（用户密钥生成） - 25.91 (s)
Guaranteed coefficient error bound（保证的系数误差上界）: 100118036622
Encryption（加密） - 94.63 (s)
Decryption（解密） - 21.72 (s)
Recovered bits（正确恢复的比特数）: 512/512
Observed error max（实测最大误差）: 279109
Error below q/4（误差小于 q/4）: True（是）
Plaintext recovered（明文恢复成功）: True（是）
```

（该输出为最终一次完整运行的结果；`Setup` 计时因四舍五入显示为 `0.0`，其真实耗时 < 0.05 s。）

除端到端运行外，还用一个缩小规模的临时校验脚本（`attr=3, V=2`，便于快速迭代）逐项验证了下列不变量：

| 不变量 | 结果 |
|--------|------|
| $b^k > q$ 且中心化数字上界 $\ge q/2$ | ✔ |
| $A_\tau\,y_{\tau,A_\tau}=\Delta_\tau$（3 次随机试验） | ✔ 精确相等 |
| $\sum_i g_iF_i=(1,0,\dots,0)$ | ✔ |
| $W^+\subseteq X$、$W^-\subseteq\Omega\setminus X$ | ✔ |
| 每个属性的 $n_{\tau,i}$ 与 $c_{\tau,i,1}$ 使用同一个 $b$ | ✔ 全部 OK |
| $\sum_\tau L_\tau\equiv1\pmod q$ | ✔ |
| 解密 512/512 比特、误差 $\ll q/4$ | ✔ |

> 说明：`AASetup`/`KeyGen`/`Encryption`/`Decryption` 的耗时与截图不完全一致，属于机器性能差异；
> 输出的**格式与行序**与截图一致（任务 4 的双语改动除外）。
