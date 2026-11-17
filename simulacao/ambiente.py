"""Acha o SUMO instalado pelo pip (eclipse-sumo) ou pelo SUMO_HOME."""

import os
import sys


def preparar_ambiente():
    """Coloca SUMO_HOME e a pasta tools no caminho do Python. Devolve o HOME ou None."""
    home = os.environ.get("SUMO_HOME")
    if not home:
        try:
            import sumo
        except ImportError:
            sumo = None
        if sumo is not None and getattr(sumo, "SUMO_HOME", None):
            home = sumo.SUMO_HOME
            os.environ["SUMO_HOME"] = home
    if not home:
        return None
    ferramentas = os.path.join(home, "tools")
    if os.path.isdir(ferramentas) and ferramentas not in sys.path:
        sys.path.insert(0, ferramentas)
    return home


def binario_sumo(gui=False):
    preparar_ambiente()
    import sumolib

    nome = "sumo-gui" if gui else "sumo"
    caminho = sumolib.checkBinary(nome)
    if not caminho or not os.path.isfile(caminho):
        raise FileNotFoundError(nome)
    return caminho


def binario_netconvert():
    preparar_ambiente()
    import sumolib

    caminho = sumolib.checkBinary("netconvert")
    if not caminho or not os.path.isfile(caminho):
        raise FileNotFoundError("netconvert")
    return caminho


def mensagem_sumo_ausente():
    return (
        "SUMO não encontrado. No Windows, com o ambiente do projeto ativo:\n"
        "  pip install eclipse-sumo\n"
        "Ou instale o pacote oficial (https://eclipse.dev/sumo/) e defina SUMO_HOME "
        "para a pasta que contém bin/ e tools/. Confira com: sumo --version"
    )
