"""Roda todos os cenários, sem janela, e grava CSV e gráficos.

    python -m simulacao.experimentos
    python -m simulacao.experimentos --duracao 900
"""

import argparse
import sys
from pathlib import Path

from simulacao.cenarios import CENARIO_VISAO, CENARIOS, DURACAO_PADRAO, SEMENTE
from simulacao.metricas_sim import salvar_csv, salvar_graficos
from simulacao.runner import rodar

PASTA_RESULTADOS = Path(__file__).resolve().parent / "resultados"


def executar(duracao=DURACAO_PADRAO, pasta=None, cenarios=None, com_visao=True, semente=SEMENTE):
    pasta = Path(pasta) if pasta else PASTA_RESULTADOS
    nomes = list(cenarios) if cenarios else list(CENARIOS.keys())
    planos = [(nome, controle, None) for nome in nomes for controle in ("fixo", "atuado")]
    if com_visao:
        planos.extend(("madrugada", controle, CENARIO_VISAO) for controle in ("fixo", "atuado"))

    resumos = []
    series = []
    for nome, controle, visao in planos:
        rotulo = visao["id"] if visao else nome
        print(f"Rodando {rotulo} / {controle} ({int(duracao)} s) ...", flush=True)
        extra = {}
        if visao:
            extra = {
                "rotulo_cenario": visao["id"],
                "demanda_visao": visao["arquivo"],
                "via_visao": visao["via"],
                "omitir_via": visao["via"],
            }
        resultado = rodar(nome, controle, duracao=duracao, semente=semente, **extra)
        resumos.append(resultado["resumo"])
        series.append(resultado["serie"])
        _imprimir(resultado["resumo"])

    salvar_csv(resumos, series, pasta)
    salvar_graficos(resumos, series, pasta, duracao, semente)
    print(f"Resultados em {pasta}")
    return resumos


def _imprimir(linha):
    print(
        f"  espera média {linha['espera_media_s']:.2f} s | "
        f"máx {linha['espera_max_s']:.2f} s | "
        f"fila média {linha['fila_media_veic']:.2f} | "
        f"máx {linha['fila_max_veic']} | "
        f"vazão {linha['throughput_veic_min']:.2f} veic/min | "
        f"paradas desnecessárias {linha['paradas_desnecessarias']} | "
        f"verde N/S {linha['tempo_verde_a_s']:.0f} s, L/O {linha['tempo_verde_b_s']:.0f} s"
    )


def _tabela(resumos):
    cabecalho = (
        f"{'cenario':<16} {'controle':<8} {'espera':>8} {'espera_max':>10} "
        f"{'fila':>8} {'vazao':>8} {'paradas':>8}"
    )
    print(cabecalho)
    for linha in resumos:
        print(
            f"{linha['cenario']:<16} {linha['controle']:<8} "
            f"{linha['espera_media_s']:8.2f} {linha['espera_max_s']:10.2f} "
            f"{linha['fila_media_veic']:8.2f} {linha['throughput_veic_min']:8.2f} "
            f"{linha['paradas_desnecessarias']:8d}"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Experimentos do cruzamento (SUMO, sem janela).")
    parser.add_argument("--duracao", type=float, default=DURACAO_PADRAO, help="Segundos simulados")
    parser.add_argument("--saida", type=str, default=None, help="Pasta dos CSV e PNG")
    parser.add_argument("--cenarios", type=str, default=None, help="Lista separada por vírgula")
    parser.add_argument("--sem-visao", action="store_true", help="Não roda o cenário da ponte com a câmera")
    parser.add_argument("--semente", type=int, default=SEMENTE)
    args = parser.parse_args(argv)
    nomes = None
    if args.cenarios:
        nomes = [item.strip() for item in args.cenarios.split(",") if item.strip()]
    try:
        resumos = executar(
            duracao=args.duracao,
            pasta=args.saida,
            cenarios=nomes,
            com_visao=not args.sem_visao,
            semente=args.semente,
        )
    except FileNotFoundError as erro:
        print(erro)
        return 1
    print()
    _tabela(resumos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
