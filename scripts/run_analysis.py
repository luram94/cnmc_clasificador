#!/usr/bin/env python3
"""
Script para ejecutar el análisis de resoluciones.
Descarga PDFs y los clasifica en: ESTIMADO, DESESTIMADO, ARCHIVADO.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import PROCESSED_DIR, OUTPUT_DIR
from src.extraction.pdf_handler import PDFHandler
from src.analysis.classifier import ResolutionClassifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_analysis(
    input_file: str = "expedientes_raw.json",
    output_file: str = "expedientes_analyzed.json",
) -> dict:
    """
    Ejecuta el análisis de resoluciones.

    Args:
        input_file: Archivo de entrada con expedientes
        output_file: Archivo de salida

    Returns:
        Diccionario con estadísticas
    """
    logger.info("=== ANÁLISIS DE RESOLUCIONES ===")

    # Cargar expedientes
    input_path = PROCESSED_DIR / input_file
    if not input_path.exists():
        logger.error(f"No se encontró: {input_path}")
        return {}

    with open(input_path, "r", encoding="utf-8") as f:
        expedientes = json.load(f)

    logger.info(f"Expedientes cargados: {len(expedientes)}")

    # Inicializar
    classifier = ResolutionClassifier()
    pdf_handler = PDFHandler()

    # Contador de resultados
    results = Counter()
    processed = 0

    # Contar expedientes con URL de resolucion
    expedientes_con_pdf = [e for e in expedientes if e.get("url_resolucion")]
    total_con_pdf = len(expedientes_con_pdf)
    logger.info(f"Expedientes con PDF a analizar: {total_con_pdf}")

    for i, exp in enumerate(expedientes, 1):
        if not exp.get("url_resolucion"):
            continue

        # Descargar PDF y extraer texto
        logger.info(f"[{processed + 1}/{total_con_pdf}] Procesando: {exp.get('id', 'N/A')}...")
        text = pdf_handler.extract_text_from_url(exp["url_resolucion"])
        if not text:
            logger.warning(f"  No se pudo extraer texto del PDF")
            results["ERROR"] += 1
            continue

        # Clasificar
        result = classifier.classify(text)

        # Actualizar expediente
        exp["resultado_clasificado"] = result.categoria
        exp["confianza"] = result.confianza
        exp["texto_clave"] = result.texto_clave[:100] if result.texto_clave else ""

        results[result.categoria] += 1
        processed += 1
        logger.info(f"  Resultado: {result.categoria} (confianza: {result.confianza})")

    pdf_handler.close()

    # Guardar resultados
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(expedientes, f, ensure_ascii=False, indent=2)
    logger.info(f"Guardado: {output_path}")

    # Generar resumen CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = OUTPUT_DIR / "resumen.csv"
    total = sum(results.values())

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("Resultado,Cantidad,Porcentaje\n")
        for result, count in sorted(results.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            f.write(f"{result},{count},{pct:.1f}%\n")
        f.write(f"TOTAL,{total},100%\n")

    logger.info(f"Resumen guardado: {summary_file}")

    # Mostrar estadísticas
    logger.info("\n=== RESULTADOS ===")
    for result, count in sorted(results.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        logger.info(f"  {result}: {count} ({pct:.1f}%)")
    logger.info(f"  TOTAL: {total}")

    return dict(results)


def main():
    parser = argparse.ArgumentParser(description="Análisis de resoluciones CNMC")
    parser.add_argument(
        "--input",
        type=str,
        default="expedientes_raw.json",
        help="Archivo de entrada"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="expedientes_analyzed.json",
        help="Archivo de salida"
    )

    args = parser.parse_args()
    run_analysis(input_file=args.input, output_file=args.output)


if __name__ == "__main__":
    main()
