"""Persistência de dados de processos em JSON."""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _filepath(numero_processo: str) -> str:
    safe_name = numero_processo.replace(".", "").replace("-", "").replace("/", "")
    return os.path.join(DATA_DIR, f"{safe_name}.json")


def salvar(numero_processo: str, dados: dict) -> str:
    """Salva dados do processo com timestamp. Retorna o caminho do arquivo."""
    _ensure_data_dir()
    filepath = _filepath(numero_processo)

    historico = carregar_historico(numero_processo)
    entrada = {
        "timestamp": datetime.now().isoformat(),
        "dados": dados,
    }
    historico.append(entrada)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    return filepath


def carregar_historico(numero_processo: str) -> list:
    """Carrega todo o histórico de consultas do processo."""
    filepath = _filepath(numero_processo)
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def comparar(numero_processo: str, dados_novos: dict) -> dict | None:
    """Compara dados novos com a última execução. Retorna diff ou None se primeira vez."""
    historico = carregar_historico(numero_processo)
    if not historico:
        return None

    dados_anteriores = historico[-1]["dados"]
    timestamp_anterior = historico[-1]["timestamp"]

    diff = {
        "timestamp_anterior": timestamp_anterior,
        "mudancas": {},
    }

    # Compara status
    if dados_anteriores.get("status") != dados_novos.get("status"):
        diff["mudancas"]["status"] = {
            "antes": dados_anteriores.get("status"),
            "agora": dados_novos.get("status"),
        }

    # Compara movimentações — identifica as novas
    movs_anteriores = {m["data"] + m["titulo"] for m in dados_anteriores.get("movimentacoes", [])}
    movs_novas = [
        m for m in dados_novos.get("movimentacoes", [])
        if m["data"] + m["titulo"] not in movs_anteriores
    ]
    if movs_novas:
        diff["mudancas"]["novas_movimentacoes"] = movs_novas

    # Compara partes
    if dados_anteriores.get("partes") != dados_novos.get("partes"):
        diff["mudancas"]["partes"] = {
            "antes": dados_anteriores.get("partes"),
            "agora": dados_novos.get("partes"),
        }

    if not diff["mudancas"]:
        return None

    return diff
