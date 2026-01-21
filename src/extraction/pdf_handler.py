"""
Manejador de PDFs para extraer texto de resoluciones.
"""

import io
import logging
from typing import Optional

import pdfplumber
from pypdf import PdfReader

import sys
sys.path.insert(0, str(__file__).rsplit("/", 4)[0])
from src.utils.http_client import CurlClient

logger = logging.getLogger(__name__)


class PDFHandler:
    """Maneja la descarga y extracción de texto de PDFs."""

    def __init__(self, client: Optional[CurlClient] = None):
        self.client = client or CurlClient()

    def download_pdf(self, url: str) -> Optional[bytes]:
        """
        Descarga un PDF desde una URL.

        Args:
            url: URL del PDF

        Returns:
            Contenido del PDF en bytes o None si falla
        """
        try:
            content = self.client.get_binary(url)

            if not content:
                logger.error(f"No se pudo descargar PDF: {url}")
                return None

            # Verificar que parece un PDF
            if not content.startswith(b"%PDF"):
                logger.warning(f"El contenido no parece ser PDF: {url}")
                # Intentar de todas formas

            return content

        except Exception as e:
            logger.error(f"Error descargando PDF {url}: {e}")
            return None

    def extract_text_pypdf(self, pdf_content: bytes) -> str:
        """
        Extrae texto de un PDF usando pypdf (más rápido, menos preciso).
        """
        try:
            reader = PdfReader(io.BytesIO(pdf_content))
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extrayendo texto con pypdf: {e}")
            return ""

    def extract_text_pdfplumber(self, pdf_content: bytes) -> str:
        """
        Extrae texto de un PDF usando pdfplumber (más lento, más preciso).
        """
        try:
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                text_parts = []

                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)

                return "\n".join(text_parts)

        except Exception as e:
            logger.error(f"Error extrayendo texto con pdfplumber: {e}")
            return ""

    def extract_text(self, pdf_content: bytes, use_pdfplumber: bool = True) -> str:
        """
        Extrae texto de un PDF.

        Args:
            pdf_content: Contenido del PDF en bytes
            use_pdfplumber: Si True, usa pdfplumber (más preciso pero lento)

        Returns:
            Texto extraído
        """
        if use_pdfplumber:
            text = self.extract_text_pdfplumber(pdf_content)
            if not text:
                text = self.extract_text_pypdf(pdf_content)
        else:
            text = self.extract_text_pypdf(pdf_content)

        return text

    def extract_text_from_url(self, url: str, use_pdfplumber: bool = True) -> Optional[str]:
        """
        Descarga un PDF y extrae su texto.

        Args:
            url: URL del PDF
            use_pdfplumber: Si True, usa pdfplumber para extracción

        Returns:
            Texto extraído o None si falla
        """
        pdf_content = self.download_pdf(url)
        if not pdf_content:
            return None

        return self.extract_text(pdf_content, use_pdfplumber)

    def close(self):
        """Cierra el cliente."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
