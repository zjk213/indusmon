from __future__ import annotations

import socket

import pytest

from indusmon.simulator import ensure_port_free, start_simulator


def test_ensure_port_free_ok():
    ensure_port_free("127.0.0.1", 15099)


def test_ensure_port_free_busy():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 15098))
    s.listen(1)
    try:
        with pytest.raises(RuntimeError, match="INDUSMON_SIM_PORT"):
            ensure_port_free("127.0.0.1", 15098)
    finally:
        s.close()


def test_start_simulator_raises_on_busy():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 15097))
    s.listen(1)
    try:
        with pytest.raises(RuntimeError, match="INDUSMON_SIM_PORT"):
            start_simulator("127.0.0.1", 15097)
    finally:
        s.close()
