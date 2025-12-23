# -*- coding: utf-8 -*-
# services/db_service.py

import os
import logging
import sys
import uuid
from datetime import datetime
from threading import Lock

import psycopg2
from psycopg2 import pool

# --- CONFIGURAÇÃO INICIAL ---
# Usamos o logger raiz para que ele herde a configuração do script principal
# Isso garante que a formatação (incluindo o run_id) seja a mesma.
logger = logging.getLogger(__name__)

# --- FUNÇÃO PARA OBTER DSN DE FORMA LAZY ---
def _get_dsn():
    """Obtém o DSN do banco de forma lazy (após o .env ser carregado)."""
    return os.getenv("EXECUTION_DB_DSN")


class ExecutionLogger:
    """
    Gerencia o logging da execução de processos em um banco de dados PostgreSQL.
    """
    _pool = None
    _pool_lock = Lock()

    def __init__(self, process_name: str, run_id_override: str = None):
        """
        Inicializa o logger. Aceita um 'run_id_override' para alinhar
        com o log de arquivo do script principal.
        """
        self.process_name = process_name

        if run_id_override:
            self.run_id = run_id_override
        else:
            self.run_id = str(uuid.uuid4())

        self.start_time = None
        self._initialize_pool()

    @classmethod
    def _initialize_pool(cls):
        """Inicializa o pool de conexões de forma thread-safe."""
        dsn = _get_dsn()
        if not dsn:
            logger.debug("Não é possível inicializar o pool de conexões; a DSN do DB está ausente.")
            return

        with cls._pool_lock:
            if not cls._pool:
                try:
                    logger.info("Inicializando o pool de conexões do PostgreSQL...")
                    cls._pool = psycopg2.pool.SimpleConnectionPool(
                        minconn=1,
                        maxconn=5,
                        dsn=dsn
                    )
                    logger.info("Pool de conexões criado com sucesso.")
                except psycopg2.OperationalError as e:
                    logger.warning(f"Falha ao inicializar o pool de conexões: {e}")
                    logger.warning("Telemetria desabilitada. Continuando execução...")
                    cls._pool = None

    def _execute(self, query: str, params: tuple = None, fetch: str = None):
        """
        Executa uma query no banco de dados usando uma conexão do pool.
        """
        if not self._pool:
            # Pool não está disponível
            return None

        conn = None
        try:
            conn = self._pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows_affected = cursor.rowcount

                # Armazena o resultado antes de commitar
                result = None
                if fetch == 'one':
                    result = cursor.fetchone()
                elif fetch == 'all':
                    result = cursor.fetchall()
                else:
                    result = rows_affected

            # IMPORTANTE: Commit DEVE acontecer ANTES de retornar
            conn.commit()
            return result

        except psycopg2.Error as e:
            # Log detalhado do erro incluindo a query
            logger.error(f"Erro no banco de dados de telemetria: {e}")
            logger.error(f"Query que falhou: {query}")
            logger.error(f"Parâmetros: {params}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                self._pool.putconn(conn)

    def start_run(self) -> str:
        """Inicia uma nova execução, registrando-a na tabela execution_runs."""
        if not self.run_id:
            logger.error("start_run chamado, mas o run_id não foi definido.")
            return ""

        self.start_time = datetime.now()

        sql = """
            INSERT INTO public.execution_runs (run_id, process_name, started_at, status, progress_pct)
            VALUES (%s, %s, %s, 'RUNNING', 0);
        """

        rows_affected = self._execute(sql, (self.run_id, self.process_name, self.start_time))

        if rows_affected is None:
            logger.warning(f"DB: Falha ao iniciar execução {self.run_id} - telemetria desabilitada")
        elif rows_affected == 0:
            logger.warning(f"DB: INSERT não afetou nenhuma linha para run_id {self.run_id}")
        else:
            logger.info(f"DB: Execução iniciada com run_id: {self.run_id} para {self.process_name}")

        return self.run_id

    def end_run(self, status: str, error_message: str = None):
        """
        Finaliza a execução atual.

        Args:
            status: Status final ('COMPLETED' ou 'FAILED')
            error_message: Mensagem de erro (opcional)
        """
        if not self.run_id or not self.start_time:
            logger.error("end_run chamado sem uma execução ativa.")
            return

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        final_progress = 100 if status == 'COMPLETED' else None

        sql = """
            UPDATE public.execution_runs
            SET ended_at = %s, status = %s, error_message = %s, duration_sec = %s,
                progress_pct = COALESCE(%s, progress_pct)
            WHERE run_id = %s;
        """

        rows_affected = self._execute(sql, (end_time, status, error_message, int(duration), final_progress, self.run_id))

        if rows_affected is None:
            logger.warning(f"DB: Falha ao finalizar execução {self.run_id} - telemetria desabilitada")
        elif rows_affected == 0:
            logger.error(f"DB: Nenhuma linha foi atualizada para run_id {self.run_id} - execução não foi encontrada no banco")
        else:
            logger.info(f"DB: Execução {self.run_id} finalizada com status {status} em {duration:.2f}s")

    def start_step(self, step_name: str, step_order: int):
        """Registra o início de uma etapa."""
        if not self.run_id:
            return

        sql = """
            INSERT INTO public.execution_steps (run_id, step_name, step_order, started_at, status)
            VALUES (%s, %s, %s, %s, 'RUNNING');
        """

        self._execute(sql, (self.run_id, step_name, step_order, datetime.now()))
        logger.debug(f"DB: Etapa '{step_name}' (ordem {step_order}) iniciada.")

    def end_step(self, step_name: str, status: str, error_message: str = None):
        """Atualiza o status de uma etapa."""
        if not self.run_id:
            return

        sql = """
            UPDATE public.execution_steps
            SET ended_at = %s, status = %s, error_message = %s
            WHERE run_id = %s AND step_name = %s AND ended_at IS NULL;
        """

        rows_affected = self._execute(sql, (datetime.now(), status, error_message, self.run_id, step_name))

        if rows_affected is None:
            logger.warning(f"DB: Falha ao finalizar etapa '{step_name}' - telemetria desabilitada")
        elif rows_affected == 0:
            logger.warning(f"DB: Nenhuma linha foi atualizada para etapa '{step_name}' - etapa não foi encontrada ou já estava finalizada")
        else:
            logger.debug(f"DB: Etapa '{step_name}' finalizada com status: {status}")

    def update_progress(self, progress: float):
        """Atualiza o percentual de progresso da execução."""
        if not self.run_id:
            return
        progress = max(0.0, min(100.0, progress))

        sql = "UPDATE public.execution_runs SET progress_pct = %s WHERE run_id = %s;"

        rows_affected = self._execute(sql, (progress, self.run_id))

        if rows_affected is None:
            logger.warning(f"DB: Falha ao atualizar progresso - telemetria desabilitada")
        elif rows_affected == 0:
            logger.warning(f"DB: Nenhuma linha foi atualizada ao tentar atualizar progresso para {progress:.2f}%")
        else:
            logger.debug(f"DB: Progresso atualizado para {progress:.2f}%.")
