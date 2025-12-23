# -*- coding: utf-8 -*-
"""
Controller de Reclassificação de Conta de Juros CC14.

Orquestra o fluxo completo de 9 steps do processo.
"""
import logging
from utils.business_calendar import deve_executar_processo, calcular_datas_mes_anterior
from services.reclassification_api import chamar_api_reclassificacao
from models.reclassification_processor import processar_reclassificacao
from models.worddata_builder import montar_word_data
from services.accounting_api import chamar_api_lancamento_contabil
from services.sharepoint_service import get_graph_access_token, upload_to_sharepoint
from services.teams_notifier import notificar_sucesso, notificar_erro_api
from services.execution_tracking import (
    start_run,
    end_run_ok,
    end_run_failed,
    end_run_cancelled,
    update_progress,
    StepLogger
)


def run():
    """
    Executa o processo completo de reclassificação.

    Fluxo de 9 steps:
    1. Verificar dia útil
    2. Calcular datas do mês anterior
    3. Chamar API de reclassificação
    4. Processar dados
    5. Montar WordData
    6. Enviar lançamentos contábeis
    7. Autenticar Graph (SharePoint)
    8. Upload para SharePoint
    9. Notificar sucesso no Teams
    """
    # Step 1: Verificar dia útil (antes de iniciar telemetria)
    if not deve_executar_processo():
        logging.info("Processo encerrado: hoje não é dia de execução.")
        return

    # Iniciar telemetria (só registra se for executar)
    run_id, started_at = start_run("ctb-reclassificar_conta_de_juros_cc_14")

    try:
        logging.info(f"Iniciando processo de reclassificação de conta de juros CC 14 (run_id: {run_id})")
        update_progress(run_id, 11.1)  # 1/9 = 11.1%

        # Step 2: Calcular datas do mês anterior
        with StepLogger(run_id, "calcular_datas", 2):
            data_inicial, data_final = calcular_datas_mes_anterior()
        update_progress(run_id, 22.2)  # 2/9

        # Step 3: Chamar API de reclassificação
        with StepLogger(run_id, "chamar_api_reclassificacao", 3):
            dados_api = chamar_api_reclassificacao(data_inicial, data_final)
            if not dados_api:
                logging.critical("Processo encerrado: erro ao obter dados da API.")
                end_run_failed(run_id, started_at, "API de reclassificação retornou erro")
                exit(1)
        update_progress(run_id, 33.3)  # 3/9

        # Step 4: Processar dados
        with StepLogger(run_id, "processar_dados", 4):
            df_creditos, diretoria_financeira_info, df_completo = processar_reclassificacao(
                dados_api, data_inicial, data_final
            )
            if df_creditos is None:
                logging.critical("Processo encerrado: erro no processamento dos dados.")
                end_run_failed(run_id, started_at, "Erro no processamento dos dados")
                exit(1)
        update_progress(run_id, 44.4)  # 4/9

        # Step 5: Montar WordData
        with StepLogger(run_id, "montar_worddata", 5):
            itens_lancamento = montar_word_data(df_creditos, diretoria_financeira_info)
        update_progress(run_id, 55.6)  # 5/9

        # Step 6: Enviar lançamentos contábeis
        with StepLogger(run_id, "enviar_lancamentos", 6):
            sucesso_lancamento = chamar_api_lancamento_contabil(itens_lancamento, data_final)
            if not sucesso_lancamento:
                logging.critical("Processo encerrado: erro ao enviar lançamentos contábeis.")
                end_run_failed(run_id, started_at, "Falha ao enviar lançamentos contábeis")
                exit(1)
        update_progress(run_id, 66.7)  # 6/9

        # Step 7: Autenticar Graph (SharePoint)
        with StepLogger(run_id, "autenticar_graph", 7):
            token = get_graph_access_token()
            if not token:
                logging.critical("Não foi possível obter token do Microsoft Graph")
                notificar_erro_api("Falha na autenticação Microsoft Graph")
                end_run_failed(run_id, started_at, "Falha na autenticação Microsoft Graph")
                exit(1)
        update_progress(run_id, 77.8)  # 7/9

        # Step 8: Upload para SharePoint
        with StepLogger(run_id, "upload_sharepoint", 8):
            sucesso_upload, link_arquivo = upload_to_sharepoint(df_completo, token)
            if not sucesso_upload:
                logging.warning("Upload para SharePoint falhou, mas processo continua...")
        update_progress(run_id, 88.9)  # 8/9

        # Step 9: Notificar sucesso no Teams
        with StepLogger(run_id, "notificar_teams", 9):
            notificar_sucesso(df_creditos, diretoria_financeira_info, link_arquivo)
        update_progress(run_id, 100.0)  # 9/9

        logging.info("Processo concluído com sucesso!")
        end_run_ok(run_id, started_at)

    except Exception as e:
        logging.exception(f"Erro inesperado: {e}")
        end_run_failed(run_id, started_at, str(e))
        raise  # Re-lançar para manter comportamento original