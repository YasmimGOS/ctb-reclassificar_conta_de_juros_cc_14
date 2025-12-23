#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste - força execução do processo para validação.
"""
import os
import sys
from datetime import datetime

# Configurar ambiente de teste
os.environ['DRY_RUN'] = 'true'
os.environ['TEST_SHAREPOINT_TEAMS'] = 'false'

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger import setup_logger
from services.execution_tracking import (
    start_run,
    end_run_ok,
    end_run_failed,
    update_progress,
    StepLogger
)
from services.reclassification_api import chamar_api_reclassificacao
from models.reclassification_processor import processar_reclassificacao
from models.worddata_builder import montar_word_data
from services.accounting_api import chamar_api_lancamento_contabil
from services.sharepoint_service import get_graph_access_token, upload_to_sharepoint
from services.teams_notifier import notificar_sucesso, notificar_erro_api
from utils.business_calendar import calcular_datas_mes_anterior

# Configurar logging
setup_logger("test-ctb-reclassificar_conta_de_juros_cc_14")

import logging
logger = logging.getLogger(__name__)


def test_full_process():
    """Executa teste completo do processo."""

    print("\n" + "="*80)
    print("TESTE DE EXECUÇÃO COMPLETO")
    print("Modo: DRY_RUN (simulação sem operações reais)")
    print("="*80 + "\n")

    # Iniciar telemetria
    run_id, started_at = start_run("test-ctb-reclassificar_conta_de_juros_cc_14")

    try:
        logger.info(f"🚀 Teste iniciado (run_id: {run_id})")

        # Step 1: Calcular datas
        with StepLogger(run_id, "calcular_datas", 1):
            data_inicial, data_final = calcular_datas_mes_anterior()
            logger.info(f"📅 Período: {data_inicial} a {data_final}")
        update_progress(run_id, 11.1)

        # Step 2: Chamar API de reclassificação
        with StepLogger(run_id, "chamar_api_reclassificacao", 2):
            dados_api = chamar_api_reclassificacao(data_inicial, data_final)
            if not dados_api:
                logger.error("❌ API não retornou dados")
                raise Exception("API de reclassificação não retornou dados")
            logger.info(f"✅ API retornou {len(dados_api)} registros")
        update_progress(run_id, 22.2)

        # Step 3: Processar dados
        with StepLogger(run_id, "processar_dados", 3):
            df_creditos, diretoria_financeira_info, df_completo = processar_reclassificacao(
                dados_api, data_inicial, data_final
            )
            if df_creditos is None:
                logger.error("❌ Erro no processamento dos dados")
                raise Exception("Erro no processamento dos dados")
            logger.info(f"✅ Processados {len(df_creditos)} centros de custo de crédito")
        update_progress(run_id, 33.3)

        # Step 4: Montar WordData
        with StepLogger(run_id, "montar_worddata", 4):
            itens_lancamento = montar_word_data(df_creditos, diretoria_financeira_info)
            logger.info(f"✅ Montados {len(itens_lancamento)} itens de lançamento")
        update_progress(run_id, 44.4)

        # Step 5: Enviar lançamentos contábeis
        with StepLogger(run_id, "enviar_lancamentos", 5):
            sucesso_lancamento = chamar_api_lancamento_contabil(itens_lancamento, data_final)
            if not sucesso_lancamento:
                logger.error("❌ Erro ao enviar lançamentos")
                raise Exception("Falha ao enviar lançamentos contábeis")
            logger.info("✅ Lançamentos contábeis enviados")
        update_progress(run_id, 55.6)

        # Step 6: Autenticar Graph
        with StepLogger(run_id, "autenticar_graph", 6):
            token = get_graph_access_token()
            if not token:
                logger.error("❌ Falha na autenticação Microsoft Graph")
                raise Exception("Falha na autenticação Microsoft Graph")
            logger.info("✅ Token Microsoft Graph obtido")
        update_progress(run_id, 66.7)

        # Step 7: Upload para SharePoint
        with StepLogger(run_id, "upload_sharepoint", 7):
            sucesso_upload, link_arquivo = upload_to_sharepoint(df_completo, token)
            if sucesso_upload:
                logger.info("✅ Upload para SharePoint realizado")
            else:
                logger.warning("⚠️ Upload falhou, mas processo continua")
        update_progress(run_id, 77.8)

        # Step 8: Notificar Teams
        with StepLogger(run_id, "notificar_teams", 8):
            notificar_sucesso(df_creditos, diretoria_financeira_info, link_arquivo)
            logger.info("✅ Notificação enviada ao Teams")
        update_progress(run_id, 100.0)

        # Finalizar com sucesso
        end_run_ok(run_id, started_at)

        print("\n" + "="*80)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print(f"Run ID: {run_id}")
        print("="*80 + "\n")

        return True

    except Exception as e:
        logger.exception(f"❌ Erro no teste: {e}")
        end_run_failed(run_id, started_at, str(e))

        print("\n" + "="*80)
        print("❌ TESTE FALHOU")
        print(f"Erro: {e}")
        print(f"Run ID: {run_id}")
        print("="*80 + "\n")

        return False


if __name__ == "__main__":
    try:
        success = test_full_process()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Teste interrompido pelo usuário")
        sys.exit(130)