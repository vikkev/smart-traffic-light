"""
Detecção e contagem de veículos/pedestres via YOLOv8 + line crossing.
TCC: Sistema inteligente de monitoramento de cruzamentos (Univ. Marília).

Uso:
    python deteccao_contagem.py --source 0 --model yolov8s.pt
"""

import argparse
import os
import sys

# --- Configuração ---
DADOS_VEICULOS = {
    "person": {"id": 0, "peso": 0.5},
    "car": {"id": 2, "peso": 1.0},
    "motorcycle": {"id": 3, "peso": 1.0},
    "bus": {"id": 5, "peso": 3.0},
    "truck": {"id": 7, "peso": 3.0},
}

ID_PARA_NOME = {v["id"]: k for k, v in DADOS_VEICULOS.items()}
IDS_CLASSES = [v["id"] for v in DADOS_VEICULOS.values()]

LIMIAR_CONF = 0.4
FRACAO_Y_LINHA = 0.6

# --- Módulo de Inteligência ---
class GerenciadorTrafego:
    def __init__(self):
        pass

    def calcular_demanda(self, contagens_atuais):
        pontuacao = 0.0
        for nome, quantidade in contagens_atuais.items():
            if nome in DADOS_VEICULOS:
                pontuacao += quantidade * DADOS_VEICULOS[nome]["peso"]
        return pontuacao

    def obter_status(self, pontuacao):
        if pontuacao > 15:
            return "PRIORIDADE", (0, 0, 255)
        elif pontuacao > 8:
            return "BUSY", (0, 165, 255)
        else:
            return "NORMAL", (0, 255, 0)

# --- Processamento de Visão ---
def extrair_deteccoes(results):
    # Importar dependências pesadas localmente apenas quando necessário
    # (permite importar este módulo em testes sem instalar todas as deps).
    import numpy as np

    if results.boxes is None or results.boxes.id is None:
        return []
    caixas = results.boxes.xyxy.cpu().numpy()
    ids = results.boxes.id.cpu().numpy().astype(int)
    classes = results.boxes.cls.cpu().numpy().astype(int)
    return list(zip(caixas[:, 0], caixas[:, 1], caixas[:, 2], caixas[:, 3], ids, classes))

def atualizar_contagem(deteccoes, y_linha, estado_anterior, contagem):
    # Contagem por transição de lado: cada objeto é identificado apenas por um ID
    # temporário do tracker para a sessão atual. Não persistimos identidade pessoal.
    for x1, y1, x2, y2, id_rastreio, id_classe in deteccoes:
        nome = ID_PARA_NOME.get(id_classe)
        if nome is None:
            # Ignora classes fora do conjunto técnico necessário para o monitoramento
            # de fluxo de tráfego, sem afetar tracking de objetos válidos.
            continue

        centro_y = (y1 + y2) / 2
        lado_atual = -1 if centro_y < y_linha else 1
        lado_anterior = estado_anterior.get(id_rastreio)

        if lado_anterior is not None and lado_atual != lado_anterior:
            contagem[nome] = contagem.get(nome, 0) + 1
        estado_anterior[id_rastreio] = lado_atual

