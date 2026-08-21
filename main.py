"""
Protótipo TCC: YOLOv8 + contagem + Webster simulado (Univ. Marília).

Uso:
    python main.py --source 0 --model yolov8s.pt
Teclas: I = painel | Q/Esc = sair | F = tela cheia
"""

import argparse
import os
import sys
import time

from src.config import FRACAO_Y_LINHA, IDS_CLASSES, LIMIAR_CONF
from src.metricas import registrar_metrica
from src.trafego import ControladorSemaforo, GerenciadorTrafego
from src.ui.painel import alternar_painel, desenhar_camera, montar_frame
from src.visao import atualizar_contagem, extrair_deteccoes


def main(source, model_path, conf=None, resize=None, log_metricas=True, log_path="logs/metricas.jsonl"):
    if not model_path:
        print("ERRO: O modelo (model) não foi especificado.")
        sys.exit(1)

    looks_like_file = isinstance(model_path, str) and (
        os.path.sep in model_path or "/" in model_path or "\\" in model_path
    )
    if looks_like_file and not os.path.exists(model_path):
        print(f"ERRO: O modelo '{model_path}' não foi encontrado no caminho especificado.")
        sys.exit(1)

    if not source or str(source) == "None":
        print("ERRO: A fonte (source) não foi definida. Forneça um ID de câmera, caminho de vídeo ou URL.")
        sys.exit(1)

    try:
        import cv2
        from ultralytics import YOLO

        model = YOLO(model_path)

        source_to_open = source
        try:
            if isinstance(source, str) and source.isdigit():
                source_to_open = int(source)
        except Exception:
            source_to_open = source

        # ponytail: try/fallback de backends no Windows
        try:
            backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        except Exception:
            backends_to_try = [cv2.CAP_ANY]

        cap = None
        b = None
        for b in backends_to_try:
            try:
                cap = cv2.VideoCapture(source_to_open, b)
                if cap is not None and cap.isOpened():
                    break
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
                cap = None
            except Exception:
                cap = None

        if cap is None or not cap.isOpened():
            print(f"ERRO: Não foi possível abrir a fonte: {source}")
            sys.exit(1)
        print(f"Fonte aberta: {source_to_open} com backend={b}")

        altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        first_frame = None
        if altura == 0:
            ok_probe, frame_probe = cap.read()
            if ok_probe and frame_probe is not None:
                altura = frame_probe.shape[0]
                first_frame = frame_probe
            else:
                altura = 480

        y_linha = int(altura * FRACAO_Y_LINHA)
        manager = GerenciadorTrafego()
        controlador = ControladorSemaforo()
        estado_anterior, contagem = {}, {}
        ultimo_tick = time.monotonic()
        painel_visivel = True

        fonte_eh_camera = isinstance(source_to_open, int)
        falhas_leitura = 0
        nome_janela = "Monitoramento Inteligente - TCC"

        print(f"Iniciando sistema com Source: {source} e Model: {model_path}")
        print("Teclas: I = HUD | Q = sair | F = tela cheia")

        cv2.namedWindow(nome_janela, cv2.WINDOW_NORMAL)
        fullscreen = False

        first_frame_consumed = first_frame is None
        if first_frame is not None:
            frame = first_frame

        while True:
            if not first_frame_consumed:
                first_frame_consumed = True
            else:
                ok, frame = cap.read()
                if not ok or frame is None:
                    falhas_leitura += 1
                    if fonte_eh_camera and falhas_leitura < 30:
                        continue
                    print("Fonte de video terminou ou ficou indisponivel.")
                    break
                falhas_leitura = 0

            conf_val = LIMIAR_CONF if conf is None else float(conf)
            scale = 1.0
            proc_frame = frame
            if resize is not None:
                try:
                    max_dim = int(resize)
                    h0, w0 = frame.shape[:2]
                    max0 = max(h0, w0)
                    if max0 > max_dim:
                        scale = max_dim / float(max0)
                        proc_frame = cv2.resize(frame, (max(1, int(w0 * scale)), max(1, int(h0 * scale))))
                except Exception:
                    scale = 1.0

            t0 = time.perf_counter()
            try:
                results = model.track(
                    proc_frame, persist=True, classes=IDS_CLASSES, conf=conf_val, verbose=False
                )[0]
                deteccoes = extrair_deteccoes(results)
            except Exception as e:
                print(f"Aviso: falha na deteccao neste frame ({e})")
                deteccoes = []

            if scale != 1.0 and deteccoes:
                deteccoes = [
                    (x1 / scale, y1 / scale, x2 / scale, y2 / scale, tid, cid)
                    for (x1, y1, x2, y2, tid, cid) in deteccoes
                ]

            atualizar_contagem(deteccoes, y_linha, estado_anterior, contagem)
            demanda = manager.calcular_demanda(contagem)
            status, cor_status = manager.obter_status(demanda)
            controlador.propor(demanda)
            agora = time.monotonic()
            eventos = controlador.tick(agora - ultimo_tick)
            ultimo_tick = agora
            latencia_ms = (time.perf_counter() - t0) * 1000.0

            if log_metricas and eventos:
                for evento in eventos:
                    evento.update({
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "demanda": round(demanda, 2),
                        "status": status,
                        "contagens": dict(contagem),
                        "latencia_ms": round(latencia_ms, 2),
                    })
                    registrar_metrica(log_path, evento)

            frame = desenhar_camera(frame, deteccoes, y_linha)
            dados = {
                "fase": controlador.fase,
                "tempo_restante": controlador.tempo_restante,
                "status": status,
                "cor_status": cor_status,
                "contagem": contagem,
            }
            saida = montar_frame(frame, dados, painel_visivel)
            cv2.imshow(nome_janela, saida)

            key = cv2.waitKeyEx(1)
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("i"), ord("I")):
                painel_visivel = alternar_painel(painel_visivel)
            if key in (ord("f"), ord("F"), 63276, 65470):
                fullscreen = not fullscreen
                try:
                    modo = cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL
                    cv2.setWindowProperty(nome_janela, cv2.WND_PROP_FULLSCREEN, modo)
                except Exception:
                    pass
    finally:
        try:
            if "cap" in locals() and cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
        finally:
            try:
                import cv2 as _cv2
                try:
                    _cv2.destroyAllWindows()
                except Exception:
                    pass
            except Exception:
                pass


