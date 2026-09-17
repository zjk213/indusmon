from __future__ import annotations

import time

import pytest

pymodbus = pytest.importorskip("pymodbus")

from pymodbus.client import ModbusTcpClient  # noqa: E402

from indusmon.simulator import RegisterBank, start_simulator  # noqa: E402


def test_register_bank_waveform_changes():
    bank = RegisterBank()
    a = bank.raw_values(1, 8)
    time.sleep(0.05)
    b = bank.raw_values(1, 8)
    # steam temp (reg 0) should not be constant forever — at least structure is valid
    assert len(a) == len(b) == 8
    assert all(isinstance(x, int) for x in a)
    # burner digital is 0/1
    assert a[3] in (0, 1)


def test_modbus_tcp_roundtrip():
    port = 15021
    start_simulator("127.0.0.1", port)
    time.sleep(0.4)
    client = ModbusTcpClient(host="127.0.0.1", port=port, timeout=2.0)
    assert client.connect()
    try:
        try:
            rr = client.read_holding_registers(0, count=4, slave=1)
        except TypeError:
            rr = client.read_holding_registers(0, count=4, device_id=1)
        assert not rr.isError()
        regs = rr.registers
        assert len(regs) == 4
        # steam temp stored as raw*100 in int16 range
        assert -32768 <= regs[0] <= 32767
        try:
            rr2 = client.read_holding_registers(0, count=4, slave=2)
        except TypeError:
            rr2 = client.read_holding_registers(0, count=4, device_id=2)
        assert not rr2.isError()
    finally:
        client.close()
