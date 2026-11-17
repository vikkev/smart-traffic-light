import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulacao.controladores import (
    ControladorAtuado,
    ControladorFixo,
    Leitura,
    estado_links,
    maximos_webster,
)


def test_estado_das_fases():
    eixos = {0: "A", 1: "A", 2: "B", 3: "B"}
    assert estado_links(eixos, "VERDE_A") == "GGrr"
    assert estado_links(eixos, "AMARELO_A") == "yyrr"
    assert estado_links(eixos, "VERDE_B") == "rrGG"
    assert estado_links(eixos, "AMARELO_B") == "rryy"
    assert estado_links(eixos, "ALLRED_AB") == "rrrr"
    assert estado_links(eixos, "ALLRED_BA") == "rrrr"


def test_webster_no_pico_nao_crava_os_dois_em_60():
    verde_a, verde_b = maximos_webster(650 / 60.0, 650 / 60.0)
    assert verde_a == pytest.approx(verde_b, abs=0.5)
    assert 15 < verde_a < 45


def test_eixo_carregado_recebe_mais_verde_maximo():
    verde_a, verde_b = maximos_webster(900 / 60.0, 90 / 60.0)
    assert verde_a > verde_b + 10


def test_fixo_ignora_detector_e_cumpre_os_tempos():
    controle = ControladorFixo(verde_a=5, verde_b=4, amarelo=2, allred=1)
    vazio = Leitura(verde_vazio=True, espera_vermelho=True)
    assert [controle.passo(1.0, vazio) for _ in range(5)] == ["VERDE_A"] * 5
    assert controle.passo(1.0, vazio) == "AMARELO_A"
    assert controle.passo(1.0, vazio) == "AMARELO_A"
    assert controle.passo(1.0, vazio) == "ALLRED_AB"
    assert controle.passo(1.0, vazio) == "VERDE_B"


def test_verde_minimo_segura_com_o_outro_lado_esperando():
    controle = ControladorAtuado(verde_max_a=40, verde_max_b=40, verde_min=8, gap_out=2)
    vazio = Leitura(verde_vazio=True, espera_vermelho=True)
    for _ in range(8):
        assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "AMARELO_A"


def test_gap_out_espera_o_buraco_inteiro():
    controle = ControladorAtuado(verde_max_a=40, verde_max_b=40, verde_min=5, gap_out=3)
    cheio = Leitura(chamada_verde=True, verde_vazio=False, espera_vermelho=True)
    vazio = Leitura(verde_vazio=True, espera_vermelho=True)
    for _ in range(5):
        assert controle.passo(1.0, cheio) == "VERDE_A"
    for _ in range(3):
        assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "AMARELO_A"


def test_chamada_zera_o_gap():
    controle = ControladorAtuado(verde_max_a=40, verde_max_b=40, verde_min=4, gap_out=3)
    cheio = Leitura(chamada_verde=True, verde_vazio=False, espera_vermelho=True)
    vazio = Leitura(verde_vazio=True, espera_vermelho=True)
    for _ in range(4):
        controle.passo(1.0, cheio)
    assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, cheio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "AMARELO_A"


def test_verde_maximo_mesmo_com_chamada():
    controle = ControladorAtuado(verde_max_a=10, verde_max_b=10, verde_min=4, gap_out=5)
    cheio = Leitura(chamada_verde=True, verde_vazio=False, espera_vermelho=True)
    for _ in range(10):
        assert controle.passo(1.0, cheio) == "VERDE_A"
    assert controle.passo(1.0, cheio) == "AMARELO_A"


def test_troca_cedo_quando_o_verde_esta_vazio():
    controle = ControladorAtuado(verde_max_a=50, verde_max_b=50, verde_min=8, gap_out=2)
    vazio = Leitura(verde_vazio=True, espera_vermelho=True)
    for _ in range(8):
        assert controle.passo(1.0, vazio) == "VERDE_A"
    assert controle.passo(1.0, vazio) == "AMARELO_A"
    assert controle.ultimo_verde == pytest.approx(8)


def test_sem_espera_no_vermelho_o_verde_fica():
    controle = ControladorAtuado(verde_max_a=6, verde_max_b=6, verde_min=4, gap_out=2)
    ocioso = Leitura(verde_vazio=True, espera_vermelho=False)
    for _ in range(20):
        assert controle.passo(1.0, ocioso) == "VERDE_A"


def test_nao_morre_de_fome():
    controle = ControladorAtuado(
        verde_max_a=12, verde_max_b=10, verde_min=8, gap_out=2, amarelo=3, allred=1
    )
    cheio = Leitura(chamada_verde=True, verde_vazio=False, espera_vermelho=True)
    verdes_a = 0
    fase = "VERDE_A"
    for _ in range(30):
        fase = controle.passo(1.0, cheio)
        if fase == "VERDE_A":
            verdes_a += 1
        else:
            break
    assert verdes_a == 12
    assert fase == "AMARELO_A"

    for _ in range(10):
        fase = controle.passo(1.0, cheio)
        if fase == "VERDE_B":
            break
    assert fase == "VERDE_B"

    verdes_b = 1  # o passo que entrou em VERDE_B já conta
    for _ in range(40):
        fase = controle.passo(1.0, Leitura(verde_vazio=True, espera_vermelho=True))
        if fase == "VERDE_B":
            verdes_b += 1
        elif fase == "VERDE_A":
            break
    assert verdes_b >= 8
    assert fase == "VERDE_A"
