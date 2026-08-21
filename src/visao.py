from src.config import ID_PARA_NOME


def extrair_deteccoes(results):
    import numpy as np

    if results.boxes is None or results.boxes.id is None:
        return []
    caixas = results.boxes.xyxy.cpu().numpy()
    ids = results.boxes.id.cpu().numpy().astype(int)
    classes = results.boxes.cls.cpu().numpy().astype(int)
    return list(zip(caixas[:, 0], caixas[:, 1], caixas[:, 2], caixas[:, 3], ids, classes))


def atualizar_contagem(deteccoes, y_linha, estado_anterior, contagem):
    # track_id só da sessão atual; sem identidade pessoal.
    for x1, y1, x2, y2, id_rastreio, id_classe in deteccoes:
        nome = ID_PARA_NOME.get(id_classe)
        if nome is None:
            continue
        # ponytail: pé da bbox (y2); centro sobe com braço/capacete e gera falso cruzamento
        ancora_y = y2
        lado_atual = -1 if ancora_y < y_linha else 1
        lado_anterior = estado_anterior.get(id_rastreio)
        if lado_anterior is not None and lado_atual != lado_anterior:
            contagem[nome] = contagem.get(nome, 0) + 1
        estado_anterior[id_rastreio] = lado_atual
