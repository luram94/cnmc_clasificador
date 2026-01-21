#!/usr/bin/env python3
"""
Script para ejecutar el análisis de resoluciones.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import PROCESSED_DIR
from src.extraction.models import Expediente
from src.extraction.pdf_handler import PDFHandler
from src.analysis.classifier import ResolutionClassifier
from src.analysis.rules import RuleBasedClassifier, extract_fallo_section

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


def save_expedientes(expedientes: list[Expediente], output_file: str):
    """Guarda expedientes en un archivo JSON."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PROCESSED_DIR / output_file

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([exp.to_dict() for exp in expedientes], f, ensure_ascii=False, indent=2)

    logger.info(f"Datos guardados en: {filepath}")


def run_analysis(
    input_file: str = "expedientes_raw.json",
    output_file: str = "expedientes_analyzed.json",
    use_rules: bool = True,
) -> list[Expediente]:
    """
    Ejecuta el análisis de resoluciones.

    Args:
        input_file: Archivo de entrada con expedientes
        output_file: Archivo de salida
        use_rules: Si True, usa clasificación basada en reglas además de keywords

    Returns:
        Lista de expedientes analizados
    """
    logger.info("=== ANÁLISIS DE RESOLUCIONES ===")

    # Cargar expedientes
    expedientes = load_expedientes(input_file)
    logger.info(f"Expedientes cargados: {len(expedientes)}")

    # Inicializar clasificadores
    keyword_classifier = ResolutionClassifier()
    rule_classifier = RuleBasedClassifier() if use_rules else None

    # Inicializar handler de PDFs
    pdf_handler = PDFHandler()

    # Estadísticas
    stats = {
        "total": len(expedientes),
        "con_pdf": 0,
        "analizados": 0,
        "clasificados": 0,
        "no_clasificados": 0,
        "errores": 0,
    }

    for i, exp in enumerate(expedientes, 1):
        logger.info(f"[{i}/{len(expedientes)}] Analizando: {exp.id}")

        if not exp.url_resolucion:
            logger.warning(f"  Sin URL de resolución: {exp.id}")
            continue

        stats["con_pdf"] += 1

        try:
            # Descargar y extraer texto del PDF
            text = pdf_handler.extract_text_from_url(exp.url_resolucion)

            if not text:
                logger.warning(f"  No se pudo extraer texto: {exp.id}")
                stats["errores"] += 1
                continue

            exp.texto_resolucion = text[:1000]  # Guardar solo un fragmento
            stats["analizados"] += 1

            # Intentar extraer solo la sección de fallo
            fallo_text = extract_fallo_section(text)
            analysis_text = fallo_text if fallo_text else text

            # Clasificar con reglas (más preciso)
            if rule_classifier:
                result = rule_classifier.classify(analysis_text)
                if result:
                    exp.resultado_clasificado = result
                    stats["clasificados"] += 1
                    logger.info(f"  Clasificado (reglas): {result}")
                    continue

            # Si no hay resultado con reglas, usar keywords
            result, keywords = keyword_classifier.classify(analysis_text)
            exp.resultado_clasificado = result
            exp.keywords_encontradas = []
            for cat, words in keywords.items():
                for word in set(words):
                    exp.keywords_encontradas.append(f"{cat}:{word}")

            if result:
                stats["clasificados"] += 1
                logger.info(f"  Clasificado (keywords): {result}")
            else:
                stats["no_clasificados"] += 1
                logger.warning(f"  No se pudo clasificar: {exp.id}")

        except Exception as e:
            logger.error(f"  Error analizando {exp.id}: {e}")
            stats["errores"] += 1

    pdf_handler.close()

    # Guardar resultados
    save_expedientes(expedientes, output_file)

    # Mostrar estadísticas
    logger.info("=== ESTADÍSTICAS ===")
    logger.info(f"Total expedientes: {stats['total']}")
    logger.info(f"Con URL de PDF: {stats['con_pdf']}")
    logger.info(f"Analizados: {stats['analizados']}")
    logger.info(f"Clasificados: {stats['clasificados']}")
    logger.info(f"No clasificados: {stats['no_clasificados']}")
    logger.info(f"Errores: {stats['errores']}")

    return expedientes


def main():
    parser = argparse.ArgumentParser(description="Análisis de resoluciones CNMC")
    parser.add_argument("--input", type=str, default="expedientes_raw.json", help="Archivo de entrada")
    parser.add_argument("--output", type=str, default="expedientes_analyzed.json", help="Archivo de salida")
    parser.add_argument("--no-rules", action="store_true", help="No usar clasificación basada en reglas")

    args = parser.parse_args()

    run_analysis(
        input_file=args.input,
        output_file=args.output,
        use_rules=not args.no_rules,
    )


if __name__ == "__main__":
    main()
