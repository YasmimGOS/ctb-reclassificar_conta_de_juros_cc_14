# -*- coding: utf-8 -*-
"""Serviço de Telemetria BPMS"""
import logging
import requests
from datetime import datetime
import os

_BPMS_BASE_URL = "https://integra.odilonsantos.com/api/Bpms"
_BPMS_TOKEN = "G0SZ33vBPMS"
_HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {_BPMS_TOKEN}"}

NOME_PROCESSO = "ctb-Reclassificar Conta de Juros CC 14"
NOME_FLUXO = "ctb-reclassificar_conta_de_juros_cc_14"
FREQUENCIA_DISPARO = "Mensal (Dia útil 3 às 02:00 am)"
TIPO_FLUXO = "Python"
TIPO_ARQUIVO = "Lançamento Mega"
VERSAO_FLUXO = "Fluxo v1."


def _is_enabled() -> bool:
    return str(os.getenv("BPMS_ENABLED", "TRUE")).strip().upper() == "TRUE"

def _formatar_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.000 -0300")

def gerar_id_disparo(data_inicio: datetime) -> str:
    return f"{NOME_FLUXO}_{data_inicio.strftime('%Y%m%d_%H%M%S')}"

def _post(endpoint: str, payload: dict) -> None:
    if not _is_enabled():
        logging.info(f"[BPMS] Telemetria desabilitada. Ignorando: {endpoint}")
        return
    url = f"{_BPMS_BASE_URL}/{endpoint}"
    try:
        response = requests.post(url, json=payload, headers=_HEADERS, timeout=15)
        if response.status_code not in (200, 201):
            logging.warning(f"[BPMS] {endpoint} retornou status {response.status_code}: {response.text[:200]}")
        else:
            logging.info(f"[BPMS] {endpoint} registrado com sucesso.")
    except Exception as e:
        logging.warning(f"[BPMS] Falha ao chamar {endpoint}: {e}")

def primeiro_disparo(id_disparo: str, data_inicio: datetime) -> None:
    em_producao = str(os.getenv("EM_PRODUCAO", "FALSE")).strip().upper()
    payload = {"id_disparo": id_disparo, "nome_processo": NOME_PROCESSO, "nome_fluxo": NOME_FLUXO,
               "frequencia_disparo": FREQUENCIA_DISPARO, "horarios_disparo": data_inicio.strftime("%H:%M"),
               "tipo_fluxo": TIPO_FLUXO, "data_inicio": _formatar_datetime(data_inicio),
               "status": "Em andamento", "em_producao": em_producao}
    _post("tabentregaveisprimeirodis", payload)

def segundo_disparo(id_disparo: str, resultado_esperado: int) -> None:
    payload = {"id_disparo": id_disparo, "tipo_arquivo": TIPO_ARQUIVO, "progresso": 0, "resultado_esperado": resultado_esperado}
    _post("tabentregaveisrpasegdisp", payload)

def update_progresso(id_disparo: str, progresso: int) -> None:
    payload = {"id_disparo": id_disparo, "progresso": progresso}
    _post("tabentregupdateprogress", payload)

def conclusao(id_disparo: str, resultado_esperado: int, resultado_entregue: int, erros_detalhados: list = None, progresso: int = 100) -> None:
    data_fim = _formatar_datetime(datetime.now())
    n_erros = resultado_esperado - resultado_entregue
    sumario = f"Esperado: {resultado_esperado} | Sucesso: {resultado_entregue} | Falha: {n_erros}."
    if erros_detalhados and n_erros > 0:
        detalhes_str = " ".join(f"{item.get('arquivo', 'Desconhecido')} - {item.get('motivo', 'Motivo não informado')};" for item in erros_detalhados)
        dados_adicionais = f"{VERSAO_FLUXO} {sumario} Arquivos com falha: {detalhes_str}"
    else:
        dados_adicionais = f"{VERSAO_FLUXO} {sumario}"
    payload = {"id_disparo": id_disparo, "data_fim": data_fim, "status": "Concluído", "progresso": progresso, "resultado_entregue": str(resultado_entregue), "dados_adicionais": dados_adicionais}
    _post("tabentregaveisconclposit", payload)

def erro(id_disparo: str, excecao: Exception, resultado_esperado: int, resultado_entregue: int, erros_detalhados: list = None, progresso: int = 0) -> None:
    data_fim = _formatar_datetime(datetime.now())
    n_erros = resultado_esperado - resultado_entregue
    sumario = f"Esperado: {resultado_esperado} | Sucesso: {resultado_entregue} | Falha: {n_erros}."
    if erros_detalhados:
        detalhes_str = " ".join(f"{item.get('arquivo', 'Desconhecido')} - {item.get('motivo', 'Motivo não informado')};" for item in erros_detalhados)
        dados_adicionais = f"{VERSAO_FLUXO} {sumario} Arquivos com falha: {detalhes_str}"
    else:
        dados_adicionais = f"{VERSAO_FLUXO} {sumario}"
    erro_str = f"{type(excecao).__name__}: {str(excecao)}" if excecao else "Erro não especificado"
    payload = {"id_disparo": id_disparo, "data_fim": data_fim, "status": "Falha", "progresso": str(progresso), "resultado_entregue": str(resultado_entregue), "dados_adicionais": dados_adicionais, "erros": erro_str}
    _post("tabentregaveiserro", payload)
