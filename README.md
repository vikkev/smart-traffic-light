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
| Cruzamento no SUMO (plano fixo e atuado) | Presente |
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
- `simulacao/`: cruzamento de quatro braços no SUMO, com plano fixo e controlador atuado

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
matplotlib
eclipse-sumo
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

A demanda que entra no Webster é uma **taxa** (equivalentes por minuto na janela do ciclo), não a contagem acumulada. O status mostrado na câmera (Tranquilo / Movimentado / Prioridade) continua usando a pontuação da janela.

Havia um erro nessa conta: com taxa a partir de 14 equivalentes/min os dois verdes batiam no teto de 60 s, e o eixo mais cheio deixava de ter prioridade. Agora, se o ciclo estoura o teto, os dois verdes encolhem juntos e a proporção se mantém.

---

## Simulação do cruzamento (SUMO)

O desenho do semáforo sobre o vídeo não faz o carro parar. Esta parte roda um cruzamento de quatro braços no [SUMO](https://eclipse.dev/sumo/), controlado pelo Python (TraCI).

- Braços norte, sul, leste e oeste. Norte/sul é a fase A (a rua da câmera). Leste/oeste é a fase B.
- Cada aproximação segue reto ou dobra à direita. O sinal da aproximação fica verde, amarelo ou vermelho junto.
- No vermelho o carro para; no verde ele atravessa.
- Se o vermelho tem veículo e não há ninguém nos últimos 70 m do eixo que está verde, o atuado troca — em vez de deixar o carro esperando numa rua vazia (madrugada, começo da manhã).
- Se o vermelho não tem ninguém, o verde permanece. Não fica abrindo e fechando à toa.

Há dois controladores:

| Controle | O que faz |
|---|---|
| `fixo` | Relógio: 30 s de verde, 3 s de amarelo e 1 s de tudo vermelho, igual nos dois eixos, em todo cenário |
| `atuado` | Verde mínimo de 8 s, amarelo de 3 s, tudo vermelho de 1 s. O verde máximo sai do Webster (a faixa escoa cerca de 1800 veic/h) e é atualizado com as chegadas medidas. Depois do mínimo, se o verde fica vazio por 2 s e o outro lado tem veículo, encerra (gap-out). Com os dois lados cheios, o máximo impede que um eixo segure o outro |

### Cenários

Semente 42. Duração padrão 900 s. O número é veículos por hora **em cada aproximação**.

| Cenário | Norte e sul | Leste e oeste |
|---|---:|---:|
| Madrugada | 30 | 30 |
| Médio | 300 | 300 |
| Pico | 650 | 650 |
| Desbalanceado | 900 | 90 |

O cenário `visao` repete a madrugada, mas a aproximação norte não usa esse fluxo: os carros nascem de um CSV de contagem (a ponte com a visão).

### Instalar o SUMO no Windows

Com o ambiente do projeto ativo:

```bat
pip install -r requirements.txt
```

O pacote `eclipse-sumo` já traz o `sumo`, o `sumo-gui`, o `netconvert` e as bibliotecas Python. Confira:

```bat
sumo --version
```

Se o `python -m simulacao.demo` não abrir a janela, use o instalador oficial:

1. Baixe em https://eclipse.dev/sumo/docs/Downloads.php
2. Na instalação, marque a opção de colocar o SUMO no PATH
3. Crie a variável `SUMO_HOME` apontando para a pasta do SUMO (a que contém `bin` e `tools`)
4. Feche e abra o terminal e rode `sumo --version`

Os experimentos sem janela funcionam com o pacote pip. Não é preciso instalar os dois ao mesmo tempo: se `SUMO_HOME` existir, o programa usa essa instalação.

A rede já vem gerada (`simulacao/malha/cruzamento.net.xml`), junto com os fontes (`.nod`, `.edg`, `.con`, `.tll`). Para reconstruir:

```bat
python -m simulacao.gerar_rede
```

### Como rodar

Na pasta do projeto:

```bat
python -m simulacao.experimentos
python -m simulacao.demo --cenario madrugada --controle atuado
python -m simulacao.demo --cenario desbalanceado --controle fixo
python -m simulacao.demo --cenario medio --controle atuado --duracao 600 --atraso 150
```

`experimentos` roda os quatro cenários e a ponte da visão, nos dois controladores, sem janela. `demo` abre o sumo-gui.

### Ponte com a visão

No protótipo da câmera, cada ciclo pode ser gravado:

```bat
python main.py --mode demo --exportar-demanda logs/demanda_visao.csv
```

O CSV tem `inicio_s,fim_s,car,motorcycle,bus,truck,person` (vírgula ou ponto e vírgula). Pessoa não vira veículo. Carro e moto entram como carro; ônibus e caminhão entram como um veículo longo, todos na aproximação norte. Há um exemplo em `simulacao/dados/contagem_visao_exemplo.csv`.

```bat
python -m simulacao.demo --cenario madrugada --controle atuado --demanda-visao simulacao/dados/contagem_visao_exemplo.csv
```

### Como ler os resultados

Os arquivos ficam em `simulacao/resultados/`.

- `resumo.csv` — uma linha por cenário e controlador
- `comparacao.png`, `verdes.png`, `filas_madrugada.png`
- `serie_<cenario>_<controle>.csv` — fila e fase a cada segundo

| Coluna | Significado |
|---|---|
| `espera_media_s` / `espera_max_s` | Tempo parado (velocidade abaixo de 0,1 m/s), média e máximo por veículo. Quem não parou entra com zero |
| `fila_media_veic` / `fila_max_veic` | Veículos parados nas quatro aproximações, ao longo da simulação |
| `throughput_veic_min` | Veículos que terminaram a travessia, por minuto |
| `paradas_desnecessarias` | Vezes em que um veículo parou no vermelho enquanto não havia ninguém nos 70 m finais do eixo que estava verde |
| `tempo_verde_a_s` / `tempo_verde_b_s` | Quanto tempo cada eixo ficou verde |

Números abaixo: SUMO 1.28, semente 42, 900 s. O arquivo `resumo.csv` é a fonte exata (decimal com ponto, para planilha e para o programa). Na tabela daqui o decimal está com vírgula.

| Cenário | Controle | Espera média (s) | Espera máx. (s) | Fila média | Fila máx. | Vazão (veíc/min) | Paradas desnecessárias |
|---|---|---:|---:|---:|---:|---:|---:|
| Madrugada | Fixo | 6,72 | 26 | 0,24 | 2 | 2,00 | 12 |
| Madrugada | Atuado | 2,94 | 13 | 0,10 | 3 | 2,13 | 5 |
| Médio | Fixo | 9,37 | 36 | 3,12 | 7 | 18,80 | 218 |
| Médio | Atuado | 3,33 | 15 | 1,11 | 4 | 19,00 | 98 |
| Pico | Fixo | 11,28 | 36 | 8,17 | 16 | 40,33 | 16 |
| Pico | Atuado | 10,87 | 35 | 7,88 | 15 | 40,27 | 2 |
| Desbalanceado | Fixo | 20,28 | 46 | 11,19 | 31 | 29,80 | 365 |
| Desbalanceado | Atuado | 3,76 | 36 | 2,09 | 9 | 30,93 | 80 |
| Visão (norte) | Fixo | 6,29 | 35 | 0,25 | 3 | 2,20 | 13 |
| Visão (norte) | Atuado | 3,06 | 13 | 0,12 | 3 | 2,27 | 6 |

No pico os dois ficam parecidos: os dois eixos estão cheios e o verde máximo do Webster fica perto dos 30 s do plano fixo. A diferença grande aparece na madrugada, no fluxo médio e, sobretudo, quando um eixo é bem mais carregado que o outro — o fixo continua dando 30 s para a rua vazia.

![Comparação fixo e atuado](simulacao/resultados/comparacao.png)

![Tempo de verde por eixo](simulacao/resultados/verdes.png)

![Fila na madrugada](simulacao/resultados/filas_madrugada.png)

### Limitações da simulação

- Não há pedestre nem fase de travessia. A contagem de pessoas do CSV é ignorada na hora de criar veículos.
- Não há conversão à esquerda. O cruzamento opera em duas fases (norte/sul e leste/oeste), com reto e direita.
- É um cruzamento só, não a malha da cidade, e não substitui um controlador homologado.
- A câmera não entra ao vivo no SUMO. A ligação é o arquivo de contagem.

---

## Testes

Para rodar a suíte atual:

```bash
pytest -q
```

Os testes cobrem:

- contagem por linha
- demanda, taxa por minuto e o Webster (inclusive o caso em que a taxa passa de 14)
- verde mínimo, gap-out, verde máximo e a garantia de que o eixo que espera recebe verde, sem abrir o SUMO
- comportamento do painel
- fontes RTSP e retry
- suporte a múltiplas entradas

Se o SUMO estiver instalado, um teste curto também confere que o carro para no vermelho e atravessa no verde.

---

## Limitações conhecidas

- O sistema é um protótipo de laboratório e não substitui um controlador de semáforo real.
- A simulação não tem pedestre nem conversão à esquerda, e a visão só alimenta o SUMO por arquivo de contagem.
- O contador depende do rastreio por frame e pode haver reidentificação em casos de perda de tracking.
- O uso de `cv2.imshow` exige uma interface gráfica disponível.
- A redução de resolução melhora desempenho em CPU, mas pode reduzir precisão da detecção.

---

## Observação final

Este projeto foi desenvolvido para validar a viabilidade de um sistema inteligente de monitoramento e controle de tráfego em ambiente acadêmico. A lógica atual cobre detecção, contagem, estimativa de demanda, HUD visual e simulação de semáforo, mantendo a implementação simples e clara para estudo e extensão.

## Atualização de manutenção

Esta versão do repositório inclui a padronização da configuração e a validação de múltiplas fontes de entrada, com suporte explícito a webcam, RTSP e vídeo gravado. O README foi revisado para refletir o estado real do projeto e manter a documentação alinhada com a implementação atual.

