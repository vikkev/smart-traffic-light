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

    def obter_status(self, pontuacao):
        if pontuacao > 15:
            return "PRIORIDADE", (0, 0, 255)
        if pontuacao > 8:
            return "BUSY", (0, 165, 255)
        return "NORMAL", (0, 255, 0)


class ControladorSemaforo:
    """Tempos de fase por Webster. Recalcula só no próximo ciclo."""

    def __init__(self):
        self.fase = "VERDE_A"
        self.tempo_restante = G_MIN
        self.verde_a = G_MIN
        self.verde_b = G_MIN
        self.ciclo = G_MIN + G_MIN + 2 * TEMPO_AMARELO
        self.sobrecarregado = False
        self.proximo_ciclo = None
        self.iniciar(0.0)

    def calcular_tempos(self, demanda):
        y_a = max(Y_A_MIN, min(Y_A_MAX, float(demanda) / DEMANDA_SATURACAO))
        y_soma = y_a + Y_B
        sobrecarregado = y_soma > Y_MAX
        Y = min(y_soma, Y_MAX)
        ciclo_webster = (1.5 * TEMPO_PERDIDO + 5.0) / (1.0 - Y)
        verde_disponivel = ciclo_webster - TEMPO_PERDIDO
        verde_a = max(G_MIN, min(G_MAX, (y_a / Y) * verde_disponivel))
        verde_b = max(G_MIN, min(G_MAX, verde_disponivel - verde_a))
        ciclo = verde_a + verde_b + 2 * TEMPO_AMARELO
        return {
            "y_a": y_a,
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
