"""Rede do cruzamento: quatro braços e o semáforo C."""

from pathlib import Path

from simulacao.cenarios import EIXO_DA_VIA

PASTA = Path(__file__).resolve().parent / "malha"
NOD = PASTA / "cruzamento.nod.xml"
EDG = PASTA / "cruzamento.edg.xml"
CON = PASTA / "cruzamento.con.xml"
TLL = PASTA / "cruzamento.tll.xml"
NET = PASTA / "cruzamento.net.xml"

# Faixa em que um carro "se aproximando" ainda segura o verde.
DISTANCIA_APROX_M = 70.0
# Laço junto à faixa de retenção, para o gap entre atuações.
POSICAO_LACO_M = -8.0

VIAS_ENTRADA = ("n_in", "s_in", "e_in", "w_in")


def mapa_eixos(net_path=None):
    """Índice da ligação no semáforo → eixo A (N/S) ou B (L/O)."""
    from simulacao.ambiente import preparar_ambiente

    preparar_ambiente()
    import sumolib

    net = sumolib.net.readNet(str(net_path or NET))
    tls = net.getTLS("C")
    mapa = {}
    for faixa_in, _faixa_out, indice in tls.getConnections():
        via = faixa_in.getEdge().getID()
        if via not in EIXO_DA_VIA:
            raise RuntimeError(f"Ligação do semáforo em via inesperada: {via}")
        mapa[int(indice)] = EIXO_DA_VIA[via]
    if not mapa:
        raise RuntimeError("O semáforo C não controla nenhuma ligação.")
    return mapa


def comprimentos(net_path=None):
    from simulacao.ambiente import preparar_ambiente

    preparar_ambiente()
    import sumolib

    net = sumolib.net.readNet(str(net_path or NET))
    medidas = {}
    for via in VIAS_ENTRADA:
        medidas[via] = net.getLane(f"{via}_0").getLength()
    return medidas


def escrever_detectores(caminho, comprimentos_via, pasta_saida):
    """Dois detectores de área e um laço por aproximação.

    `presenca` cobre a via inteira (tem alguém no vermelho?).
    `aprox` cobre os últimos DISTANCIA metros (tem alguém chegando no verde?).
    """
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    linhas = ['<additional>']
    for via, comprimento in comprimentos_via.items():
        inicio_aprox = max(0.0, comprimento - DISTANCIA_APROX_M)
        arquivo = pasta_saida / f"{via}.xml"
        linhas.append(
            f'    <laneAreaDetector id="presenca_{via}" lane="{via}_0" '
            f'pos="0" endPos="{comprimento:.2f}" freq="1" '
            f'file="{arquivo}" friendlyPos="true"/>'
        )
        linhas.append(
            f'    <laneAreaDetector id="aprox_{via}" lane="{via}_0" '
            f'pos="{inicio_aprox:.2f}" endPos="{comprimento:.2f}" freq="1" '
            f'file="{arquivo}" friendlyPos="true"/>'
        )
        linhas.append(
            f'    <inductionLoop id="laco_{via}" lane="{via}_0" '
            f'pos="{POSICAO_LACO_M}" freq="1" file="{arquivo}" friendlyPos="true"/>'
        )
    linhas.append("</additional>")
    linhas.append("")
    Path(caminho).write_text("\n".join(linhas), encoding="utf-8")
    return Path(caminho)


def programa_estatico(eixo_por_indice):
    """Plano fixo de reserva, embutido na rede (30 s / 30 s)."""
    from simulacao.controladores import ALLRED, VERDE_FIXO, estado_links
    from src.config import TEMPO_AMARELO

    fases = (
        (VERDE_FIXO, "VERDE_A"),
        (TEMPO_AMARELO, "AMARELO_A"),
        (ALLRED, "ALLRED_AB"),
        (VERDE_FIXO, "VERDE_B"),
        (TEMPO_AMARELO, "AMARELO_B"),
        (ALLRED, "ALLRED_BA"),
    )
    linhas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<tlLogics>",
        '    <tlLogic id="C" type="static" programID="0" offset="0">',
    ]
    for duracao, fase in fases:
        estado = estado_links(eixo_por_indice, fase)
        linhas.append(f'        <phase duration="{int(duracao)}" state="{estado}"/>')
    linhas.append("    </tlLogic>")
    linhas.append("</tlLogics>")
    linhas.append("")
    return "\n".join(linhas)
