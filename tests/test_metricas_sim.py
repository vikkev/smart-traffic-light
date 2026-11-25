import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulacao.metricas_sim import resumir, salvar_csv, salvar_graficos


def _linha(cenario, controle, espera, fila, vazao, paradas, verde_a, verde_b):
    viagens = [{"espera_s": espera, "saiu": True} for _ in range(4)]
    filas = [fila, fila]
    return resumir(
        viagens,
        duracao_s=60,
        filas=filas,
        paradas=paradas,
        tempos_verde={"A": verde_a, "B": verde_b},
        cenario=cenario,
        controle=controle,
        semente=42,
    )


def test_resumo_e_grafico(tmp_path):
    resumos = [
        _linha("madrugada", "fixo", 12, 1, 4, 5, 30, 30),
        _linha("madrugada", "atuado", 3, 0, 4, 1, 40, 10),
    ]
    assert resumos[0]["espera_media_s"] == 12
    assert resumos[1]["paradas_desnecessarias"] == 1
    series = [
        {
            "cenario": "madrugada",
            "controle": "fixo",
            "t": [1, 2],
            "fila": [1, 0],
            "fila_a": [1, 0],
            "fila_b": [0, 0],
            "fase": ["VERDE_A", "VERDE_B"],
        },
        {
            "cenario": "madrugada",
            "controle": "atuado",
            "t": [1, 2],
            "fila": [0, 0],
            "fila_a": [0, 0],
            "fila_b": [0, 0],
            "fase": ["VERDE_A", "VERDE_A"],
        },
    ]
    salvar_csv(resumos, series, tmp_path)
    salvar_graficos(resumos, series, tmp_path, 60, 42)
    assert (tmp_path / "resumo.csv").exists()
    assert (tmp_path / "comparacao.png").stat().st_size > 1000
    assert (tmp_path / "verdes.png").stat().st_size > 1000
    assert (tmp_path / "filas_madrugada.png").stat().st_size > 1000
