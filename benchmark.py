#!/usr/bin/env python3
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np


def detectar_dispositivo(forcar_cpu=False):
    if forcar_cpu:
        return "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            return 0
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def benchmark(modelo, video, frames=300, forcar_cpu=False):
    from ultralytics import YOLO

    dispositivo = detectar_dispositivo(forcar_cpu)
    model = YOLO(modelo)
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        print(f"ERRO: vídeo não encontrado: {video}")
        sys.exit(1)

    tempos = []
    for _ in range(frames):
        ok, frame = cap.read()
        if not ok:
            break
        t0 = time.perf_counter()
        model.track(frame, persist=True, conf=0.4, verbose=False, device=dispositivo)
        tempos.append((time.perf_counter() - t0) * 1000)

    cap.release()
    if not tempos:
        print(f"ERRO: nenhum frame processado para {modelo}")
        return

    arr = np.array(tempos)
    print(
        f"{Path(modelo).name} | {dispositivo} | {len(tempos)} frames | "
        f"FPS {1000 / arr.mean():.1f} | lat {arr.mean():.1f} ms | p95 {np.percentile(arr, 95):.1f} ms"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark YOLO standalone")
    parser.add_argument("--video", default="samples/teste_curto.mp4")
    parser.add_argument("--models", nargs="+", default=["yolov8s.pt"])
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if not Path(args.video).exists():
        print(f"ERRO: vídeo não encontrado: {args.video}")
        sys.exit(1)

    for modelo in args.models:
        if not Path(modelo).exists():
            print(f"ERRO: modelo não encontrado: {modelo}")
            sys.exit(1)
        benchmark(modelo, args.video, args.frames, args.force_cpu)
