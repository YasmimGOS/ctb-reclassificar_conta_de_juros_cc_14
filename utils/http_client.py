"""
Cliente HTTP seguro com retry e timeout.

Fornece sessão HTTP configurada com:
- Retry automático (5 tentativas)
- Backoff exponencial
- User-Agent identificável
- Timeout obrigatório
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HTTPClient:
    """
    Cliente HTTP seguro com retry, timeout e User-Agent.

    Configuração:
    - Retry: 5 tentativas
    - Backoff: exponencial (1s, 2s, 4s, 8s, 16s)
    - Status codes para retry: 408, 429, 500, 502, 503, 504
    - User-Agent: ctb-reclassificar-cc14/1.0
    """

    def __init__(self):
        self.session = requests.Session()

        # Configurar retry
        retry = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[408, 429, 500, 502, 503, 504]
        )

        # Configurar adapter
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=retry
        )

        # Montar sessão
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'User-Agent': 'ctb-reclassificar-cc14/1.0'
        })

    def get_session(self) -> requests.Session:
        """
        Retorna sessão HTTP configurada.

        Returns:
            requests.Session: Sessão com retry e timeout configurados
        """
        return self.session

    def post(self, url: str, timeout: int = 30, **kwargs):
        """POST com timeout obrigatório (default 30s)."""
        return self.session.post(url, timeout=timeout, **kwargs)

    def put(self, url: str, timeout: int = 30, **kwargs):
        """PUT com timeout obrigatório (default 30s)."""
        return self.session.put(url, timeout=timeout, **kwargs)

    def get(self, url: str, timeout: int = 30, **kwargs):
        """GET com timeout obrigatório (default 30s)."""
        return self.session.get(url, timeout=timeout, **kwargs)
