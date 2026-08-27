"""Visão: detecção, linha de contagem (auto/manual) e filtro piloto/moto."""

import math
import os

from src.config import (
    AUTO_ANGULO_MIN_R,
    AUTO_LINHA_MAX_CV_GAPS,
    AUTO_LINHA_MIN_SEGMENTOS,
    AUTO_LINHA_MIN_SPAN_X,
    AUTO_LINHA_ROI_Y,
    CONTAINMENT_PERSON_MOTO,
    FRACAO_Y_LINHA,
    ID_PARA_NOME,
    LINHAS_CONTAGEM,
    PERSON_AS_MOTO_ASPECT,
    TRACK_CLASS_HIST,
)


def media_angulo_reta(angulos, min_r=None, pesos=None):
    """Média circular de ângulos de reta em [0, pi).

    Retas a 5° e 175° são a mesma direção; média aritmética daria ~90° (errado).
    Truque: dobrar o ângulo, média vetorial seno/cosseno, dividir por 2.

    Se a magnitude R do vetor resultante for baixa (ângulos se cancelam,
    ex. 45°+135°), retorna None — sem direção dominante clara.
    pesos: opcional; pondera segmentos longos (bordas longas da zebra).
    """
    if min_r is None:
        min_r = AUTO_ANGULO_MIN_R
    vals = list(angulos)
    if not vals:
        return None
    if pesos is None or len(pesos) != len(vals):
        ws = [1.0] * len(vals)
    else:
        ws = [max(float(w), 1e-6) for w in pesos]

    sx = 0.0
    cx = 0.0
    wsum = 0.0
    for theta, w in zip(vals, ws):
        t = float(theta) % math.pi
        if t < 0:
            t += math.pi
        t2 = 2.0 * t
        sx += w * math.sin(t2)
        cx += w * math.cos(t2)
        wsum += w
    sx /= wsum
    cx /= wsum
    r = math.hypot(sx, cx)
    if r < float(min_r):
        return None
    return 0.5 * math.atan2(sx, cx)


def _id_classe_moto():
    return next(cid for cid, nome in ID_PARA_NOME.items() if nome == "motorcycle")


def estabilizar_deteccoes(deteccoes, historico_classes, max_hist=None, aspect_moto=None):
    """Corrige flicker YOLO: person larga → moto; classe = voto majoritário do track.

    Evita: moto contada como carro/pessoa no frame do cruzamento.
    """
    from collections import Counter

    if max_hist is None:
        max_hist = TRACK_CLASS_HIST
    if aspect_moto is None:
        aspect_moto = PERSON_AS_MOTO_ASPECT
    id_moto = _id_classe_moto()
    saida = []
    for x1, y1, x2, y2, tid, cid in deteccoes:
        nome = ID_PARA_NOME.get(cid)
        w = max(0.0, x2 - x1)
        h = max(1e-6, y2 - y1)
        # Moto com sidecar / visão lateral: YOLO às vezes devolve só "person" larga.
        if nome == "person" and (w / h) >= float(aspect_moto):
            cid = id_moto
        hist = historico_classes.setdefault(int(tid), [])
        hist.append(int(cid))
        if len(hist) > int(max_hist):
            del hist[: len(hist) - int(max_hist)]
        cid_estavel = Counter(hist).most_common(1)[0][0]
        saida.append((x1, y1, x2, y2, tid, cid_estavel))
    return saida


def lado_da_linha(px, py, p1, p2):
    """Lado do ponto em relação à reta p1→p2 via produto vetorial (-1 ou 1)."""
    x1, y1 = p1
    x2, y2 = p2
    cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if cross < 0:
        return -1
    if cross > 0:
        return 1
    # Sobre a linha: trata como lado +1 para estabilidade.
    return 1


def _norm_path(fonte):
    if fonte is None:
        return ""
    return str(fonte).replace("\\", "/").strip()


def segmento_horizontal_fallback(largura, altura, fracao_y=None):
    if fracao_y is None:
        fracao_y = FRACAO_Y_LINHA
    y = int(altura * float(fracao_y))
    return ((0, y), (int(largura) - 1, y))


