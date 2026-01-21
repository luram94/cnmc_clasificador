"""
Cliente HTTP usando curl (requests está bloqueado por la CNMC).
"""

import subprocess
import time
import logging
import shutil
from typing import Optional

import sys
sys.path.insert(0, str(__file__).rsplit("/", 3)[0])
from config.settings import REQUEST_TIMEOUT, REQUEST_DELAY

logger = logging.getLogger(__name__)


class CurlClient:
    """Cliente HTTP basado en curl para evitar bloqueos anti-bot."""

    def __init__(
        self,
        timeout: int = REQUEST_TIMEOUT,
        delay: float = REQUEST_DELAY,
    ):
        self.timeout = timeout
        self.delay = delay
        self.last_request_time = 0.0

        # Verificar que curl está disponible
        if not shutil.which("curl"):
            raise RuntimeError("curl no está instalado en el sistema")

    def _wait_for_rate_limit(self):
        """Espera si es necesario para respetar el rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def get(self, url: str) -> Optional[str]:
        """
        Realiza una petición GET con curl.

        Args:
            url: URL a obtener

        Returns:
            Contenido HTML o None si falla
        """
        self._wait_for_rate_limit()

        cmd = [
            "curl",
            "-s",  # Silent
            "-L",  # Follow redirects
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: es-ES,es;q=0.9",
            "--max-time", str(self.timeout),
            url,
        ]

        logger.debug(f"GET {url}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 5)
            self.last_request_time = time.time()

            if result.returncode != 0:
                logger.error(f"curl falló con código {result.returncode}: {result.stderr}")
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout en GET {url}")
            return None
        except Exception as e:
            logger.error(f"Error en GET {url}: {e}")
            return None

    def get_binary(self, url: str) -> Optional[bytes]:
        """
        Descarga contenido binario (PDFs, imágenes).

        Args:
            url: URL a descargar

        Returns:
            Contenido en bytes o None si falla
        """
        self._wait_for_rate_limit()

        cmd = [
            "curl",
            "-s",
            "-L",
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--max-time", str(self.timeout),
            url,
        ]

        logger.debug(f"GET (binary) {url}")

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=self.timeout + 5)
            self.last_request_time = time.time()

            if result.returncode != 0:
                logger.error(f"curl falló con código {result.returncode}")
                return None

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout en GET {url}")
            return None
        except Exception as e:
            logger.error(f"Error en GET {url}: {e}")
            return None

    def close(self):
        """No-op para compatibilidad."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Alias para compatibilidad
HTTPClient = CurlClient
