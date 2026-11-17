import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulacao.ambiente import binario_sumo
from simulacao.cenarios import CENARIOS, ROTAS, escrever_rotas
from simulacao.rede import NET


def _sumo_ok():
    if not NET.exists():
        return False
    try:
        binario_sumo(gui=False)
    except Exception:
        return False
    return True


def test_rotas_batem_com_os_fluxos(tmp_path):
    escrever_rotas(tmp_path, duracao=900)
    for nome, dados in CENARIOS.items():
        texto = (tmp_path / f"{nome}.rou.xml").read_text(encoding="utf-8")
        for taxa in dados["fluxos"].values():
            assert f'vehsPerHour="{taxa}"' in texto
        commitado = ROTAS / f"{nome}.rou.xml"
        assert commitado.read_text(encoding="utf-8") == texto


@pytest.mark.skipif(not _sumo_ok(), reason="SUMO ou a rede não estão disponíveis")
def test_malha_tem_os_quatro_bracos():
    from simulacao.controladores import estado_links
    from simulacao.rede import mapa_eixos

    texto = NET.read_text(encoding="utf-8")
    for via in ("n_in", "s_in", "e_in", "w_in"):
        assert f'id="{via}"' in texto
    mapa = mapa_eixos()
    assert set(mapa.values()) == {"A", "B"}
    verde = estado_links(mapa, "VERDE_A")
    assert len(verde) == max(mapa) + 1
    assert "G" in verde and "r" in verde
    assert estado_links(mapa, "ALLRED_AB") == "r" * len(verde)


@pytest.mark.skipif(not _sumo_ok(), reason="SUMO ou a rede não estão disponíveis")
def test_sumo_para_no_vermelho_e_anda_no_verde():
    from simulacao.runner import rodar

    fixo = rodar("medio", "fixo", duracao=120, avisos=False)["resumo"]
    atuado = rodar("medio", "atuado", duracao=120, avisos=False)["resumo"]
    assert fixo["veiculos_inseridos"] > 0
    assert fixo["veiculos_saidos"] > 0
    assert fixo["espera_max_s"] > 0
    assert atuado["veiculos_saidos"] > 0
    assert atuado["tempo_verde_a_s"] > 0
    assert atuado["tempo_verde_b_s"] > 0
