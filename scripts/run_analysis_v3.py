#!/usr/bin/env python3
"""
Script para ejecutar el análisis con el clasificador v3 (mejorado).
Re-clasifica todos los expedientes que ya tienen texto de resolución.
"""

import json
import logging
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import PROCESSED_DIR, OUTPUT_DIR
from src.extraction.pdf_handler import PDFHandler
from src.analysis.classifier_v2 import ResolutionClassifierV2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== ANÁLISIS CON CLASIFICADOR V3 ===")

    # Cargar expedientes existentes
    input_file = PROCESSED_DIR / "expedientes_2024_v2.json"
    if not input_file.exists():
        logger.error(f"No se encontró: {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        expedientes = json.load(f)

    logger.info(f"Expedientes cargados: {len(expedientes)}")

    # Inicializar
    classifier = ResolutionClassifierV2()
    pdf_handler = PDFHandler()

    # Contador de resultados
    results = Counter()
    reclassified = 0

    for i, exp in enumerate(expedientes, 1):
        if not exp.get("url_resolucion"):
            continue

        # Descargar PDF y clasificar
        text = pdf_handler.extract_text_from_url(exp["url_resolucion"])
        if not text:
            results["ERROR"] += 1
            continue

        # Clasificar
        result = classifier.classify(text)

        old_result = exp.get("resultado_clasificado", "N/A")
        new_result = result.categoria

        # Actualizar
        exp["resultado_clasificado"] = new_result
        exp["keywords_encontradas"] = [f"texto:{result.texto_clave[:30]}"]
        exp["confianza"] = result.confianza

        results[new_result] += 1

        if old_result != new_result:
            reclassified += 1
            logger.info(f"[{i}] {exp['id']}: {old_result} -> {new_result}")

        if i % 50 == 0:
            logger.info(f"Progreso: {i}/{len(expedientes)}")

    pdf_handler.close()

    # Guardar resultados
    output_file = PROCESSED_DIR / "expedientes_2024_v3.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(expedientes, f, ensure_ascii=False, indent=2)
    logger.info(f"Guardado: {output_file}")

    # Generar resumen CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_file = OUTPUT_DIR / "resumen_2024_v3.csv"
    total = sum(results.values())

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("Resultado,Cantidad,Porcentaje\n")
        for result, count in sorted(results.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            f.write(f"{result},{count},{pct:.1f}%\n")
        f.write(f"TOTAL,{total},100%\n")

    logger.info(f"Resumen guardado: {summary_file}")

    # Mostrar estadísticas
    logger.info("\n=== RESULTADOS V3 ===")
    for result, count in sorted(results.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        logger.info(f"  {result}: {count} ({pct:.1f}%)")
    logger.info(f"  TOTAL: {total}")
    logger.info(f"  Reclasificados: {reclassified}")


if __name__ == "__main__":
    main()
