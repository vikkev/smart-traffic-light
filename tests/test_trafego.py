import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import G_MAX, G_MIN, TEMPO_AMARELO, Y_MAX
from src.trafego import ControladorSemaforo, GerenciadorTrafego


def test_calculate_demand_and_status():
    manager = GerenciadorTrafego()
    counts = {"person": 2, "car": 3, "motorcycle": 1}
    score = manager.calcular_demanda(counts)
    assert abs(score - 5.0) < 1e-6
    status, _ = manager.obter_status(score)
    assert status == "NORMAL"

    counts = {"person": 5, "car": 5, "bus": 1}
    score = manager.calcular_demanda(counts)
    status, _ = manager.obter_status(score)
    assert status in ("BUSY", "PRIORIDADE")

    counts = {"truck": 5, "bus": 3}
    score = manager.calcular_demanda(counts)
    status, _ = manager.obter_status(score)
    assert status == "PRIORIDADE"


def test_demanda_alta_aumenta_verde_a():
    controlador = ControladorSemaforo()
    baixo = controlador.calcular_tempos(2.0)
    alto = controlador.calcular_tempos(30.0)
    assert alto["verde_a"] > baixo["verde_a"]


def test_clamps_de_verde_e_Y():
    controlador = ControladorSemaforo()
    for demanda in (0.0, 8.0, 30.0, 1000.0):
        tempos = controlador.calcular_tempos(demanda)
        assert G_MIN <= tempos["verde_a"] <= G_MAX
        assert G_MIN <= tempos["verde_b"] <= G_MAX
        assert tempos["Y"] <= Y_MAX

    extremo = controlador.calcular_tempos(1000.0)
    assert extremo["sobrecarregado"] is True
    assert extremo["ciclo"] <= (G_MAX + G_MAX + 2 * TEMPO_AMARELO) + 1e-6
    assert extremo["ciclo_webster"] < 400


def test_recalculo_nao_altera_verde_em_andamento():
    controlador = ControladorSemaforo()
    controlador.iniciar(2.0)
    verde_atual = controlador.verde_a
    controlador.propor(30.0)
    assert controlador.verde_a == verde_atual
    assert controlador.proximo_ciclo["verde_a"] > verde_atual

    controlador.tick(controlador.verde_a + 1e-6)
    controlador.tick(TEMPO_AMARELO + 1e-6)
    controlador.tick(controlador.verde_b + 1e-6)
    eventos = controlador.tick(TEMPO_AMARELO + 1e-6)
    assert controlador.fase == "VERDE_A"
    assert controlador.verde_a == pytest.approx(controlador.calcular_tempos(30.0)["verde_a"])
    assert any(evento["evento"] == "ciclo" for evento in eventos)


def test_demanda_alta_nao_iguala_os_verdes():
    # Antes, demanda >= 14 fazia os dois verdes baterem em G_MAX.
    controlador = ControladorSemaforo()
    for demanda in (14.0, 20.0, 30.0, 1000.0):
        tempos = controlador.calcular_tempos(demanda)
        assert tempos["verde_a"] > tempos["verde_b"] + 5


def test_eixos_medidos_repartem_pelo_fluxo():
    controlador = ControladorSemaforo()
    carregado = controlador.calcular_tempos(16.0, taxa_b=2.0)
    assert carregado["verde_a"] > carregado["verde_b"]
    equilibrado = controlador.calcular_tempos(4.0, taxa_b=4.0)
    assert equilibrado["verde_a"] == pytest.approx(equilibrado["verde_b"], abs=0.05)


def test_taxa_nao_trata_contagem_como_volume():
    gestor = GerenciadorTrafego()
    controlador = ControladorSemaforo()
    curta = gestor.taxa_por_minuto(14.0, 60.0)
    longa = gestor.taxa_por_minuto(14.0, 180.0)
    assert curta == pytest.approx(14.0)
    assert longa == pytest.approx(14.0 / 3.0)
    assert controlador.calcular_tempos(curta)["verde_a"] > controlador.calcular_tempos(longa)["verde_a"]
    assert gestor.taxa_por_minuto(10.0, 0.0) == 0.0


def test_ciclo_completo_de_fases():
    controlador = ControladorSemaforo()
    controlador.iniciar(5.0)
    assert controlador.fase == "VERDE_A"
    controlador.tick(controlador.verde_a + 1e-6)
    assert controlador.fase == "AMARELO_A"
    controlador.tick(TEMPO_AMARELO + 1e-6)
    assert controlador.fase == "VERDE_B"
    controlador.tick(controlador.verde_b + 1e-6)
    assert controlador.fase == "AMARELO_B"
    controlador.tick(TEMPO_AMARELO + 1e-6)
    assert controlador.fase == "VERDE_A"
