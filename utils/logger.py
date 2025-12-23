"""
Configuração de logging para o projeto.

Configura logging para arquivo e console.
"""
import os
import logging
from datetime import datetime


def setup_logger(log_name: str) -> None:
    """
    Configura logging para arquivo e console.

    Cria pasta logs/ se não existir e configura:
    - Handler de arquivo: logs/{log_name}_{timestamp}_pid{pid}.log
    - Handler de console: stdout
    - Formato: %(asctime)s - %(levelname)s - %(message)s
    - Level: INFO

    Args:
        log_name: Nome base do arquivo de log (sem extensão)
    """
    # Criar pasta de logs se não existir
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Nome do arquivo de log com timestamp e PID
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    pid = os.getpid()
    log_filename = f"{log_name}_{timestamp}_pid{pid}.log"
    log_filepath = os.path.join(logs_dir, log_filename)

    # Formato comum para arquivo e console
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # IMPORTANTE: Remover handlers antigos para evitar duplicação
    root_logger.handlers.clear()

    # Handler para arquivo
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Handler para console (com mesmo formato)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info(f"Log sendo salvo em: {log_filepath}")