# All channel operations are simulated in this process.
import argparse
import random
import sys
import time

import numpy as np

import config as cfg
from AA import AA
from KGC import Setup
from User import User
from demo_input import choose_input, load_json_input
from message import decode_text
from util import centered, poly_add


def timeit(code, title):
    start = time.perf_counter()
    result = code()
    print(title, '-', round(time.perf_counter() - start, 2), '(s)', flush=True)
    return result


def main(argv=None):
    # Windows redirected streams may otherwise use a legacy Chinese code page.
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='CP-ABE 自定义内容与属性加解密演示')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--input', metavar='JSON', help='直接读取 JSON 输入文件，跳过启动菜单')
    mode.add_argument('--demo', action='store_true', help='直接运行原有随机二进制演示')
    options = parser.parse_args(argv)
    try:
        data = None if options.demo else (load_json_input(options.input)
                                          if options.input else choose_input())
    except (ValueError, OSError, EOFError) as error:
        parser.error(f'Input error / 输入错误: {error}')
    print('Sampling profile / 采样方案: bounded / 有界采样', flush=True)
    print(
        f'Parameters / 参数: N={cfg.N}, f={cfg.f}, attr={cfg.attr}, b={cfg.b}, m={cfg.m}',
        flush=True)
    authorities = [AA(theta) for theta in range(1, cfg.N + 1)]
    user = User()
    requested = data['attributes'] if data is not None else None
    attributes = np.array([
        aa.S(None if requested is None else requested[i])
        for i, aa in enumerate(authorities)
    ],
                          dtype=object)
    user.AccessControl(attributes,
                       policy=data['policy'] if data is not None else None)
    # Check user-selected policies before spending time on trapdoors and keys.
    for i, aa in enumerate(authorities):
        try:
            aa.reconstruction({'W': user.W[i], 'F': user.F[i]})
        except PermissionError as error:
            parser.error(f'AA{aa.theta} Access denied / 属性不满足访问策略: {error}')
    if data is not None:
        print(f'Input bytes / 输入字节数: {data["byte_length"]}/{cfg.f // 8}')
        for i, aa in enumerate(authorities):
            print(f'AA{aa.theta} attributes / 用户属性: {attributes[i].tolist()}')
            print(f'AA{aa.theta} policy / 访问策略: {user.W[i].tolist()}')
    shares = timeit(Setup, 'Setup / 全局初始化')
    timeit(lambda: [aa.AASetup() for aa in authorities], 'AASetup / 属性机构初始化')
    timeit(
        lambda: [aa.SecretKey(shares[i]) for i, aa in enumerate(authorities)],
        'KeyGen / 密钥生成')
    bound = user.noise_bound(authorities)
    print(f'Guaranteed coefficient error bound / 系数误差保证上界: {bound}',
          flush=True)
    phi = data['phi'] if data is not None else np.array(
        [random.getrandbits(1) for _ in range(cfg.f)], dtype=object)
    cipher = timeit(
        lambda: user.Encrypt(phi, [aa.A for aa in authorities], [
            aa.b_plus for aa in authorities
        ], [aa.b_minus for aa in authorities]), 'Encryption / 加密')
    recovered = timeit(lambda: user.Decrypt(cipher, authorities),
                       'Decryption / 解密')
    errors = int(np.count_nonzero(phi != recovered))
    # Only the local demo knows phi; decryption itself never uses the plaintext.
    noise = centered(poly_add(user.last_residual, -(cfg.q // 2) * phi))
    observed_error = max(abs(int(value)) for value in noise)
    below_threshold = 4 * observed_error < cfg.q
    print(f'Recovered bits / 已恢复位数: {cfg.f - errors}/{cfg.f}')
    print(f'Observed error max / 观测误差最大值: {observed_error}')
    print(f'Error below q/4 / 误差低于 q/4: {below_threshold}')
    print(f'Plaintext recovered / 明文已恢复: {errors == 0}')
    if errors or observed_error > bound or not below_threshold:
        raise RuntimeError('Round-trip verification failed / 加解密往返验证失败')
    if data is not None:
        text = decode_text(recovered, data['byte_length'])
        if text != data['text']:
            raise RuntimeError('Text recovery failed / 文本恢复与输入不一致')
        print(f'Recovered text / 恢复文本: {text}')


if __name__ == '__main__':
    main()
