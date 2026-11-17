"""Reconstrói a rede com netconvert e atualiza as rotas padrão.

    python -m simulacao.gerar_rede
"""

import subprocess
import sys
from pathlib import Path

from simulacao.ambiente import binario_netconvert, mensagem_sumo_ausente, preparar_ambiente
from simulacao.cenarios import DURACAO_PADRAO, ROTAS, escrever_rotas
from simulacao.rede import CON, EDG, NET, NOD, TLL, mapa_eixos, programa_estatico


def gerar():
    preparar_ambiente()
    try:
        netconvert = binario_netconvert()
    except (FileNotFoundError, ImportError):
        print(mensagem_sumo_ausente())
        return 1

    # Primeiro a geometria, para saber a ordem das ligações do semáforo.
    _rodar(netconvert, tll=None, saida=NET)
    eixo_por_indice = mapa_eixos(NET)
    TLL.write_text(programa_estatico(eixo_por_indice), encoding="utf-8")
    _rodar(netconvert, tll=TLL, saida=NET)

    # A ordem não pode mudar ao recolocar o plano; senão o estado fica torto.
    if mapa_eixos(NET) != eixo_por_indice:
        print("ERRO: a ordem das ligações mudou ao aplicar o plano semafórico.")
        return 1

    escrever_rotas(ROTAS, duracao=DURACAO_PADRAO)
    print(f"Rede: {NET}")
    print(f"Plano: {TLL}")
    print(f"Rotas: {ROTAS}")
    print("Ligações:", " ".join(f"{i}:{e}" for i, e in sorted(eixo_por_indice.items())))
    return 0


def _rodar(netconvert, tll, saida):
    comando = [
        netconvert,
        "--node-files", str(NOD),
        "--edge-files", str(EDG),
        "--connection-files", str(CON),
        "--output-file", str(saida),
        "--no-turnarounds", "true",
        "--no-left-connections", "true",
        "--tls.guess", "true",
        "--junctions.corner-detail", "5",
        "--no-warnings", "false",
    ]
    if tll is not None:
        comando.extend(["--tllogic-files", str(tll)])
    resultado = subprocess.run(comando, check=False, capture_output=True, text=True)
    if resultado.returncode != 0:
        sys.stderr.write(resultado.stdout)
        sys.stderr.write(resultado.stderr)
        raise RuntimeError("netconvert falhou")
    if resultado.stderr.strip():
        print(resultado.stderr.strip())


if __name__ == "__main__":
    sys.exit(gerar())
