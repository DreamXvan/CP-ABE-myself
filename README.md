# 论文算法的 Python 正确性复现

本项目对应论文 *An Efficient and Secure Post-Quantum Multi-Authority Ciphertext-Policy Attribute-Based Encryption Method Using Lattice*，论文 PDF 位于项目根目录。

目前可执行完整的 `Setup → AASetup → KeyGen → Encryption → Decryption` 流程，并逐位检查明文恢复结果。所有 `N` 个机构参与同一组 Shamir 份额的重构，机构在一个进程中顺序模拟。

**实现边界：这是带明确补充假设的正确性研究原型。** 论文未完整指定属性密钥、误差和 Gaussian 原像采样所需的条件。本实现采用短线性属性密钥、非零截断离散 Gaussian 误差，以及满足精确原像等式的 gadget 构造；不声称具有 GPV 陪集分布、原论文的 IND-sCPA 安全性或生产安全等级。策略支持正属性、负属性和通配的合取，不支持任意 OR/阈值策略。详见 [算法核对与限制](docs/algorithm-notes.md) 和 [改动记录](change.md)。

## 环境与运行

已在 Windows、Python 3.12.2、NumPy 2.5.4 中验证；运行依赖只有 NumPy，测试使用标准库 `unittest`。不需要编译或额外构建。

### `main` 分支与 `main.py` 入口

运行入口是当前工作区的 `main.py`。本次检查时，工作分支为 `dev-codex`，修复仍是未提交的工作区修改；Git 的 `main` 和 `origin/main` 仍指向旧提交 `e301e18`，其中不包含本文所述修复。仅切换或重新克隆干净的 `main` 分支，不能运行此新版。

以下命令适用于当前已修复的工作区。若要从 Git `main` 分支运行同一方案，需要先将这些修改提交并合入该分支，再使用同样的安装和启动命令。本次未自动提交或合并分支。

### 安装与启动

在项目目录执行：

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

也可使用已安装依赖的 Python：

```powershell
python -m pip install -r requirements.txt
python main.py
python -m unittest discover -s tests -v
```

Linux/macOS 中将虚拟环境解释器路径替换为 `./venv/bin/python`。

### 启动时选择你自己的数据

运行 `python main.py` 后，会出现两个选项：

```text
Input mode / 请选择数据输入方式:
1. JSON 文件（加密内容、用户属性和访问策略）
2. 交互填写
请选择 1 或 2 [2]:
```

输入 `1` 后填写 JSON 路径，例如 `examples/custom_input.json`；输入 `2` 或直接回车，则逐项填写加密文本、各机构的用户属性和访问策略。属性与策略均可使用逗号、中文逗号或空格分隔；属性行留空时随机生成，策略行留空时自动生成与该用户匹配的合取策略。

文件方式可直接修改 [examples/custom_input.json](examples/custom_input.json)。文件结构如下，默认 `N=3`、`attr=10`，两个矩阵均为 3 行、每行 10 个整数：

```json
{
  "text": "你好，CP-ABE！",
  "attributes": [
    [1, 0, 1, 0, 0, 1, 0, 0, 0, 1],
    [0, 1, 0, 1, 0, 0, 1, 0, 0, 0],
    [1, 1, 0, 0, 1, 0, 0, 1, 0, 0]
  ],
  "policy": [
    [1, -1, 0, 0, 0, 0, 0, 0, 0, 0],
    [-1, 1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, -1, 0, 0, 0, 0, 0, 0, 0]
  ]
}
```

- `text`：你要加密的字符串。使用 UTF-8 编码，默认一轮最多 **64 字节**，不是 64 个汉字。超过时提示错误，不会截断；空文本也可以运行。
- `attributes`：第几行对应第几个机构；`1` 表示用户持有该属性，`0` 表示不持有。
- `policy`：每个机构的合取要求；`1` 表示必须持有，`-1` 表示必须不持有，`0` 表示通配。例如第一行 `[1,-1,0,...]` 要求持有第一个属性且不持有第二个属性。

JSON 文件使用 UTF-8 保存；`attributes`、`policy` 可分别省略，省略时自动生成。JSON 中的多行文本使用 `\n` 表示换行。机构数、属性数量和环参数仍在 `config.py` 中设置，修改后输入矩阵尺寸也要对应调整。此版本处理一个文本块，尚未实现长文件分块或跨进程密文/密钥存取。

如果希望跳过菜单，可使用：

```powershell
python main.py --input examples/custom_input.json
```

程序会显示实际使用的属性与策略，验证解密结果后输出 `Recovered text / 恢复文本: 你好，CP-ABE！`。不符合策略的用户会在耗时的 Setup 前被拒绝。文本长度作为本次演示的元数据保留，消息编码不改变底层 CP-ABE 算法，也不提供额外的密文认证。

### 原有随机演示

运行 `python main.py --demo` 可直接执行随机二进制演示，不进入菜单。该模式按参考截图的顺序输出 12 行，中英文标题共用一行，阶段计时保持 `名称 - 时间 (s)` 格式。例如（数值仅为格式示意，实际结果随随机采样变化）：

