"""
Script de diagnóstico para descobrir IDs do SharePoint.

Execução:
    python diagnostico_sharepoint.py

Este script irá:
1. Autenticar no Microsoft Graph
2. Descobrir SITE_ID e DRIVE_ID automaticamente
3. Listar pastas disponíveis no drive
4. Testar acesso ao DRIVE_ITEM_ID configurado (se existir)
5. Mostrar os valores corretos para configurar no .env
"""
import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar path do projeto ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.sharepoint_service import get_graph_access_token
from utils.sharepoint_discovery import (
    discover_sharepoint_ids,
    list_drive_folders,
    test_folder_access
)
from config.settings import get_site_id, get_drive_item_id


def main():
    """Função principal do diagnóstico."""
    print("=" * 80)
    print("DIAGNOSTICO DE CONFIGURACAO DO SHAREPOINT")
    print("=" * 80)
    print()

    # 1. Obter token de autenticação
    print("Passo 1: Autenticando no Microsoft Graph...")
    access_token = get_graph_access_token()

    if not access_token or access_token == "dry_run_token_fake":
        print("[ERRO] Nao foi possivel obter token de autenticacao")
        print("Verifique as credenciais no .env:")
        print("  - TENANT_ID")
        print("  - CLIENT_ID")
        print("  - CLIENT_SECRET")
        return

    print("[OK] Autenticacao bem-sucedida!")
    print()

    # 2. Usar SITE_ID já configurado
    current_site_id = get_site_id()

    if not current_site_id:
        print("[ERRO] SITE_ID nao configurado no .env")
        print("Configure SITE_ID no .env e tente novamente")
        return

    print(f"Passo 2: Usando SITE_ID configurado...")
    print(f"SITE_ID: {current_site_id}")
    print()

    # 3. Obter DRIVE_ID do site
    print("Passo 3: Obtendo DRIVE_ID do site...")

    import requests
    drive_url = f"https://graph.microsoft.com/v1.0/sites/{current_site_id}/drive"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(drive_url, headers=headers, timeout=30)
        response.raise_for_status()
        drive_data = response.json()
        drive_id = drive_data.get("id")
        print(f"[OK] DRIVE_ID: {drive_id}")
        print()
    except Exception as e:
        print(f"[ERRO] Nao foi possivel obter DRIVE_ID: {e}")
        return

    # 4. Listar pastas do drive
    print("Passo 4: Listando pastas no drive raiz...")
    print("(Use um destes IDs como DRIVE_ITEM_ID no .env)")
    print()
    list_drive_folders(access_token, current_site_id, drive_id)
    print()

    # 5. Testar acesso ao DRIVE_ITEM_ID configurado (se existir)
    current_drive_item_id = get_drive_item_id()

    if current_drive_item_id:
        print(f"Passo 5: Testando acesso ao DRIVE_ITEM_ID configurado...")
        print(f"DRIVE_ITEM_ID atual: {current_drive_item_id}")
        print()
        test_folder_access(access_token, current_site_id, current_drive_item_id)
        print()

    # 6. Mostrar resumo de configuração
    print("=" * 80)
    print("RESUMO - Configuracao atual:")
    print("=" * 80)
    print(f"SITE_ID={current_site_id}")
    print(f"DRIVE_ITEM_ID={current_drive_item_id or '(nao configurado)'}")
    print()
    print("# Escolha um dos IDs das pastas listadas acima e configure no .env")
    print("=" * 80)


if __name__ == "__main__":
    main()