"""
Scraper para la web de expedientes de la CNMC.
"""

import re
import logging
from datetime import datetime
from typing import Generator, Optional
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

import sys
sys.path.insert(0, str(__file__).rsplit("/", 4)[0])
from config.settings import CNMC_BASE_URL
from src.extraction.models import Expediente
from src.utils.http_client import CurlClient

logger = logging.getLogger(__name__)

# URL del buscador de expedientes con filtros
# idtipoexp=6062 -> Conflictos de acceso - Energía
EXPEDIENTES_URL = "https://www.cnmc.es/va/expedientes"


class CNMCScraper:
    """Scraper para extraer expedientes de la CNMC."""

    # Mapeo de tipos de expediente a sus IDs
    TIPO_EXPEDIENTE_IDS = {
        "Conflictos de acceso - Energía": "6062",
        # Añadir más según se necesiten
    }

    def __init__(self, client: Optional[CurlClient] = None):
        self.client = client or CurlClient()
        self.base_url = CNMC_BASE_URL

    def _build_search_url(
        self,
        page: int = 0,
        tipo_expediente: Optional[str] = None,
        ambito: str = "All",
    ) -> str:
        """Construye la URL de búsqueda con filtros."""
        params = {
            "t": "",  # Término de búsqueda vacío
            "idambito": ambito,
            "hidprocedim": "All",
        }

        # Añadir tipo de expediente si se especifica
        if tipo_expediente:
            tipo_id = self.TIPO_EXPEDIENTE_IDS.get(tipo_expediente, tipo_expediente)
            params["idtipoexp"] = tipo_id
        else:
            params["idtipoexp"] = "All"

        # Añadir página si no es la primera
        if page > 0:
            params["page"] = page

        return f"{EXPEDIENTES_URL}?{urlencode(params)}"

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsea una fecha en varios formatos."""
        if not date_str:
            return None

        date_str = date_str.strip()

        # Formatos: "01 Apr 2014", "15/03/2024", "2024-03-15"
        formats = [
            "%d %b %Y",      # 01 Apr 2014
            "%d %B %Y",      # 01 April 2014
            "%d/%m/%Y",      # 15/03/2024
            "%Y-%m-%d",      # 2024-03-15
        ]

        # Mapeo de meses en español/valenciano
        month_map = {
            "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
            "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
            "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
            "gen": "Jan", "abril": "Apr", "maig": "May", "juny": "Jun",
            "juliol": "Jul", "agost": "Aug", "setembre": "Sep",
            "octubre": "Oct", "novembre": "Nov", "desembre": "Dec",
        }

        # Normalizar meses
        date_lower = date_str.lower()
        for es, en in month_map.items():
            if es in date_lower:
                date_str = re.sub(es, en, date_str, flags=re.IGNORECASE)
                break

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"No se pudo parsear fecha: {date_str}")
        return None

    def _extract_expediente_from_row(self, row: BeautifulSoup) -> Optional[Expediente]:
        """Extrae un expediente de una fila de resultados."""
        try:
            # Buscar el h2 con los enlaces del expediente
            h2 = row.find("h2")
            if not h2:
                return None

            links = h2.find_all("a", href=True)
            if not links:
                return None

            # Primer enlace: ID del expediente (ej: CFT/DE/014/17)
            # Segundo enlace: título/descripción
            exp_id = links[0].get_text(strip=True)
            url = urljoin(self.base_url, links[0]["href"])

            titulo = ""
            if len(links) > 1:
                titulo = links[1].get_text(strip=True)
                # La URL canónica suele estar en el segundo enlace
                if "/expedientes/" in links[1].get("href", ""):
                    url = urljoin(self.base_url, links[1]["href"])

            # Buscar fecha en el elemento time
            fecha = None
            time_elem = row.find("time", class_="datetime")
            if time_elem:
                # Usar el atributo datetime si existe
                dt_attr = time_elem.get("datetime")
                if dt_attr:
                    try:
                        fecha = datetime.fromisoformat(dt_attr.replace("Z", "+00:00")).date()
                    except ValueError:
                        pass
                # O el texto
                if not fecha:
                    fecha = self._parse_date(time_elem.get_text(strip=True))

            # Buscar tipo y sector
            tipo = ""
            sector = ""
            tipo_elem = row.find("p", class_="small")
            if tipo_elem:
                tipo_text = tipo_elem.get_text(strip=True)
                # Formato: "Conflictos - Conflictos de acceso - Energía"
                parts = [p.strip() for p in tipo_text.split("-")]
                if len(parts) >= 2:
                    sector = parts[0]
                    tipo = " - ".join(parts[1:])

            # Buscar último resultado
            ultimo_resultado = ""
            result_elem = row.find("span", class_="views-field-title")
            if result_elem:
                ultimo_resultado = result_elem.get_text(strip=True)

            return Expediente(
                id=exp_id,
                titulo=titulo,
                fecha=fecha,
                tipo=tipo or "Conflictos de acceso - Energía",
                sector=sector or "Conflictos",
                ambito="Energía",
                ultimo_resultado=ultimo_resultado,
                url=url,
            )

        except Exception as e:
            logger.error(f"Error extrayendo expediente: {e}")
            return None

    def _parse_expedientes_page(self, html: str) -> list[Expediente]:
        """Parsea una página de resultados."""
        soup = BeautifulSoup(html, "lxml")
        expedientes = []

        # Los expedientes están en div.row.views-row con m-bott-20
        rows = soup.find_all("div", class_=lambda c: c and "views-row" in c and "m-bott-20" in c)

        logger.debug(f"Filas encontradas: {len(rows)}")

        for row in rows:
            exp = self._extract_expediente_from_row(row)
            if exp:
                expedientes.append(exp)

        return expedientes

    def _get_total_pages(self, html: str) -> int:
        """Obtiene el número total de páginas."""
        soup = BeautifulSoup(html, "lxml")

        # Buscar paginación
        pager = soup.find("nav", class_="pager") or soup.find("ul", class_="pagination")
        if pager:
            # Buscar el enlace a la última página
            page_links = pager.find_all("a", href=True)
            max_page = 0
            for link in page_links:
                href = link.get("href", "")
                match = re.search(r"page=(\d+)", href)
                if match:
                    max_page = max(max_page, int(match.group(1)))
            return max_page + 1  # Las páginas empiezan en 0

        return 1

    def scrape_expedientes(
        self,
        tipo_expediente: str = "Conflictos de acceso - Energía",
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        max_pages: Optional[int] = None,
        reverse: bool = True,
    ) -> Generator[Expediente, None, None]:
        """
        Extrae expedientes de la CNMC.

        Args:
            tipo_expediente: Tipo de expediente a filtrar
            year_from: Filtrar desde este año (inclusive)
            year_to: Filtrar hasta este año (inclusive)
            max_pages: Máximo de páginas a procesar
            reverse: Si True, empieza desde las páginas más recientes (por defecto True)

        Yields:
            Expediente: Cada expediente encontrado
        """
        # Primero obtener el total de páginas
        url = self._build_search_url(page=0, tipo_expediente=tipo_expediente)
        html = self.client.get(url)
        if not html or "403 Forbidden" in html:
            logger.error("No se pudo obtener la primera página")
            return

        total_pages = self._get_total_pages(html)
        logger.info(f"Total de páginas detectadas: {total_pages}")

        # Determinar el orden de las páginas
        if reverse:
            # Empezar desde la última página (expedientes más recientes)
            pages = range(total_pages - 1, -1, -1)
            logger.info("Orden: desde más recientes a más antiguos")
        else:
            pages = range(total_pages)
            logger.info("Orden: desde más antiguos a más recientes")

        expedientes_count = 0
        pages_processed = 0
        stop_early = False

        for page in pages:
            if stop_early:
                break

            url = self._build_search_url(page=page, tipo_expediente=tipo_expediente)
            logger.info(f"Scrapeando página {page + 1}/{total_pages}: {url}")

            html = self.client.get(url)
            if not html or "403 Forbidden" in html:
                logger.error(f"No se pudo obtener la página {page + 1}")
                continue

            expedientes = self._parse_expedientes_page(html)
            logger.info(f"Expedientes encontrados en página {page + 1}: {len(expedientes)}")

            if not expedientes:
                continue

            # Contador de expedientes fuera de rango en esta página
            out_of_range_count = 0

            for exp in expedientes:
                # Filtrar por año si se especifica
                if exp.fecha:
                    if year_from and exp.fecha.year < year_from:
                        out_of_range_count += 1
                        continue
                    if year_to and exp.fecha.year > year_to:
                        out_of_range_count += 1
                        continue

                expedientes_count += 1
                yield exp

            pages_processed += 1

            # Si estamos en modo reverse y todos los expedientes de esta página
            # son anteriores a year_from, podemos parar (están ordenados cronológicamente)
            if reverse and year_from and out_of_range_count == len(expedientes):
                logger.info(f"Todos los expedientes de página {page + 1} son anteriores a {year_from}, parando")
                stop_early = True

            # Verificar límite de páginas
            if max_pages and pages_processed >= max_pages:
                logger.info(f"Alcanzado límite de páginas: {max_pages}")
                break

        logger.info(f"Total expedientes extraídos: {expedientes_count}")

        logger.info(f"Total expedientes extraídos: {expedientes_count}")

    def get_expediente_detail(self, url: str) -> Optional[dict]:
        """
        Obtiene los detalles de un expediente, incluyendo URLs de PDFs.

        Args:
            url: URL de la página del expediente

        Returns:
            Diccionario con los detalles
        """
        html = self.client.get(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        details = {}

        # Buscar enlaces a PDFs
        pdf_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))

        resolution_urls = []
        for link in pdf_links:
            href = link.get("href", "")
            full_url = urljoin(self.base_url, href)
            text = link.get_text(strip=True).lower()

            # Priorizar resoluciones
            if any(kw in text for kw in ["resolución", "resolucion", "publ_"]):
                resolution_urls.insert(0, full_url)
            else:
                resolution_urls.append(full_url)

        details["pdf_urls"] = resolution_urls
        details["url_resolucion"] = resolution_urls[0] if resolution_urls else None

        # Extraer campos adicionales
        for field_name in ["fecha", "tipo", "estado", "sector", "ambito"]:
            elem = soup.find(class_=re.compile(f"page-nw-proceedings-{field_name}"))
            if elem:
                details[field_name] = elem.get_text(strip=True)

        return details

    def close(self):
        """Cierra el cliente."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
