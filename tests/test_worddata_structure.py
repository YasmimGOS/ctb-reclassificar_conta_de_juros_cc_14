# -*- coding: utf-8 -*-
"""
Test script: Estrutura WordData

Testa a construção da estrutura WordData (JSON) para API MegaIntegrador.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import json
from datetime import date
from tests.test_data_sample import (
    SAMPLE_API_RESPONSE,
    EMPRESA_TESTE,
    LOTE_TESTE,
    CONTA_REDUZIDO_TESTE,
    PROJETO_REDUZIDO_TESTE,
    DATA_LANCAMENTO_TESTE
)
from models.reclassification_processor import processar_reclassificacao
from models.worddata_builder import montar_word_data


def test_worddata_structure():
    """Testa a construção da estrutura WordData."""

    print("=" * 80)
    print("TESTE: Estrutura WordData")
    print("=" * 80)

    # Processar dados
    dados_api = SAMPLE_API_RESPONSE['data']
    data_inicial = date(2025, 11, 1)
    data_final = date(2025, 11, 30)

    df_creditos, diretoria_financeira_info, df_completo = processar_reclassificacao(
        dados_api, data_inicial, data_final
    )

    print(f"\n✓ Processamento concluído:")
    print(f"  - Total de créditos: {len(df_creditos)}")
    print(f"  - Diretoria Financeira: VALORDEBITO = R$ {diretoria_financeira_info['VALOR']:,.2f}")

    # Montar WordData
    itens_lancamento = montar_word_data(df_creditos, diretoria_financeira_info)

    print(f"\n✓ WordData montado:")
    print(f"  - Total de itens: {len(itens_lancamento)}")
    print(f"  - Créditos: {len(itens_lancamento) - 1}")
    print(f"  - Débito (Diretoria Financeira): 1")

    # Estrutura completa para validação
    print("\n" + "=" * 80)
    print("ESTRUTURA WORDDATA COMPLETA")
    print("=" * 80)
    print(json.dumps(itens_lancamento, indent=2, ensure_ascii=False))
    print("=" * 80)

    # Validações
    total_creditos = sum(item.get('VALORCREDITO', 0) for item in itens_lancamento)
    total_debitos = sum(item.get('VALORDEBITO', 0) for item in itens_lancamento)

    print(f"\n✓ Validações:")
    print(f"  - Total VALORCREDITO: R$ {total_creditos:,.2f}")
    print(f"  - Total VALORDEBITO: R$ {total_debitos:,.2f}")
    print(f"  - Balanceamento: {'✓ OK' if abs(total_creditos - total_debitos) < 0.01 else '✗ FALHA'}")

    # Verificar item de débito Diretoria Financeira
    item_debito = next(
        (item for item in itens_lancamento if item.get('VALORDEBITO', 0) > 0),
        None
    )

    if item_debito:
        print(f"\n✓ Item Débito Diretoria Financeira:")
        print(f"  - CENTRODECUSTO: {item_debito.get('CENTRODECUSTO')}")
        print(f"  - VALORDEBITO: R$ {item_debito.get('VALORDEBITO', 0):,.2f}")
        print(f"  - VALORCREDITO: {item_debito.get('VALORCREDITO', 0)}")

    return True


if __name__ == "__main__":
    try:
        test_worddata_structure()
        print("\n" + "=" * 80)
        print("✓ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 80)
    except Exception as e:
        print(f"\n✗ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        raise