def _rodar_probe():
    import cv2

    try:
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    except Exception:
        backends = [cv2.CAP_ANY]
    for b in backends:
        for i in range(6):
            try:
                cap = cv2.VideoCapture(i, b)
                opened = cap.isOpened()
                read_ok = False
                shape = None
                if opened:
                    ok, frame = cap.read()
                    read_ok = ok
                    if ok and frame is not None:
                        shape = frame.shape
                try:
                    cap.release()
                except Exception:
                    pass
                print(f"backend={b} index={i} opened={opened} read_ok={read_ok} shape={shape}")
            except Exception as e:
                print(f"backend={b} index={i} error={e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, default="0", help="Fonte (câmera, arquivo ou RTSP)")
    parser.add_argument("--model", type=str, default="yolov8s.pt", help="Caminho para o modelo .pt")
    parser.add_argument("--conf", type=float, default=None, help="Limiar de confiança")
    parser.add_argument("--probe", action="store_true", help="Probe de câmeras")
    parser.add_argument("--resize", type=int, default=None, help="Reduz maior dimensão (px)")
    parser.add_argument("--log-path", type=str, default="logs/metricas.jsonl", help="JSONL de métricas")
    parser.add_argument("--sem-log-metricas", action="store_true", help="Desliga o log")
    args = parser.parse_args()

    if args.probe:
        _rodar_probe()
        sys.exit(0)

    main(
        str(args.source) if args.source is not None else "0",
        str(args.model) if args.model is not None else "yolov8s.pt",
        conf=args.conf,
        resize=args.resize,
        log_metricas=not args.sem_log_metricas,
        log_path=args.log_path,
    )
