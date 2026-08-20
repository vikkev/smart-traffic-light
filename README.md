# Sistema Inteligente de Monitoramento de Cruzamentos

<p align="center"><strong>Smart Traffic Light v2.0</strong></p>

<div align="center">

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF.svg)](https://github.com/ultralytics/ultralytics)
[![Licença](https://img.shields.io/badge/License-Apache-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Status](https://img.shields.io/badge/Status-Produção-brightgreen.svg)]()

<h4>Detecção, tracking e contagem de veículos e pedestres em tempo real com classificação inteligente de demanda de tráfego usando YOLOv8.</h4>

<p>Versão otimizada — Marília, 2026</p>

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

Este é um protótipo inteligente para monitorar cruzamentos de forma contínua e eficiente. A ideia é simples: usar câmeras e **visão computacional** (YOLOv8) para entender o fluxo real de veículos nos cruzamentos, detectar padrões de tráfego (normal, congestionado ou crítico) e ajustar os semáforos automaticamente. Funciona com webcam, vídeo ou câmeras IP via RTSP, e tudo foi desenvolvido pensando em robustez e facilidade de teste.

## Identificação técnica e LGPD

A identificação usada neste sistema é exclusivamente técnica e temporária para acompanhar objetos entre frames, validar cruzamento de linha e evitar contagem duplicada. Não há reconhecimento facial, OCR de placas, identificação de proprietários, perfis individuais de veículos ou armazenamento de dados pessoais.

- Processamento local, sem envio para APIs ou serviços de terceiros.
- Nenhum rosto, placa, vídeo ou imagem é armazenado.
- Os resultados são agregados em estatísticas de tráfego, por exemplo: 14:30 → 18 carros, 4 motos, 2 caminhões.
- A finalidade é análise e melhoria do fluxo de tráfego, sem identificação individual.

---

## Principais funcionalidades

| Funcionalidade | Descrição |
|---|---|
| **Detecção + Tracking** | YOLOv8 com rastreamento persistente de objetos |
| **Contagem inteligente** | Line-crossing com deduplicação de frames repetidos |
| **Classificação de demanda** | NORMAL / BUSY / PRIORIDADE baseado em pesos por classe |
| **Múltiplas fontes** | Webcam, vídeo local, streams RTSP |
| **Probe de câmeras** | Auto-detecção de backends (DSHOW/MSMF/ANY no Windows) |
| **Performance** | Suporte a redimensionamento de imagem (`--resize`) para CPU |
| **Fullscreen adaptável** | Toggle por tecla `f` com fallback F11 |
| **Testes unitários** | Cobertura pytest para lógica de demanda e line-crossing |

### Sistema de demanda ponderada

O algoritmo calcula uma pontuação baseada no volume e tipo de veículo:

```
Pesos por classe:
  • Pedestre     → 0.5
  • Carro        → 1.0
  • Motocicleta  → 1.0
  • Ônibus       → 3.0
  • Caminhão     → 3.0

Classificação de status:
  • Pontuação > 15  → PRIORIDADE
  • Pontuação > 8   → BUSY
  • Pontuação ≤ 8   → NORMAL
```

---

## Pré-requisitos

- **Python 3.10+** (foi testado até a versão 3.12)
- **GPU é ideal** para rodar tudo rápido, mas não é obrigatório — CPU também funciona bem usando `--resize`

### Dependências

| Para quê | Pacotes |
|----------|---------|
| **Se quer testar tudo** | `pytest`, `numpy`, `opencv-python` |
| **Para rodar o sistema** | `ultralytics`, `torch`, `torchvision` |

---

## Instalação rápida

### 1. Clonar o repositório

```sh
git clone https://github.com/vikkev/smart-traffic-light
cd smart-traffic-light
```

### 2. Criar um ambiente isolado (recomendado para não bagunçar suas dependências)

```sh
python -m venv venv
# Se você está no Windows
venv\Scripts\activate
# Se você está no macOS ou Linux
source venv/bin/activate
```

### 3. Instalar dependências

```sh
pip install -r requirements.txt
```

Para GPU (CUDA):

```sh
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install ultralytics
```

---

## Como usar

### Usar a webcam (o mais simples)

```sh
python main.py --source 0
```

Não funcionou? Tente os IDs 1, 2 etc:

```sh
python main.py --source 1
```

### Processar um vídeo gravado

```sh
python main.py --source caminho/para/video.mp4
```

### Conectar a uma câmera IP remota (RTSP)

```sh
python main.py --source "rtsp://usuario:senha@192.168.1.100:554/stream"
```

### Testar quais câmeras o seu PC reconhece

```sh
python main.py --probe
```

Isso lista todos os backends disponíveis (DSHOW, MSMF, ANY) e tenta conectar a câmeras 0–5.

### Ajustar o limiar de confiança (ser mais rigoroso ou permissivo)

```sh
python main.py --source 0 --conf 0.5
```

Quanto maior o valor, mais rigoroso. Tente 0.3 se quer pegar tudo, ou 0.7 se quer só as detecções muito seguras.

### Otimizar para rodar em CPU (mais lento, mas possível)

```sh
python main.py --source video.mp4 --resize 640 --model yolov8s.pt
```

**Dica:** `--resize 640` reduz a imagem para 640 pixels na maior dimensão. Fica mais rápido, mas menos preciso.

### Usar seu próprio modelo treinado

```sh
python main.py --source 0 --model /caminho/para/seu_modelo.pt
```

---

## Opções de linha de comando

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| `--source` | `0` | ID da câmera, caminho de vídeo ou URL RTSP |
| `--model` | `yolov8m.pt` | Modelo local ou nome que Ultralytics resolve |
| `--conf` | `0.5` | Limiar de confiança (0–1) |
| `--resize` | `None` | Redimensiona a maior dimensão (ex: 640) |
| `--probe` | `False` | Testa backends e índices de câmera |

---

## Testes

### Rodar todos os testes

```sh
pytest tests/ -v
```

Isso executa toda a suite de testes e mostra o resultado.

### O que está testado

| Arquivo | O que valida |
|---------|-----------|
| `test_traffic_manager.py` | Se o cálculo de demanda e classificação funcionam certo |
| `test_line_crossing.py` | Se a contagem de veículos por line-crossing está correta |

Se quer rodar um teste específico:

```sh
pytest tests/test_traffic_manager.py::test_demand_calculation -v
```

---

## Melhorias nesta versão

| Correção | Impacto |
|----------|---------|
| **Leitura contínua de frames** | Previne congelamento; `cap.read()` em cada iteração |
| **Fullscreen adaptável** | Toggle por `f` com fallback F11 |
| **Opção `--resize`** | Acelera inferência em CPU |
| **Probe de backends** | Auto-detecção de câmeras no Windows |
| **Cleanup robusto** | Proteção contra exceções secundárias (release/destroyAllWindows) |
| **Contagem inteligente** | Rastreamento de estado anterior; elimina double-counting de frames repetidos |

---

## Limitações conhecidas

**Re-ID persistente não implementado:** Se o tracker perde e reatribui `track_id`, o evento será contado como novo. Isso é aceitável para contagem de eventos, mas persistência real requer um modelo adicional.

**cv2.imshow requer interface gráfica:** Não funciona em ambientes headless (sem X/Wayland).

**Trade-off em `--resize`:** Reduz latência mas pode diminuir a precisão das caixas de detecção.

---

## Quer contribuir? (Guia para TCC)

1. **Clone ou faça um fork** do repositório
2. **Crie uma branch** com um nome descritivo: `git checkout -b feat/nova-funcionalidade`
3. **Faça commits pequenos e claros**:
   ```sh
   git commit -m "feat: adiciona detecção de pedestres"
   git commit -m "fix: corrige contagem duplicada em line-crossing"
   ```
4. **Configure seu nome** (importante para aparecer no histórico do TCC):
   ```sh
   git config user.name "Seu Nome"
   git config user.email "seu.email@unesp.br"
   ```
5. **Faça um push** e abra um Pull Request explicando a mudança

---

## Estrutura de arquivos

```
smart-traffic-light/
├── main.py                          # Entry point do pipeline
├── requirements.txt                 # Dependências
├── tests/
│   ├── test_traffic_manager.py     # Testes de demanda
│   └── test_line_crossing.py       # Testes de contagem
├── src/
│   ├── traffic_manager.py          # Lógica de demanda e status
│   ├── line_crossing.py            # Detecção de travessia
│   └── utils.py                    # Funções auxiliares
└── README.md
```

---

## Conformidade e segurança

### LGPD (Lei nº 13.709/2018)

| Princípio | Implementação |
|-----------|---------------|
| **Minimização de dados** | Apenas dados de tráfego; sem identificação de pessoas |
| **Finalidade específica** | Imagens utilizadas exclusivamente para gestão de tráfego |
| **Segurança da informação** | Dados protegidos por criptografia e controle de acesso |

---

## Performance esperada

| Métrica | CPU | GPU (CUDA) |
|--------|-----|-----------|
| **Latência (YOLOv8m)** | ~100–150ms | ~15–30ms |
| **FPS** | 6–10 | 30–60 |
| **Memória** | ~800MB | ~2GB |

*Valores aproximados com vídeo 1080p; ajuste com `--resize` ou `--model yolov8s.pt` conforme necessário.*

---

## Licença

Este projeto está licenciado sob **Apache License 2.0**. Consulte [LICENSE](./LICENSE) para detalhes.

---

## Dúvidas? Sugestões? Encontrou um bug?

Abra uma [Issue](https://github.com/vikkev/smart-traffic-light/issues) no repositório. A gente responde!

**Quem está por trás:**
- Lucas Valente, Vinicius Ibaraki, João Pedro Koga
- Orientado por Prof. Claudio de Jesus Junior
- Bacharelado em Ciência da Computação — Marília, 2026

---

<div align="center">

**Desenvolvido em Marília, SP**

<<<<<<< HEAD
</div>
=======
</div>
>>>>>>> 1404883 (adequacao-LGPD)
