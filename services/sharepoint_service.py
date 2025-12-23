"""
Integração com Microsoft SharePoint via Graph API.

Responsável por autenticação e upload de arquivos Excel.
"""
import io
import logging
from datetime import datetime
from typing import Optional
import pandas as pd
from utils.http_client import HTTPClient
from config.settings import (
    get_tenant_id,
    get_client_id,
    get_client_secret,
    get_site_id,
    get_drive_item_id
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

    site_id = get_site_id()
    drive_folder_id = get_drive_item_id()
    filename = f"Reclassificação cc14 {datetime.now().strftime('%Y%m%d')}.xlsx"

    # 1. Preparar DataFrame para Excel com colunas VALORCREDITO e VALORDEBITO
    df_excel = df.copy()

    # Remover coluna CONTA (não precisa no Excel)
    if 'CONTA' in df_excel.columns:
        df_excel = df_excel.drop(columns=['CONTA'])

    # Calcular somatório de todos os VALORCREDITO positivos
    soma_creditos = df_excel[df_excel['VALORCREDITO'] > 0]['VALORCREDITO'].sum()
    logging.info(f"Somatório de VALORCREDITO positivos: R$ {soma_creditos:,.2f}")

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

    # 3. API Upload
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{drive_folder_id}:/{filename}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    }

    try:
        response = SESSION_GRAPH.put(url, headers=headers, data=output.read(), timeout=60)
        response.raise_for_status()

        # Extrair webUrl da resposta
        response_data = response.json()
        web_url = response_data.get("webUrl", "")

        logging.info(f"Relatório enviado ao SharePoint: {filename}")
        logging.info(f"Link do arquivo: {web_url}")
        return True, web_url
    except Exception as e:
        logging.error(f"Erro de upload: {e}")
        logging.error(f"URL tentada: {url}")
        logging.error(f"SITE_ID configurado: {site_id}")
        logging.error(f"DRIVE_ITEM_ID configurado: {drive_folder_id}")
        logging.error("Verifique se SITE_ID e DRIVE_ITEM_ID estão corretos no .env")
        logging.error("Para obter SITE_ID: https://graph.microsoft.com/v1.0/sites/{hostname}:/{site-path}")
        logging.error("Para obter DRIVE_ITEM_ID: https://graph.microsoft.com/v1.0/sites/{site-id}/drive/root/children")
        return False, ""