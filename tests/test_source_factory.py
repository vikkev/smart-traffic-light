from unittest.mock import MagicMock

import cv2

from main import (
    abrir_fonte,
    aplicar_modo,
    reiniciar_video_se_eof,
    resolver_fonte,
)
from src.config import VIDEO_DEMO_PADRAO


def test_resolver_fonte_prefere_fonte_explicitamente_passada():
    resolved_source, resolved_type = resolver_fonte("rtsp://example/stream", "video", "sample.mp4")
    assert resolved_source == "rtsp://example/stream"
    assert resolved_type == "rtsp"


def test_abrir_fonte_retorna_capture_para_video_inexistente_sem_quebrar():
    cap = abrir_fonte(source_type="video", source_path="arquivo_que_nao_existe.mp4")
    assert cap is not None
    assert isinstance(cap, cv2.VideoCapture)
    cap.release()


def test_aplicar_modo_camera_mantem_source_zero():
    assert aplicar_modo("camera", "0") == "0"
    assert aplicar_modo("camera", None) == "0"


def test_aplicar_modo_demo_usa_video_padrao():
    assert aplicar_modo("demo", "0") == VIDEO_DEMO_PADRAO
    assert aplicar_modo("demo", None) == VIDEO_DEMO_PADRAO
    src, tipo = resolver_fonte(aplicar_modo("demo", "0"))
    assert src == VIDEO_DEMO_PADRAO
    assert tipo == "video"


def test_aplicar_modo_demo_respeita_source_explicito():
    assert aplicar_modo("demo", "outro.mp4") == "outro.mp4"
    assert aplicar_modo("demo", "1") == "1"
    src, tipo = resolver_fonte(aplicar_modo("demo", "outro.mp4"))
    assert src == "outro.mp4"
    assert tipo == "video"


def test_reiniciar_video_se_eof_chama_set_pos_frames():
    cap = MagicMock()
    cap.set.return_value = True
    assert reiniciar_video_se_eof(cap) is True
    cap.set.assert_called_once_with(cv2.CAP_PROP_POS_FRAMES, 0)


def test_reiniciar_video_se_eof_falha_retorna_false():
    cap = MagicMock()
    cap.set.side_effect = RuntimeError("fail")
    assert reiniciar_video_se_eof(cap) is False
