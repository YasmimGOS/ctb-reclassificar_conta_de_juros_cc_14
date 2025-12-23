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
- PostgreSQL (opcional): Telemetria de execução
- Microsoft Graph: SharePoint upload
- Power Automate: Notificações Teams
- APIs externas: Reclassificação e MegaIntegrador
"""
import logging
import os
from dotenv import load_dotenv
from utils.logger import setup_logger
from controllers.reclassification_controller import run


# ==============================================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================================

# Carregar variáveis de ambiente
dotenv_path = os.path.join('config', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Configurar logging
setup_logger("ctb-reclassificar_conta_de_juros_cc_14")


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.exception(f"Erro fatal: {e}")
        exit(1)