def desenhar_overlay(frame, deteccoes, y_linha, contagem, manager):
    import cv2

    h, w = frame.shape[:2]
    cv2.line(frame, (0, int(y_linha)), (w, int(y_linha)), (0, 255, 255), 3)
    for x1, y1, x2, y2, track_id, cls_id in deteccoes:
        nome = ID_PARA_NOME.get(cls_id, str(cls_id))
        p1, p2 = (int(x1), int(y1)), (int(x2), int(y2))
        cv2.rectangle(frame, p1, p2, (0, 200, 0), 2)
        cv2.putText(frame, f"{nome} {track_id}", (p1[0], max(p1[1]-10, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1)

    pontuacao_demanda = manager.calcular_demanda(contagem)
    texto_status, cor_status = manager.obter_status(pontuacao_demanda)

    cv2.rectangle(frame, (10, 10), (350, 160), (0, 0, 0), -1)
    cv2.putText(frame, f"STATUS: {texto_status}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor_status, 2)
    cv2.putText(frame, f"DEMANDA: {pontuacao_demanda:.1f}", (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    stats_str = " | ".join([f"{k}:{v}" for k, v in contagem.items()])
    cv2.putText(frame, stats_str, (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    return frame

# --- Validação e Execução ---
def main(source, model_path, conf=None, resize=None):
    # Validação explícita mínima antes de iniciar o modelo
    if not model_path:
        print("ERRO: O modelo (model) não foi especificado.")
        sys.exit(1)

    # Se o argumento parecer um caminho local (contém separador), exigir existência.
    # Não tratar apenas por extensão (.pt) — permitir que ultralytics resolva/download de modelos como 'yolov8s.pt'.
    looks_like_file = isinstance(model_path, str) and (os.path.sep in model_path or '/' in model_path or '\\' in model_path)
    if looks_like_file and not os.path.exists(model_path):
        print(f"ERRO: O modelo '{model_path}' não foi encontrado no caminho especificado.")
        sys.exit(1)

    if not source or str(source) == "None":
        print("ERRO: A fonte (source) não foi definida. Forneça um ID de câmera, caminho de vídeo ou URL.")
        sys.exit(1)

    try:
        # Import heavy runtime libraries lazily to allow importing this module
        # (e.g., for unit tests) without installing all runtime deps.
        import cv2
        from ultralytics import YOLO

        def probe_devices(max_index=5, backends=None):
            if backends is None:
                try:
                    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
                except Exception:
                    backends = [cv2.CAP_ANY]
            results = []
            for b in backends:
                for i in range(max_index+1):
                    try:
                        cap_probe = cv2.VideoCapture(i, b)
                        opened = cap_probe.isOpened()
                        read_ok = False
                        shape = None
                        if opened:
                            ok, frame = cap_probe.read()
                            read_ok = ok
                            if ok and frame is not None:
                                shape = frame.shape
                        try:
                            cap_probe.release()
                        except Exception:
                            pass
                        results.append((b, i, opened, read_ok, shape))
                    except Exception:
                        results.append((b, i, False, False, None))
            return results

        model = YOLO(model_path)

        # Normalizar source: "0" -> int(0) para webcam, deixar RTSP/paths como string
        source_to_open = source
        try:
            if isinstance(source, str) and source.isdigit():
                source_to_open = int(source)
        except Exception:
            source_to_open = source

        # Tentar múltiplos backends (DSHOW, MSMF, ANY) para melhorar compatibilidade no Windows
        # ponytail: mínimo try/fallback sem adicionar dependências; prioriza dshow por padrão
        backends_to_try = []
        try:
            backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        except Exception:
            backends_to_try = [cv2.CAP_ANY]

        cap = None
        for b in backends_to_try:
            try:
                cap = cv2.VideoCapture(source_to_open, b)
                if cap is not None and cap.isOpened():
                    # aberto com backend b
                    break
                else:
                    try:
                        if cap is not None:
                            cap.release()
                    except Exception:
                        pass
                    cap = None
            except Exception:
                cap = None

        if cap is None or not cap.isOpened():
            print(f"ERRO: Não foi possível abrir a fonte: {source}")
            sys.exit(1)
        else:
            try:
                print(f"Fonte aberta: {source_to_open} com backend={b}")
            except Exception:
                pass

        altura = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # fallback if CAP_PROP_FRAME_HEIGHT not available yet
        if altura == 0:
            # try reading one frame to get size
            ok_probe, frame_probe = cap.read()
            if ok_probe and frame_probe is not None:
                altura = frame_probe.shape[0]
                # Put frame back into processing loop by using it immediately
                first_frame = frame_probe
            else:
                altura = 480
                first_frame = None

        y_linha = int(altura * FRACAO_Y_LINHA)

        manager = GerenciadorTrafego()
        estado_anterior, contagem = {}, {}

        print(f"Iniciando sistema com Source: {source} e Model: {model_path}")

        # Preparar janela e fullscreen toggle
        cv2.namedWindow("Monitoramento Inteligente - TCC", cv2.WINDOW_NORMAL)
        fullscreen = False

        # If we probed a first frame, process it first; ensure we only reuse it once
        first_frame_consumed = True
        if 'first_frame' in locals() and first_frame is not None:
            frame = first_frame
            ok = True
            first_frame_consumed = False
        else:
            ok = True

        while True:
            if not ok:
                break

            if not first_frame_consumed:
                # use the probed frame once, then read from capture normally
                first_frame_consumed = True
            else:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break

            # usar limiar de confiança passado por CLI se fornecido
            conf_val = LIMIAR_CONF if conf is None else float(conf)

            # opcional: redimensionar para acelerar inferência
            scale = 1.0
            proc_frame = frame
            if resize is not None:
                try:
                    max_dim = int(resize)
                    h0, w0 = frame.shape[:2]
                    max0 = max(h0, w0)
                    if max0 > max_dim:
                        scale = max_dim / float(max0)
                        new_w = max(1, int(w0 * scale))
                        new_h = max(1, int(h0 * scale))
                        proc_frame = cv2.resize(frame, (new_w, new_h))
                        print(f"Redimensionando frame {w0}x{h0} -> {new_w}x{new_h} (scale={scale:.3f})")
                except Exception:
                    scale = 1.0

            # Tracking temporário somente para sustentar a contagem por linha e
            # evitar duplicação dentro do processamento do vídeo atual.
            results = model.track(proc_frame, persist=False, classes=IDS_CLASSES,
                                  conf=conf_val, verbose=False)[0]

            deteccoes = extrair_deteccoes(results)
            # se redimensionamos, escalar caixas de volta para coordenadas do frame original
            if scale != 1.0 and deteccoes:
                deteccoes = [(x1/scale, y1/scale, x2/scale, y2/scale, tid, cid) for (x1,y1,x2,y2,tid,cid) in deteccoes]

            atualizar_contagem(deteccoes, y_linha, estado_anterior, contagem)
            frame = desenhar_overlay(frame, deteccoes, y_linha, contagem, manager)
            cv2.imshow("Monitoramento Inteligente - TCC", frame)

            # Use waitKeyEx to capture extended keys (F11) when possible
            key = cv2.waitKeyEx(1)
            # Quit on 'q'
            if key == ord('q') or key == 113:
                break
            # Toggle fullscreen on 'f' or F11 (common F11 codes attempted)
            if key == ord('f') or key == 102 or key in (0xFF, 63276, 65470):
                fullscreen = not fullscreen
                try:
                    if fullscreen:
                        cv2.setWindowProperty("Monitoramento Inteligente - TCC", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    else:
                        cv2.setWindowProperty("Monitoramento Inteligente - TCC", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                except Exception:
                    pass

            # Se usuário fechou a janela (clicou no X), encerre o loop
            try:
                vis = cv2.getWindowProperty("Monitoramento Inteligente - TCC", cv2.WND_PROP_VISIBLE)
                if vis < 1:
                    break
            except Exception:
                # se getWindowProperty não estiver disponível, ignore
                pass
    finally:
        # ponytail: ensure cleanup doesn't raise secondary exceptions if init failed
        try:
            if 'cap' in locals() and cap is not None:
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=str, default="0", help="Fonte (câmera, arquivo ou RTSP)")
    parser.add_argument("--model", type=str, default="yolov8s.pt", help="Caminho para o modelo .pt")
    parser.add_argument("--conf", type=float, default=None, help="Limiar de confiança para detecções (sobrepõe config)")
    parser.add_argument("--probe", action="store_true", help="Faz probe de índices/backends de câmera e imprime resultados")
    parser.add_argument("--resize", type=int, default=None, help="Reduz a maior dimensão do frame para acelerar inferência (px). Ex: --resize 640")
    args = parser.parse_args()

    # Forçamos a conversão para string e removemos nulos antes de passar para a função principal
    src_val = str(args.source) if args.source is not None else "0"
    mdl_val = str(args.model) if args.model is not None else "yolov8s.pt"
    
    if args.probe:
        # run probe and exit
        # Import here to reuse main's probe helper via importing module
        from main import main as _m
        # call main with probe mode: import cv2 inside main will define probe_devices
        # We call main with a special flag by invoking the helper directly after import
        # Simpler: re-import cv2 here and call probe_devices defined in module scope is not available
        import cv2
        try:
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        except Exception:
            backends = [cv2.CAP_ANY]
        # run a simple probe and print
        from main import __file__ as _mfile
        # Use the probe logic: open small loop
        results = []
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
                    print(f'backend={b} index={i} opened={opened} read_ok={read_ok} shape={shape}')
                except Exception as e:
                    print(f'backend={b} index={i} error={e}')
        sys.exit(0)
    else:
        main(src_val, mdl_val, conf=args.conf, resize=args.resize)
