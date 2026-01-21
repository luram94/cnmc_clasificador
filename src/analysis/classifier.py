"""
Clasificador de resoluciones basado en keywords.
"""

import re
import logging
from typing import Optional
from collections import Counter

import sys
sys.path.insert(0, str(__file__).rsplit("/", 4)[0])
from config.settings import CLASSIFICATION_KEYWORDS, CLASSIFICATION_HIERARCHY
from src.extraction.models import Expediente

logger = logging.getLogger(__name__)


class ResolutionClassifier:
    """Clasifica resoluciones basándose en keywords."""

    def __init__(
        self,
        keywords: Optional[dict[str, list[str]]] = None,
        hierarchy: Optional[list[str]] = None,
    ):
        """
        Inicializa el clasificador.

        Args:
            keywords: Diccionario {categoria: [keywords]}
            hierarchy: Lista de categorías ordenadas por prioridad
        """
        self.keywords = keywords or CLASSIFICATION_KEYWORDS
        self.hierarchy = hierarchy or CLASSIFICATION_HIERARCHY

        # Compilar patrones regex para cada categoría
        self._patterns = {}
        for category, words in self.keywords.items():
            # Crear patrón que busque cualquiera de las palabras
            # Usamos word boundaries para evitar falsos positivos
            pattern = r"\b(" + "|".join(re.escape(w) for w in words) + r")\w*\b"
            self._patterns[category] = re.compile(pattern, re.IGNORECASE)

    def find_keywords(self, text: str) -> dict[str, list[str]]:
        """
        Encuentra todas las keywords en el texto.

        Args:
            text: Texto a analizar

        Returns:
            Diccionario {categoria: [keywords encontradas]}
        """
        results = {}

        for category, pattern in self._patterns.items():
            matches = pattern.findall(text)
            if matches:
                # Normalizar a minúsculas y contar
                results[category] = [m.lower() for m in matches]

        return results

    def count_keywords(self, text: str) -> dict[str, int]:
        """
        Cuenta las ocurrencias de keywords por categoría.

        Args:
            text: Texto a analizar

        Returns:
            Diccionario {categoria: conteo}
        """
        found = self.find_keywords(text)
        return {cat: len(words) for cat, words in found.items()}

    def classify(self, text: str) -> tuple[Optional[str], dict[str, list[str]]]:
        """
        Clasifica el texto según las keywords encontradas.

        Args:
            text: Texto a clasificar

        Returns:
            Tupla (clasificación, keywords_encontradas)
            - clasificación: Categoría o None si no se encontró ninguna
            - keywords_encontradas: Dict con las keywords por categoría
        """
        found_keywords = self.find_keywords(text)

        if not found_keywords:
            return None, {}

        # Si solo hay una categoría, retornarla
        if len(found_keywords) == 1:
            category = list(found_keywords.keys())[0]
            return category, found_keywords

        # Si hay múltiples categorías, aplicar jerarquía
        for category in self.hierarchy:
            if category in found_keywords:
                logger.debug(
                    f"Múltiples categorías encontradas: {list(found_keywords.keys())}. "
                    f"Aplicando jerarquía: {category}"
                )
                return category, found_keywords

        # Si ninguna está en la jerarquía, retornar la que tenga más ocurrencias
        counts = {cat: len(words) for cat, words in found_keywords.items()}
        max_category = max(counts, key=counts.get)
        return max_category, found_keywords

    def classify_expediente(self, expediente: Expediente, text: str) -> Expediente:
        """
        Clasifica un expediente y actualiza sus campos.

        Args:
            expediente: Expediente a clasificar
            text: Texto de la resolución

        Returns:
            Expediente actualizado
        """
        classification, keywords = self.classify(text)

        expediente.resultado_clasificado = classification
        expediente.keywords_encontradas = []

        # Aplanar las keywords encontradas
        for category, words in keywords.items():
            for word in words:
                keyword_info = f"{category}:{word}"
                if keyword_info not in expediente.keywords_encontradas:
                    expediente.keywords_encontradas.append(keyword_info)

        return expediente


def analyze_context(text: str, keyword: str, window: int = 100) -> list[str]:
    """
    Extrae el contexto alrededor de una keyword.

    Args:
        text: Texto completo
        keyword: Keyword a buscar
        window: Número de caracteres de contexto a cada lado

    Returns:
        Lista de fragmentos con contexto
    """
    contexts = []
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)

    for match in pattern.finditer(text):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        context = text[start:end]

        # Limpiar el contexto
        context = " ".join(context.split())
        contexts.append(f"...{context}...")

    return contexts
