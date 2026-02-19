# -*- coding: utf-8 -*-
"""
RPA: Reclassificação de Conta de Juros CC14

Processo automatizado que executa no 3º dia útil de cada mês para:
1. Obter dados de reclassificação via API
2. Processar e transformar dados
3. Enviar lançamentos contábeis
4. Fazer upload de Excel no SharePoint
5. Notificar sucesso no Teams

Dependências:
- BPMS: Telemetria de execução
- Microsoft Graph: SharePoint upload
- Power Automate: Notificações Teams
- APIs externas: Reclassificação e MegaIntegrador
"""
# ==============================================================================
# IMPORTANTE: Carregar .env ANTES de qualquer import de módulos do projeto
# ==============================================================================
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente (usando caminho absoluto)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, 'config', '.env')

# Tentar carregar do caminho absoluto primeiro
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    # Fallback: tentar carregar do diretório atual
    load_dotenv(override=True)

# ==============================================================================
# IMPORTS (após carregar .env)
# ==============================================================================
import logging
from utils.logger import setup_logger
from controllers.reclassification_controller import run


# ==============================================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================================

# Configurar logging
setup_logger("ctb-reclassificar_conta_de_juros_cc_14")

# Log do caminho do .env para debug
if os.path.exists(dotenv_path):
    logging.info(f"Arquivo .env carregado de: {dotenv_path}")
else:
    logging.warning(f"Arquivo .env não encontrado em: {dotenv_path} (tentando diretório atual)")

# Validar variáveis críticas
critical_vars = [
    "API_RECLASSIFICACAO_TOKEN",
    "API_LANCAMENTO_TOKEN",
    "POWER_AUTOMATE_WEBHOOK_URL",
    "TENANT_ID",
    "CLIENT_ID",
    "CLIENT_SECRET",
]
missing_vars = [var for var in critical_vars if not os.getenv(var)]
if missing_vars:
    logging.warning(f"Variáveis de ambiente faltando: {', '.join(missing_vars)}")
    logging.warning(f"Diretório de trabalho atual: {os.getcwd()}")
    logging.warning(f"Diretório do script: {BASE_DIR}")
else:
    logging.info("Todas as variáveis críticas carregadas com sucesso")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.exception(f"Erro fatal: {e}")
        exit(1)