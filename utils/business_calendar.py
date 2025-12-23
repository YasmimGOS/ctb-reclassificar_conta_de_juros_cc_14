"""
Cálculos de calendário comercial e dias úteis.

Usa workalendar.Brazil para considerar feriados brasileiros.
"""
import logging
from datetime import datetime, timedelta, date
from typing import Tuple
from workalendar.america import Brazil
from config.settings import is_forced_execution


# Calendário brasileiro (considera feriados nacionais)
cal = Brazil()


def calcular_datas_mes_anterior() -> Tuple[str, str]:
    """
    Calcula o primeiro e último dia do mês anterior.

    Returns:
        tuple: (data_inicial, data_final) no formato DD/MM/YYYY
    """
    hoje = datetime.now()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

    data_inicial = primeiro_dia_mes_anterior.strftime('%d/%m/%Y')
    data_final = ultimo_dia_mes_anterior.strftime('%d/%m/%Y')

    logging.info(f"Período de análise: {data_inicial} até {data_final}")
    return data_inicial, data_final


def eh_terceiro_dia_corrido() -> bool:
    """
    Verifica se hoje é o 3º dia útil do mês.

    COMPLIANCE: Processo deve executar automaticamente no 3º dia ÚTIL de cada mês
    (excluindo finais de semana e feriados brasileiros). Usa workalendar.Brazil.

    Returns:
        bool: True se hoje é o 3º dia útil, False caso contrário
    """
    hoje = datetime.now().date()
    primeiro_dia_mes = hoje.replace(day=1)

    # Contar dias corridos (úteis) desde o início do mês
    dias_corridos = 0
    dia_atual = primeiro_dia_mes

    while dia_atual <= hoje:
        # Verifica se é dia útil (não é sábado, domingo ou feriado)
        if cal.is_working_day(dia_atual):
            dias_corridos += 1
            if dia_atual == hoje:
                break
        dia_atual += timedelta(days=1)

    logging.info(f"Hoje ({hoje.strftime('%d/%m/%Y')}) é o {dias_corridos}º dia corrido do mês")
    return dias_corridos == 3


def deve_executar_processo() -> bool:
    """
    Verifica se o processo deve ser executado.

    Retorna True se:
    1. FORCAR_EXECUCAO=true no .env (escape manual), OU
    2. Hoje é o 3º dia útil do mês

    Returns:
        bool: True se deve executar, False caso contrário
    """
    forcar = is_forced_execution()

    if forcar:
        logging.warning("EXECUÇÃO FORÇADA via variável FORCAR_EXECUCAO")
        return True

    if eh_terceiro_dia_corrido():
        logging.info("Hoje é o 3º dia corrido. Processo será executado.")
        return True

    logging.info("Hoje não é o 3º dia corrido. Processo não será executado.")
    return False