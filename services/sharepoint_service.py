"""
Integração com Microsoft SharePoint via Graph API.

Responsável por autenticação e upload de arquivos Excel.
"""
import io
import logging
import time
from datetime import datetime
from typing import Optional
import pandas as pd
from utils.http_client import HTTPClient
from config.settings import (
    get_tenant_id,
    get_client_id,
    get_client_secret,
    get_site_id,
    get_drive_item_id,
    get_drive_id,
    get_folder_path
)


# Cliente HTTP para Graph API
http_client = HTTPClient()
SESSION_GRAPH = http_client.get_session()


def get_graph_access_token() -> Optional[str]:
    """
    Obtém o token do Graph API usando OAuth 2.0 client credentials.

    Returns:
        str: Access token ou None em caso de erro
    """
    from config.settings import is_dry_run, test_sharepoint_teams

    # Modo DRY_RUN (mas não em modo teste): retornar token simulado
    if is_dry_run() and not test_sharepoint_teams():
        logging.info("[DRY_RUN] Simulando autenticação Microsoft Graph...")
        return "dry_run_token_fake"

    tenant_id = get_tenant_id()
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    payload = {
        "client_id": get_client_id(),
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": get_client_secret(),
        "grant_type": "client_credentials"
    }

    try:
        response = SESSION_GRAPH.post(url, data=payload, timeout=30)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logging.error(f"Erro ao obter token do Graph: {e}")
        return None


def upload_to_sharepoint(df: pd.DataFrame, access_token: str) -> tuple[bool, str]:
    """
    Gera Excel em memória e faz upload para o SharePoint.

    Args:
        df: DataFrame completo (inclui todos os centros de custo)
        access_token: Token de autenticação do Graph API

    Returns:
        tuple[bool, str]: (sucesso, link_do_arquivo)
    """
    from config.settings import is_dry_run, test_sharepoint_teams

    # Modo DRY_RUN (mas não em modo teste): simular upload
    if is_dry_run() and not test_sharepoint_teams():
        logging.info("[DRY_RUN] Simulando upload para SharePoint...")
        logging.info(f"[DRY_RUN] Arquivo: Reclassificação cc14 {datetime.now().strftime('%Y%m%d')}.xlsx")
        logging.info(f"[DRY_RUN] Total de linhas: {len(df)}")
        return True, ""

    # Incluir timestamp completo para evitar conflitos (erro 423 - arquivo bloqueado)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Reclassificação cc14 {timestamp}.xlsx"

    # Verificar qual formato de configuração usar (preferência pelo novo formato)
    drive_id = get_drive_id()
    folder_path = get_folder_path()

    if drive_id and folder_path:
        # Formato novo: DRIVE_ID + FOLDER_PATH
        # URL: /drives/{drive-id}/root:/{folder-path}/{filename}:/content
        url_base = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{folder_path}/{filename}:/content"
        logging.info(f"Usando formato novo: DRIVE_ID + FOLDER_PATH")
        logging.info(f"Drive ID: {drive_id}")
        logging.info(f"Pasta: {folder_path}")
    else:
        # Formato antigo (fallback): SITE_ID + DRIVE_ITEM_ID
        site_id = get_site_id()
        drive_folder_id = get_drive_item_id()
        url_base = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{drive_folder_id}:/{filename}:/content"
        logging.info(f"Usando formato antigo: SITE_ID + DRIVE_ITEM_ID")
        logging.info(f"Site ID: {site_id}")
        logging.info(f"Drive Item ID: {drive_folder_id}")

    # 1. Preparar DataFrame para Excel com colunas VALORCREDITO e VALORDEBITO
    df_excel = df.copy()

    # Remover coluna CONTA (não precisa no Excel)
    if 'CONTA' in df_excel.columns:
        df_excel = df_excel.drop(columns=['CONTA'])

    # Calcular somatório de TODOS os VALORCREDITO (positivos + negativos), exceto Dir. Financeira
    df_sem_financeira = df_excel[df_excel['CENTROCUSTO'] != '11102001-Diretoria Financeira']
    soma_creditos = df_sem_financeira['VALORCREDITO'].sum()
    logging.info(f"Somatório de VALORCREDITO (todos os valores): R$ {soma_creditos:,.2f}")

    # Criar coluna VALORDEBITO com valor None por padrão
    df_excel['VALORDEBITO'] = None

    # Para Diretoria Financeira: VALORDEBITO = somatório, VALORCREDITO = None
    mask_financeira = df_excel['CENTROCUSTO'] == '11102001-Diretoria Financeira'
    df_excel.loc[mask_financeira, 'VALORDEBITO'] = soma_creditos
    df_excel.loc[mask_financeira, 'VALORCREDITO'] = None

    # 2. Criar Excel em memória
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_excel.to_excel(writer, index=False, sheet_name='Lancamentos')
    output.seek(0)

    # 3. API Upload com retry (máximo 3 tentativas)
    url = url_base
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }

    max_retries = 3
    for tentativa in range(1, max_retries + 1):
        try:
            output.seek(0)  # Reset buffer position
            response = SESSION_GRAPH.put(url, headers=headers, data=output.read(), timeout=60)
            response.raise_for_status()

            # Extrair webUrl da resposta
            response_data = response.json()
            web_url = response_data.get("webUrl", "")

            logging.info(f"Relatório enviado ao SharePoint: {filename}")
            logging.info(f"Link do arquivo: {web_url}")
            return True, web_url

        except Exception as e:
            # Verificar se é erro 423 (Locked)
            if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 423:
                if tentativa < max_retries:
                    wait_time = tentativa * 2  # Backoff: 2s, 4s, 6s
                    logging.warning(f"Arquivo bloqueado (423). Tentativa {tentativa}/{max_retries}. Aguardando {wait_time}s...")
                    time.sleep(wait_time)

                    # Na última tentativa, adicionar sufixo único
                    if tentativa == max_retries - 1:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename_retry = f"Reclassificação cc14 {timestamp}_v{tentativa}.xlsx"
                        # Reconstruir URL com novo nome
                        if drive_id and folder_path:
                            url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{folder_path}/{filename_retry}:/content"
                        else:
                            url = f"https://graph.microsoft.com/v1.0/sites/{get_site_id()}/drive/items/{get_drive_item_id()}:/{filename_retry}:/content"
                        logging.info(f"Tentando com novo nome: {filename_retry}")
                    continue
                else:
                    logging.error(f"Erro 423: Arquivo bloqueado no SharePoint após {max_retries} tentativas")
                    logging.error("Possíveis causas: arquivo aberto por outro usuário, lock de sincronização OneDrive")
                    logging.error("Solução: Feche o arquivo no SharePoint/Excel e tente novamente")

            # Outros erros ou última tentativa
            if tentativa == max_retries:
                logging.error(f"Erro de upload após {max_retries} tentativas: {e}")
                logging.error(f"URL tentada: {url}")
                if drive_id and folder_path:
                    logging.error(f"DRIVE_ID configurado: {drive_id}")
                    logging.error(f"FOLDER_PATH configurado: {folder_path}")
                else:
                    logging.error(f"SITE_ID configurado: {get_site_id()}")
                    logging.error(f"DRIVE_ITEM_ID configurado: {get_drive_item_id()}")
                logging.error("Verifique as variáveis de ambiente no .env")
                return False, ""
            else:
                logging.warning(f"Erro na tentativa {tentativa}/{max_retries}: {e}. Tentando novamente...")
                time.sleep(2)
                continue

    return False, ""