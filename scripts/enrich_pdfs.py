#!/usr/bin/env python3
"""
Script para enriquecer expedientes existentes con URLs de resolución PDF.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import PROCESSED_DIR
from src.extraction.scraper import CNMCScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def enrich_with_pdfs(
    input_file: str,
    output_file: str = None,
):
    """
    Enriquece expedientes existentes con URLs de resolución PDF.

    Args:
        input_file: Archivo de entrada con expedientes
        output_file: Archivo de salida (si no se especifica, sobrescribe el de entrada)
    """
    input_path = PROCESSED_DIR / input_file
    output_path = PROCESSED_DIR / (output_file or input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {input_path}")

    # Cargar expedientes
    with open(input_path, "r", encoding="utf-8") as f:
        expedientes = json.load(f)

    logger.info(f"Expedientes cargados: {len(expedientes)}")

    # Contar los que ya tienen URL de resolución
    con_url = sum(1 for exp in expedientes if exp.get("url_resolucion"))
    logger.info(f"Ya tienen URL de resolución: {con_url}")

    # Estadísticas
    stats = {
        "total": len(expedientes),
        "ya_tenian_url": con_url,
        "urls_encontradas": 0,
        "sin_url": 0,
        "errores": 0,
    }

    with CNMCScraper() as scraper:
        for i, exp in enumerate(expedientes, 1):
            # Saltar si ya tiene URL de resolución
            if exp.get("url_resolucion"):
                continue

            exp_id = exp.get("id", "N/A")
            exp_url = exp.get("url")

            if not exp_url:
                logger.warning(f"[{i}/{len(expedientes)}] Sin URL de expediente: {exp_id}")
                stats["errores"] += 1
                continue

            logger.info(f"[{i}/{len(expedientes)}] Obteniendo detalles: {exp_id}")

            try:
                details = scraper.get_expediente_detail(exp_url)
                if details and details.get("url_resolucion"):
                    exp["url_resolucion"] = details["url_resolucion"]
                    stats["urls_encontradas"] += 1
                    logger.info(f"  URL encontrada: {details['url_resolucion'][:70]}...")
                else:
                    stats["sin_url"] += 1
                    logger.warning(f"  No se encontró URL de resolución")
            except Exception as e:
                logger.error(f"  Error: {e}")
                stats["errores"] += 1

            # Guardar progreso cada 50 expedientes
            if i % 50 == 0:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(expedientes, f, ensure_ascii=False, indent=2)
                logger.info(f"  Progreso guardado ({i}/{len(expedientes)})")

    # Guardar resultados finales
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(expedientes, f, ensure_ascii=False, indent=2)

    logger.info(f"Datos guardados en: {output_path}")

    # Mostrar estadísticas
    logger.info("=== ESTADÍSTICAS ===")
    logger.info(f"Total expedientes: {stats['total']}")
    logger.info(f"Ya tenían URL: {stats['ya_tenian_url']}")
    logger.info(f"URLs nuevas encontradas: {stats['urls_encontradas']}")
    logger.info(f"Sin URL de resolución: {stats['sin_url']}")
    logger.info(f"Errores: {stats['errores']}")


def main():
    parser = argparse.ArgumentParser(description="Enriquecer expedientes con URLs de PDF")
    parser.add_argument("--input", type=str, required=True, help="Archivo de entrada")
    parser.add_argument("--output", type=str, help="Archivo de salida (opcional)")

    args = parser.parse_args()

    enrich_with_pdfs(
        input_file=args.input,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
