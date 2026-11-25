"""Roda um cenário no SUMO, com plano fixo ou com o controlador em Python."""

import tempfile
import uuid
from pathlib import Path

from simulacao.ambiente import binario_sumo, mensagem_sumo_ausente, preparar_ambiente
from simulacao.cenarios import (
    ROTA_RETA,
    SEMENTE,
    VIAS,
    DURACAO_PADRAO,
    obter,
    taxa_eixo_por_minuto,
)
from simulacao.controladores import (
    ControladorAtuado,
    ControladorFixo,
    estado_links,
    maximos_webster,
)
from simulacao.metricas_sim import ler_tripinfo, resumir
from simulacao.ponte_visao import eventos_de_chegada, taxa_media_por_minuto
from simulacao.rede import NET, VIAS_ENTRADA, comprimentos, escrever_detectores, mapa_eixos


def rodar(
    cenario,
    controle,
    duracao=DURACAO_PADRAO,
    gui=False,
    atraso_ms=150,
    demanda_visao=None,
    via_visao="n_in",
    omitir_via=None,
    rotulo_cenario=None,
    semente=SEMENTE,
    avisos=False,
):
    """Devolve {'resumo': {...}, 'serie': {...}}."""
    preparar_ambiente()
    if not NET.exists():
        raise FileNotFoundError(
            f"Rede não encontrada em {NET}. Rode: python -m simulacao.gerar_rede"
        )
    try:
        binario = binario_sumo(gui=gui)
    except (FileNotFoundError, ImportError) as erro:
        raise FileNotFoundError(mensagem_sumo_ausente()) from erro

    dados = obter(cenario)
    fluxos = dict(dados["fluxos"])
    nome = rotulo_cenario or cenario
    if demanda_visao:
        omitir_via = omitir_via or via_visao
    fluxos_rota = dict(fluxos)
    if omitir_via:
        fluxos_rota[omitir_via] = 0
    fluxos_plano = dict(fluxos)
    if demanda_visao and omitir_via:
        fluxos_plano[omitir_via] = taxa_media_por_minuto(demanda_visao) * 60.0
    taxas = taxa_eixo_por_minuto(fluxos_plano)

    with tempfile.TemporaryDirectory(prefix="tcc-sumo-") as pasta_tmp:
        pasta = Path(pasta_tmp)
        from simulacao.cenarios import escrever_rotas_de

        rotas = escrever_rotas_de(fluxos_rota, pasta / "rotas.rou.xml", duracao)
        adicionais = escrever_detectores(pasta / "det.add.xml", comprimentos(NET), pasta / "det")
        viagem = pasta / "tripinfo.xml"
        return _executar(
            binario=binario,
            rotas=rotas,
            adicionais=adicionais,
            viagem=viagem,
            duracao=float(duracao),
            controle=controle,
            taxas=taxas,
            nome=nome,
            semente=semente,
            gui=gui,
            atraso_ms=atraso_ms,
            avisos=avisos,
            demanda_visao=demanda_visao,
            via_visao=omitir_via or via_visao,
        )


def _executar(
    binario,
    rotas,
    adicionais,
    viagem,
    duracao,
    controle,
    taxas,
    nome,
    semente,
    gui,
    atraso_ms,
    avisos,
    demanda_visao,
    via_visao,
):
    import traci
    from traci.exceptions import TraCIException

    comando = [
        binario,
        "-n", str(NET),
        "-r", str(rotas),
        "-a", str(adicionais),
        "--begin", "0",
        "--end", str(duracao),
        "--seed", str(int(semente)),
        "--step-length", "1",
        "--time-to-teleport", "-1",
        "--no-step-log", "true",
        "--duration-log.disable", "true",
        "--tripinfo-output", str(viagem),
        "--tripinfo-output.write-unfinished", "true",
        "--collision.action", "warn",
    ]
    if not avisos:
        comando.extend(["--no-warnings", "true"])
    if gui:
        comando.extend([
            "--start", "true",
            "--quit-on-end", "true",
            "--delay", str(int(atraso_ms)),
        ])

    rotulo = f"tcc_{uuid.uuid4().hex[:8]}"
    con = _abrir_sumo(comando, rotulo)
    try:
        return _loop(
            con,
            TraCIException,
            duracao=duracao,
            controle=controle,
            taxas=taxas,
            nome=nome,
            semente=semente,
            demanda_visao=demanda_visao,
            via_visao=via_visao,
            viagem=viagem,
        )
    finally:
        try:
            traci.getConnection(rotulo).close()
        except Exception:
            pass
        # O tripinfo é escrito no close. A leitura fica depois do finally do chamador.
        # (o arquivo está na pasta temporária, então lemos antes de sair do with.)


