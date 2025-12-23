#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste - registra execução no banco para validação.
"""
import os
import sys

# Configurar ambiente ANTES dos imports
os.environ['FORCAR_EXECUCAO'] = 'true'  # Força execução mesmo não sendo 3º dia útil
os.environ['DRY_RUN'] = 'true'          # Simula operações sem executar de verdade
os.environ['TEST_SHAREPOINT_TEAMS'] = 'false'

from dotenv import load_dotenv

# Carregar .env
dotenv_path = os.path.join('../config', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Configurar logging
from utils.logger import setup_logger
setup_logger("test-db-ctb-reclassificar")

import logging
logger = logging.getLogger(__name__)

# Importar o controller
from controllers.reclassification_controller import run

print("\n" + "="*80)
print("TESTE DE REGISTRO NO BANCO DE DADOS")
print("="*80)
print("Configurações:")
print("  - FORCAR_EXECUCAO: true (ignora regra do 3º dia útil)")
print("  - DRY_RUN: true (simula operações)")
print("  - Banco: Supabase PostgreSQL")
print("="*80 + "\n")

try:
    logger.info("Iniciando teste de registro no banco...")
    run()
    print("\n" + "="*80)
    print("✅ TESTE CONCLUÍDO!")
    print("="*80)
    print("\nVerifique no Supabase:")
    print("  SELECT * FROM public.execution_runs ORDER BY started_at DESC LIMIT 5;")
    print("  SELECT * FROM public.execution_steps WHERE run_id = '<run_id>' ORDER BY step_order;")
    print("="*80 + "\n")
except Exception as e:
    print("\n" + "="*80)
    print("❌ TESTE FALHOU")
    print(f"Erro: {e}")
    print("="*80 + "\n")
    logger.exception(f"Erro no teste: {e}")
    sys.exit(1)