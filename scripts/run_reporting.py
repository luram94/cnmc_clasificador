#!/usr/bin/env python3
"""
Script para generar informes y reportes.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import PROCESSED_DIR, OUTPUT_DIR
from src.extraction.models import Expediente
from src.reporting.csv_generator import generate_csv, generate_summary_csv
from src.reporting.excel_generator import generate_excel_report
from src.reporting.charts import generate_all_charts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_expedientes(input_file: str) -> list[Expediente]:
    """Carga expedientes desde un archivo JSON."""
    filepath = PROCESSED_DIR / input_file

    if not filepath.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Expediente.from_dict(d) for d in data]


def run_reporting(
    input_file: str = "expedientes_analyzed.json",
    generate_csv_file: bool = True,
    generate_excel: bool = True,
    generate_charts: bool = True,
) -> dict:
    """
    Genera todos los informes.

    Args:
        input_file: Archivo de entrada con expedientes analizados
        generate_csv_file: Si True, genera CSV
        generate_excel: Si True, genera Excel
        generate_charts: Si True, genera gráficos

    Returns:
        Diccionario con paths de archivos generados
    """
    logger.info("=== GENERACIÓN DE INFORMES ===")

    # Cargar expedientes
    expedientes = load_expedientes(input_file)
    logger.info(f"Expedientes cargados: {len(expedientes)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_files = {}

    # Generar CSV
    if generate_csv_file:
        logger.info("Generando CSV...")
        csv_path = generate_csv(expedientes)
        summary_path = generate_summary_csv(expedientes)
        generated_files["csv"] = str(csv_path)
        generated_files["csv_summary"] = str(summary_path)

    # Generar Excel
    if generate_excel:
        logger.info("Generando Excel...")
        excel_path = generate_excel_report(expedientes)
        generated_files["excel"] = str(excel_path)

    # Generar gráficos
    if generate_charts:
        logger.info("Generando gráficos...")
        chart_paths = generate_all_charts(expedientes)
        generated_files["charts"] = [str(p) for p in chart_paths]

    # Mostrar resumen
    logger.info("=== ARCHIVOS GENERADOS ===")
    for key, value in generated_files.items():
        if isinstance(value, list):
            for v in value:
                logger.info(f"  {v}")
        else:
            logger.info(f"  {value}")

    # Mostrar estadísticas rápidas
    logger.info("=== RESUMEN RÁPIDO ===")
    from collections import Counter
    resultados = Counter(exp.resultado_clasificado or "NO_CLASIFICADO" for exp in expedientes)
    total = len(expedientes)

    for resultado, count in resultados.most_common():
        pct = (count / total * 100) if total > 0 else 0
        logger.info(f"  {resultado}: {count} ({pct:.1f}%)")

    return generated_files


def main():
    parser = argparse.ArgumentParser(description="Generación de informes CNMC")
    parser.add_argument("--input", type=str, default="expedientes_analyzed.json", help="Archivo de entrada")
    parser.add_argument("--no-csv", action="store_true", help="No generar CSV")
    parser.add_argument("--no-excel", action="store_true", help="No generar Excel")
    parser.add_argument("--no-charts", action="store_true", help="No generar gráficos")

    args = parser.parse_args()

    run_reporting(
        input_file=args.input,
        generate_csv_file=not args.no_csv,
        generate_excel=not args.no_excel,
        generate_charts=not args.no_charts,
    )


if __name__ == "__main__":
    main()
