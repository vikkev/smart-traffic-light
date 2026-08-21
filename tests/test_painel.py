import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.painel import alternar_painel, desenhar_texto_ajustado, formatar_contagem


def test_alternar_painel():
    assert alternar_painel(True) is False
    assert alternar_painel(False) is True


def test_formatar_contagem():
    assert formatar_contagem(1, "carro", "carros") == "1 carro"
    assert formatar_contagem(2, "carro", "carros") == "2 carros"
    assert formatar_contagem(1, "pessoa", "pessoas") == "1 pessoa"
    assert formatar_contagem(3, "pessoa", "pessoas") == "3 pessoas"


def test_desenhar_texto_ajustado_trunca_ou_reduz():
    import cv2

    img = np.zeros((80, 120, 3), dtype=np.uint8)
    longo = "nesta rua · Cheio Movimentado com texto bem longo"
    desenhado = desenhar_texto_ajustado(
        img, longo, (5, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 1, 100
    )
    (tw, _), _ = cv2.getTextSize(desenhado, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    # cabe na largura com alguma escala >= FONTE_MIN ou truncado
    assert tw <= 120 or desenhado.endswith("...")
    assert len(desenhado) < len(longo) or desenhado.endswith("...")