```text
Sampling profile / 采样方案: bounded / 有界采样
Parameters / 参数: N=3, f=512, attr=10, b=17, m=42
Setup / 全局初始化 - ... (s)
AASetup / 属性机构初始化 - ... (s)
KeyGen / 密钥生成 - ... (s)
Guaranteed coefficient error bound / 系数误差保证上界: ...
Encryption / 加密 - ... (s)
Decryption / 解密 - ... (s)
Recovered bits / 已恢复位数: 512/512
Observed error max / 观测误差最大值: ...
Error below q/4 / 误差低于 q/4: True
Plaintext recovered / 明文已恢复: True
```

原始 `f=512`、161 位模数采用精确 Python 大整数卷积，运行可能需要数分钟。希望先快速检查流程，可临时使用较小环而不修改文件：

```powershell
python -c "import config; config.f=16; config.u=config.u[:16].copy(); from main import main; main(['--demo'])"
```

该命令仅缩小本次进程的多项式维数；不是安全参数配置。回归测试同样使用小环加速，但保留大整数模数。自定义模式在原有指标之外显示输入字节数、各机构的属性与策略以及恢复后的文本。

主程序在加密前检查保证误差界，解密时再次检查。`Observed error max` 来自聚合解密残差减去已知原始明文编码后的实际系数误差，不是恢复位数的估计。只有演示程序使用已知明文进行这项验证，解密算法本身不读取原始明文。成功时应同时满足完整位数恢复、实际误差不超过保证上界以及误差低于 `q/4`；否则程序以异常退出。

`bounded` 是当前实现的采样方案名称，没有额外的方案切换命令。采样条件的可选处理方法、默认参数界及推荐理由见 [方案对比与推荐](docs/algorithm-notes.md#6-采样缺失项的处理方案对比与推荐)。

## 参数与文件

在 `config.py` 中设置参数：

| 参数 | 含义 |
| --- | --- |
| `N` | 机构数量；当前要求全部 `1..N` 机构参与解密 |
| `f = 1 << v` | 商环模多项式 `x^f+1` 的次数 |
| `q` | 奇素数；按论文要求满足 `q % (2*f) == 1`，且机构编号在模 q 下不同 |
| `b, k, m, h` | 一致的 base-b gadget；`h[i]=b**i`、`m=k+2`，`k` 由整数运算计算 |
| `attr` | 每个机构的属性数量；单机构被指定的 literal 数不超过 `m` |
| `V` | 短线性属性密钥映射的输入维数 |
| `sigma, sigma_s, noise_sigma` | 陷门、原像扰动及密文误差的采样参数 |
| `gaussian_tail` | 有限采样支撑倍数，默认 6 |
| `key_coefficient_bound, key_input_bound` | 属性密钥线性映射系数和输入的绝对值界 |

修改采样参数可能使噪声界超过解码阈值；程序会明确拒绝这种解密。不要将误差设为零来获得误导性的成功结果。

| 文件 | 职责 |
| --- | --- |
| `KGC.py` | 一个 Shamir 多项式的 N 个份额 |
| `AA.py` | 各机构的陷门、公私钥、属性密钥和部分解密 |
| `User.py` | 合取策略、LSSS、加密及聚合解密 |
| `algo.py` | RTrapGen 和精确原像原型 RSamplePre |
| `util.py` | 精确商环运算、有限 Gaussian 采样和重构系数 |
| `main.py` | 五阶段演示、计时及明文一致性检查 |
| `demo_input.py` | 启动菜单、JSON/交互输入、内容与矩阵校验 |
| `message.py` | UTF-8 文本与单块二进制消息之间的编码、恢复 |

`User.AccessControl(policy=...)` 接受形状为 `(N, attr)` 的矩阵：`1` 表示必须持有属性，`-1` 表示必须不持有，`0` 表示通配。例如 `[1, -1, 0, 0]` 表示“持有第一个属性，且不持有第二个属性”。未指定 policy 时，演示按用户属性随机选取可满足的合取。

## 常见问题

- `ModuleNotFoundError: numpy`：使用与启动程序相同的解释器运行 `python -m pip install -r requirements.txt`。
- PowerShell 禁止激活脚本：直接使用上面的 `venv\Scripts\python.exe` 命令，无需激活。
- 长时间停留在 KeyGen/Encryption：默认参数使用精确大整数卷积；可先运行小环命令。成功时必须检查 `已恢复位数: 512/512` 与 `明文已恢复: True`，不能只看阶段耗时。
- `PermissionError`：至少一个机构的用户属性不满足正/负合取要求。
- `Noise bound is too large`：当前密钥和噪声参数无法满足确定性正确性界，请检查参数；程序不会继续输出“成功”。
- 重构矩阵或机构数量错误：必须提供可重构的 LSSS，并提供每个机构一次。该构造使用 N-of-N 共享，不能任意丢弃机构。
- `UTF-8 text requires ...; capacity is ...`：文本编码后的字节数超过一轮容量，请缩短文本；不要只按汉字个数计算长度。
- 输入提示矩阵尺寸错误：按当前 `N` 和 `attr` 填写，每个机构一行，属性取 0/1，策略取 -1/0/1。
- 重定向日志或终端显示中文乱码：入口显式按 UTF-8 读取和输出；请使用 UTF-8 终端或日志查看器。PowerShell 可用 `python main.py --demo | Out-File -Encoding utf8 run.log` 保存无需交互的演示日志。


