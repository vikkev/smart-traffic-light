import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulacao.ponte_visao import (
    anexar_janela,
    eventos_de_chegada,
    ler_janelas,
    taxa_media_por_minuto,
)


def test_pessoa_nao_vira_veiculo(tmp_path):
    caminho = tmp_path / "contagem.csv"
    anexar_janela(caminho, 0, 60, {"car": 1, "person": 4, "bus": 1})
    janelas = ler_janelas(caminho)
    assert janelas[0]["person"] == 4
    eventos = eventos_de_chegada(caminho, rota="reto_n")
    assert len(eventos) == 2
    tipos = sorted(item[2] for item in eventos)
    assert tipos == ["carro", "pesado"]
    assert taxa_media_por_minuto(caminho) == 2.0


def test_aceita_ponto_e_virgula(tmp_path):
    caminho = tmp_path / "excel.csv"
    caminho.write_text(
        "inicio_s;fim_s;car;motorcycle;bus;truck;person\n0;30;2;0;0;0;1\n",
        encoding="utf-8",
    )
    eventos = eventos_de_chegada(caminho)
    assert len(eventos) == 2
    assert eventos[0][0] < eventos[1][0]


def test_exemplo_da_visao_e_deterministico():
    from simulacao.ponte_visao import caminho_exemplo

    primeiro = eventos_de_chegada(caminho_exemplo())
    segundo = eventos_de_chegada(caminho_exemplo())
    assert primeiro == segundo
    assert all(rota == "reto_n" for _t, rota, _tipo in primeiro)
    assert not any(tipo == "person" for _t, _rota, tipo in primeiro)
