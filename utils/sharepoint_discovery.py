"""
Utilitário para descobrir IDs do SharePoint dinamicamente.

Fornece funções para obter SITE_ID e DRIVE_ID sem precisar configurá-los manualmente.
"""
import logging
import requests
from typing import Optional, Tuple


def discover_sharepoint_ids(
    access_token: str,
    hostname: str = "constate.sharepoint.com",
    site_path: str = "/sites/FinanceiroGOS"
) -> Optional[Tuple[str, str]]:
    """
    Descobre automaticamente SITE_ID e DRIVE_ID do SharePoint.

    Args:
        access_token: Token de autenticação do Graph API
        hostname: Hostname do SharePoint (ex: constate.sharepoint.com)
        site_path: Caminho do site (ex: /sites/FinanceiroGOS)

    Returns:
        Tuple[site_id, drive_id] ou None em caso de erro

    Example:
        >>> token = get_graph_access_token()
        >>> site_id, drive_id = discover_sharepoint_ids(token)
        >>> print(f"SITE_ID={site_id}")
        >>> print(f"DRIVE_ID={drive_id}")
    """
    try:
        # 1. Obter informações do site usando path-based approach
        site_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:{site_path}"
        headers = {"Authorization": f"Bearer {access_token}"}

        logging.info(f"Descobrindo SITE_ID: {site_url}")
        response = requests.get(site_url, headers=headers, timeout=30)
        response.raise_for_status()

        site_data = response.json()
        site_id = site_data.get("id")

        logging.info(f"SITE_ID descoberto: {site_id}")
        print(f"[OK] SITE_ID descoberto: {site_id}")

        # 2. Obter informações do drive padrão do site
        drive_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"

        logging.info(f"Descobrindo DRIVE_ID...")
        response = requests.get(drive_url, headers=headers, timeout=30)
        response.raise_for_status()

        drive_data = response.json()
        drive_id = drive_data.get("id")

        logging.info(f"DRIVE_ID descoberto: {drive_id}")
        print(f"[OK] DRIVE_ID descoberto: {drive_id}")

        return site_id, drive_id

    except requests.exceptions.HTTPError as e:
        logging.error(f"Erro HTTP ao descobrir IDs do SharePoint: {e}")
        logging.error(f"Status: {e.response.status_code}, Response: {e.response.text}")
        return None
    except Exception as e:
        logging.error(f"Erro ao descobrir IDs do SharePoint: {e}")
        return None


def list_drive_folders(access_token: str, site_id: str, drive_id: str) -> None:
    """
    Lista as pastas no drive para ajudar a encontrar o DRIVE_ITEM_ID correto.

    Args:
        access_token: Token de autenticação do Graph API
        site_id: ID do site do SharePoint
        drive_id: ID do drive do SharePoint
    """
    try:
        # Listar conteúdo raiz do drive
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
        headers = {"Authorization": f"Bearer {access_token}"}

        logging.info("Listando pastas no drive raiz...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        items = response.json().get("value", [])

        print("\nPastas encontradas no drive raiz:")
        print("-" * 80)

        for item in items:
            if "folder" in item:
                item_id = item.get("id")
                item_name = item.get("name")
                print(f"Nome: {item_name}")
                print(f"ID: {item_id}")
                print("-" * 80)
                logging.info(f"Pasta encontrada: {item_name} (ID: {item_id})")

    except Exception as e:
        logging.error(f"Erro ao listar pastas: {e}")


def test_folder_access(access_token: str, site_id: str, drive_item_id: str) -> bool:
    """
    Testa se consegue acessar uma pasta específica.

    Args:
        access_token: Token de autenticação do Graph API
        site_id: ID do site do SharePoint
        drive_item_id: ID da pasta/item a testar

    Returns:
        bool: True se consegue acessar, False caso contrário
    """
    try:
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{drive_item_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        logging.info(f"Testando acesso à pasta {drive_item_id}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        item_data = response.json()
        item_name = item_data.get("name", "Unknown")

        logging.info(f"[OK] Acesso bem-sucedido a pasta: {item_name}")
        print(f"[OK] Acesso bem-sucedido a pasta: {item_name}")
        return True

    except requests.exceptions.HTTPError as e:
        logging.error(f"[ERRO] Erro ao acessar pasta: HTTP {e.response.status_code}")
        logging.error(f"Response: {e.response.text}")
        print(f"[ERRO] Erro ao acessar pasta: HTTP {e.response.status_code}")
        return False
    except Exception as e:
        logging.error(f"[ERRO] Erro ao acessar pasta: {e}")
        print(f"[ERRO] Erro ao acessar pasta: {e}")
        return False