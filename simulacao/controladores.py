"""Planos do semáforo, sem falar com o SUMO.

O plano fixo só olha o relógio. O atuado lê uma fotografia dos detectores
(`Leitura`) e pode encerrar o verde cedo.
"""

from dataclasses import dataclass

from src.config import DEMANDA_SATURACAO, G_MIN, TEMPO_AMARELO
from src.trafego import ControladorSemaforo

# Uma faixa a 50 km/h escoa cerca de 1800 veic/h. O Webster do protótipo
# divide por DEMANDA_SATURACAO (equiv/min), então a taxa da simulação entra reescalada.
SATURACAO_FAIXA_VEIC_MIN = 30.0

PROXIMA = {
    "VERDE_A": "AMARELO_A",
    "AMARELO_A": "ALLRED_AB",
    "ALLRED_AB": "VERDE_B",
    "VERDE_B": "AMARELO_B",
    "AMARELO_B": "ALLRED_BA",
    "ALLRED_BA": "VERDE_A",
}

VERDE_FIXO = 30.0
ALLRED = 1.0
GAP_OUT = 2.0


@dataclass
class Leitura:
    """O que os detectores dizem neste segundo.

    `verde_vazio`: ninguém a até DISTANCIA metros da faixa no eixo que está verde.
    `espera_vermelho`: há veículo na aproximação que está vermelha.
    `chamada_verde`: o laço do verde foi atuado neste passo (zera o gap).
    """

    chamada_verde: bool = False
    verde_vazio: bool = True
    espera_vermelho: bool = False


def transicionar(controle):
    if controle.fase.startswith("VERDE"):
        controle.ultimo_verde = controle.t_fase
    controle.fase = PROXIMA[controle.fase]
    controle.t_fase = 0.0
    controle._gap = 0.0


def estado_links(eixo_por_indice, fase):
    """Monta a string r/y/G do SUMO a partir do eixo de cada ligação."""
    if not eixo_por_indice:
        return ""
    n = max(eixo_por_indice) + 1
    caracteres = ["r"] * n
    for indice, eixo in eixo_por_indice.items():
        caracteres[indice] = _cor(eixo, fase)
    return "".join(caracteres)


def _cor(eixo, fase):
    if fase == "VERDE_A" and eixo == "A":
        return "G"
    if fase == "AMARELO_A" and eixo == "A":
        return "y"
    if fase == "VERDE_B" and eixo == "B":
        return "G"
    if fase == "AMARELO_B" and eixo == "B":
        return "y"
    return "r"


def maximos_webster(taxa_a, taxa_b):
    """Verde máximo de cada eixo, pelo plano Webster (já limitado a G_MIN/G_MAX)."""
    fator = DEMANDA_SATURACAO / SATURACAO_FAIXA_VEIC_MIN
    tempos = ControladorSemaforo().calcular_tempos(taxa_a * fator, taxa_b=taxa_b * fator)
    return tempos["verde_a"], tempos["verde_b"]


class ControladorFixo:
    """Ciclo rígido. Os detectores não mudam a decisão."""

    def __init__(self, verde_a=VERDE_FIXO, verde_b=VERDE_FIXO, amarelo=TEMPO_AMARELO, allred=ALLRED):
        self.verde_a = float(verde_a)
        self.verde_b = float(verde_b)
        self.amarelo = float(amarelo)
        self.allred = float(allred)
        self.fase = "VERDE_A"
        self.t_fase = 0.0
        self._gap = 0.0
        self.ultimo_verde = None

    def passo(self, dt, leitura=None):
        """Um segundo de simulação. A fase devolvida é a que fica no semáforo."""
        if dt < 0:
            dt = 0.0
        if self.t_fase >= self._limite() - 1e-9:
            transicionar(self)
        self.t_fase += dt
        return self.fase

    def _limite(self):
        if self.fase == "VERDE_A":
            return self.verde_a
        if self.fase == "VERDE_B":
            return self.verde_b
        if self.fase.startswith("AMARELO"):
            return self.amarelo
        return self.allred


class ControladorAtuado:
    """Verde mínimo, amarelo, verde máximo e gap-out.

    Depois do mínimo, se o vermelho tem veículo e o verde está vazio
    (ninguém dentro da distância) por `gap_out` segundos, troca.
    Sem veículo no vermelho, o verde permanece — evita ciclo vazio de madrugada.
    Com fila nos dois, o máximo (Webster) impede que um eixo segure o outro.
    Pensado para ser chamado uma vez por segundo.
    """

    def __init__(
        self,
        verde_max_a,
        verde_max_b,
        verde_min=G_MIN,
        amarelo=TEMPO_AMARELO,
        allred=ALLRED,
        gap_out=GAP_OUT,
    ):
        self.verde_min = float(verde_min)
        self.amarelo = float(amarelo)
        self.allred = float(allred)
        self.gap_out = float(gap_out)
        self.verde_max = {"A": self.verde_min, "B": self.verde_min}
        self.definir_maximos(verde_max_a, verde_max_b)
        self.fase = "VERDE_A"
        self.t_fase = 0.0
        self._gap = 0.0
        self.ultimo_verde = None

    def definir_maximos(self, verde_a, verde_b):
        self.verde_max["A"] = max(self.verde_min, float(verde_a))
        self.verde_max["B"] = max(self.verde_min, float(verde_b))

    def passo(self, dt, leitura=None):
        """Um segundo de simulação. A fase devolvida é a que fica no semáforo."""
        if leitura is None:
            leitura = Leitura()
        if dt < 0:
            dt = 0.0
        if self._deve_encerrar(leitura):
            transicionar(self)
        self.t_fase += dt
        if self.fase.startswith("VERDE"):
            if leitura.chamada_verde or not leitura.verde_vazio:
                self._gap = 0.0
            else:
                self._gap += dt
        return self.fase

    def _deve_encerrar(self, leitura):
        if self.fase.startswith("VERDE"):
            eixo = "A" if self.fase == "VERDE_A" else "B"
            if not leitura.espera_vermelho:
                return False
            if self.t_fase < self.verde_min - 1e-9:
                return False
            if self.t_fase >= self.verde_max[eixo] - 1e-9:
                return True
            return leitura.verde_vazio and self._gap >= self.gap_out - 1e-9
        limite = self.amarelo if self.fase.startswith("AMARELO") else self.allred
        return self.t_fase >= limite - 1e-9