def segmento_norm_para_px(seg_norm, largura, altura):
    (x1, y1), (x2, y2) = seg_norm
    return (
        (int(round(x1 * largura)), int(round(y1 * altura))),
        (int(round(x2 * largura)), int(round(y2 * altura))),
    )


def segmento_px_para_norm(seg_px, largura, altura):
    (x1, y1), (x2, y2) = seg_px
    w = max(float(largura), 1.0)
    h = max(float(altura), 1.0)
    return ((x1 / w, y1 / h), (x2 / w, y2 / h))


def preset_linha_para_fonte(fonte):
    key = _norm_path(fonte)
    if key in LINHAS_CONTAGEM:
        return LINHAS_CONTAGEM[key]
    base = os.path.basename(key)
    for k, v in LINHAS_CONTAGEM.items():
        if os.path.basename(k) == base:
            return v
    return None


def _bbox_area(x1, y1, x2, y2):
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _intersecao_area(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    return _bbox_area(ix1, iy1, ix2, iy2)


def filtrar_pessoas_em_motos(deteccoes, limiar=None):
    """Remove person cuja bbox está majoritariamente dentro de alguma motorcycle.

    Contenção = interseção / área_pessoa (não IoU — proporções pessoa/moto diferem).

    Decisão consciente: compara contra UMA moto por vez, não a união de várias
    boxes. Em fila de motos no farol, pessoa "dividida" entre duas bboxes pode
    não bater o limiar — aceitável no protótipo.
    """
    if limiar is None:
        limiar = CONTAINMENT_PERSON_MOTO
    motos = []
    pessoas = []
    outros = []
    for det in deteccoes:
        x1, y1, x2, y2, tid, cid = det
        nome = ID_PARA_NOME.get(cid)
        if nome == "motorcycle":
            motos.append(det)
        elif nome == "person":
            pessoas.append(det)
        else:
            outros.append(det)

    filtradas = []
    for p in pessoas:
        px1, py1, px2, py2, _tid, _cid = p
        area_p = _bbox_area(px1, py1, px2, py2)
        if area_p <= 1e-6:
            continue
        piloto = False
        for m in motos:
            mx1, my1, mx2, my2, _mtid, _mcid = m
            inter = _intersecao_area((px1, py1, px2, py2), (mx1, my1, mx2, my2))
            if (inter / area_p) >= float(limiar):
                piloto = True
                break
        if not piloto:
            filtradas.append(p)

    return outros + motos + filtradas


def extrair_deteccoes(results):
    import numpy as np

    if results.boxes is None or results.boxes.id is None:
        return []
    caixas = results.boxes.xyxy.cpu().numpy()
    ids = results.boxes.id.cpu().numpy().astype(int)
    classes = results.boxes.cls.cpu().numpy().astype(int)
    return list(zip(caixas[:, 0], caixas[:, 1], caixas[:, 2], caixas[:, 3], ids, classes))


def atualizar_contagem(deteccoes, linha_px, estado_anterior, contagem):
    """Conta cruzamento do pé da bbox (mid_x, y2) pelo segmento linha_px.

    linha_px: ((x1,y1),(x2,y2)) em pixels. Aceita também y escalar legado
    (converte para segmento horizontal infinito em x via âncora só em y).
    """
    if isinstance(linha_px, (int, float)):
        # Compat: y fixo → compara só ancora_y (testes antigos / fallback).
        y_linha = float(linha_px)
        for x1, y1, x2, y2, id_rastreio, id_classe in deteccoes:
            nome = ID_PARA_NOME.get(id_classe)
            if nome is None:
                continue
            ancora_y = y2
            lado_atual = -1 if ancora_y < y_linha else 1
            lado_anterior = estado_anterior.get(id_rastreio)
            if lado_anterior is not None and lado_atual != lado_anterior:
                contagem[nome] = contagem.get(nome, 0) + 1
            estado_anterior[id_rastreio] = lado_atual
        return

    p1, p2 = linha_px
    for x1, y1, x2, y2, id_rastreio, id_classe in deteccoes:
        nome = ID_PARA_NOME.get(id_classe)
        if nome is None:
            continue
        # Pé da bbox: mid_x, y2 — centro sobe com braço e gera falso cruzamento.
        mid_x = 0.5 * (x1 + x2)
        lado_atual = lado_da_linha(mid_x, y2, p1, p2)
        lado_anterior = estado_anterior.get(id_rastreio)
        if lado_anterior is not None and lado_atual != lado_anterior:
            contagem[nome] = contagem.get(nome, 0) + 1
        estado_anterior[id_rastreio] = lado_atual


def _angulo_segmento(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1) % math.pi


def _periodicidade_ok(projecoes, min_n, max_cv):
    """Projeções ao longo da normal às listras: gaps com CV baixo = zebra."""
    if len(projecoes) < min_n:
        return False, []
    xs = sorted(projecoes)
    # Agrupa picos próximos (mesma listra)
    picos = [xs[0]]
    span = xs[-1] - xs[0]
    tol = max(3.0, span / max(len(xs) * 2, 1))
    for x in xs[1:]:
        if x - picos[-1] > tol:
            picos.append(x)
        else:
            picos[-1] = 0.5 * (picos[-1] + x)
    if len(picos) < min_n:
        return False, picos
    gaps = [picos[i + 1] - picos[i] for i in range(len(picos) - 1)]
    if not gaps:
        return False, picos

    # Usa a maior janela consecutiva de gaps com CV aceitável
    # (Hough mistura ruído; CV global sozinho rejeita zebra real).
    best_len = 0
    best_slice = None
    for i in range(len(gaps)):
        for j in range(i + min_n - 1, len(gaps) + 1):
            chunk = gaps[i:j]
            mean_g = sum(chunk) / len(chunk)
            if mean_g <= 1e-6:
                continue
            var = sum((g - mean_g) ** 2 for g in chunk) / len(chunk)
            cv = math.sqrt(var) / mean_g
            if cv <= float(max_cv) and len(chunk) > best_len:
                best_len = len(chunk)
                best_slice = (i, j)
    if best_slice is None:
        return False, picos
    i, j = best_slice
    return True, picos[i : j + 1]


def detectar_faixa_auto(frame, debug=None):
    """Detecta zebra e retorna segmento de contagem NORMALIZADO ((x1,y1),(x2,y2)) ou None.

    A linha de contagem é PERPENDICULAR às listras (corta o fluxo do pedestre),
    com comprimento = largura da zebra ao longo da direção das listras.

    Sinal de v = (-uy, ux) é arbitrário (a outra normal é (uy,-ux)); não afeta
    lado_da_linha — só a orientação do desenho.
    """
    import cv2
    import numpy as np

    if debug is not None:
        debug.clear()
        debug.update(
            {
                "hough": [],
                "cluster": [],
                "picos": [],
                "u": None,
                "v": None,
                "segmento_px": None,
            }
        )

    if frame is None or getattr(frame, "size", 0) == 0:
        return None

    h, w = frame.shape[:2]
    if h < 20 or w < 20:
        return None

    y0 = int(h * AUTO_LINHA_ROI_Y)
    roi = frame[y0:h, :]
    if roi.size == 0:
        return None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    edges = cv2.Canny(bw, 50, 150)
    min_len = max(20, int(0.08 * w))
    lines = cv2.HoughLinesP(
        edges, 1, math.pi / 180, threshold=40, minLineLength=min_len, maxLineGap=12
    )
    if lines is None:
        return None

    segs = []
    for line in lines:
        pts = np.asarray(line).reshape(-1)
        if pts.size < 4:
            continue
        x1, y1, x2, y2 = [int(v) for v in pts[:4]]
        # Coordenadas no frame completo
        y1f, y2f = y1 + y0, y2 + y0
        ang = _angulo_segmento(x1, y1f, x2, y2f)
        length = math.hypot(x2 - x1, y2f - y1f)
        segs.append((x1, y1f, x2, y2f, ang, length))

    if debug is not None:
        debug["hough"] = [(s[0], s[1], s[2], s[3]) for s in segs]

    if len(segs) < AUTO_LINHA_MIN_SEGMENTOS:
        return None

    # Cluster por proximidade ao ângulo médio iterativo (bins de ~15°)
    best_cluster = None
    best_score = -1
    for seed in segs:
        seed_ang = seed[4]
        cluster = []
        for s in segs:
            # Diferença de ângulo de reta em [0, pi/2]
            d = abs(s[4] - seed_ang)
            d = min(d, math.pi - d)
            if d < math.radians(15):
                cluster.append(s)
        score = len(cluster) + 0.01 * sum(c[5] for c in cluster)
        if score > best_score:
            best_score = score
            best_cluster = cluster

    if best_cluster is None or len(best_cluster) < AUTO_LINHA_MIN_SEGMENTOS:
        return None

    angs = [c[4] for c in best_cluster]
    lens = [c[5] for c in best_cluster]
    theta_u = media_angulo_reta(angs, pesos=lens)
    if theta_u is None:
        return None

    ux, uy = math.cos(theta_u), math.sin(theta_u)
    # v perpendicular a u; sinal arbitrário — ver docstring.
    vx, vy = -uy, ux

    # Centroides dos segmentos + projeções
    mids = []
    proj_u = []
    proj_n = []  # normal = v
    for x1, y1, x2, y2, _a, _l in best_cluster:
        mx = 0.5 * (x1 + x2)
        my = 0.5 * (y1 + y2)
        mids.append((mx, my))
        proj_u.append(mx * ux + my * uy)
        proj_n.append(mx * vx + my * vy)

    ok_period, picos = _periodicidade_ok(proj_n, AUTO_LINHA_MIN_SEGMENTOS, AUTO_LINHA_MAX_CV_GAPS)
    if debug is not None:
        debug["cluster"] = [(c[0], c[1], c[2], c[3]) for c in best_cluster]
        debug["picos"] = list(picos)
        debug["u"] = (ux, uy)
        debug["v"] = (vx, vy)

    if not ok_period:
        return None

    cx = sum(m[0] for m in mids) / len(mids)
    cy = sum(m[1] for m in mids) / len(mids)
    u_min, u_max = min(proj_u), max(proj_u)
    half = 0.5 * (u_max - u_min)
    if half < 10:
        return None

    # Segmento ao longo de v, comprimento = extensão em u (largura da zebra).
    p1 = (cx - half * vx, cy - half * vy)
    p2 = (cx + half * vx, cy + half * vy)

    # Clip leve à imagem
    def _clip(p):
        x, y = p
        return (max(0, min(w - 1, x)), max(0, min(h - 1, y)))

    p1 = _clip(p1)
    p2 = _clip(p2)
    if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 20:
        return None

    # Linha quase vertical cobrindo pouco em X → tipicamente errada neste ângulo de câmera.
    span_x = abs(p2[0] - p1[0]) / float(w)
    if span_x < float(AUTO_LINHA_MIN_SPAN_X):
        if debug is not None:
            debug["rejeitado"] = f"span_x={span_x:.2f}"
        return None

    if debug is not None:
        debug["segmento_px"] = (p1, p2)

    return segmento_px_para_norm((p1, p2), w, h)


def resolver_linha(fonte, frame, override_norm=None, forcar_auto=False):
    """Resolve segmento em pixels: override → preset (se conhecido) → auto → fallback.

    Arquivos em LINHAS_CONTAGEM usam preset por padrão (auto neste ângulo costuma
    errar). Tecla A (forcar_auto) tenta auto primeiro; se falhar, cai no preset.

    Retorna (linha_px, origem, debug_info) onde origem ∈
    {'override','auto','preset','fallback'}.
    """
    h, w = frame.shape[:2]
    debug = {}

    if override_norm is not None and not forcar_auto:
        return segmento_norm_para_px(override_norm, w, h), "override", debug

    preset = preset_linha_para_fonte(fonte)

    if forcar_auto or preset is None:
        auto_norm = detectar_faixa_auto(frame, debug=debug)
        if auto_norm is not None:
            return segmento_norm_para_px(auto_norm, w, h), "auto", debug

    if preset is not None:
        return segmento_norm_para_px(preset, w, h), "preset", debug

    if not forcar_auto:
        auto_norm = detectar_faixa_auto(frame, debug=debug)
        if auto_norm is not None:
            return segmento_norm_para_px(auto_norm, w, h), "auto", debug

    return segmento_horizontal_fallback(w, h), "fallback", debug
