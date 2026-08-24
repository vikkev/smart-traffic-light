DADOS_VEICULOS = {
    "person": {"id": 0, "peso": 0.5},
    "car": {"id": 2, "peso": 1.0},
    "motorcycle": {"id": 3, "peso": 1.0},
    "bus": {"id": 5, "peso": 3.0},
    "truck": {"id": 7, "peso": 3.0},
}

ID_PARA_NOME = {v["id"]: k for k, v in DADOS_VEICULOS.items()}
IDS_CLASSES = [v["id"] for v in DADOS_VEICULOS.values()]
NOMES_PT = {
    "person": "Pessoa",
    "car": "Carro",
    "motorcycle": "Moto",
    "bus": "Onibus",
    "truck": "Caminhao",
}
NOMES_PT_PLURAL = {
    "person": "pessoas",
    "car": "carros",
    "motorcycle": "motos",
    "bus": "onibus",
    "truck": "caminhoes",
}
NOMES_PT_SINGULAR = {
    "person": "pessoa",
    "car": "carro",
    "motorcycle": "moto",
    "bus": "onibus",
    "truck": "caminhao",
}

LIMIAR_CONF = 0.4
FRACAO_Y_LINHA = 0.6

TEMPO_AMARELO = 3.0
TEMPO_PERDIDO = 8.0  # L: 2 fases × (~3 s âmbar + 1 s all-red)
Y_B = 0.20  # ponytail: uma câmera; braço complementar não é medido
Y_A_MIN = 0.10
Y_A_MAX = 0.85
Y_MAX = 0.90
G_MIN = 8.0
G_MAX = 60.0
DEMANDA_SATURACAO = 20.0
FASES = ("VERDE_A", "AMARELO_A", "VERDE_B", "AMARELO_B")

# Fonte de entrada do protótipo: webcam, rtsp ou video gravado.
SOURCE_TYPE = "webcam"
SOURCE_PATH = "0"

FONTE_MIN_ESCALA = 0.45
STATUS_PT = {
    "NORMAL": "Tranquilo",
    "BUSY": "Movimentado",
    "PRIORIDADE": "Prioridade",
}
