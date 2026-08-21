"""HUD essencial desenhado direto na câmera (sem fundo cinza)."""

from src.config import (
    FONTE_MIN_ESCALA,
    ID_PARA_NOME,
    NOMES_PT,
    NOMES_PT_PLURAL,
    NOMES_PT_SINGULAR,
    STATUS_PT,
)


def alternar_painel(estado_atual):
    return not estado_atual


def formatar_contagem(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def desenhar_texto_ajustado(img, texto, pos, fonte, escala_inicial, cor, espessura, largura_max_px):
    import cv2

    aa = cv2.LINE_AA
    escala = float(escala_inicial)
    desenho = texto
    while True:
        (tw, _), _ = cv2.getTextSize(desenho, fonte, escala, espessura)
        if tw <= largura_max_px:
            break
        if escala > FONTE_MIN_ESCALA + 1e-9:
            escala = max(FONTE_MIN_ESCALA, round(escala - 0.05, 2))
            continue
        base = desenho.rstrip(".")
        while base:
            candidato = base + "..."
            (tw, _), _ = cv2.getTextSize(candidato, fonte, FONTE_MIN_ESCALA, espessura)
            if tw <= largura_max_px:
                desenho = candidato
                break
            base = base[:-1]
        else:
            desenho = "..."
        escala = FONTE_MIN_ESCALA
        break
    _texto_contorno(img, desenho, pos, fonte, escala, cor, espessura)
    return desenho


def _texto_contorno(img, texto, pos, fonte, escala, cor, espessura=2):
    """Texto colorido com borda preta — legível sem caixa cinza."""
    import cv2

    aa = cv2.LINE_AA
    x, y = pos
    # contorno
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1), (-2, 0), (2, 0), (0, -2), (0, 2)):
        cv2.putText(img, texto, (x + dx, y + dy), fonte, escala, (0, 0, 0), espessura + 2, aa)
    cv2.putText(img, texto, pos, fonte, escala, cor, espessura, aa)


def _cor_fase(fase):
    if fase.startswith("VERDE"):
        return "Verde", (0, 255, 80)
    if fase.startswith("AMARELO"):
        return "Amarelo", (0, 255, 255)
    return "Sinal", (220, 220, 220)


def _texto_passaram(contagem):
    if not contagem:
        return "Contagem: —"
    partes = []
    for nome, qtd in contagem.items():
        singular = NOMES_PT_SINGULAR.get(nome, NOMES_PT.get(nome, nome).lower())
        plural = NOMES_PT_PLURAL.get(nome, singular + "s")
        partes.append(formatar_contagem(qtd, singular, plural))
    return " · ".join(partes)


def desenhar_camera(frame, deteccoes, y_linha):
    import cv2

    aa = cv2.LINE_AA
    h, w = frame.shape[:2]
    cv2.line(frame, (0, int(y_linha)), (w, int(y_linha)), (0, 255, 255), 2, aa)

    for x1, y1, x2, y2, _tid, cls_id in deteccoes:
        nome = NOMES_PT.get(ID_PARA_NOME.get(cls_id, ""), str(cls_id))
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(frame, p1, p2, (0, 200, 0), 2, aa)
        _texto_contorno(frame, nome, (p1[0], max(p1[1] - 6, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)
    return frame


def montar_frame(frame_camera, dados_resumo, painel_visivel):
    import cv2

    h, w = frame_camera.shape[:2]
    fonte = cv2.FONT_HERSHEY_SIMPLEX

    if not painel_visivel:
        _texto_contorno(frame_camera, "I = HUD   Q = sair", (10, h - 12), fonte, 0.5, (200, 200, 200), 1)
        return frame_camera

    nome, cor_sinal = _cor_fase(dados_resumo["fase"])
    restam = max(0, int(dados_resumo["tempo_restante"]))
    fluxo = STATUS_PT.get(dados_resumo["status"], dados_resumo["status"])
    contagem = _texto_passaram(dados_resumo["contagem"])

    x, y = 12, 28
    # bolinha da cor do sinal
    cv2.circle(frame_camera, (x + 8, y - 8), 9, (0, 0, 0), -1, cv2.LINE_AA)
    cv2.circle(frame_camera, (x + 8, y - 8), 8, cor_sinal, -1, cv2.LINE_AA)

    _texto_contorno(frame_camera, f"{nome}  {restam}s", (x + 24, y), fonte, 0.75, cor_sinal, 2)
    _texto_contorno(frame_camera, f"Fluxo: {fluxo}", (x, y + 32), fonte, 0.6, dados_resumo["cor_status"], 2)
    desenhar_texto_ajustado(frame_camera, contagem, (x, y + 60), fonte, 0.55, (0, 255, 255), 2, max(80, w - 24))
    return frame_camera
