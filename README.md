# README

Paper link:
*https://scholar.google.com/citations?view_op=view_citation&hl=en&user=bToAUHMAAAAJ&sortby=pubdate&citation_for_view=bToAUHMAAAAJ:9LpHyFPp1DQC*

## An Efficient and Secure Post-Quantum Multi-Authority Ciphertext-Policy Attribute-Based Encryption Method Using Lattice

This project contains the implemented codebase for the methods and procedures described in above paper.

---

## How to Run

### 0. Branch

All three branches (`main`, `dev-ds`, `dev-codex`) currently point at the same commit, so the
steps below are identical on `main`:

```bash
git checkout main          # the branch this section documents
python main.py
```

> **Note.** The correctness fixes described in `change.md` live in the working tree of the
> branch that was checked out while they were made. To make `main` itself runnable, commit and
> fast-forward it:
> ```bash
> git add -A && git commit -m "make the scheme run correctly per the paper"
> git branch -f main HEAD     # main is an ancestor, so this is a plain fast-forward
> ```
> The same steps apply on any branch, since the source files are branch-independent.

### 1. Environment requirements

| Item | Requirement | Notes |
|------|-------------|-------|
| Python | 3.8+ (tested on 3.12.2) | `pow(x, -1, q)` needs 3.8+; `random.choices` needs 3.6+ |
| numpy | any recent version (tested on 2.5.4) | the **only** third-party dependency |
| OS | any (tested on Windows 10 / Git Bash) | pure Python, no compiler needed |

> `q ≈ 1.46e48` exceeds 64 bits, so every coefficient is carried as a **Python int**
> (`numpy` `dtype=object`). This is deliberate — see `change.md` §2.2.

### 2. Install

```bash
# from the project root
python -m venv venv

# Windows (cmd / PowerShell)
venv\Scripts\activate
# Windows (Git Bash)
source venv/Scripts/activate
# macOS / Linux
source venv/bin/activate

pip install numpy
```

No build/compile step: the project is plain Python, so there is nothing to build.

### 3. Run

```bash
python main.py
```

Expected output (timings vary with the machine):

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

**A full run takes roughly 2.5 minutes** on a typical laptop (the ring multiplications over
512-coefficient big-integer polynomials dominate). `Recovered bits` must be `512/512` and
`Plaintext recovered` must be `True`; anything else means the parameters no longer satisfy the
correctness condition (see §5).

The last five lines are the correctness diagnostics:

| Line | Meaning |
|------|---------|
| `Guaranteed coefficient error bound` | analytic worst-case bound on the decryption error, from `util.guaranteed_error_bound()` |
| `Recovered bits` | how many of the `f` message bits came back correctly |
| `Observed error max` | largest actual `\|φ'ᵢ − ⌊q/2⌋φᵢ\|` measured mod `q` |
| `Error below q/4` | the correctness condition of the paper, `‖ε‖∞ < q/4` |
| `Plaintext recovered` | whether the recovered bit string equals the plaintext |

### 4. Set parameters in config.py

* `(N)` number of authorities — currently `3`
* `(f)` degree of polynomial - power of 2 — currently `512`
* `(q)` large prime number — currently `≈ 1.46e48`
* `(b)` base of the gadget vector, `k = ⌊log_b(q)+1⌋`, `m = k+2` — currently `17` / `40` / `42`
* `(attr)` number of attributes — currently `10`
* `(V)` parameter for linear combination of z — currently `10`
* `(SIGMA)` std-dev of the bounded discrete Gaussian — currently `1.0`
* `(BOUND)` hard bound on every sampled coefficient — currently `2`

> `m` is **derived**, not free: `m = ⌊log_b(q)⌋ + 3`. Changing `b` or `q` changes `m`.
> `m` must stay `> f`-independent but the gadget needs `b^k > q`.

### 5. Common issues

**`OverflowError: int too big to convert`**
The coefficients are being stored in an int64 array. Every array that holds values mod `q`
must be created with `dtype=object`. Check `config.py` (`u`), `util.gen_polynomial`,
`algo.RTrapGen`, `AA.SecretKey` and `User.Encrypt`.

**`ModuleNotFoundError: No module named 'numpy'`**
The virtual environment is not active, or `numpy` was installed into another interpreter.
Run `venv/Scripts/python.exe -m pip install numpy` and invoke the script with
`venv/Scripts/python.exe main.py`.

**`python` is not recognised (Windows)**
Use the interpreter inside the venv explicitly:
`venv\Scripts\python.exe main.py`. In Git Bash: `./venv/Scripts/python.exe main.py`.

**Chinese output shows as `��` (Windows console)**
The console code page is not UTF-8. Run `chcp 65001` first, or redirect the output:
`python main.py > out.txt`.

**`Recovered bits` is far below `512/512`**
The correctness inequality `q > 4·[β + Λ(mfβY_A + hfβY_i + hβ)]` is violated. In order of
likelihood:
1. `BOUND` was raised without raising `q` — re-check `util.guaranteed_error_bound()` against `q/4`;
2. `q` was lowered so that `b^k > q` no longer holds, and `algo._digits` raises
   `AssertionError: gadget is too short to represent the target`;
3. `AccessControl` no longer guarantees `W⁺ ⊆ X` and `W⁻ ⊆ Ω∖X`, so the sign of `n_{τ,i}` and of
   the ciphertext component disagree — see `change.md` §6.1;
4. `SecretKey` stopped accumulating `Δ_τ` (`change.md` §5.2) or `SK[attr]` is not produced by
   `SamplePre` (`change.md` §5.4).

**The run is very slow / `KeyGen` or `Encryption` seems hung**
Expected: `Encryption` performs ~2500 ring multiplications of 512-coefficient big integers and
takes ~1.5 minutes. Reduce `attr`, `V` or `f` in `config.py` for a quicker smoke test.

**Decryption appears to fail only for some attributes**
Check the polarity of the access structure: for `xᵢ ∈ W'`, the ciphertext component `c_{τ,i,1}`
and the key component `n_{τ,i}` must use the **same** `b` (`b⁺` iff `xᵢ ∈ S`). This is the
invariant verified in `change.md` §8.

---

## Algorithms

1. AA.py - Authority
    * AASetup — `RTrapGen` + the attribute key material `b⁺/b⁻`
    * SecretKey — accumulates `Δ_τ = E(τ) − Σᵢ n_{τ,i}` and calls `SamplePre`
    * Decrypt — returns this authority's share `Θ_τ` (the `Σ_τ L_τ Θ_τ` reconstruction happens in `main.py`)

2. KGC.py - Key Generation Center
    * Setup — `E(x) = u + Σ_{I≥1} G_I x^I` evaluated at `x = 1..N`

3. User.py
    * AccessControl — builds the policy `W' = W⁺ ∪ W⁻` satisfied by the user's attribute set
    * Encryption — builds the LSSS matrix `F` and the per-authority ciphertext

4. algo.py
    * RTrapGen — ring trapdoor generation
    * SamplePre — ring Gaussian preimage sampling (`RSamplePre`), base-`b` gadget decomposition

5. util.py
    * bounded discrete Gaussian samplers, ring arithmetic mod `x^f + 1`, Lagrange coefficients
    * `guaranteed_error_bound` — the analytic decryption error bound

See `change.md` for every modification made to the original code, and
`采样与噪声方案分析.md` for why the sampling ranges and noise distribution had to be added.
