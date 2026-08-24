import cv2

from main import abrir_fonte, resolver_fonte


def test_resolver_fonte_prefere_fonte_explicitamente_passada():
    resolved_source, resolved_type = resolver_fonte("rtsp://example/stream", "video", "sample.mp4")
    assert resolved_source == "rtsp://example/stream"
    assert resolved_type == "rtsp"


def test_abrir_fonte_retorna_capture_para_video_inexistente_sem_quebrar():
    cap = abrir_fonte(source_type="video", source_path="arquivo_que_nao_existe.mp4")
    assert cap is not None
    assert isinstance(cap, cv2.VideoCapture)
    cap.release()
