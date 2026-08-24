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

from src.config import FRACAO_Y_LINHA, IDS_CLASSES, LIMIAR_CONF, SOURCE_PATH, SOURCE_TYPE
from src.metricas import registrar_metrica
from src.trafego import ControladorSemaforo, GerenciadorTrafego
from src.ui.painel import alternar_painel, desenhar_camera, montar_frame
from src.visao import atualizar_contagem, extrair_deteccoes


def resolver_fonte(source=None, source_type=None, source_path=None):
    """Resolve a fonte de entrada para webcam, RTSP ou vídeo gravado."""
    if source is not None and str(source) != "None":
        source_str = str(source).strip()
        if isinstance(source, int):
            return source, "webcam"
        if source_str.isdigit():
            return int(source_str), "webcam"
        if source_str.lower().startswith("rtsp"):
            return source_str, "rtsp"
        return source_str, "video"

    tipo = (source_type or SOURCE_TYPE or "webcam").lower()
    if tipo == "webcam":
        default = source_path if source_path is not None else SOURCE_PATH
        if default is None or str(default) == "None":
            return 0, "webcam"
        default_str = str(default).strip()
        if default_str.isdigit():
            return int(default_str), "webcam"
        return default_str, "video"
    if tipo == "rtsp":
        default = source_path if source_path is not None else SOURCE_PATH
        return str(default or "rtsp://localhost/stream"), "rtsp"
    if tipo == "video":
        default = source_path if source_path is not None else SOURCE_PATH
        return str(default or "video.mp4"), "video"

    raise ValueError(f"Tipo de fonte inválido: {source_type!r}")


def abrir_fonte(source=None, source_type=None, source_path=None):
    """Abre a fonte usando um backend OpenCV simples e verifica a primeira leitura."""
    source_to_open, resolved_type = resolver_fonte(source, source_type=source_type, source_path=source_path)
    if isinstance(source_to_open, str) and source_to_open.isdigit():
        source_to_open = int(source_to_open)
        resolved_type = "webcam"

    try:
        import cv2
    except Exception as e:
        print(f"ERRO: falha ao importar OpenCV (cv2): {e}")
        raise

    try:
        backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    except Exception:
        backends_to_try = [cv2.CAP_ANY]

    cap = None
    backend_usado = None
    for backend in backends_to_try:
        candidate = None
        try:
            candidate = cv2.VideoCapture(source_to_open, backend)
            if candidate is not None:
                if candidate.isOpened():
                    cap = candidate
                    backend_usado = backend
                    break
                else:
                    candidate.release()
            else:
                cap = None
        except Exception:
            cap = None

    if cap is None:
        try:
            cap = cv2.VideoCapture(source_to_open)
            backend_usado = "default"
        except Exception:
            return None

    try:
        ok_probe, _frame_probe = cap.read()
        if not ok_probe:
            print(f"AVISO: fonte aberta, mas não foi possível ler o primeiro frame em {source_to_open}.")
    except Exception:
        pass

    print(f"Fonte aberta: {source_to_open} (tipo={resolved_type}, backend={backend_usado})")
    return cap


def fonte_com_retry_for(source_to_open):
    """Retorna True se a fonte deve usar o mecanismo de retry (câmera local ou RTSP)."""
    return isinstance(source_to_open, int) or (
        isinstance(source_to_open, str) and source_to_open.lower().startswith("rtsp")
    )


