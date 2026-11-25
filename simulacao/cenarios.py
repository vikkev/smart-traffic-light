"""Cenários de demanda. A semente fica fixa para o resultado poder ser repetido."""

from pathlib import Path

PASTA = Path(__file__).resolve().parent
ROTAS = PASTA / "rotas"
DADOS = PASTA / "dados"
ARQUIVO_VISAO = DADOS / "contagem_visao_exemplo.csv"

SEMENTE = 42
DURACAO_PADRAO = 900

# Eixo A = norte/sul (a "rua da câmera" no protótipo). Eixo B = leste/oeste.
VIAS = {
    "A": ("n_in", "s_in"),
    "B": ("e_in", "w_in"),
}
DESTINO = {
    "n_in": "s_out",
    "s_in": "n_out",
    "e_in": "w_out",
    "w_in": "e_out",
}
ROTA_RETA = {
    "n_in": "reto_n",
    "s_in": "reto_s",
    "e_in": "reto_e",
    "w_in": "reto_w",
}
EIXO_DA_VIA = {via: eixo for eixo, vias in VIAS.items() for via in vias}

# Veículos por hora em cada aproximação (não na soma do eixo).
CENARIOS = {
    "madrugada": {
        "nome": "Madrugada",
        "fluxos": {"n_in": 30, "s_in": 30, "e_in": 30, "w_in": 30},
    },
    "medio": {
        "nome": "Médio",
        "fluxos": {"n_in": 300, "s_in": 300, "e_in": 300, "w_in": 300},
    },
    "pico": {
        "nome": "Pico",
        "fluxos": {"n_in": 650, "s_in": 650, "e_in": 650, "w_in": 650},
    },
    "desbalanceado": {
        "nome": "Desbalanceado",
        "fluxos": {"n_in": 900, "s_in": 900, "e_in": 90, "w_in": 90},
    },
}

# Mesma malha da madrugada, mas o norte deixa de usar o fluxo do cenário
# e passa a nascer da contagem exportada pela visão.
CENARIO_VISAO = {
    "id": "visao",
    "nome": "Visão (norte)",
    "base": "madrugada",
    "via": "n_in",
    "arquivo": ARQUIVO_VISAO,
}


def obter(nome):
    if nome not in CENARIOS:
        conhecidos = ", ".join(CENARIOS)
        raise KeyError(f"Cenário desconhecido: {nome}. Use: {conhecidos}")
    return CENARIOS[nome]


def taxa_eixo_por_minuto(fluxos):
    """Taxa crítica de cada eixo: a aproximação mais cheia, em veículos/min."""
    taxas = {}
    for eixo, vias in VIAS.items():
        taxas[eixo] = max(fluxos[via] for via in vias) / 60.0
    return taxas


def escrever_rotas(pasta, duracao=DURACAO_PADRAO, cenarios=None):
    """Grava um .rou.xml por cenário. `pasta` pode ser temporária."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    escolhidos = cenarios or CENARIOS.keys()
    caminhos = {}
    for nome in escolhidos:
        caminho = pasta / f"{nome}.rou.xml"
        caminho.write_text(_xml_rotas(CENARIOS[nome]["fluxos"], duracao), encoding="utf-8")
        caminhos[nome] = caminho
    return caminhos


def escrever_rotas_de(fluxos, caminho, duracao, omitir_via=None):
    fluxos = dict(fluxos)
    if omitir_via:
        fluxos[omitir_via] = 0
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    Path(caminho).write_text(_xml_rotas(fluxos, duracao), encoding="utf-8")
    return Path(caminho)


def _fim(duracao):
    valor = float(duracao)
    if valor.is_integer():
        return str(int(valor))
    return f"{valor:.1f}"


def _xml_rotas(fluxos, duracao):
    fim = _fim(duracao)
    linhas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f"<!-- semente {SEMENTE}; fim {fim} s. Gerado por simulacao.cenarios -->",
        "<routes>",
        '    <vType id="carro" accel="2.6" decel="4.5" sigma="0.3" length="4.5" minGap="2.5" maxSpeed="13.89" guiShape="passenger" color="255,255,255"/>',
        '    <vType id="pesado" accel="1.3" decel="4.0" sigma="0.3" length="12" minGap="3.0" maxSpeed="11.11" guiShape="truck" color="200,120,40"/>',
    ]
    for via, rota in ROTA_RETA.items():
        linhas.append(f'    <route id="{rota}" edges="{via} {DESTINO[via]}"/>')
    for via, taxa in fluxos.items():
        if taxa <= 0:
            continue
        linhas.append(
            f'    <flow id="fluxo_{via}" type="carro" route="{ROTA_RETA[via]}" '
            f'begin="0" end="{fim}" vehsPerHour="{int(taxa)}" '
            f'departLane="best" departPos="base" departSpeed="avg"/>'
        )
    linhas.append("</routes>")
    linhas.append("")
    return "\n".join(linhas)
