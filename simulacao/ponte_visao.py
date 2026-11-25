"""Ponte por arquivo entre a contagem da visão e as chegadas no SUMO.

O CSV registra janelas (um ciclo do protótipo, ou um trecho do vídeo).
Cada carro, moto, ônibus ou caminhão vira um veículo na aproximação escolhida.
Pessoa não gera veículo: a faixa de pedestre não entra nesta simulação.
"""

import csv
import os
from pathlib import Path

COLUNAS = ("inicio_s", "fim_s", "car", "motorcycle", "bus", "truck", "person")


def anexar_janela(caminho, inicio_s, fim_s, contagens):
    caminho = Path(caminho)
    if caminho.parent and not caminho.parent.exists():
        caminho.parent.mkdir(parents=True, exist_ok=True)
    novo = not caminho.exists() or caminho.stat().st_size == 0
    with caminho.open("a", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        if novo:
            escritor.writeheader()
        escritor.writerow({
            "inicio_s": f"{float(inicio_s):.2f}",
            "fim_s": f"{float(fim_s):.2f}",
            "car": int(contagens.get("car", 0)),
            "motorcycle": int(contagens.get("motorcycle", 0)),
            "bus": int(contagens.get("bus", 0)),
            "truck": int(contagens.get("truck", 0)),
            "person": int(contagens.get("person", 0)),
        })


def ler_janelas(caminho):
    caminho = Path(caminho)
    with caminho.open("r", encoding="utf-8", newline="") as arquivo:
        amostra = arquivo.read(4096)
        arquivo.seek(0)
        delimitador = ";" if amostra.count(";") > amostra.count(",") else ","
        leitor = csv.DictReader(arquivo, delimiter=delimitador)
        janelas = []
        for linha in leitor:
            if not linha or not (linha.get("inicio_s") or "").strip():
                continue
            janelas.append({
                "inicio_s": float(linha["inicio_s"]),
                "fim_s": float(linha["fim_s"]),
                "car": _inteiro(linha.get("car")),
                "motorcycle": _inteiro(linha.get("motorcycle")),
                "bus": _inteiro(linha.get("bus")),
                "truck": _inteiro(linha.get("truck")),
                "person": _inteiro(linha.get("person")),
            })
    return janelas


def eventos_de_chegada(caminho, rota="reto_n"):
    """Lista (instante, rota, tipo) determinística. Pessoa é ignorada."""
    eventos = []
    for janela in ler_janelas(caminho):
        _espacar(eventos, janela, janela["car"] + janela["motorcycle"], "carro", rota)
        _espacar(eventos, janela, janela["bus"] + janela["truck"], "pesado", rota)
    eventos.sort(key=lambda item: (item[0], item[2], item[1]))
    return eventos


def taxa_media_por_minuto(caminho):
    """Veículos (sem pessoas) por minuto, no intervalo coberto pelo arquivo."""
    janelas = ler_janelas(caminho)
    if not janelas:
        return 0.0
    inicio = min(item["inicio_s"] for item in janelas)
    fim = max(item["fim_s"] for item in janelas)
    duracao = fim - inicio
    if duracao <= 0.0:
        return 0.0
    total = 0
    for item in janelas:
        total += item["car"] + item["motorcycle"] + item["bus"] + item["truck"]
    return total * 60.0 / duracao


def _espacar(eventos, janela, quantidade, tipo, rota):
    if quantidade <= 0:
        return
    inicio = float(janela["inicio_s"])
    fim = float(janela["fim_s"])
    largura = max(fim - inicio, 1e-6)
    for indice in range(quantidade):
        instante = inicio + (indice + 0.5) * largura / quantidade
        eventos.append((instante, rota, tipo))


def _inteiro(valor):
    if valor is None or str(valor).strip() == "":
        return 0
    return int(float(valor))


def caminho_exemplo():
    return os.path.join(os.path.dirname(__file__), "dados", "contagem_visao_exemplo.csv")
