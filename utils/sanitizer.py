"""
Sanitização de dados sensíveis para logs e notificações.

Previne vazamento de tokens, credenciais e dados financeiros em logs.
"""
from typing import Any, Dict, List, Union


def sanitize_for_log(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Remove dados sensíveis antes de logar.

    Substitui valores de chaves sensíveis por '***REDACTED***'.

    Args:
        data: Dicionário, lista ou valor a ser sanitizado

    Returns:
        Dados sanitizados (mesma estrutura, valores sensíveis removidos)
    """
    sensitive_keys = [
        'password', 'token', 'secret', 'api_key', 'authorization',
        'client_secret', 'access_token', 'refresh_token', 'bearer',
        'apikey', 'api-key', 'senha', 'credencial'
    ]

    if isinstance(data, dict):
        return {
            k: '***REDACTED***' if any(s in k.lower() for s in sensitive_keys) else sanitize_for_log(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_for_log(item) for item in data]
    else:
        return data


def sanitize_error_for_notification(error_msg: str, max_length: int = 200) -> str:
    """
    Sanitiza mensagem de erro para notificação Teams.

    Remove stack traces e limita tamanho.

    Args:
        error_msg: Mensagem de erro original
        max_length: Tamanho máximo da mensagem

    Returns:
        Mensagem sanitizada
    """
    # Pegar apenas primeira linha (sem stack trace)
    lines = error_msg.split('\n')
    sanitized = lines[0] if lines else error_msg

    # Limitar tamanho
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + '...'

    return sanitized


def log_metadata_only(data: Union[Dict, List], entity_name: str = "item") -> str:
    """
    Retorna string com apenas metadados (count, keys), sem valores.

    Args:
        data: Dicionário ou lista de dados
        entity_name: Nome da entidade (para mensagem)

    Returns:
        String descritiva com metadados
    """
    if isinstance(data, dict):
        keys = list(data.keys())
        return f"{len(keys)} {entity_name}(s): {', '.join(keys[:5])}{'...' if len(keys) > 5 else ''}"
    elif isinstance(data, list):
        return f"{len(data)} {entity_name}(s)"
    else:
        return f"1 {entity_name}"
