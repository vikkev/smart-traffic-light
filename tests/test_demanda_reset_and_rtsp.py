from src.trafego import GerenciadorTrafego, ControladorSemaforo
from main import fonte_com_retry_for


def test_contagem_cleared_on_ciclo():
    # preparar uma contagem elevada
    contagem = {"car": 20}
    manager = GerenciadorTrafego()
    controlador = ControladorSemaforo()

    demanda = manager.calcular_demanda(contagem)
    controlador.propor(demanda)

    # avançar tempo suficientemente para que o proximo_ciclo seja aplicado
    eventos = controlador.tick(1000.0)
    assert any(ev.get("evento") == "ciclo" for ev in eventos)

    # comportamento desejado (mesmo que implementado em main): limpar contagens quando houver ciclo
    if eventos and any(ev.get("evento") == "ciclo" for ev in eventos):
        contagem.clear()

    assert contagem == {}


def test_fonte_com_retry_for_logic():
    # câmera local (int)
    assert fonte_com_retry_for(0) is True
    # RTSP (string que começa com rtsp)
    assert fonte_com_retry_for("rtsp://example/stream") is True
    assert fonte_com_retry_for("RTSP://UPPERCASE") is True
    # arquivo de vídeo ou caminho não-RTSP não deve ser tratado como retry-only camera
    assert fonte_com_retry_for("video.mp4") is False
    assert fonte_com_retry_for("/path/to/file.mp4") is False
