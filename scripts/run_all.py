#!/usr/bin/env python3
"""
Script principal para ejecutar el pipeline completo.
"""

import argparse
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.run_extraction import run_extraction
from scripts.run_analysis import run_analysis
from scripts.run_reporting import run_reporting

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline(
    year_from: int = 2024,
    year_to: int = None,
    tipo_expediente: str = None,
    ambito: str = None,
    max_pages: int = None,
    skip_extraction: bool = False,
    skip_analysis: bool = False,
    skip_reporting: bool = False,
):
    """
    Ejecuta el pipeline completo de extracción, análisis y reporting.

    Args:
        year_from: Año inicial
        year_to: Año final
        tipo_expediente: Tipo de expediente
        ambito: Ámbito (Energía, Competencia, etc.)
        max_pages: Máximo de páginas a procesar
        skip_extraction: Si True, omite la extracción
        skip_analysis: Si True, omite el análisis
        skip_reporting: Si True, omite el reporting
    """
    logger.info("=" * 60)
    logger.info("PIPELINE DE ANÁLISIS DE RESOLUCIONES CNMC")
    logger.info("=" * 60)

    # 1. EXTRACCIÓN
    if not skip_extraction:
        logger.info("\n>>> PASO 1: EXTRACCIÓN <<<\n")
        run_extraction(
            year_from=year_from,
            year_to=year_to,
            tipo_expediente=tipo_expediente,
            ambito=ambito,
            max_pages=max_pages,
        )
    else:
        logger.info("\n>>> PASO 1: EXTRACCIÓN (OMITIDO) <<<\n")

    # 2. ANÁLISIS
    if not skip_analysis:
        logger.info("\n>>> PASO 2: ANÁLISIS <<<\n")
        run_analysis()
    else:
        logger.info("\n>>> PASO 2: ANÁLISIS (OMITIDO) <<<\n")

    # 3. REPORTING
    if not skip_reporting:
        logger.info("\n>>> PASO 3: REPORTING <<<\n")
        run_reporting()
    else:
        logger.info("\n>>> PASO 3: REPORTING (OMITIDO) <<<\n")

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETADO")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo de análisis de resoluciones CNMC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

  # Ejecutar pipeline completo con filtros por defecto (2024, Conflictos de acceso - Energía)
  python run_all.py

  # Ejecutar solo desde 2023
  python run_all.py --year-from 2023

  # Omitir extracción (usar datos existentes)
  python run_all.py --skip-extraction

  # Solo generar informes
  python run_all.py --skip-extraction --skip-analysis
        """,
    )
    parser.add_argument("--year-from", type=int, default=2024, help="Año inicial (default: 2024)")
    parser.add_argument("--year-to", type=int, help="Año final")
    parser.add_argument("--tipo", type=str, help="Tipo de expediente")
    parser.add_argument("--ambito", type=str, help="Ámbito (Energía, Competencia, etc.)")
    parser.add_argument("--max-pages", type=int, help="Máximo de páginas a procesar")
    parser.add_argument("--skip-extraction", action="store_true", help="Omitir extracción")
    parser.add_argument("--skip-analysis", action="store_true", help="Omitir análisis")
    parser.add_argument("--skip-reporting", action="store_true", help="Omitir reporting")

    args = parser.parse_args()

    run_pipeline(
        year_from=args.year_from,
        year_to=args.year_to,
        tipo_expediente=args.tipo,
        ambito=args.ambito,
        max_pages=args.max_pages,
        skip_extraction=args.skip_extraction,
        skip_analysis=args.skip_analysis,
        skip_reporting=args.skip_reporting,
    )


if __name__ == "__main__":
    main()
