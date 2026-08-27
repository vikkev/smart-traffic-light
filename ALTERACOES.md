# O que mudou nesta branch 

Texto para quem não é da área de programação — grupo, orientador ou banca.

---

## Em uma frase

Antes o programa só **via** carros/pessoas na câmera. Agora ele também **calcula um semáforo simulado**, organiza o código melhor, mostra só o essencial na tela e conta de forma mais confiável.

---

## O que o sistema faz hoje

1. **Olha a câmera** (ou um vídeo) e identifica veículos/pessoas com IA (YOLOv8).
2. **Conta** quem passa na linha amarela.
3. **Simula um semáforo**: decide quanto tempo o sinal ficaria verde, conforme o movimento (método Webster — regra clássica de engenharia de trânsito).
4. **Mostra na tela**, em português e com cores, o essencial:
   - cor do sinal e segundos que faltam
   - se o fluxo está tranquilo ou movimentado
   - quantos passaram na linha
5. **Guarda números** em um arquivo de log (só totais, sem rosto, sem placa, sem gravar vídeo) — alinhado à LGPD.

Isso é um **protótipo de laboratório**, não um semáforo instalado na rua.

---

## Principais mudanças desta branch

### De “só detectar” para “também controlar (simulado)”
O programa passou a calcular tempos de verde/amarelo em duas fases. A rua da câmera é medida de verdade; a “outra rua” usa um valor fixo estimado (porque só há uma câmera).

### Tela mais clara e leve
- Textos em português (`Pessoa`, `Carro`), sem nomes técnicos em inglês.
- Informações **por cima da câmera**, coloridas e com contorno, sem aquele quadrado cinza grande que cobria a imagem e deixava o programa lento.
- Tecla **I** esconde ou mostra essas infos. **Q** sai.

### Contagem mais correta
Antes, se a pessoa levantava o braço, a caixa de detecção crescia e o sistema achava que alguém “passou” na linha. Agora a contagem usa o **pé** da caixa (parte de baixo), então gesto de braço não gera contagem falsa.

### Código mais organizado
O projeto foi separado em pastas (`src/`): visão, trânsito, tela, métricas. Ficou mais fácil de manter e de testar.

### Testes
Foram adicionados testes automáticos do básico: cálculo do semáforo, contagem e o botão de esconder/mostrar o HUD.

### Modos câmera e demo
- **`--mode camera`**: webcam (padrão).
- **`--mode demo`**: abre `samples/semaforo.mp4` e **reinicia o vídeo em loop** no fim (contagem e semáforo simulado continuam).
- Ainda dá para passar `--source caminho.mp4` manualmente.

### Linha de contagem adaptável (zero-config)
- No demo (`semaforo.mp4`) usa **preset** calibrado na faixa (mais estável); na câmera tenta **auto**.
- **A** = forçar auto · **L** = 2 cliques · **D** / `--debug-linha` = ver Hough/cluster.
- Auto rejeita linha quase vertical (pouca largura) — evita o “traço torto” no lado direito.
- Classes estáveis por `track_id` (voto): moto não vira “carro” no frame do cruzamento; person larga → moto.
- Piloto: filtro por contenção da bbox da pessoa dentro da moto.

### Robustez de câmeras e RTSP
- **Retry automático**: Para fontes de câmera local (int) e RTSP, até 30 tentativas automáticas de reconexão em caso de falha.
- **Fallback de modelo**: Se `ultralytics` não estiver instalado, o sistema continua funcionando em modo reduzido (_DummyModel) para testes estruturais.
- **Poda de track_ids**: IDs de rastreamento não vistos há 300+ frames são removidos automaticamente da memória, evitando vazamento.
### Debug e validação
- **--max-frames**: Argumento de debug que processa apenas N frames e encerra o programa. Útil para smoke tests rápidos com `--max-frames 120`.
- **Reset de contagem ao ciclo**: Quando um ciclo completo de Webster termina, a contagem de veículos é zerada. Isso garante que a demanda do próximo ciclo reflita tráfego recente, não acumulado.

### Novo teste
- **test_demanda_reset_and_rtsp.py**: Valida que contagens são limpas ao final do ciclo e que a lógica `fonte_com_retry_for()` funciona corretamente para câmeras (int), RTSP e arquivos.

---

## O que isso NÃO é (importante)

Ainda **não** temos:

- semáforo físico na rua  
- malha de semáforos da cidade inteira  
- prova de que “menos espera = menos crime”  
- estudo estatístico longo (DiD) nem metas de 12 meses  

O que entregamos é um **protótipo que demonstra** detecção + contagem + decisão de tempos na tela, para o TCC.

---

## Como usar (bem resumido)

```text
python main.py --mode camera
python main.py --mode demo --resize 640
python main.py --mode demo --debug-linha
```

- **camera** — webcam ao vivo  
- **demo** — vídeo `samples/semaforo.mp4` em loop  
- **A** — auto-calibrar linha de novo  
- **L** — calibrar linha com 2 cliques  
- **D** — debug da linha (mostra o que o algoritmo viu)  
- **I** — mostrar/esconder as infos na câmera  
- **Q** — sair  
- Se estiver lento: acrescente `--resize 640`---

## Resumo para a banca

| Antes | Agora |
|-------|--------|
| Só detectava e mostrava status | Detecta, conta e simula tempos de semáforo |
| Tela confusa / painel pesado | Infos essenciais coloridas em cima da câmera |
| Contagem enganava com movimento do braço | Contagem pelo “pé” da detecção |
| Tudo misturado em um arquivo | Código em pastas + testes |
| Parecia sistema de cidade | Deixa claro: protótipo de laboratório |
