"""Encode one UTF-8 text block for the binary ring message.

The byte length is demo metadata; it is not authenticated by this prototype.
"""

from numbers import Integral

import numpy as np

import config as cfg


def encode_text(text):
    """Return zero-padded, MSB-first message bits and the original byte length."""
    payload = text.encode('utf-8')
    if len(payload) * 8 > cfg.f:
        raise ValueError(
            f'UTF-8 text requires {len(payload)} bytes ({len(payload) * 8} bits); '
            f'capacity is {cfg.f // 8} bytes ({cfg.f} bits)'
        )
    bits = np.zeros(cfg.f, dtype=object)
    bits[:len(payload) * 8] = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))
    return bits, len(payload)


def decode_text(bits, byte_length):
    """Decode binary coefficients using explicit, unauthenticated length metadata."""
    if (not isinstance(byte_length, Integral) or isinstance(byte_length, bool)
            or not 0 <= byte_length <= cfg.f // 8):
        raise ValueError(f'byte_length must be an integer from 0 to {cfg.f // 8}')
    bits = np.asarray(bits, dtype=object)
    if bits.shape != (cfg.f,):
        raise ValueError(f'message must contain exactly {cfg.f} binary coefficients')
    if any(not isinstance(bit, (Integral, np.bool_)) or bit not in (0, 1)
           for bit in bits):
        raise ValueError('message coefficients must be binary integers (0 or 1)')
    if any(bits[byte_length * 8:]):
        raise ValueError('message padding must be zero after byte_length')
    payload = np.packbits(np.asarray(bits[:byte_length * 8], dtype=np.uint8)).tobytes()
    return payload.decode('utf-8')