def _loop(con, erro_traci, duracao, controle, taxas, nome, semente, demanda_visao, via_visao, viagem):
    mapa = mapa_eixos(NET)
    if controle == "fixo":
        sinal = ControladorFixo()
    elif controle == "atuado":
        verde_a, verde_b = maximos_webster(taxas["A"], taxas["B"])
        sinal = ControladorAtuado(verde_a, verde_b)
    else:
        raise KeyError(f"Controle desconhecido: {controle}")

    estado = estado_links(mapa, sinal.fase)
    links = con.trafficlight.getControlledLinks("C")
    if len(estado) != len(links):
        raise RuntimeError(
            f"O plano tem {len(estado)} luzes e o SUMO espera {len(links)}. "
            "Rode python -m simulacao.gerar_rede de novo."
        )
    _aplicar(con, estado)

    eventos = []
    if demanda_visao:
        eventos = eventos_de_chegada(demanda_visao, rota=ROTA_RETA[via_visao])
    proximo_evento = 0
    seq_visao = 0
    adios = {}

    vistos = {via: set() for via in VIAS_ENTRADA}
    ja_vistos = set()
    taxa_suave = dict(taxas)
    fase_anterior = None
    inicio_ciclo = 0.0
    paradas = 0
    em_parada = set()
    filas = []
    serie = {"cenario": nome, "controle": controle, "t": [], "fila": [], "fila_a": [], "fila_b": [], "fase": []}
    verdes = {"A": 0.0, "B": 0.0}
    dt = con.simulation.getDeltaT() or 1.0

    while con.simulation.getTime() < duracao - 1e-6:
        dados = _ler_detectores(con)
        from simulacao.controladores import Leitura

        leitura = _leitura(dados, sinal.fase)
        fase = sinal.passo(dt, leitura)
        if (
            controle == "atuado"
            and fase == "VERDE_A"
            and fase_anterior not in (None, "VERDE_A")
        ):
            agora = con.simulation.getTime()
            duracao_ciclo = max(agora - inicio_ciclo, 1.0)
            if duracao_ciclo >= 15.0:
                taxa_suave = _atualizar_webster(sinal, vistos, duracao_ciclo, taxa_suave)
            vistos = {via: set() for via in VIAS_ENTRADA}
            inicio_ciclo = agora
        _aplicar(con, estado_links(mapa, fase))
        proximo_evento, seq_visao = _inserir(
            con, erro_traci, eventos, proximo_evento, seq_visao, adios, via_visao
        )
        con.simulationStep()
        agora = con.simulation.getTime()
        dados = _ler_detectores(con)
        for via in VIAS_ENTRADA:
            ids = set(dados[via]["ids"])
            # Só a primeira vez que o veículo aparece: é chegada, não fila parada.
            vistos[via].update(ids - ja_vistos)
            ja_vistos.update(ids)
        fila_a, fila_b, fila = _filas(con)
        filas.append(fila)
        serie["t"].append(int(agora))
        serie["fila"].append(fila)
        serie["fila_a"].append(fila_a)
        serie["fila_b"].append(fila_b)
        serie["fase"].append(fase)
        if fase == "VERDE_A":
            verdes["A"] += dt
        elif fase == "VERDE_B":
            verdes["B"] += dt
        paradas, em_parada = _paradas(con, fase, dados, paradas, em_parada)
        fase_anterior = fase

    # Fecha e só então o SUMO despeja o tripinfo. Quem chama está dentro do TemporaryDirectory.
    con.close()
    viagens = ler_tripinfo(viagem) if viagem.exists() else []
    return {
        "resumo": resumir(
            viagens,
            duracao,
            filas,
            paradas,
            verdes,
            nome,
            controle,
            semente,
        ),
        "serie": serie,
    }


