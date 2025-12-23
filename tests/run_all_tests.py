# -*- coding: utf-8 -*-
"""
Test Runner - Executa todos os testes de validação

Executa sequencialmente:
1. test_excel_generation.py
2. test_worddata_structure.py
"""
import sys
import os

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from test_excel_generation import test_excel_generation
from test_worddata_structure import test_worddata_structure


def run_all_tests():
    """Executa todos os testes de validação."""
    print("\n" + "=" * 80)
    print(" RPA RECLASSIFICAÇÃO CC14 - TEST SUITE")
    print("=" * 80 + "\n")

    tests = [
        ("Excel Generation", test_excel_generation),
        ("WordData Structure", test_worddata_structure),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n▶ Executando: {test_name}")
        print("-" * 80)

        try:
            test_func()
            results.append((test_name, "✓ PASSOU"))
            print(f"\n✓ {test_name}: PASSOU")
        except Exception as e:
            results.append((test_name, f"✗ FALHOU: {str(e)}"))
            print(f"\n✗ {test_name}: FALHOU")
            print(f"   Erro: {e}")

    # Sumário final
    print("\n" + "=" * 80)
    print(" SUMÁRIO DE TESTES")
    print("=" * 80)

    for test_name, result in results:
        status_icon = "✓" if result.startswith("✓") else "✗"
        print(f"{status_icon} {test_name}: {result}")

    total_passed = sum(1 for _, result in results if result.startswith("✓"))
    total_tests = len(results)

    print("\n" + "=" * 80)
    print(f" RESULTADO FINAL: {total_passed}/{total_tests} testes passaram")
    print("=" * 80 + "\n")

    return total_passed == total_tests


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Erro fatal no test runner: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)