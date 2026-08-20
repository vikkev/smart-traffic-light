import os
import sys
import pytest

# Ensure project root is on sys.path for imports during pytest collection
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import atualizar_contagem


def make_det(y_center, track_id=1, cls_id=2, box_h=20, box_w=10):
    # construct bbox (x1,y1,x2,y2,track_id,cls_id) from center y
    x_center = 50
    x1 = x_center - box_w/2
    x2 = x_center + box_w/2
    y1 = y_center - box_h/2
    y2 = y_center + box_h/2
    return (x1, y1, x2, y2, track_id, cls_id)


def test_single_crossing_counts_once():
    y_linha = 100
    estado = {}
    contagem = {}

    # frame 1: object above the line
    dets = [make_det(80, track_id=1, cls_id=0)]  # person id 0
    atualizar_contagem(dets, y_linha, estado, contagem)
    assert contagem == {}

    # frame 2: object crosses below the line
    dets = [make_det(120, track_id=1, cls_id=0)]
    atualizar_contagem(dets, y_linha, estado, contagem)
    assert contagem.get('person', 0) == 1

    # frame 3: same object remains below, shouldn't increment
    dets = [make_det(130, track_id=1, cls_id=0)]
    atualizar_contagem(dets, y_linha, estado, contagem)
    assert contagem.get('person', 0) == 1


def test_multiple_crossings_count_each_time():
    y_linha = 100
    estado = {}
    contagem = {}

    # above -> below -> above -> below (3 crossings)
    seq = [80, 120, 70, 140]
    for i, y in enumerate(seq):
        dets = [make_det(y, track_id=2, cls_id=2)]  # car id 2
        atualizar_contagem(dets, y_linha, estado, contagem)

    # crossings occurred at transitions: 80->120, 120->70, 70->140 => 3 crossings
    assert contagem.get('car', 0) == 3


def test_multi_object_and_classes():
    y_linha = 100
    estado = {}
    contagem = {}

    dets = [
        make_det(120, track_id=1, cls_id=2),  # car below
        make_det(120, track_id=2, cls_id=5),  # bus below
        make_det(80, track_id=3, cls_id=0),   # person above
    ]
    # Initialize states (no counts expected)
    atualizar_contagem(dets, y_linha, estado, contagem)
    assert contagem == {}

    # Now all three cross to other side
    dets = [
        make_det(80, track_id=1, cls_id=2),
        make_det(80, track_id=2, cls_id=5),
        make_det(120, track_id=3, cls_id=0),
    ]
    atualizar_contagem(dets, y_linha, estado, contagem)
    # Each should have been counted once
    assert contagem.get('car', 0) == 1
    assert contagem.get('bus', 0) == 1
    assert contagem.get('person', 0) == 1


def test_unknown_classes_are_ignored_for_counting():
    y_linha = 100
    estado = {}
    contagem = {}

    dets = [
        make_det(80, track_id=10, cls_id=99),
        make_det(120, track_id=10, cls_id=99),
    ]

    atualizar_contagem(dets, y_linha, estado, contagem)

    assert contagem == {}
