# Sistema de Monitoramento Inteligente de Cruzamentos (TCC)

Este repositório contém um protótipo para detecção e contagem de veículos/pedestres
usando YOLOv8 com lógica de contagem por travessia de linha.

Pré-requisitos mínimos

- Python 3.10+ (testado com 3.12)
- (Opcional) GPU e drivers para aceleração de inferência

Instalação (dependências leves para desenvolvimento e testes)

```bash
python -m venv .venv
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Observação: o pacote `ultralytics` (YOLOv8) não está listado em `requirements.txt` por
ser opcional durante o desenvolvimento de testes unitários. Para rodar o pipeline completo,
instale `ultralytics`:

```bash
pip install ultralytics
```

Como executar o sistema

```bash
python main.py --source 0 --model yolov8s.pt
```

- `--source`: ID da câmera, caminho para um arquivo de vídeo ou URL RTSP.
- `--model`: caminho para um arquivo `.pt` do modelo YOLOv8.

Testes

```bash
pytest -q
```

Estrutura principal

- `main.py`: código principal do pipeline (detecção, tracking, contagem, overlay).
- `tests/`: testes unitários (ex.: `test_traffic_manager.py`).
- `requirements.txt`: dependências para testes e desenvolvimento.

Notas

- Muitas variáveis e funções agora estão em português para facilitar a leitura.
- Se quiser, posso traduzir comentários adicionais, renomear mais variáveis locais ou
  fornecer instruções para execução com GPU.
