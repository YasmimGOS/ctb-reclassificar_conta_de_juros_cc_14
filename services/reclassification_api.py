"""
Integração com API de Reclassificação de Juros.

Responsável por chamar a API externa que retorna dados de reclassificação.
"""
import json
import logging
from typing import Optional
import requests
from utils.http_client import HTTPClient
from utils.sanitizer import log_metadata_only, sanitize_error_for_notification
from utils.rate_limiter import RateLimiter
from config.settings import (
    get_api_reclassificacao_token,
    get_dado_comparativo_tabela,
    get_empresa_consolidadora
)
from services.teams_notifier import notificar_erro_api, notificar_sem_dados


# Cliente HTTP para API
http_client = HTTPClient()
SESSION_API = http_client.get_session()


@RateLimiter(max_calls=10, period=60)  # 10 chamadas por minuto
def chamar_api_reclassificacao(data_inicial: str, data_final: str) -> Optional[dict]:
    """
    Chama a API de reclassificação de juros.

    Args:
        data_inicial: Data inicial no formato DD/MM/YYYY
        data_final: Data final no formato DD/MM/YYYY

    Returns:
        dict: Resposta da API ou None em caso de erro
    """
    url = "https://integra.odilonsantos.com/api/Bpms/reclassificajuros"
    token = get_api_reclassificacao_token()
    conta_reduzido = get_dado_comparativo_tabela()
    empresa = get_empresa_consolidadora()

    if not token:
        logging.error("API_RECLASSIFICACAO_TOKEN não configurado no .env")
        notificar_erro_api("Token de autenticação não configurado")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "ContaReduzido": conta_reduzido,
        "Empresa": empresa,
        "DataInicial": data_inicial,
        "DataFinal": data_final
    }

    try:
        logging.info(f"Chamando API de reclassificacao: {data_inicial} a {data_final}")
        logging.info(f"URL: {url}")
        logging.info("REQUEST BODY:")
        logging.info(json.dumps(payload, indent=2, ensure_ascii=False))

        response = SESSION_API.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        dados = response.json()

        logging.info(f"RESPONSE STATUS: {response.status_code}")
        logging.info("RESPONSE BODY:")
        logging.info(json.dumps(dados, indent=2, ensure_ascii=False))

        # Verificar se retornou dados
        if not dados.get("success"):
            erro_msg = dados.get("message", "Erro desconhecido")
            logging.error(f"API retornou erro: {erro_msg}")
            erro_sanitizado = sanitize_error_for_notification(erro_msg)
            notificar_erro_api(erro_sanitizado)
            return None

        if not dados.get("data") or len(dados.get("data", [])) == 0:
            logging.warning("API retornou sem dados")
            notificar_sem_dados()
            return None

        logging.info(f"API retornou {len(dados['data'])} registros")
        return dados

    except requests.exceptions.HTTPError as e:
        erro_msg_log = f"HTTP {e.response.status_code}: {e.response.text}"
        erro_msg_teams = sanitize_error_for_notification(
            f"HTTP {e.response.status_code}: Erro na API de reclassificação"
        )
        logging.error(f"Erro HTTP na API: {erro_msg_log}")
        notificar_erro_api(erro_msg_teams)
        return None
    except requests.exceptions.RequestException as e:
        erro_msg_log = f"Erro de conexão: {str(e)}"
        erro_msg_teams = sanitize_error_for_notification("Erro de conexão com API")
        logging.error(f"Erro de conexão com API: {erro_msg_log}")
        notificar_erro_api(erro_msg_teams)
        return None
    except Exception as e:
        erro_msg_log = f"Erro inesperado: {str(e)}"
        erro_msg_teams = sanitize_error_for_notification("Erro inesperado na API")
        logging.error(f"Erro ao chamar API: {erro_msg_log}")
        notificar_erro_api(erro_msg_teams)
        return None