def main(source, model_path, conf=None, resize=None, log_metricas=True, log_path="logs/metricas.jsonl", max_frames=None, source_type=None, source_path=None):
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
    except Exception as e:
        print(f"ERRO: falha ao importar OpenCV (cv2): {e}")
        raise

    # Carregamento do modelo YOLO — mensagens claras para falhas conhecidas
    class _DummyModel:
        def track(self, *args, **kwargs):
            # simula resultado sem detecções
            class R:
                boxes = None

            return [R()]

    try:
        try:
            from ultralytics import YOLO
            ULTRALYTICS_AVAILABLE = True
        except Exception:
            ULTRALYTICS_AVAILABLE = False
            print("AVISO: biblioteca 'ultralytics' não encontrada. O pipeline continuará em modo reduzido (sem detecções).")

        if ULTRALYTICS_AVAILABLE:
            try:
                model = YOLO(model_path)
            except FileNotFoundError:
                print(f"ERRO: arquivo de modelo '{model_path}' não foi encontrado.")
                sys.exit(1)
            except Exception as e:
                print(f"ERRO: falha ao carregar o modelo '{model_path}': {e}")
                raise
        else:
            model = _DummyModel()
    except Exception:
        raise

    try:
        source_to_open, resolved_type = resolver_fonte(source, source_type=source_type, source_path=source_path)
        if isinstance(source_to_open, str) and source_to_open.isdigit():
            source_to_open = int(source_to_open)
            resolved_type = "webcam"

        cap = abrir_fonte(source_to_open, source_type=resolved_type, source_path=source_path)
        if cap is None or not cap.isOpened():
            print(f"ERRO: Não foi possível abrir a fonte: {source_to_open}")
            sys.exit(1)

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
        # Para poda de track_ids que não aparecem faz tempo
        ultimo_visto = {}
        frame_idx = 0
        N_FRAMES_PRUNE = 300
        painel_visivel = True

        fonte_eh_camera = isinstance(source_to_open, int)
        fonte_com_retry = fonte_eh_camera or (
            isinstance(source_to_open, str) and source_to_open.lower().startswith("rtsp")
        )
        falhas_leitura = 0
        nome_janela = "Monitoramento Inteligente - TCC"

        print(f"Iniciando sistema com Source: {source} e Model: {model_path}")
        print("Teclas: I = HUD | Q = sair | F = tela cheia")

        cv2.namedWindow(nome_janela, cv2.WINDOW_NORMAL)
        fullscreen = False
        try:
            import numpy as _np
            # criar frame preto mínimo para forçar abertura da janela
            _h, _w = 480, 640
            _blank = _np.zeros((_h, _w, 3), dtype=_np.uint8)
            try:
                cv2.imshow(nome_janela, _blank)
                cv2.waitKey(1)
                try:
                    cv2.setWindowProperty(nome_janela, cv2.WND_PROP_TOPMOST, 1)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

        first_frame_consumed = first_frame is None
        if first_frame is not None:
            frame = first_frame
            try:
                # garantir que a janela seja criada/visível antes do loop principal
                cv2.imshow(nome_janela, frame)
                cv2.waitKey(1)
                try:
                    # tentar colocar a janela em primeiro plano (se suportado)
                    cv2.setWindowProperty(nome_janela, cv2.WND_PROP_TOPMOST, 1)
                except Exception:
                    pass
            except Exception:
                pass

        while True:
            if not first_frame_consumed:
                first_frame_consumed = True
            else:
                ok, frame = cap.read()
                if not ok or frame is None:
                    falhas_leitura += 1
                    if fonte_com_retry and falhas_leitura < 30:
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
            # atualizar últimos vistos por id para poda futura
            try:
                ids_presentes = [int(tid) for (_x1, _y1, _x2, _y2, tid, _cid) in deteccoes]
            except Exception:
                ids_presentes = []
            for tid in ids_presentes:
                ultimo_visto[tid] = frame_idx
            # poda periódica de ids antigos do estado_anterior
            if frame_idx % N_FRAMES_PRUNE == 0 and frame_idx > 0:
                lim = frame_idx - N_FRAMES_PRUNE
                to_remove = [iid for iid, last in ultimo_visto.items() if last < lim]
                for iid in to_remove:
                    ultimo_visto.pop(iid, None)
                    estado_anterior.pop(iid, None)
            frame_idx += 1
            # modo de depuração: sair após processar `max_frames` frames
            if max_frames is not None:
                try:
                    if frame_idx >= int(max_frames):
                        print(f"Debug: atingido max_frames={max_frames}, encerrando.")
                        break
                except Exception:
                    pass
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

            # Se houver ciclo (Webster), limpar as contagens para que a
            # demanda do próximo ciclo represente tráfego recente.
            if eventos and any(ev.get("evento") == "ciclo" for ev in eventos):
                contagem.clear()

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
    parser.add_argument("--source-type", type=str, default=None, choices=["webcam", "rtsp", "video"], help="Tipo de fonte: webcam, rtsp ou video")
    parser.add_argument("--source-path", type=str, default=None, help="Caminho da fonte para streams RTSP/vídeo")
    parser.add_argument("--model", type=str, default="yolov8s.pt", help="Caminho para o modelo .pt")
    parser.add_argument("--conf", type=float, default=None, help="Limiar de confiança")
    parser.add_argument("--probe", action="store_true", help="Probe de câmeras")
    parser.add_argument("--resize", type=int, default=None, help="Reduz maior dimensão (px)")
    parser.add_argument("--log-path", type=str, default="logs/metricas.jsonl", help="JSONL de métricas")
    parser.add_argument("--sem-log-metricas", action="store_true", help="Desliga o log")
    parser.add_argument("--max-frames", type=int, default=None, help="(debug) processar apenas N frames e sair")
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
        max_frames=args.max_frames,
        source_type=args.source_type,
        source_path=args.source_path,
    )
