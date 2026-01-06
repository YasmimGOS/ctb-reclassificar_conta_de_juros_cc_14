"""
Construção de estrutura WordData para API de lançamento contábil.

WordData é o formato JSON específico usado pela API MegaIntegrador.
"""
import os
import logging
from typing import Optional
import pandas as pd


def montar_word_data(
    df_creditos: pd.DataFrame,
    diretoria_financeira_info: Optional[dict]
) -> list[dict]:
    """
    Monta a estrutura WordData para a API de lançamento contábil.

    ESTRUTURA WORDDATA:
    - N itens de CRÉDITO (todos os centros EXCETO Diretoria Financeira)
      * Inclui Diretoria Operacional e todos os demais centros de custo
    - 1 item de DÉBITO (Diretoria Financeira com valor = soma de todos os créditos)

    Por quê Diretoria Financeira é débito?
    - Contabilmente, os créditos nos centros de custo precisam de uma contrapartida.
    - A Dir. Financeira recebe o débito total para fechar o lançamento.

    Args:
        df_creditos: DataFrame com os centros de custo para crédito (exceto Dir. Financeira)
        diretoria_financeira_info: Dict com informações da Diretoria Financeira

    Returns:
        list: Lista de itens de lançamento no formato WordData
    """
    conta_reduzido = int(os.getenv("DADO_COMPARATIVO_TABELA", "1829"))
    projeto_reduzido = 192  # Fixo conforme especificação

    itens_lancamento = []

    # 1. Lançamentos de CRÉDITO (para cada centro de custo)
    for idx, row in df_creditos.iterrows():
        item_credito = {
            "filial": int(row['FIL_IN_CODIGO']),
            "contaCreditoRed": conta_reduzido,
            "complemento": "Reclassificaçao de CC Osac",
            "valor": float(row['VALORCREDITO']),
            "operacao": "I",
            "centroCusto": [
                {
                    "centroCustoReduzido": int(row['CUS_IN_REDUZIDO']),
                    "valor": float(row['VALORCREDITO']),
                    "natureza": "C",
                    "operacao": "I",
                    "projeto": [
                        {
                            "projetoReduzido": projeto_reduzido,
                            "valor": float(row['VALORCREDITO']),
                            "operacao": "I"
                        }
                    ]
                }
            ]
        }
        itens_lancamento.append(item_credito)

    # 2. Lançamento de DÉBITO único para Diretoria Financeira (com valor total)
    if diretoria_financeira_info:
        item_diretoria_debito = {
            "filial": int(diretoria_financeira_info['FIL_IN_CODIGO']),
            "contaDebitoRed": conta_reduzido,
            "complemento": "Reclassificaçao de CC Osac",
            "valor": float(diretoria_financeira_info['VALOR']),
            "operacao": "I",
            "centroCusto": [
                {
                    "centroCustoReduzido": int(diretoria_financeira_info['CUS_IN_REDUZIDO']),
                    "valor": float(diretoria_financeira_info['VALOR']),
                    "natureza": "D",
                    "operacao": "I",
                    "projeto": [
                        {
                            "projetoReduzido": projeto_reduzido,
                            "valor": float(diretoria_financeira_info['VALOR']),
                            "operacao": "I"
                        }
                    ]
                }
            ]
        }
        itens_lancamento.append(item_diretoria_debito)

    logging.info(f"Montados {len(itens_lancamento)} itens de lançamento")
    return itens_lancamento
