"""
Reglas de clasificación y jerarquía para resoluciones.
"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ClassificationRule:
    """Regla de clasificación."""

    name: str
    pattern: str
    category: str
    priority: int = 0
    negative_patterns: list[str] = None

    def __post_init__(self):
        self._pattern = re.compile(self.pattern, re.IGNORECASE)
        self._negative_patterns = []
        if self.negative_patterns:
            self._negative_patterns = [
                re.compile(p, re.IGNORECASE) for p in self.negative_patterns
            ]

    def matches(self, text: str) -> bool:
        """Verifica si el texto cumple la regla."""
        # Verificar patrón positivo
        if not self._pattern.search(text):
            return False

        # Verificar patrones negativos (no deben aparecer)
        for neg_pattern in self._negative_patterns:
            if neg_pattern.search(text):
                return False

        return True


# Reglas predefinidas para clasificación más precisa
DEFAULT_RULES = [
    # Reglas de desestimación
    ClassificationRule(
        name="desestimacion_total",
        pattern=r"se\s+desestima\s+(la\s+)?(reclamación|solicitud|recurso)",
        category="DESESTIMADO",
        priority=10,
    ),
    ClassificationRule(
        name="desestimacion_fallo",
        pattern=r"(fallo|resuelve).*desestim",
        category="DESESTIMADO",
        priority=10,
    ),
    # Reglas de estimación
    ClassificationRule(
        name="estimacion_total",
        pattern=r"se\s+estima\s+(la\s+)?(reclamación|solicitud|recurso)",
        category="ESTIMADO",
        priority=10,
        negative_patterns=[r"no\s+se\s+estima", r"se\s+desestima"],
    ),
    ClassificationRule(
        name="estimacion_parcial",
        pattern=r"estim(ar|a)\s+parcialmente",
        category="ESTIMADO_PARCIAL",
        priority=8,
    ),
    ClassificationRule(
        name="estimacion_fallo",
        pattern=r"(fallo|resuelve).*estim",
        category="ESTIMADO",
        priority=9,
        negative_patterns=[r"(fallo|resuelve).*desestim"],
    ),
    # Reglas de archivo
    ClassificationRule(
        name="archivo_actuaciones",
        pattern=r"archivar?\s+(las\s+)?actuaciones",
        category="ARCHIVADO",
        priority=10,
    ),
    ClassificationRule(
        name="archivo_expediente",
        pattern=r"archivo\s+del\s+expediente",
        category="ARCHIVADO",
        priority=10,
    ),
]


class RuleBasedClassifier:
    """Clasificador basado en reglas."""

    def __init__(self, rules: Optional[list[ClassificationRule]] = None):
        self.rules = rules or DEFAULT_RULES
        # Ordenar por prioridad descendente
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def classify(self, text: str) -> Optional[str]:
        """
        Clasifica el texto aplicando reglas.

        Args:
            text: Texto a clasificar

        Returns:
            Categoría o None si ninguna regla aplica
        """
        for rule in self.rules:
            if rule.matches(text):
                return rule.category
        return None

    def classify_with_details(self, text: str) -> tuple[Optional[str], list[str]]:
        """
        Clasifica el texto y retorna las reglas que aplicaron.

        Args:
            text: Texto a clasificar

        Returns:
            Tupla (categoría, lista de nombres de reglas que aplicaron)
        """
        matched_rules = []
        category = None

        for rule in self.rules:
            if rule.matches(text):
                matched_rules.append(rule.name)
                if category is None:
                    category = rule.category

        return category, matched_rules


def extract_fallo_section(text: str) -> Optional[str]:
    """
    Extrae la sección de "FALLO" o "RESUELVE" de una resolución.

    Esta sección suele contener la decisión final.

    Args:
        text: Texto completo de la resolución

    Returns:
        Texto de la sección de fallo o None si no se encuentra
    """
    # Patrones para encontrar la sección de fallo
    patterns = [
        r"(?:FALLO|RESUELVE|RESOLUCIÓN)[:\s]*(.{100,2000}?)(?:NOTIFÍQUESE|$)",
        r"(?:Por\s+todo\s+lo\s+anterior)[,\s]*(.{50,1000}?)(?:\.|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

    return None
