"""Números da simulação e os gráficos fixo × atuado."""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from simulacao.cenarios import CENARIO_VISAO, CENARIOS

ORDEM = list(CENARIOS.keys()) + [CENARIO_VISAO["id"]]
ROTULOS = {nome: dados["nome"] for nome, dados in CENARIOS.items()}
ROTULOS[CENARIO_VISAO["id"]] = CENARIO_VISAO["nome"]

COLUNAS = (
    "cenario",
    "controle",
    "semente",
    "duracao_s",
    "veiculos_inseridos",
    "veiculos_saidos",
    "espera_media_s",
    "espera_max_s",
    "fila_media_veic",
    "fila_max_veic",
    "throughput_veic_min",
    "paradas_desnecessarias",
    "tempo_verde_a_s",
    "tempo_verde_b_s",
)

COR_FIXO = "#7f8c8d"
COR_ATUADO = "#1e8449"


def resumir(viagens, duracao_s, filas, paradas, tempos_verde, cenario, controle, semente):
    esperas = [float(item["espera_s"]) for item in viagens]
    saidos = sum(1 for item in viagens if item["saiu"])
    minutos = max(float(duracao_s) / 60.0, 1e-9)
    return {
        "cenario": cenario,
        "controle": controle,
        "semente": int(semente),
        "duracao_s": round(float(duracao_s), 1),
        "veiculos_inseridos": len(viagens),
        "veiculos_saidos": saidos,
        "espera_media_s": round(sum(esperas) / len(esperas), 2) if esperas else 0.0,
        "espera_max_s": round(max(esperas), 2) if esperas else 0.0,
        "fila_media_veic": round(sum(filas) / len(filas), 3) if filas else 0.0,
        "fila_max_veic": int(max(filas) if filas else 0),
        "throughput_veic_min": round(saidos / minutos, 3),
        "paradas_desnecessarias": int(paradas),
        "tempo_verde_a_s": round(float(tempos_verde.get("A", 0.0)), 1),
        "tempo_verde_b_s": round(float(tempos_verde.get("B", 0.0)), 1),
    }


def ler_tripinfo(caminho):
    import xml.etree.ElementTree as ET

    arvore = ET.parse(caminho)
    viagens = []
    for elemento in arvore.getroot().iter("tripinfo"):
        chegada = elemento.get("arrival")
        saiu = False
        if chegada not in (None, ""):
            try:
                saiu = float(chegada) >= 0.0
            except ValueError:
                saiu = False
        viagens.append({
            "id": elemento.get("id"),
            "espera_s": float(elemento.get("waitingTime", "0") or 0),
            "saiu": saiu,
        })
    return viagens


