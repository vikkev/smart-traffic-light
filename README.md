# Sistema Inteligente de Monitoramento de Cruzamentos

<p align="center"><strong>Smart Traffic Light v2.0</strong></p>

<div align="center">

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF.svg)](https://github.com/ultralytics/ultralytics)
[![Licença](https://img.shields.io/badge/License-Apache-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Status](https://img.shields.io/badge/Status-Protótipo-brightgreen.svg)]()

<h4>Protótipo de monitoramento de cruzamentos com visão computacional, contagem por linha e simulação de semáforo.</h4>

<p>Versão de laboratório — Marília, 2026</p>

</div>

---

## Integrantes

| Nome |
|------|
| Lucas Valente |
| Vinicius Ibaraki |
| João Pedro Koga |

**Orientador:** Prof. Claudio de Jesus Junior

---

## Sobre este projeto

Este repositório reúne um protótipo para monitorar fluxos de tráfego em interseções usando visão computacional. O sistema captura frames de uma câmera, vídeo local ou stream RTSP, detecta objetos com YOLOv8, conta cruzamentos por linha e estima demanda de tráfego para simular decisões de semáforo.

O objetivo principal é validar a lógica de detecção, contagem, demanda e controle em laboratório, sem transformar esse código em um sistema de produção instalado na rua.

---

## Identificação técnica e LGPD

A identificação usada neste sistema é estritamente técnica e temporária, com foco em rastreamento de objeto entre frames para validar cruzamento de linha e evitar contagem duplicada.

- Não há reconhecimento facial.
- Não há OCR de placas.
- Não há armazenamento de imagens ou vídeos do fluxo.
- Não há perfil individual de veículo ou pessoa.
- Os dados são agregados por contagem e demanda, sem identificação pessoal.

---

## Funcionalidades atuais

| Funcionalidade | Estado |
|---|---|
| Detecção com YOLOv8 | Presente |
| Tracking por objeto | Presente |
| Contagem por linha | Presente |
| Simulação de semáforo por Webster | Presente |
| Webcam, vídeo local e RTSP | Presente |
| Configuração de fonte por arquivo/CLI | Presente |
| Redimensionamento para otimizar CPU | Presente |
| HUD sobreposto na imagem | Presente |
| Log de métricas em JSONL | Presente |
| Testes automatizados | Presente |

---

## Arquitetura principal

O projeto está organizado em módulos simples:

- `main.py`: ponto de execução principal e abertura da fonte
- `src/config.py`: constantes e parâmetros do sistema
- `src/visao.py`: extração de detecções e contagem por linha
- `src/trafego.py`: demanda, status e lógica do semáforo
- `src/ui/painel.py`: desenho do HUD sobre a imagem
- `src/metricas.py`: escrita de métricas em arquivo JSONL

---

## Requisitos

- Python 3.10+
- OpenCV
- NumPy
- pytest
- Ultralytics opcional para execução completa com YOLOv8

### Dependências reais do projeto

O arquivo [requirements.txt](requirements.txt) está definido como mínimo para testes e execução base:

```txt
pytest
numpy
opencv-python
# ultralytics is optional for runtime; install when running full pipeline
# ultralytics
```

Se a intenção for rodar o pipeline completo com YOLOv8, a instalação do pacote `ultralytics` é necessária no ambiente de execução.

---

## Instalação

```bash
git clone https://github.com/vikkev/smart-traffic-light
cd smart-traffic-light
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
pip install -r requirements.txt
```

Se for usar YOLOv8 completo:

```bash
pip install ultralytics
```

---

## Como usar

### Modos rápidos (recomendado)

```bash
# Câmera ao vivo (padrão)
python main.py --mode camera

# Vídeo demo em loop (samples/semaforo.mp4) — teste/ilustração
python main.py --mode demo --resize 640
```

`--source` sobrescreve o preset quando diferente de `0` (ex.: outro arquivo ou índice de câmera).

### Webcam local

```bash
python main.py --source 0
```

### Vídeo gravado

```bash
python main.py --source samples/semaforo.mp4
# ou qualquer arquivo:
python main.py --source caminho/para/video.mp4
```

Arquivos de vídeo reiniciam do início ao terminar (loop), sem zerar contagem/Webster.

### Linha de contagem (auto)

No primeiro frame o sistema tenta detectar a **faixa de pedestres** e posiciona a linha amarela **perpendicular** às listras (corta o fluxo). Sem configuração.

| Tecla / flag | Ação |
|---|---|
| **A** | Nova auto-calibração |
| **L** | Calibração manual (2 cliques); Esc cancela |
| **D** / `--debug-linha` | Overlay: segmentos Hough, cluster e linha final |

Se a auto falhar: preset do demo (`samples/semaforo.mp4`) ou linha horizontal de reserva. Piloto em moto não é contado como pedestre (contenção bbox).

### Stream RTSP

```bash
python main.py --source "rtsp://usuario:senha@192.168.1.100:554/stream"
```

### Configuração por tipo de fonte

O projeto também aceita configuração explícita em código e por CLI:

```bash
python main.py --source-type webcam --source-path 0
python main.py --source-type video --source-path video.mp4
python main.py --source-type rtsp --source-path "rtsp://..."
```

### Testar câmeras disponíveis

```bash
python main.py --probe
```

### Ajustar limiar de confiança

```bash
python main.py --source 0 --conf 0.4
```

### Reduzir resolução para otimizar CPU

```bash
python main.py --source video.mp4 --resize 640
```

### Limitar quantidade de frames para debug

```bash
python main.py --source 0 --max-frames 50
```

---

## Opções de linha de comando

| Opção | Padrão | Descrição |
|---|---|---|
| `--mode` | `camera` | Preset: `camera` (webcam) ou `demo` (`samples/semaforo.mp4` em loop) |
| `--source` | `0` | ID da câmera, caminho de vídeo ou URL RTSP (sobrescreve o preset se ≠ `0`) |
| `--source-type` | `None` | Tipo da fonte: `webcam`, `rtsp` ou `video` |
| `--source-path` | `None` | Caminho ou endpoint da fonte |
| `--model` | `yolov8s.pt` | Modelo YOLOv8 |
| `--conf` | `None` | Limiar de confiança |
| `--resize` | `None` | Reduz a maior dimensão para otimizar CPU |
| `--probe` | `False` | Explora câmeras e backends disponíveis |
| `--log-path` | `logs/metricas.jsonl` | Caminho do arquivo de métricas |
| `--sem-log-metricas` | `False` | Desabilita a gravação de métricas |
| `--max-frames` | `None` | Processa apenas N frames em modo debug |
| `--debug-linha` | `False` | Overlay de debug da auto-calibração da linha |
| `--force-cpu` | `False` | Força CPU mesmo com GPU disponível |

---

## Sistema de demanda e semáforo

O sistema calcula uma demanda ponderada com base nos tipos de objetos detectados. Essa demanda influencia o status do cruzamento e o tempo de verde do semáforo simulado.

### Pesos por classe

- Pessoa: 0.5
- Carro: 1.0
- Moto: 1.0
- Ônibus: 3.0
- Caminhão: 3.0

### Status possíveis

- NORMAL
- BUSY
- PRIORIDADE

O algoritmo foi implementado em [src/trafego.py](src/trafego.py) e utiliza tempos de fase baseados em lógica de Webster.

---

## Testes

Para rodar a suíte atual:

```bash
pytest -q
```

Os testes cobrem:

- contagem por linha
- demanda e reset de ciclo
- comportamento do painel
- fontes RTSP e retry
- suporte a múltiplas entradas

---

## Limitações conhecidas

- O sistema é um protótipo de laboratório e não substitui um controlador de semáforo real.
- O contador depende do rastreio por frame e pode haver reidentificação em casos de perda de tracking.
- O uso de `cv2.imshow` exige uma interface gráfica disponível.
- A redução de resolução melhora desempenho em CPU, mas pode reduzir precisão da detecção.

---

## Observação final

Este projeto foi desenvolvido para validar a viabilidade de um sistema inteligente de monitoramento e controle de tráfego em ambiente acadêmico. A lógica atual cobre detecção, contagem, estimativa de demanda, HUD visual e simulação de semáforo, mantendo a implementação simples e clara para estudo e extensão.

## Atualização de manutenção

Esta versão do repositório inclui a padronização da configuração e a validação de múltiplas fontes de entrada, com suporte explícito a webcam, RTSP e vídeo gravado. O README foi revisado para refletir o estado real do projeto e manter a documentação alinhada com a implementação atual.

