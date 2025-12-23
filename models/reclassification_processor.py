"""
Processamento de dados de reclassificação.

Responsável por transformar dados da API em estruturas prontas para lançamento contábil.
"""
import json
import logging
from datetime import date
from typing import Optional, Tuple
import pandas as pd


def processar_reclassificacao(
    dados_api: list[dict],
    data_inicial: date,
    data_final: date
) -> Tuple[Optional[pd.DataFrame], Optional[dict], Optional[pd.DataFrame]]:
    """
    Processa o JSON da API e aplica as regras de negócio.

    REGRAS DE NEGÓCIO:
    1. Diretoria Financeira (11102001) vai pro Excel mas NÃO pros lançamentos
       - Motivo: Ela receberá o lançamento de DÉBITO (contrapartida dos créditos)
    2. Diretoria Operacional (12200001) é REMOVIDA dos créditos
       - Motivo: Não faz parte da reclassificação
       - Porém é INCLUÍDA no cálculo do somatório do débito
    3. Cálculo do débito: Soma TODOS os centros (incluindo Dir. Operacional),
       exceto Diretoria Financeira

    Args:
        dados_api: Lista de dicionários com dados da API
        data_inicial: Data inicial do período (não usado atualmente)
        data_final: Data final do período (não usado atualmente)

    Returns:
        tuple: (df_creditos, diretoria_financeira_info, df_completo)
            - df_creditos: DataFrame com créditos (sem Dir. Financeira e Dir. Operacional)
            - diretoria_financeira_info: Dict com info da Dir. Financeira para débito
            - df_completo: DataFrame completo para Excel (inclui TODOS os registros)
    """
    try:
        if isinstance(dados_api, str):
            dados = json.loads(dados_api)
        else:
            dados = dados_api

        df = pd.DataFrame(dados['data'])
        logging.info(f"Processando {len(df)} registros da API")

        # 1. Separar Diretoria Financeira (vai pro Excel mas não pros lançamentos)
        df_diretoria_financeira = df[df['CENTROCUSTO'] == '11102001-Diretoria Financeira'].copy()
        df_sem_financeira = df[df['CENTROCUSTO'] != '11102001-Diretoria Financeira'].copy()

        logging.info(
            f"Diretoria Financeira: {len(df_diretoria_financeira)} registros "
            f"(vai pro Excel mas não para lançamento)"
        )
        logging.info(f"Outros centros de custo: {len(df_sem_financeira)} registros")

        # 2. Separar Diretoria Operacional dos demais
        df_diretoria_op = df_sem_financeira[
            df_sem_financeira['CENTROCUSTO'] == '12200001-Diretoria Operacional'
        ].copy()
        df_creditos = df_sem_financeira[
            df_sem_financeira['CENTROCUSTO'] != '12200001-Diretoria Operacional'
        ].copy()

        # 3. Calcular somatório de TODOS os centros (exceto Dir. Financeira)
        # Inclui Diretoria Operacional no cálculo do débito
        valor_razao_diretoria_op = df_sem_financeira['VALORCREDITO'].sum()
        logging.info(
            f"Valor total para débito (Diretoria Financeira): R$ {valor_razao_diretoria_op:,.2f}"
        )

        # 4. Extrair informações da Diretoria Financeira (para o débito)
        diretoria_financeira_info = None
        if len(df_diretoria_financeira) > 0:
            diretoria_financeira_info = {
                'FIL_IN_CODIGO': df_diretoria_financeira.iloc[0]['FIL_IN_CODIGO'],
                'CUS_IN_REDUZIDO': df_diretoria_financeira.iloc[0]['CUS_IN_REDUZIDO'],
                'CENTROCUSTO': df_diretoria_financeira.iloc[0]['CENTROCUSTO'],
                'VALOR': valor_razao_diretoria_op  # Soma de todos os créditos
            }
        else:
            logging.warning("Diretoria Financeira não encontrada no JSON original")

        # 5. DataFrame completo para Excel (inclui TODOS os registros)
        return df_creditos, diretoria_financeira_info, df

    except Exception as e:
        logging.error(f"Erro no processamento dos dados: {e}")
        return None, None, None
