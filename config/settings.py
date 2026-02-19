"""
Centralização de variáveis de ambiente.

Fornece helpers para acessar variáveis de ambiente de forma type-safe.
"""
import os
from typing import Optional


# Azure AD / Microsoft Graph
def get_tenant_id() -> str:
    """Retorna TENANT_ID do Azure AD."""
    return os.getenv("TENANT_ID", "")


def get_client_id() -> str:
    """Retorna CLIENT_ID do App Registration."""
    return os.getenv("CLIENT_ID", "")


def get_client_secret() -> str:
    """Retorna CLIENT_SECRET do App Registration."""
    return os.getenv("CLIENT_SECRET", "")


def get_site_id() -> str:
    """Retorna SITE_ID do SharePoint (DEPRECATED - use get_drive_id)."""
    return os.getenv("SITE_ID", "")


def get_drive_item_id() -> str:
    """Retorna DRIVE_ITEM_ID da pasta no SharePoint (DEPRECATED - use get_folder_path)."""
    return os.getenv("DRIVE_ITEM_ID", "")


def get_drive_id() -> str:
    """Retorna DRIVE_ID do SharePoint (formato novo)."""
    return os.getenv("DRIVE_ID", "")


def get_folder_path() -> str:
    """Retorna FOLDER_PATH do SharePoint (caminho relativo da pasta)."""
    return os.getenv("FOLDER_PATH", "")


# Power Automate
def get_power_automate_webhook() -> str:
    """Retorna URL do webhook Power Automate (Teams)."""
    return os.getenv("POWER_AUTOMATE_WEBHOOK_URL", "")


# APIs Externas
def get_api_reclassificacao_token() -> str:
    """Retorna token de autenticação da API de reclassificação."""
    return os.getenv("API_RECLASSIFICACAO_TOKEN", "")


def get_api_lancamento_token() -> str:
    """Retorna token de autenticação da API MegaIntegrador."""
    return os.getenv("API_LANCAMENTO_TOKEN", "")


# Configurações de Negócio
def get_empresa_consolidadora() -> str:
    """Retorna código da empresa consolidadora."""
    return os.getenv("EMPRESA_CONSOLIDADORA", "15534")


def get_num_lote() -> str:
    """Retorna número do lote."""
    return os.getenv("NUM_LOTE", "10401")


def get_dado_comparativo_tabela() -> str:
    """Retorna código da conta contábil (dado comparativo tabela)."""
    return os.getenv("DADO_COMPARATIVO_TABELA", "1829")


# Flags de Desenvolvimento
def is_forced_execution() -> bool:
    """Verifica se execução forçada está habilitada."""
    return os.getenv("FORCAR_EXECUCAO", "false").lower() == "true"


def is_dry_run() -> bool:
    """Verifica se está em modo DRY_RUN (sem chamadas reais a APIs)."""
    return os.getenv("DRY_RUN", "false").lower() == "true"


def test_sharepoint_teams() -> bool:
    """
    Verifica se deve testar SharePoint e Teams mesmo em DRY_RUN.

    Use para validar upload de Excel e notificações sem enviar lançamentos reais.
    """
    return os.getenv("TEST_SHAREPOINT_TEAMS", "false").lower() == "true"


# Telemetria BPMS
def get_bpms_enabled() -> str:
    return os.getenv("BPMS_ENABLED", "TRUE")


def get_em_producao() -> str:
    return os.getenv("EM_PRODUCAO", "FALSE")
