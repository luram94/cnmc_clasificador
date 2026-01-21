"""
Generador de informes CSV.
"""

import csv
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

import sys
sys.path.insert(0, str(__file__).rsplit("/", 4)[0])
from config.settings import OUTPUT_DIR
from src.extraction.models import Expediente

logger = logging.getLogger(__name__)


def expedientes_to_dataframe(expedientes: list[Expediente]) -> pd.DataFrame:
    """
    Convierte una lista de expedientes a DataFrame.

    Args:
        expedientes: Lista de expedientes

    Returns:
        DataFrame con los datos
    """
    data = []
    for exp in expedientes:
        data.append({
            "ID_expediente": exp.id,
            "Titulo": exp.titulo,
            "Fecha": exp.fecha,
            "Tipo": exp.tipo,
            "Sector": exp.sector,
            "Ambito": exp.ambito,
            "Estado": exp.estado,
            "Ultimo_resultado_web": exp.ultimo_resultado,
            "Resultado_clasificado": exp.resultado_clasificado or "NO_CLASIFICADO",
            "Keywords_encontradas": "; ".join(exp.keywords_encontradas),
            "URL_expediente": exp.url,
            "URL_resolucion": exp.url_resolucion or "",
        })

    return pd.DataFrame(data)


def generate_csv(
    expedientes: list[Expediente],
    output_path: Optional[Path] = None,
    filename: str = "expedientes_cnmc.csv",
) -> Path:
    """
    Genera un archivo CSV con los expedientes.

    Args:
        expedientes: Lista de expedientes
        output_path: Directorio de salida (por defecto OUTPUT_DIR)
        filename: Nombre del archivo

    Returns:
        Path del archivo generado
    """
    output_dir = output_path or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename

    df = expedientes_to_dataframe(expedientes)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")

    logger.info(f"CSV generado: {filepath} ({len(expedientes)} registros)")
    return filepath


def generate_summary_csv(
    expedientes: list[Expediente],
    output_path: Optional[Path] = None,
    filename: str = "resumen_clasificacion.csv",
) -> Path:
    """
    Genera un CSV con el resumen de clasificación.

    Args:
        expedientes: Lista de expedientes
        output_path: Directorio de salida
        filename: Nombre del archivo

    Returns:
        Path del archivo generado
    """
    output_dir = output_path or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / filename

    # Calcular estadísticas
    df = expedientes_to_dataframe(expedientes)
    total = len(df)

    summary_data = []
    for resultado in df["Resultado_clasificado"].unique():
        count = len(df[df["Resultado_clasificado"] == resultado])
        percentage = (count / total * 100) if total > 0 else 0
        summary_data.append({
            "Resultado": resultado,
            "Cantidad": count,
            "Porcentaje": f"{percentage:.1f}%",
        })

    # Ordenar por cantidad descendente
    summary_data.sort(key=lambda x: x["Cantidad"], reverse=True)

    # Añadir total
    summary_data.append({
        "Resultado": "TOTAL",
        "Cantidad": total,
        "Porcentaje": "100%",
    })

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(filepath, index=False, encoding="utf-8-sig")

    logger.info(f"Resumen CSV generado: {filepath}")
    return filepath
