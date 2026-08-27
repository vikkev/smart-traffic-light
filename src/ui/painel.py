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


def desenhar_debug_linha(frame, debug_info):
    """Overlay: Hough bruto, cluster, picos e linha (defesa TCC)."""
    import cv2

    if not debug_info:
        return frame
    aa = cv2.LINE_AA
    for x1, y1, x2, y2 in debug_info.get("hough") or []:
        cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (80, 80, 80), 1, aa)
    for x1, y1, x2, y2 in debug_info.get("cluster") or []:
        cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)), (255, 128, 0), 2, aa)
    u = debug_info.get("u")
    seg = debug_info.get("segmento_px")
    if u is not None and seg is not None:
        (sx, sy), _ = seg
        # picos: posições ao longo da normal; marcar perto do centro do segmento
        for i, _p in enumerate(debug_info.get("picos") or []):
            cv2.circle(frame, (int(sx) + i * 3, int(sy)), 4, (255, 0, 255), -1, aa)
    return frame


def desenhar_camera(
    frame,
    deteccoes,
    linha_px,
    debug_info=None,
    mostrar_debug=False,
    calibrando=False,
    calib_pontos=None,
    mouse_pos=None,
):
    import cv2

    aa = cv2.LINE_AA
    if mostrar_debug and debug_info:
        desenhar_debug_linha(frame, debug_info)

    if linha_px is not None:
        if isinstance(linha_px, (int, float)):
            h, w = frame.shape[:2]
            cv2.line(frame, (0, int(linha_px)), (w, int(linha_px)), (0, 255, 255), 2, aa)
        else:
            p1, p2 = linha_px
            cv2.line(
                frame,
                (int(p1[0]), int(p1[1])),
                (int(p2[0]), int(p2[1])),
                (0, 255, 255),
                2,
                aa,
            )

    if calibrando:
        pts = list(calib_pontos or [])
        for p in pts:
            cv2.circle(frame, (int(p[0]), int(p[1])), 6, (0, 200, 255), -1, aa)
        if len(pts) == 1 and mouse_pos is not None:
            cv2.line(
                frame,
                (int(pts[0][0]), int(pts[0][1])),
                (int(mouse_pos[0]), int(mouse_pos[1])),
                (0, 200, 255),
                1,
                aa,
            )
        _texto_contorno(
            frame,
            "Calibrar: clique 2 pontos (Esc cancela)",
            (12, frame.shape[0] - 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 200, 255),
            2,
        )

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
        _texto_contorno(frame_camera, "I=HUD  A=auto  L=linha  D=debug  Q=sair", (10, h - 12), fonte, 0.45, (200, 200, 200), 1)
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
    origem = dados_resumo.get("origem_linha")
    if origem:
        _texto_contorno(frame_camera, f"Linha: {origem}", (x, y + 88), fonte, 0.45, (180, 180, 180), 1)
    return frame_camera
