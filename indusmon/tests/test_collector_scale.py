from __future__ import annotations

import pytest

from indusmon.collector import decode_registers


def test_uint16_scale_offset():
    assert decode_registers([16500], "uint16", 0.01, 0.0) == pytest.approx(165.0)
    assert decode_registers([100], "uint16", 1.0, 5.0) == pytest.approx(105.0)


def test_int16_negative():
    # -1 stored as 0xFFFF
    assert decode_registers([65535], "int16", 0.01, 0.0) == pytest.approx(-0.01)


def test_float32():
    import struct

    hi, lo = struct.unpack(">HH", struct.pack(">f", 12.5))
    assert decode_registers([hi, lo], "float32", 1.0, 0.0) == pytest.approx(12.5)
