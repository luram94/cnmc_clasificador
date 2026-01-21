"""
Configuración global del proyecto CNMC Analyzer.
"""

from pathlib import Path

# Rutas del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"

# URLs base de la CNMC
CNMC_BASE_URL = "https://www.cnmc.es"
CNMC_EXPEDIENTES_URL = f"{CNMC_BASE_URL}/expedientes"

# Configuración de scraping
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 2  # segundos entre requests
MAX_RETRIES = 3

# Headers para simular navegador
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Filtros por defecto para primera iteración
DEFAULT_FILTERS = {
    "year_from": 2024,
    "year_to": None,  # None = hasta la fecha actual
    "tipo_expediente": "Conflictos de acceso",
    "ambito": "Energía",
}

# Keywords para clasificación de resoluciones
CLASSIFICATION_KEYWORDS = {
    "DESESTIMADO": ["desestimar", "desestimado", "desestima", "desestimación"],
    "ESTIMADO": ["estimar", "estimado", "estima", "estimación"],
    "ARCHIVADO": ["archivar", "archivado", "archiva", "archivo"],
}

# Jerarquía para casos con múltiples keywords (mayor prioridad primero)
CLASSIFICATION_HIERARCHY = ["DESESTIMADO", "ESTIMADO", "ARCHIVADO"]

# Configuración de cache
CACHE_ENABLED = True
CACHE_EXPIRE_HOURS = 24
