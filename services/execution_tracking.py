# -*- coding: utf-8 -*-
"""
Serviço de Telemetria - Execution Tracking
Schema: public

Este módulo registra execuções e passos do RPA no PostgreSQL (Supabase).
Comportamento defensivo: se EXECUTION_DB_DSN ausente, todas as funções são no-op.
"""

import logging
import uuid
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.db_service import ExecutionLogger

try:
    from services.db_service import ExecutionLogger
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    ExecutionLogger = None  # type: ignore
    logging.warning("psycopg2 não instalado ou db_service não disponível. Telemetria desabilitada.")

# Carrega DSN do módulo de configurações (que lê o .env)
try:
    from config.settings import EXECUTION_DB_DSN
except ImportError:
    EXECUTION_DB_DSN = None
    logging.warning("Não foi possível importar configurações. Telemetria desabilitada.")

# Logger
logger = logging.getLogger(__name__)

# Process Name Fixo
PROCESS_NAME = "ctb-reclassificar_conta_de_juros_cc_14"

# Cache para armazenar instâncias de ExecutionLogger por run_id
_execution_loggers = {}

# Cache para mapear (run_id, step_order) -> step_name
_step_cache = {}


def _is_telemetry_enabled():
    """Verifica se a telemetria está configurada."""
    return PSYCOPG_AVAILABLE and EXECUTION_DB_DSN is not None


# ==============================================================================
# RUN-LEVEL FUNCTIONS (Tabela: public.execution_runs)
# ==============================================================================

def start_run(process_name=PROCESS_NAME):
    """
    Registra o início de uma nova execução.

    Args:
        process_name (str): Nome do processo

    Returns:
        tuple: (run_id, started_at_dt) ou (local_id, datetime.now()) se desabilitado
    """
    started_at_dt = datetime.now()

    if not _is_telemetry_enabled():
        logger.warning("Telemetria desabilitada (EXECUTION_DB_DSN não configurado).")
        return (f"local_{uuid.uuid4()}", started_at_dt)

    try:
        # Criar instância do ExecutionLogger
        exec_logger = ExecutionLogger(process_name)
        run_id = exec_logger.start_run()

        # Armazenar no cache
        _execution_loggers[run_id] = exec_logger

        logger.info(f"Telemetria: Execução iniciada. run_id={run_id}")
        return (run_id, started_at_dt)
    except Exception as e:
        logger.warning(f"Falha ao iniciar run: {e}")
        return (f"local_{uuid.uuid4()}", started_at_dt)


def _end_run(run_id, status, started_at_dt, error_message=None):
    """
    Função interna para finalizar um run.
    Calcula duration_sec automaticamente (feito pela classe ExecutionLogger).
    Se status for COMPLETED, garante progress_pct = 100%.
    """
    if not _is_telemetry_enabled() or run_id.startswith("local_"):
        return

    exec_logger = _execution_loggers.get(run_id)
    if exec_logger is None:
        logger.warning(f"ExecutionLogger não encontrado para run_id {run_id}")
        return

    try:
        # Garantir progress 100% se COMPLETED
        if status == "COMPLETED":
            exec_logger.update_progress(100.0)

        # Finalizar o run
        exec_logger.end_run(status, error_message)
        logger.info(f"Telemetria: Execução finalizada. run_id={run_id}, status={status}")

        # Remover do cache
        _execution_loggers.pop(run_id, None)
    except Exception as e:
        logger.warning(f"Falha ao finalizar run: {e}")


def end_run_ok(run_id, started_at_dt):
    """Atualiza o status de um run para 'COMPLETED'."""
    _end_run(run_id, "COMPLETED", started_at_dt)


def end_run_failed(run_id, started_at_dt, error_message):
    """Atualiza o status de um run para 'FAILED' e registra o erro."""
    if isinstance(error_message, Exception):
        error_msg = f"{type(error_message).__name__}: {str(error_message)}"
    else:
        error_msg = str(error_message)
    _end_run(run_id, "FAILED", started_at_dt, error_msg[:2000])  # Trunca a mensagem de erro


def end_run_cancelled(run_id, started_at_dt, reason):
    """Atualiza o status de um run para 'CANCELLED'."""
    _end_run(run_id, "CANCELLED", started_at_dt, reason[:2000])


def update_progress(run_id, progress_pct):
    """Atualiza o percentual de progresso de um run."""
    if not _is_telemetry_enabled() or run_id.startswith("local_"):
        return

    exec_logger = _execution_loggers.get(run_id)
    if exec_logger is None:
        return

    try:
        exec_logger.update_progress(progress_pct)
        logger.debug(f"Telemetria: Progresso atualizado para {progress_pct:.1f}%")
    except Exception as e:
        logger.warning(f"Falha ao atualizar progresso: {e}")


# ==============================================================================
# STEP-LEVEL FUNCTIONS (Tabela: public.execution_steps)
# ==============================================================================

def start_step(run_id, step_name, step_order):
    """Registra o início de um passo."""
    if not _is_telemetry_enabled() or run_id.startswith("local_"):
        return

    exec_logger = _execution_loggers.get(run_id)
    if exec_logger is None:
        return

    try:
        # Cachear o step_name para usar em _end_step
        _step_cache[(run_id, step_order)] = step_name

        # Registrar o step
        exec_logger.start_step(step_name, step_order)
        logger.debug(f"Telemetria: Step {step_order} ({step_name}) iniciado.")
    except Exception as e:
        logger.warning(f"Falha ao iniciar step: {e}")


def _end_step(run_id, step_order, status, error_message=None):
    """Função interna para finalizar um passo."""
    if not _is_telemetry_enabled() or run_id.startswith("local_"):
        return

    exec_logger = _execution_loggers.get(run_id)
    if exec_logger is None:
        return

    # Recuperar step_name do cache
    step_name = _step_cache.get((run_id, step_order))
    if step_name is None:
        logger.warning(f"Step {step_order} não encontrado no cache. Não é possível finalizar.")
        return

    try:
        exec_logger.end_step(step_name, status, error_message)
        logger.debug(f"Telemetria: Step {step_order} ({step_name}) finalizado com status={status}.")

        # Limpar do cache
        _step_cache.pop((run_id, step_order), None)
    except Exception as e:
        logger.warning(f"Falha ao finalizar step: {e}")


def end_step_ok(run_id, step_order):
    """Atualiza o status de um passo para 'COMPLETED'."""
    _end_step(run_id, step_order, "COMPLETED")


def end_step_failed(run_id, step_order, error_message):
    """Atualiza o status de um passo para 'FAILED' e registra o erro."""
    if isinstance(error_message, Exception):
        error_msg = f"{type(error_message).__name__}: {str(error_message)}"
    else:
        error_msg = str(error_message)
    _end_step(run_id, step_order, "FAILED", error_msg[:2000])  # Trunca


# ==============================================================================
# CONTEXT MANAGER (Opcional - para blocos de código inline)
# ==============================================================================

class StepLogger:
    """
    Context manager para instrumentar passos automaticamente.

    Uso:
        with StepLogger(run_id, "Nome do Step", 1):
            # código do passo
    """

    def __init__(self, run_id, step_name, step_order):
        self.run_id = run_id
        self.step_name = step_name
        self.step_order = step_order

    def __enter__(self):
        start_step(self.run_id, self.step_name, self.step_order)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            end_step_ok(self.run_id, self.step_order)
        else:
            end_step_failed(self.run_id, self.step_order, exc_val)
        return False  # Não suprimir exceção