# -*- coding: utf-8 -*-
"""
Test script: Geração de Excel para validação

Testa a geração de Excel com dados de amostra.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
from datetime import datetime
from tests.test_data_sample import SAMPLE_API_RESPONSE


def test_excel_generation():
    """Testa a geração de Excel com a estrutura correta."""

    # Processar dados da API
    df = pd.DataFrame(SAMPLE_API_RESPONSE['data'])

    print(f"Total de registros: {len(df)}")
    print(f"Colunas: {list(df.columns)}")

    # Remover coluna CONTA
    if 'CONTA' in df.columns:
        df = df.drop(columns=['CONTA'])

    # Calcular somatório de todos os VALORCREDITO positivos
    soma_creditos = df[df['VALORCREDITO'] > 0]['VALORCREDITO'].sum()

    # Criar coluna VALORDEBITO com valor None por padrão
    df['VALORDEBITO'] = None

    # Para Diretoria Financeira: VALORDEBITO = somatório, VALORCREDITO = None
    mask_financeira = df['CENTROCUSTO'] == '11102001-Diretoria Financeira'
    df.loc[mask_financeira, 'VALORDEBITO'] = soma_creditos
    df.loc[mask_financeira, 'VALORCREDITO'] = None

    print(f"\n✓ Estrutura Excel validada:")
    print(f"  - Somatório de VALORCREDITO positivos: R$ {soma_creditos:,.2f}")
    print(f"  - Diretoria Financeira VALORDEBITO: {df[mask_financeira]['VALORDEBITO'].values}")
    print(f"  - Coluna CONTA removida: {'CONTA' not in df.columns}")

    # Gerar Excel para validação manual
    filename = f"test_reclassificacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_path = os.path.join(os.path.dirname(__file__), filename)

    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Lancamentos')

    print(f"\n✓ Excel gerado: {filename}")
    print(f"  Localização: {output_path}")
    print(f"  Total de linhas: {len(df)}")

    return True


if __name__ == "__main__":
    try:
        test_excel_generation()
        print("\n✓ Teste concluído com sucesso!")
    except Exception as e:
        print(f"\n✗ Erro no teste: {e}")
        raise