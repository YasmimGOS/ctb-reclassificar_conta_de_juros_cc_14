# -*- coding: utf-8 -*-
"""
Controller de Reclassificação de Conta de Juros CC14.

Orquestra o fluxo completo de 9 steps do processo.
"""
import logging
from datetime import datetime
from utils.business_calendar import deve_executar_processo, calcular_datas_mes_anterior
from services.reclassification_api import chamar_api_reclassificacao
from models.reclassification_processor import processar_reclassificacao
from models.worddata_builder import montar_word_data
from services.accounting_api import chamar_api_lancamento_contabil
from services.sharepoint_service import get_graph_access_token, upload_to_sharepoint
from services.teams_notifier import notificar_sucesso, notificar_erro_api
from services import bpms_telemetry_service as bpms


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
    id_disparo = None

    # Step 1: Verificar dia útil (antes de iniciar telemetria)
    if not deve_executar_processo():
        logging.info("Processo encerrado: hoje não é dia de execução.")
        return

    # Iniciar telemetria BPMS (só registra se for executar)
    data_inicio = datetime.now()
    id_disparo = bpms.gerar_id_disparo(data_inicio)
    bpms.primeiro_disparo(id_disparo, data_inicio)
    bpms.segundo_disparo(id_disparo, 1)

    progresso_atual = 0

    try:
        logging.info(f"Iniciando processo de reclassificação de conta de juros CC 14 (id_disparo: {id_disparo})")
        progresso_atual = 11
        bpms.update_progresso(id_disparo, progresso_atual)  # 1/9 = ~11%

        # Step 2: Calcular datas do mês anterior
        data_inicial, data_final = calcular_datas_mes_anterior()
        progresso_atual = 22
        bpms.update_progresso(id_disparo, progresso_atual)  # 2/9 = ~22%

        # Step 3: Chamar API de reclassificação
        dados_api = chamar_api_reclassificacao(data_inicial, data_final)
        if not dados_api:
            logging.critical("Processo encerrado: erro ao obter dados da API.")
            bpms.erro(id_disparo, Exception("API de reclassificação retornou erro"), 1, 0, [], progresso_atual)
            exit(1)
        progresso_atual = 33
        bpms.update_progresso(id_disparo, progresso_atual)  # 3/9 = ~33%

        # Step 4: Processar dados
        df_creditos, diretoria_financeira_info, df_completo = processar_reclassificacao(
            dados_api, data_inicial, data_final
        )
        if df_creditos is None:
            logging.critical("Processo encerrado: erro no processamento dos dados.")
            bpms.erro(id_disparo, Exception("Erro no processamento dos dados"), 1, 0, [], progresso_atual)
            exit(1)
        progresso_atual = 44
        bpms.update_progresso(id_disparo, progresso_atual)  # 4/9 = ~44%

        # Step 5: Montar WordData
        itens_lancamento = montar_word_data(df_creditos, diretoria_financeira_info)
        progresso_atual = 56
        bpms.update_progresso(id_disparo, progresso_atual)  # 5/9 = ~56%

        # Step 6: Enviar lançamentos contábeis
        sucesso_lancamento = chamar_api_lancamento_contabil(itens_lancamento, data_final)
        if not sucesso_lancamento:
            logging.critical("Processo encerrado: erro ao enviar lançamentos contábeis.")
            bpms.erro(id_disparo, Exception("Falha ao enviar lançamentos contábeis"), 1, 0, [], progresso_atual)
            exit(1)
        progresso_atual = 67
        bpms.update_progresso(id_disparo, progresso_atual)  # 6/9 = ~67%

        # Step 7: Autenticar Graph (SharePoint)
        token = get_graph_access_token()
        if not token:
            logging.critical("Não foi possível obter token do Microsoft Graph")
            notificar_erro_api("Falha na autenticação Microsoft Graph")
            bpms.erro(id_disparo, Exception("Falha na autenticação Microsoft Graph"), 1, 0, [], progresso_atual)
            exit(1)
        progresso_atual = 78
        bpms.update_progresso(id_disparo, progresso_atual)  # 7/9 = ~78%

        # Step 8: Upload para SharePoint
        sucesso_upload, link_arquivo = upload_to_sharepoint(df_completo, token)
        if not sucesso_upload:
            logging.warning("Upload para SharePoint falhou, mas processo continua...")
        progresso_atual = 89
        bpms.update_progresso(id_disparo, progresso_atual)  # 8/9 = ~89%

        # Step 9: Notificar sucesso no Teams
        notificar_sucesso(df_creditos, diretoria_financeira_info, link_arquivo)
        progresso_atual = 100
        bpms.update_progresso(id_disparo, progresso_atual)  # 9/9 = 100%

        logging.info("Processo concluído com sucesso!")
        bpms.conclusao(id_disparo, 1, 1, [], 100)

    except Exception as e:
        logging.exception(f"Erro inesperado: {e}")
        bpms.erro(id_disparo, e, 1, 0, [], progresso_atual)
        raise  # Re-lançar para manter comportamento original
