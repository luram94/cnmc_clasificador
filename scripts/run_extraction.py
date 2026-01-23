#!/usr/bin/env python3
"""
Script para ejecutar la extracción de expedientes de la CNMC.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DEFAULT_FILTERS, PROCESSED_DIR
from src.extraction.scraper import CNMCScraper
from src.extraction.pdf_handler import PDFHandler
from src.extraction.models import Expediente

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_extraction(
    year_from: int = None,
    year_to: int = None,
    tipo_expediente: str = None,
    ambito: str = None,
    max_pages: int = None,
    output_file: str = "expedientes_raw.json",
    extract_pdfs: bool = True,
) -> list[Expediente]:
    """
    Ejecuta la extracción de expedientes.

    Args:
        year_from: Año inicial
        year_to: Año final
        tipo_expediente: Tipo de expediente
        ambito: Ámbito (Energía, Competencia, etc.)
        max_pages: Máximo de páginas a procesar
        output_file: Archivo de salida
        extract_pdfs: Si True, extrae URLs de PDFs

    Returns:
        Lista de expedientes extraídos
    """
    # Usar filtros por defecto si no se especifican
    year_from = year_from or DEFAULT_FILTERS.get("year_from")
    tipo_expediente = tipo_expediente or DEFAULT_FILTERS.get("tipo_expediente")
    ambito = ambito or DEFAULT_FILTERS.get("ambito")

    logger.info("=== EXTRACCIÓN DE EXPEDIENTES CNMC ===")
    logger.info(f"Filtros: año>={year_from}, tipo={tipo_expediente}, ámbito={ambito}")

    expedientes = []

    with CNMCScraper() as scraper:
        # Extraer lista de expedientes (desde más recientes)
        for exp in scraper.scrape_expedientes(
            tipo_expediente=tipo_expediente,
            year_from=year_from,
            year_to=year_to,
            max_pages=max_pages,
            reverse=True,  # Empezar por los más recientes
        ):
            expedientes.append(exp)
            logger.info(f"Extraído: {exp.id} - {exp.titulo[:50] if exp.titulo else 'Sin título'}...")

        # Obtener detalles y URLs de PDFs
        if extract_pdfs:
            logger.info("Extrayendo URLs de resoluciones PDF...")
            for exp in expedientes:
                details = scraper.get_expediente_detail(exp.url)
                if details:
                    exp.url_resolucion = details.get("url_resolucion")

    logger.info(f"Total expedientes extraídos: {len(expedientes)}")

    # Guardar resultados
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / output_file

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump([exp.to_dict() for exp in expedientes], f, ensure_ascii=False, indent=2)

    logger.info(f"Datos guardados en: {output_path}")

    return expedientes


def main():
    parser = argparse.ArgumentParser(description="Extracción de expedientes CNMC")
    parser.add_argument("--year-from", type=int, default=2024, help="Año inicial")
    parser.add_argument("--year-to", type=int, help="Año final")
    parser.add_argument("--tipo", type=str, help="Tipo de expediente")
    parser.add_argument("--ambito", type=str, help="Ámbito (Energía, Competencia, etc.)")
    parser.add_argument("--max-pages", type=int, help="Máximo de páginas a procesar")
    parser.add_argument("--output", type=str, default="expedientes_raw.json", help="Archivo de salida")
    parser.add_argument("--no-pdfs", action="store_true", help="No extraer URLs de PDFs")

    args = parser.parse_args()

    run_extraction(
        year_from=args.year_from,
        year_to=args.year_to,
        tipo_expediente=args.tipo,
        ambito=args.ambito,
        max_pages=args.max_pages,
        output_file=args.output,
        extract_pdfs=not args.no_pdfs,
    )


if __name__ == "__main__":
    main()
