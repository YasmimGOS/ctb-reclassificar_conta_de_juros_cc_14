"""
Rate limiter usando algoritmo Token Bucket.
"""
import time
import logging
from functools import wraps
from typing import Callable


class RateLimiter:
    """
    Decorador para rate limiting (token bucket).

    Limita número de chamadas a uma função em um período de tempo.

    Args:
        max_calls: Número máximo de chamadas permitidas
        period: Período em segundos (ex: 60 para 1 minuto)

    Exemplo:
        @RateLimiter(max_calls=10, period=60)  # 10 chamadas por minuto
        def chamar_api():
            ...
    """

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # Remove chamadas antigas (fora do período)
            self.calls = [c for c in self.calls if c > now - self.period]

            # Verificar se excedeu limite
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    logging.warning(
                        f"Rate limit atingido para {func.__name__}. "
                        f"Aguardando {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
                    self.calls = []

            # Registrar chamada atual
            self.calls.append(time.time())

            # Executar função
            return func(*args, **kwargs)

        return wrapper