import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.visao import atualizar_contagem


def make_det(y_center, track_id=1, cls_id=2, box_h=20, box_w=10):
    x_center = 50
    x1 = x_center - box_w / 2
    x2 = x_center + box_w / 2
    y1 = y_center - box_h / 2
    y2 = y_center + box_h / 2
    return (x1, y1, x2, y2, track_id, cls_id)


def make_bbox(y1, y2, track_id=1, cls_id=0):
    return (40.0, float(y1), 60.0, float(y2), track_id, cls_id)


def test_single_crossing_counts_once():
    y_linha = 100
    estado = {}
    contagem = {}
    atualizar_contagem([make_det(80, track_id=1, cls_id=0)], y_linha, estado, contagem)
    assert contagem == {}
    atualizar_contagem([make_det(120, track_id=1, cls_id=0)], y_linha, estado, contagem)
    assert contagem.get("person", 0) == 1
    atualizar_contagem([make_det(130, track_id=1, cls_id=0)], y_linha, estado, contagem)
    assert contagem.get("person", 0) == 1


def test_multiple_crossings_count_each_time():
    y_linha = 100
    estado = {}
    contagem = {}
    for y in (80, 120, 70, 140):
        atualizar_contagem([make_det(y, track_id=2, cls_id=2)], y_linha, estado, contagem)
    assert contagem.get("car", 0) == 3


def test_unknown_classes_are_ignored_for_counting():
    y_linha = 100
    estado = {}
    contagem = {}
    atualizar_contagem([make_det(80, track_id=10, cls_id=99)], y_linha, estado, contagem)
    atualizar_contagem([make_det(120, track_id=10, cls_id=99)], y_linha, estado, contagem)
    assert contagem == {}


def test_braco_para_cima_nao_conta():
    """y2 fixo abaixo da linha; y1 sobe (caixa cresce) — não cruza."""
    y_linha = 100
    estado = {}
    contagem = {}
    atualizar_contagem([make_bbox(80, 140, track_id=1)], y_linha, estado, contagem)
    assert contagem == {}
    atualizar_contagem([make_bbox(20, 140, track_id=1)], y_linha, estado, contagem)
    assert contagem.get("person", 0) == 0


def test_pe_cruzando_linha_conta_uma_vez():
    y_linha = 100
    estado = {}
    contagem = {}
    atualizar_contagem([make_bbox(50, 90, track_id=7)], y_linha, estado, contagem)
    assert contagem == {}
    atualizar_contagem([make_bbox(50, 120, track_id=7)], y_linha, estado, contagem)
    assert contagem.get("person", 0) == 1
