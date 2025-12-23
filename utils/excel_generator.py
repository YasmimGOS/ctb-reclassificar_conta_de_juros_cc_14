"""
Geração de arquivos Excel.

Cria arquivos Excel formatados para upload no SharePoint.
"""
import os
import logging
from datetime import datetime
import pandas as pd


def gerar_excel(df: pd.DataFrame, data_inicial: str, data_final: str) -> str:
    """
    Gera arquivo Excel a partir de DataFrame.

    Filename: Reclassificação cc14 YYYYMMDD.xlsx (onde YYYYMMDD é a data_final)

    Args:
        df: DataFrame com dados para Excel
        data_inicial: Data inicial do período (DD/MM/YYYY)
        data_final: Data final do período (DD/MM/YYYY)

    Returns:
        str: Path completo do arquivo Excel gerado
    """
    # Converter data_final (DD/MM/YYYY) para YYYYMMDD
    data_obj = datetime.strptime(data_final, '%d/%m/%Y')
    data_formatada = data_obj.strftime('%Y%m%d')

    # Nome do arquivo
    filename = f"Reclassificação cc14 {data_formatada}.xlsx"
    output_path = os.path.join(os.path.dirname(__file__), '..', filename)

    # Preparar DataFrame para Excel (remover colunas desnecessárias se houver)
    df_excel = df.copy()

    # Se tiver coluna CONTA, remover (não vai pro Excel)
    if 'CONTA' in df_excel.columns:
        df_excel = df_excel.drop(columns=['CONTA'])

    # Gerar Excel
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df_excel.to_excel(writer, sheet_name='Reclassificação', index=False)

    logging.info(f"Excel gerado: {output_path}")
    return output_path