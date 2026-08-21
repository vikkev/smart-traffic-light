# O que foi alterado nesta etapa

Documento para o grupo e para a banca. O README descreve o produto; este arquivo descreve a **mudança de rota**.

## Antes / depois

| Antes | Depois |
|-------|--------|
| Tudo em `main.py` + overlay confuso cobrindo a câmera | Pacote `src/` + tela dividida (câmera 65% + painel 35%) |
| Textos tipo `1) Situacao (pontos…)` / `person 1` | Painel leigo: semáforo visual, PT claro, sem id |
| Painel sempre na frente da imagem | Tecla **I** esconde/mostra o painel; câmera nunca para |
| Só status NORMAL/BUSY | Webster 2 fases + log JSONL na troca de fase/ciclo |

## Arquivos

| Arquivo | Motivo |
|---------|--------|
| `main.py` | Só CLI + loop |
| `src/config.py` | Constantes |
| `src/trafego.py` | Demanda + Webster |
| `src/visao.py` | Contagem |
| `src/metricas.py` | JSONL |
| `src/ui/painel.py` | Split + `alternar_painel` |
| `tests/test_trafego.py` / `test_contagem.py` / `test_painel.py` | Essenciais |
| `README.md` / `ALTERACOES.md` / `agente_tcc.agent.md` | Docs |

## Como usar a tela

- Abre com **câmera + painel** (painel à direita).
- **I** — esconde ou mostra o painel.
- **Q** — sair.
- **F** — tela cheia da janela.

## O que continua fora

Hardware de semáforo, malha urbana, RL, DiD, geoespacial SSP operacional, prova causal de crime, metas de 12 meses da Tabela 1.

## Monografia

Metodologia = protótipo de laboratório. YOLOv8 único. Fase B com `Y_B` fixo (1 câmera). Metas grandes = hipótese futura.