def salvar_csv(resumos, series, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    resumo_csv = pasta / "resumo.csv"
    with resumo_csv.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        for linha in resumos:
            escritor.writerow({coluna: linha[coluna] for coluna in COLUNAS})

    for serie in series:
        nome = f"serie_{serie['cenario']}_{serie['controle']}.csv"
        with (pasta / nome).open("w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.writer(arquivo)
            escritor.writerow(("t_s", "fila_veic", "fila_a", "fila_b", "fase"))
            for t, fila, fila_a, fila_b, fase in zip(
                serie["t"], serie["fila"], serie["fila_a"], serie["fila_b"], serie["fase"]
            ):
                escritor.writerow((t, fila, fila_a, fila_b, fase))
    return resumo_csv


def salvar_graficos(resumos, series, pasta, duracao_s, semente):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    comparacao = pasta / "comparacao.png"
    filas = pasta / "filas_madrugada.png"
    verdes = pasta / "verdes.png"
    _grafico_barras(resumos, comparacao, duracao_s, semente)
    _grafico_verdes(resumos, verdes, duracao_s, semente)
    _grafico_fila_madrugada(series, filas, duracao_s, semente)
    return comparacao, verdes, filas


def _pares(resumos):
    por = {(item["cenario"], item["controle"]): item for item in resumos}
    cenarios = [nome for nome in ORDEM if (nome, "fixo") in por and (nome, "atuado") in por]
    return cenarios, por


def _grafico_barras(resumos, caminho, duracao_s, semente):
    cenarios, por = _pares(resumos)
    if not cenarios:
        return
    paineis = (
        ("espera_media_s", "Espera média (s)"),
        ("fila_media_veic", "Fila média (veículos)"),
        ("throughput_veic_min", "Vazão (veíc/min)"),
        ("paradas_desnecessarias", "Paradas desnecessárias"),
    )
    rotulos = [ROTULOS.get(nome, nome) for nome in cenarios]
    fig, eixos = plt.subplots(2, 2, figsize=(11.2, 7.4))
    for eixo, (chave, titulo) in zip(eixos.ravel(), paineis):
        fixo = [por[(nome, "fixo")][chave] for nome in cenarios]
        atuado = [por[(nome, "atuado")][chave] for nome in cenarios]
        pos = list(range(len(cenarios)))
        eixo.bar([p - 0.18 for p in pos], fixo, width=0.36, color=COR_FIXO, label="Fixo")
        eixo.bar([p + 0.18 for p in pos], atuado, width=0.36, color=COR_ATUADO, label="Atuado")
        eixo.set_title(titulo)
        eixo.set_xticks(pos, rotulos, rotation=15, ha="right")
        eixo.set_ylim(bottom=0)
        eixo.grid(axis="y", alpha=0.3)
        eixo.legend(frameon=False, loc="upper left")
    fig.suptitle(f"Cruzamento — fixo × atuado  (semente {semente}, {int(duracao_s)} s)")
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)


def _grafico_verdes(resumos, caminho, duracao_s, semente):
    cenarios, por = _pares(resumos)
    if not cenarios:
        return
    fig, eixo = plt.subplots(figsize=(10.2, 4.6))
    pos = list(range(len(cenarios)))
    largura = 0.18
    series = (
        (-1.5, "fixo", "tempo_verde_a_s", COR_FIXO, "Fixo N/S"),
        (-0.5, "fixo", "tempo_verde_b_s", "#b0b7bd", "Fixo L/O"),
        (0.5, "atuado", "tempo_verde_a_s", COR_ATUADO, "Atuado N/S"),
        (1.5, "atuado", "tempo_verde_b_s", "#58d68d", "Atuado L/O"),
    )
    for desloca, controle, chave, cor, legenda in series:
        valores = [por[(nome, controle)][chave] for nome in cenarios]
        eixo.bar([p + desloca * largura for p in pos], valores, width=largura, color=cor, label=legenda)
    eixo.set_xticks(pos, [ROTULOS.get(nome, nome) for nome in cenarios])
    eixo.set_ylabel("Tempo total de verde (s)")
    eixo.set_title(f"Repartição do verde  (semente {semente}, {int(duracao_s)} s)")
    eixo.set_ylim(bottom=0)
    eixo.grid(axis="y", alpha=0.3)
    eixo.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    fig.savefig(caminho)
    plt.close(fig)


def _grafico_fila_madrugada(series, caminho, duracao_s, semente):
    fig, eixo = plt.subplots(figsize=(10.2, 4.2))
    desenhos = 0
    for serie in series:
        if serie["cenario"] != "madrugada":
            continue
        cor = COR_FIXO if serie["controle"] == "fixo" else COR_ATUADO
        nome = "Fixo" if serie["controle"] == "fixo" else "Atuado"
        eixo.plot(serie["t"], serie["fila"], color=cor, label=nome, linewidth=1.4)
        desenhos += 1
    if desenhos == 0:
        plt.close(fig)
        return
    eixo.set_xlabel("Tempo (s)")
    eixo.set_ylabel("Veículos parados")
    eixo.set_title(f"Fila na madrugada  (semente {semente}, {int(duracao_s)} s)")
    eixo.set_ylim(bottom=0)
    eixo.grid(alpha=0.3)
    eixo.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(caminho)
    plt.close(fig)
