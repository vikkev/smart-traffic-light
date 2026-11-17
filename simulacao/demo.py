"""Abre o sumo-gui com um cenário e um controlador.

    python -m simulacao.demo --cenario madrugada --controle atuado
    python -m simulacao.demo --cenario desbalanceado --controle fixo
    python -m simulacao.demo --cenario madrugada --controle atuado --demanda-visao simulacao/dados/contagem_visao_exemplo.csv
"""

import argparse
import sys

from simulacao.cenarios import CENARIOS, DURACAO_PADRAO, SEMENTE
from simulacao.runner import rodar


def main(argv=None):
    parser = argparse.ArgumentParser(description="Demonstração ao vivo no sumo-gui.")
    parser.add_argument("--cenario", default="madrugada", choices=list(CENARIOS.keys()))
    parser.add_argument("--controle", default="atuado", choices=("fixo", "atuado"))
    parser.add_argument("--duracao", type=float, default=DURACAO_PADRAO)
    parser.add_argument("--atraso", type=int, default=150, help="Milissegundos entre passos")
    parser.add_argument("--demanda-visao", default=None, help="CSV de contagem da visão, no braço norte")
    parser.add_argument("--semente", type=int, default=SEMENTE)
    args = parser.parse_args(argv)
    print(
        f"Abrindo sumo-gui: {args.cenario} / {args.controle} "
        f"({int(args.duracao)} s, semente {args.semente})"
    )
    try:
        resultado = rodar(
            args.cenario,
            args.controle,
            duracao=args.duracao,
            gui=True,
            atraso_ms=args.atraso,
            demanda_visao=args.demanda_visao,
            semente=args.semente,
        )
    except FileNotFoundError as erro:
        print(erro)
        return 1
    linha = resultado["resumo"]
    print(
        f"Espera média {linha['espera_media_s']:.2f} s, "
        f"paradas desnecessárias {linha['paradas_desnecessarias']}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
