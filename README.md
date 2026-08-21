# Sistema Inteligente de Monitoramento de Cruzamentos

<p align="center"><strong>Smart Traffic Light v2.0</strong></p>

<div align="center">

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF.svg)](https://github.com/ultralytics/ultralytics)
[![Licença](https://img.shields.io/badge/License-Apache-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Status](https://img.shields.io/badge/Status-Protótipo_laboratório-yellow.svg)]()

<h4>Protótipo de laboratório: YOLOv8 + contagem de fluxo e tempos semafóricos simulados (Webster, 2 fases).</h4>

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

Protótipo de **laboratório** (TCC): câmera ou vídeo + **YOLOv8** para contar o fluxo, e um controlador **simulado** que calcula tempos de verde pelo método de Webster. Não é implantação municipal, malha semafórica nem prova de redução de crime.

Funciona com webcam, arquivo de vídeo ou RTSP. Relato do que mudou nesta etapa: [`ALTERACOES.md`](ALTERACOES.md).

### Escopo do protótipo

**Inclui**
- Detecção e classificação com **YOLOv8** (Ultralytics / PyTorch). Não usamos YOLOv3/v4 nem TensorFlow.
- Contagem por travessia de linha e status de demanda (`NORMAL` / `BUSY` / `PRIORIDADE`).
- Semáforo simulado de **2 fases**. Fase A = via da câmera. Fase B usa demanda fixa `Y_B = 0.20` porque só há uma câmera — o outro braço do cruzamento **não é medido**.
- Log de laboratório em `logs/metricas.jsonl` **somente** na troca de fase ou de ciclo (não a cada frame).

**Não inclui** (trabalho futuro / texto da monografia, não desta entrega)
- Controlador físico, 4G/5G, malha da cidade, servidor preditivo, aprendizado por reforço.
- Análise geoespacial SSP-SP/CET operacional.
- Difference-in-Differences (DiD) e metas de 12 meses da Tabela 1 da monografia (`≥20%` espera, `≥95%` detecção). O JSONL mede latência e tempos de ciclo neste protótipo; não afirma essas metas.
- Prova causal de que menos espera reduz crime.

### Constantes Webster

| Constante | Valor | Significado |
|-----------|-------|-------------|
| `L` (`TEMPO_PERDIDO`) | 8 s | 2 fases × (~3 s âmbar + 1 s all-red) |
| `TEMPO_AMARELO` | 3 s | Duração de cada âmbar |
| `Y_B` | 0.20 | Demanda fixa da fase complementar |
| `Y_A` | 0.10–0.85 | Razão da via observada (pela pontuação de demanda) |
| `Y_MAX` | 0.90 | Teto de saturação; acima disso o estado é `SOBRECARREGADO` e o ciclo não explode |
| Verde | 8–60 s | Clamp de cada fase |

Fórmula: `C = (1.5L + 5) / (1 − Y)`; `g_a = (y_a / Y)(C − L)`, depois os clamps. Demanda nova **não** corta o verde atual; entra só no **próximo** ciclo.

## Identificação técnica e LGPD

A **Lei Geral de Proteção de Dados** (LGPD, Lei nº 13.709/2018) regula o uso de dados que identifiquem uma pessoa. Este protótipo trata imagem só para **contar veículos e estimar fluxo**. Não identifica motorista, passageiro, placa nem rosto.

- Processamento local: o vídeo não é enviado a API de terceiros.
- A imagem **não é gravada**. Depois do frame, resta só número agregado (ex.: 18 carros, 4 motos).
- O `track_id` do YOLO existe só enquanto o programa roda, para não contar o mesmo objeto duas vezes. Não é cadastro de pessoa ou veículo.
- Finalidade: gestão de tráfego simulada no laboratório, não vigilância.

Quem lê o TCC sem ser da área: a câmera aqui é um **sensor de volume**, não um sistema de reconhecimento.

---

## Principais funcionalidades

| Funcionalidade | Descrição |
|---|---|
| **Detecção + Tracking** | YOLOv8 com rastreamento persistente na sessão (`persist=True`) |
| **Contagem inteligente** | Line-crossing com deduplicação de frames repetidos |
| **Classificação de demanda** | NORMAL / BUSY / PRIORIDADE baseado em pesos por classe |
| **Webster simulado** | 2 fases, recálculo só no próximo ciclo, estado `SOBRECARREGADO` |
| **Painel de resumo** | Split 65/35 (câmera + painel); tecla `I` esconde/mostra |
| **Métricas de laboratório** | JSONL na troca de fase/ciclo (`latencia_ms`, verdes, ciclo) |
| **Múltiplas fontes** | Webcam, vídeo local, streams RTSP |
| **Probe de câmeras** | Auto-detecção de backends (DSHOW/MSMF/ANY no Windows) |
| **Performance** | Suporte a redimensionamento de imagem (`--resize`) para CPU |
| **Fullscreen adaptável** | Toggle por tecla `f` com fallback F11 |
| **Testes unitários** | Demanda, contagem, Webster e `alternar_painel` |

### Tela e teclas

- Ao abrir: câmera à esquerda (~65%) + painel de resumo à direita (~35%) com semáforo visual e textos em português claro.
- **I** — esconde ou mostra o painel (câmera continua rodando; com painel oculto fica tela cheia).
- **Q** ou **Esc** — sair.
- **F** — tela cheia da janela.

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
| `--model` | `yolov8s.pt` | Modelo YOLOv8 local ou nome que Ultralytics resolve |
| `--conf` | `0.4` | Limiar de confiança (0–1); CLI sobrepõe o padrão |
| `--resize` | `None` | Redimensiona a maior dimensão (ex: 640) |
| `--probe` | `False` | Testa backends e índices de câmera |
| `--log-path` | `logs/metricas.jsonl` | Destino do log (só fase/ciclo) |
| `--sem-log-metricas` | `False` | Desliga o JSONL |

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
| `test_trafego.py` | Demanda, status, Webster (clamps, recálculo, ciclo completo) |
| `test_contagem.py` | Contagem por line-crossing |
| `test_painel.py` | Tecla de esconder/mostrar painel (`alternar_painel`) |

```sh
pytest tests/test_trafego.py::test_ciclo_completo_de_fases -v
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
| **Webster 2 fases** | Tempos simulados + painel de resumo |
| **Painel minimizável** | Split 65/35; tecla `I` esconde/mostra |
| **Log JSONL** | Só na transição de fase/ciclo; não distorce latência por I/O a cada frame |

---

## Limitações conhecidas

**Re-ID persistente entre sessões não implementado:** Se o tracker perde e reatribui `track_id`, o evento será contado como novo.

**Fase B não observada:** `Y_B = 0.20` é hipótese de laboratório. Cruzamento real exigiria segunda câmera ou outro sensor.

**Semáforo é simulação:** nenhum comando vai para hardware de campo.

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
├── main.py                 # CLI + loop da câmera
├── requirements.txt
├── ALTERACOES.md
├── README.md
├── src/
│   ├── config.py           # pesos, Webster, nomes em PT
│   ├── trafego.py          # demanda + ControladorSemaforo
│   ├── visao.py            # detecção / contagem
│   ├── metricas.py         # log JSONL
│   └── ui/
│       └── painel.py       # split + painel minimizável
├── tests/
│   ├── test_trafego.py
│   ├── test_contagem.py
│   └── test_painel.py
├── logs/                   # metricas.jsonl (runtime)
└── samples/                # vídeos de teste (opcional)
```

---

## Conformidade e segurança

### LGPD (Lei nº 13.709/2018)

| Princípio | Implementação |
|-----------|---------------|
| **Minimização** | Só totais por classe; sem PII |
| **Finalidade** | Fluxo de tráfego no laboratório |
| **Não armazenamento de imagem** | Frame descartado após o processamento |
| **Segurança** | Processo local; JSONL sem identificadores |

---

## Performance esperada

| Métrica | CPU | GPU (CUDA) |
|--------|-----|-----------|
| **Latência (YOLOv8s)** | ~100–150ms | ~15–30ms |
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

</div>

