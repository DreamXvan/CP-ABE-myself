"""Read and validate user-controlled data for the single-process demonstration."""
import json
import random
import re
from pathlib import Path

import numpy as np

import config as cfg
from message import encode_text


def _matrix(value, choices, name):
    if value is None:
        return None
    matrix = np.asarray(value, dtype=object)
    if matrix.shape != (cfg.N, cfg.attr):
        raise ValueError(f'{name} 必须有 {cfg.N} 行，每行 {cfg.attr} 个整数')
    if any(isinstance(item, bool) or not isinstance(item, (int, np.integer)) or item not in choices
           for item in matrix.flat):
        raise ValueError(f'{name} 只能包含整数 {choices}')
    return matrix.copy()


def validate_input(data):
    if not isinstance(data, dict) or not isinstance(data.get('text'), str):
        raise ValueError('输入必须是 JSON 对象，text 字段必须是字符串')
    unknown = set(data) - {'text', 'attributes', 'policy'}
    if unknown:
        raise ValueError(f'未知输入字段: {", ".join(sorted(unknown))}')
    phi, byte_length = encode_text(data['text'])
    return {
        'text': data['text'], 'phi': phi, 'byte_length': byte_length,
        'attributes': _matrix(data.get('attributes'), (0, 1), 'attributes / 用户属性'),
        'policy': _matrix(data.get('policy'), (-1, 0, 1), 'policy / 访问策略'),
    }


def load_json_input(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as error:
        raise ValueError(f'JSON 格式错误，第 {error.lineno} 行，第 {error.colno} 列') from error
    return validate_input(data)


def _read_row(prompt, choices, default):
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default()
        try:
            row = [int(item) for item in re.split(r'[,，\s]+', raw)]
            if len(row) != cfg.attr or any(item not in choices for item in row):
                raise ValueError(f'请输入 {cfg.attr} 个整数，取值为 {choices}')
            return row
        except ValueError as error:
            print(f'Invalid input / 输入无效: {error}')


def interactive_input():
    print(f'UTF-8 text / 加密文本：最多 {cfg.f // 8} 字节；中文和 emoji 通常占多个字节。')
    while True:
        text = input('Text / 请输入加密内容（可为空）: ')
        try:
            encode_text(text)
            break
        except ValueError as error:
            print(f'Invalid text / 文本超出容量: {error}')
    print(f'每个机构填写 {cfg.attr} 个值，使用逗号或空格分隔。')
    print('用户属性：1=持有，0=不持有；策略：1=必须持有，-1=必须不持有，0=通配。')
    attributes, policy = [], []
    for theta in range(1, cfg.N + 1):
        row = _read_row(
            f'AA{theta} attributes / 用户属性（回车随机）: ', (0, 1),
            lambda: [random.getrandbits(1) for _ in range(cfg.attr)],
        )
        attributes.append(row)
        policy.append(_read_row(
            f'AA{theta} policy / 访问策略（回车生成匹配策略）: ', (-1, 0, 1),
            lambda: [(1 if bit else -1) if random.getrandbits(1) else 0 for bit in row],
        ))
    return validate_input({'text': text, 'attributes': attributes, 'policy': policy})


def choose_input():
    print('Input mode / 请选择数据输入方式:')
    print('1. JSON 文件（加密内容、用户属性和访问策略）')
    print('2. 交互填写')
    while True:
        choice = input('请选择 1 或 2 [2]: ').strip() or '2'
        if choice == '1':
            path = input('JSON path / 输入文件路径: ').strip().strip('"')
            return load_json_input(path)
        if choice == '2':
            return interactive_input()
        print('Invalid choice / 请输入 1 或 2')
