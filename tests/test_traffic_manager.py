import os
import sys
import pytest

# Ensure project root is on sys.path for imports during pytest collection
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import GerenciadorTrafego


def test_calculate_demand_and_status():
    manager = GerenciadorTrafego()
    counts = {"person": 2, "car": 3, "motorcycle": 1}
    score = manager.calcular_demanda(counts)
    # person:2*0.5=1.0, car:3*1=3, motorcycle:1*1=1 => total 5.0
    assert abs(score - 5.0) < 1e-6

    status, _ = manager.obter_status(score)
    assert status == "NORMAL"

    # increase counts to push to BUSY
    counts = {"person": 5, "car": 5, "bus": 1}
    score = manager.calcular_demanda(counts)
    status, _ = manager.obter_status(score)
    assert status in ("BUSY", "PRIORIDADE")

    # very high demand
    counts = {"truck": 5, "bus": 3}
    score = manager.calcular_demanda(counts)
    status, _ = manager.obter_status(score)
    assert status == "PRIORIDADE"