def _abrir_sumo(comando, rotulo):
    """Sobe o SUMO e conecta. O retry do TraCI fica em silêncio."""
    import contextlib
    import io
    import subprocess

    import traci
    from sumolib.miscutils import getFreeSocketPort

    porta = getFreeSocketPort()
    processo = subprocess.Popen(comando + ["--remote-port", str(porta)])
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            traci.connect(
                porta,
                numRetries=40,
                host="127.0.0.1",
                proc=processo,
                waitBetweenRetries=0.1,
                label=rotulo,
            )
    except Exception as erro:
        if processo.poll() is None:
            processo.kill()
        raise RuntimeError(f"Falha ao iniciar o SUMO: {erro}") from erro
    traci.switch(rotulo)
    return traci.getConnection(rotulo)


def _atualizar_webster(sinal, vistos, duracao_ciclo, taxa_suave):
    """Volume do ciclo (veículos distintos na via) vira a taxa do próximo Webster."""
    medido = {}
    for eixo, vias in VIAS.items():
        contagem = max(len(vistos[via]) for via in vias)
        medido[eixo] = contagem * 60.0 / duracao_ciclo
    suave = {}
    for eixo in ("A", "B"):
        suave[eixo] = 0.5 * medido[eixo] + 0.5 * taxa_suave[eixo]
    verde_a, verde_b = maximos_webster(suave["A"], suave["B"])
    sinal.definir_maximos(verde_a, verde_b)
    return suave


def _aplicar(con, estado):
    con.trafficlight.setRedYellowGreenState("C", estado)
    con.trafficlight.setPhaseDuration("C", 1.0e5)


def _ler_detectores(con):
    dados = {}
    for via in VIAS_ENTRADA:
        dados[via] = {
            "aprox": con.lanearea.getLastStepVehicleNumber(f"aprox_{via}"),
            "presenca": con.lanearea.getLastStepVehicleNumber(f"presenca_{via}"),
            "chamada": con.inductionloop.getLastStepVehicleNumber(f"laco_{via}") > 0,
            "ids": con.lanearea.getLastStepVehicleIDs(f"presenca_{via}"),
        }
    return dados


def _leitura(dados, fase):
    from simulacao.controladores import Leitura

    if fase in ("VERDE_B", "AMARELO_B", "ALLRED_BA"):
        verde, vermelho = "B", "A"
    else:
        verde, vermelho = "A", "B"
    return Leitura(
        chamada_verde=any(dados[via]["chamada"] for via in VIAS[verde]),
        verde_vazio=all(dados[via]["aprox"] == 0 for via in VIAS[verde]),
        espera_vermelho=any(dados[via]["presenca"] > 0 for via in VIAS[vermelho]),
    )


def _filas(con):
    def halting(eixo):
        return sum(con.lane.getLastStepHaltingNumber(f"{via}_0") for via in VIAS[eixo])

    fila_a = halting("A")
    fila_b = halting("B")
    return fila_a, fila_b, fila_a + fila_b


def _paradas(con, fase, dados, total, ativos):
    """Parada no vermelho enquanto o eixo verde não tem ninguém na distância."""
    if fase not in ("VERDE_A", "VERDE_B"):
        return total, set()
    verde = "A" if fase == "VERDE_A" else "B"
    vermelho = "B" if verde == "A" else "A"
    if any(dados[via]["aprox"] > 0 for via in VIAS[verde]):
        return total, set()
    parados = set()
    for via in VIAS[vermelho]:
        for vid in con.lane.getLastStepVehicleIDs(f"{via}_0"):
            if con.vehicle.getSpeed(vid) < 0.1:
                parados.add(vid)
    total += len(parados - ativos)
    return total, parados


def _inserir(con, erro_traci, eventos, indice, seq, adios, via):
    agora = con.simulation.getTime()
    while indice < len(eventos) and eventos[indice][0] <= agora + 1e-6:
        _instante, rota, tipo = eventos[indice]
        ident = f"visao_{seq}"
        try:
            con.vehicle.add(
                ident,
                rota,
                typeID=tipo,
                depart="now",
                departLane="best",
                departPos="base",
                departSpeed="avg",
            )
            seq += 1
            indice += 1
        except erro_traci:
            adios[indice] = adios.get(indice, 0) + 1
            if adios[indice] >= 30:
                indice += 1
            else:
                break
    return indice, seq
