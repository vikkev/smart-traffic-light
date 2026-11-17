from src.config import (
    DADOS_VEICULOS,
    DEMANDA_SATURACAO,
    FASES,
    G_MAX,
    G_MIN,
    TEMPO_AMARELO,
    TEMPO_PERDIDO,
    Y_A_MAX,
    Y_A_MIN,
    Y_B,
    Y_MAX,
)


class GerenciadorTrafego:
    def calcular_demanda(self, contagens_atuais):
        pontuacao = 0.0
        for nome, quantidade in contagens_atuais.items():
            if nome in DADOS_VEICULOS:
                pontuacao += quantidade * DADOS_VEICULOS[nome]["peso"]
        return pontuacao

    def taxa_por_minuto(self, pontuacao, duracao_s):
        """Equivalentes por minuto. Contagem acumulada não é volume de Webster."""
        duracao_s = float(duracao_s)
        if duracao_s <= 0.0:
            return 0.0
        return float(pontuacao) * 60.0 / duracao_s

    def obter_status(self, pontuacao):
        if pontuacao > 15:
            return "PRIORIDADE", (0, 0, 255)
        if pontuacao > 8:
            return "BUSY", (0, 165, 255)
        return "NORMAL", (0, 255, 0)


def _y_por_taxa(taxa):
    return max(Y_A_MIN, min(Y_A_MAX, float(taxa) / DEMANDA_SATURACAO))


def _limitar_proporcional(verde_a, verde_b):
    """Encolhe os dois verdes juntos quando algum passa de G_MAX.

    Limitar cada verde sozinho jogava o resto no outro. Com demanda >= 14
    os dois batiam em 60 s e o eixo mais cheio perdia a prioridade.
    """
    maior = max(verde_a, verde_b, 1e-9)
    if maior > G_MAX:
        escala = G_MAX / maior
        verde_a *= escala
        verde_b *= escala
    verde_a = min(G_MAX, max(G_MIN, verde_a))
    verde_b = min(G_MAX, max(G_MIN, verde_b))
    return verde_a, verde_b


class ControladorSemaforo:
    """Tempos de fase por Webster. Recalcula só no próximo ciclo.

    A demanda é taxa (equivalentes por minuto), na mesma unidade de
    DEMANDA_SATURACAO. Sem taxa do eixo B, usa o Y_B fixo da câmera única.
    """

    def __init__(self):
        self.fase = "VERDE_A"
        self.tempo_restante = G_MIN
        self.verde_a = G_MIN
        self.verde_b = G_MIN
        self.ciclo = G_MIN + G_MIN + 2 * TEMPO_AMARELO
        self.sobrecarregado = False
        self.proximo_ciclo = None
        self.iniciar(0.0)

    def calcular_tempos(self, demanda, taxa_b=None):
        y_a = _y_por_taxa(demanda)
        y_b = Y_B if taxa_b is None else _y_por_taxa(taxa_b)
        y_soma = y_a + y_b
        sobrecarregado = y_soma > Y_MAX
        if sobrecarregado and y_soma > 0.0:
            fator = Y_MAX / y_soma
            y_a *= fator
            y_b *= fator
        Y = min(y_a + y_b, Y_MAX)
        ciclo_webster = (1.5 * TEMPO_PERDIDO + 5.0) / (1.0 - Y)
        verde_disponivel = max(0.0, ciclo_webster - TEMPO_PERDIDO)
        if Y <= 1e-9:
            bruto_a = bruto_b = verde_disponivel / 2.0
        else:
            bruto_a = (y_a / Y) * verde_disponivel
            bruto_b = (y_b / Y) * verde_disponivel
        verde_a, verde_b = _limitar_proporcional(bruto_a, bruto_b)
        ciclo = verde_a + verde_b + 2 * TEMPO_AMARELO
        return {
            "y_a": y_a,
            "y_b": y_b,
            "Y": Y,
            "verde_a": verde_a,
            "verde_b": verde_b,
            "ciclo": ciclo,
            "ciclo_webster": ciclo_webster,
            "sobrecarregado": sobrecarregado,
        }

    def iniciar(self, demanda):
        self._aplicar(self.calcular_tempos(demanda))
        self.fase = "VERDE_A"
        self.tempo_restante = self.verde_a
        self.proximo_ciclo = None

    def propor(self, demanda):
        self.proximo_ciclo = self.calcular_tempos(demanda)

    def tick(self, dt):
        if dt < 0:
            dt = 0.0
        self.tempo_restante -= dt
        eventos = []
        passos = 0
        while self.tempo_restante <= 1e-9 and passos < 20:
            passos += 1
            idx = FASES.index(self.fase)
            proxima = FASES[(idx + 1) % len(FASES)]
            aplicou_ciclo = False
            if proxima == "VERDE_A" and self.proximo_ciclo is not None:
                self._aplicar(self.proximo_ciclo)
                self.proximo_ciclo = None
                aplicou_ciclo = True
            self.fase = proxima
            self.tempo_restante += self._duracao(self.fase)
            if aplicou_ciclo:
                eventos.append(self._evento("ciclo"))
            eventos.append(self._evento("fase"))
        return eventos

    def _duracao(self, fase):
        if fase == "VERDE_A":
            return self.verde_a
        if fase == "VERDE_B":
            return self.verde_b
        return TEMPO_AMARELO

    def _aplicar(self, tempos):
        self.verde_a = tempos["verde_a"]
        self.verde_b = tempos["verde_b"]
        self.ciclo = tempos["ciclo"]
        self.sobrecarregado = tempos["sobrecarregado"]

    def _evento(self, tipo):
        return {
            "evento": tipo,
            "fase": self.fase,
            "verde_a": round(self.verde_a, 2),
            "verde_b": round(self.verde_b, 2),
            "ciclo": round(self.ciclo, 2),
            "sobrecarregado": self.sobrecarregado,
            "tempo_restante": round(max(self.tempo_restante, 0.0), 2),
        }
