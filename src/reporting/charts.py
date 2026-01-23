"""
Generador de gráficos con matplotlib.
"""

import logging
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd

import sys
sys.path.insert(0, str(__file__).rsplit("/", 4)[0])
from config.settings import OUTPUT_DIR
from src.extraction.models import Expediente
from src.reporting.csv_generator import expedientes_to_dataframe

logger = logging.getLogger(__name__)

# Colores para las categorías
CATEGORY_COLORS = {
    "DESESTIMADO": "#E74C3C",  # Rojo
    "ESTIMADO": "#27AE60",      # Verde
    "ESTIMADO_PARCIAL": "#F39C12",  # Naranja
    "ARCHIVADO": "#3498DB",    # Azul
    "NO_CLASIFICADO": "#95A5A6",  # Gris
}


def generate_pie_chart(
    expedientes: list[Expediente],
    output_path: Optional[Path] = None,
    filename: str = "distribucion_resultados.png",
) -> Path:
    """
    Genera un gráfico circular de distribución de resultados.

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

    df = expedientes_to_dataframe(expedientes)
    counts = df["Resultado_clasificado"].value_counts()

    # Preparar colores
    colors = [CATEGORY_COLORS.get(cat, "#95A5A6") for cat in counts.index]

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(10, 8))

    wedges, texts, autotexts = ax.pie(
        counts.values,
        labels=counts.index,
        autopct="%1.1f%%",
        colors=colors,
        explode=[0.02] * len(counts),
        shadow=True,
        startangle=90,
    )

    # Estilo
    ax.set_title("Distribución de Resultados de Resoluciones CNMC", fontsize=14, fontweight="bold")

    # Leyenda
    ax.legend(
        wedges,
        [f"{cat}: {count}" for cat, count in zip(counts.index, counts.values)],
        title="Categorías",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
    )

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico circular generado: {filepath}")
    return filepath


def generate_bar_chart(
    expedientes: list[Expediente],
    output_path: Optional[Path] = None,
    filename: str = "barras_resultados.png",
) -> Path:
    """
    Genera un gráfico de barras de resultados.

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

    df = expedientes_to_dataframe(expedientes)
    counts = df["Resultado_clasificado"].value_counts()

    # Preparar colores
    colors = [CATEGORY_COLORS.get(cat, "#95A5A6") for cat in counts.index]

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.bar(counts.index, counts.values, color=colors, edgecolor="black", linewidth=0.5)

    # Añadir etiquetas en las barras
    for bar, count in zip(bars, counts.values):
        height = bar.get_height()
        ax.annotate(
            f"{count}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    # Estilo
    ax.set_title("Resultados de Resoluciones CNMC", fontsize=14, fontweight="bold")
    ax.set_xlabel("Resultado", fontsize=12)
    ax.set_ylabel("Cantidad", fontsize=12)
    ax.set_ylim(0, max(counts.values) * 1.15)

    # Rotar etiquetas si son muchas
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico de barras generado: {filepath}")
    return filepath


def generate_timeline_chart(
    expedientes: list[Expediente],
    output_path: Optional[Path] = None,
    filename: str = "timeline_resultados.png",
) -> Path:
    """
    Genera un gráfico de línea temporal de resoluciones.

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

    df = expedientes_to_dataframe(expedientes)

    # Filtrar solo los que tienen fecha
    df = df[df["Fecha"].notna()].copy()

    if df.empty:
        logger.warning("No hay expedientes con fecha para generar timeline")
        return filepath

    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Mes"] = df["Fecha"].dt.to_period("M")

    # Agrupar por mes y resultado
    pivot = df.groupby(["Mes", "Resultado_clasificado"]).size().unstack(fill_value=0)

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(12, 6))

    for column in pivot.columns:
        color = CATEGORY_COLORS.get(column, "#95A5A6")
        ax.plot(
            pivot.index.astype(str),
            pivot[column],
            marker="o",
            label=column,
            color=color,
            linewidth=2,
        )

    ax.set_title("Evolución Temporal de Resoluciones", fontsize=14, fontweight="bold")
    ax.set_xlabel("Mes", fontsize=12)
    ax.set_ylabel("Cantidad", fontsize=12)
    ax.legend(title="Resultado", bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Gráfico temporal generado: {filepath}")
    return filepath


def generate_all_charts(
    expedientes: list[Expediente],
    output_path: Optional[Path] = None,
) -> list[Path]:
    """
    Genera todos los gráficos disponibles.

    Args:
        expedientes: Lista de expedientes
        output_path: Directorio de salida

    Returns:
        Lista de paths de archivos generados
    """
    paths = []

    paths.append(generate_pie_chart(expedientes, output_path))
    paths.append(generate_bar_chart(expedientes, output_path))
    paths.append(generate_timeline_chart(expedientes, output_path))

    return paths
