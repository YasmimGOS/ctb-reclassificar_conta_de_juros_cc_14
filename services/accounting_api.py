"""
Integração com API MegaIntegrador (Lançamentos Contábeis).

Responsável por enviar lançamentos contábeis no formato WordData.
"""
import json
import logging
from typing import List
import requests
from utils.http_client import HTTPClient
from utils.rate_limiter import RateLimiter
from utils.sanitizer import sanitize_error_for_notification
from config.settings import (
    get_api_lancamento_token,
    get_empresa_consolidadora,
    get_num_lote,
    is_dry_run
)
from services.teams_notifier import notificar_erro_api


# Cliente HTTP para API
http_client = HTTPClient()
SESSION_API = http_client.get_session()


@RateLimiter(max_calls=5, period=60)  # 5 chamadas por minuto (mais restritivo)
def chamar_api_lancamento_contabil(itens_lancamento: List[dict], data_lancamento: str) -> bool:
    """
    Envia os lançamentos contábeis para a API MegaIntegrador.

    Args:
        itens_lancamento: Lista de itens no formato WordData
        data_lancamento: Data do lançamento (DD/MM/YYYY)

    Returns:
        bool: True se sucesso, False se erro
    """
    url = "http://integra.odilonsantos.com/api/MegaIntegrador/lancamento-contabil"
    token = get_api_lancamento_token()
    empresa = get_empresa_consolidadora()
    num_lote = int(get_num_lote())

    if not token:
        logging.error("API_LANCAMENTO_TOKEN não configurado no .env")
        notificar_erro_api("Token de lançamento contábil não configurado")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "empresa": int(empresa),
        "lote": num_lote,
        "acao": 20,
        "dataLancamento": data_lancamento,
        "lancNaoAtualizadoGravar": "S",
        "operacao": "I",
        "itensLancamento": itens_lancamento
    }

    # Modo DRY_RUN: simular chamada (mas mostrar REQUEST BODY para debug)
    if is_dry_run():
        logging.info("[DRY_RUN] Simulando envio de lançamento contábil...")
        logging.info(f"[DRY_RUN] Total de itens: {len(itens_lancamento)}")
        logging.info(f"[DRY_RUN] Empresa: {empresa}, Lote: {num_lote}, Data: {data_lancamento}")
        logging.info("[DRY_RUN] REQUEST BODY (Lancamento Contabil):")
        logging.info(json.dumps(payload, indent=2, ensure_ascii=False))
        return True

    # Modo PRODUÇÃO: registrar detalhes completos
    logging.info(f"Enviando {len(itens_lancamento)} itens para API de lancamento contabil...")
    logging.info(f"URL: {url}")
    logging.info("REQUEST BODY (Lancamento Contabil):")
    logging.info(json.dumps(payload, indent=2, ensure_ascii=False))

    try:
        response = SESSION_API.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()

        resultado = response.json()

        logging.info(f"RESPONSE STATUS: {response.status_code}")
        logging.info("RESPONSE BODY:")
        logging.info(json.dumps(resultado, indent=2, ensure_ascii=False))

        logging.info("Lançamentos enviados com sucesso!")
        return True

    except requests.exceptions.HTTPError as e:
        erro_msg_log = f"HTTP {e.response.status_code}: {e.response.text}"
        erro_msg_teams = sanitize_error_for_notification(
            f"Lançamento contábil - HTTP {e.response.status_code}"
        )
        logging.error(f"Erro HTTP na API de lançamento: {erro_msg_log}")
        notificar_erro_api(erro_msg_teams)
        return False
    except requests.exceptions.RequestException as e:
        erro_msg_log = f"Erro de conexão: {str(e)}"
        erro_msg_teams = sanitize_error_for_notification("Lançamento contábil - Erro de conexão")
        logging.error(f"Erro de conexão com API de lançamento: {erro_msg_log}")
        notificar_erro_api(erro_msg_teams)
        return False
    except Exception as e:
        erro_msg_log = f"Erro inesperado: {str(e)}"
        erro_msg_teams = sanitize_error_for_notification("Lançamento contábil - Erro inesperado")
        logging.error(f"Erro ao chamar API de lançamento: {erro_msg_log}")
        notificar_erro_api(erro_msg_teams)
        return False