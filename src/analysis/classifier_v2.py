"""
Clasificador mejorado de resoluciones CNMC v3.

Mejoras respecto a v2:
- Patrones de sección más estrictos (solo MAYÚSCULAS como título)
- Prioriza patrones estrictos sobre flexibles
- Soporte para plurales: "los conflictos", "las reclamaciones"
- Más conjugaciones verbales: "desestime", "estime"
- Patrones para "declarar la desaparición", "falta de objeto"
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Resultado de la clasificación."""
    categoria: str
    confianza: str  # "alta", "media", "baja"
    texto_clave: str  # Fragmento que determinó la clasificación
    seccion_encontrada: bool


class ResolutionClassifierV2:
    """Clasificador mejorado de resoluciones CNMC."""

    # Patrones para extraer la sección de resolución (SOLO MAYÚSCULAS)
    # Requiere que ACUERDA/RESUELVE aparezca como título (mayúsculas completas)
    SECTION_PATTERNS_STRICT = [
        # Patrón estricto: ACUERDA o RESUELVE en MAYÚSCULAS seguido de punto numerado
        r'(?:^|\n)\s*(ACUERDA|RESUELVE)\s*[:\.]?\s*\n+((?:PRIMERO|ÚNICO|ÚNICA|PRIMERA|SEGUNDO|1º|1\.|I\.)[^\n]*[\s\S]+?)(?=Comuníquese|El presente acuerdo|El presente resolución|Madrid,|Notifíquese|COMISIÓN NACIONAL|\Z)',
    ]

    SECTION_PATTERNS_FLEXIBLE = [
        # Patrón flexible: ACUERDA o RESUELVE en mayúsculas, contenido más libre
        r'(?:^|\n)\s*(ACUERDA|RESUELVE)\s*[:\.]?\s*\n+(.{50,}?)(?=Comuníquese|El presente|Madrid,|Notifíquese|\Z)',
    ]

    # Categorías y sus patrones (orden de prioridad)
    # Se buscan en el PRIMER punto de la resolución
    CATEGORIES = {
        "ARCHIVADO": [
            r'declarar?\s+concluso',
            r'aceptar?\s+(?:de\s+plano\s+)?(?:el\s+)?desistimiento',
            r'archivar?\s+(?:las\s+)?actuaciones',
            r'archivo\s+(?:de\s+las\s+)?actuaciones',
            r'desaparición\s+(?:sobrevenida\s+)?(?:de\s+(?:su\s+)?)?objeto',
            r'declarar?\s+la\s+desaparición',
            r'pérdida\s+(?:sobrevenida\s+)?(?:de\s+)?objeto',
            r'falta\s+de\s+objeto',
            r'inadmitir?\s+(?:a\s+trámite)?',
            r'tener\s+por\s+desistid[oa]',
        ],
        "DESESTIMADO": [
            # Singular con "el"
            r'desestim(?:ar?|e)\s+(?:el\s+)?(?:conflicto|recurso|reclamación|solicitud)',
            # Plural con "los/las"
            r'desestim(?:ar?|e)\s+(?:los\s+)?conflictos',
            r'desestim(?:ar?|e)\s+(?:las\s+)?(?:reclamaciones|solicitudes)',
            # Otras formas
            r'no\s+(?:ha\s+)?lugar\s+(?:a\s+)?(?:la\s+)?(?:estimación|reclamación)',
            r'desestimación\s+(?:de\s+)?(?:los?\s+)?(?:conflictos?|recursos?)',
            # "sin perjuicio" a menudo indica desestimación parcial
            r'desestimar?,?\s+sin\s+perjuicio',
        ],
        "ESTIMADO": [
            # Singular con "el"
            r'estim(?:ar?|e)\s+(?:parcialmente\s+)?(?:el\s+)?(?:conflicto|recurso|reclamación|solicitud)',
            # Plural con "los/las"
            r'estim(?:ar?|e)\s+(?:parcialmente\s+)?(?:los\s+)?conflictos',
            r'estim(?:ar?|e)\s+(?:las\s+)?(?:reclamaciones|solicitudes)',
            # Otras formas de estimación
            r'estimación\s+(?:parcial\s+)?(?:de\s+)?(?:los?\s+)?(?:conflictos?|recursos?)',
            r'declarar?\s+(?:la\s+)?(?:nulidad|vulneración)',
            r'ordenar?\s+a\s+.{5,50}\s+(?:que|el\s+cumplimiento)',
            r'dejar?\s+sin\s+efecto',
            # Requerir acción (implica estimación)
            r'requerir?\s+a\s+.{5,50}\s+(?:que|para\s+que)',
        ],
    }

    def __init__(self):
        # Compilar patrones de sección (estrictos primero, flexibles después)
        self._section_patterns_strict = [
            re.compile(p, re.MULTILINE | re.DOTALL) for p in self.SECTION_PATTERNS_STRICT
        ]
        self._section_patterns_flexible = [
            re.compile(p, re.MULTILINE | re.DOTALL) for p in self.SECTION_PATTERNS_FLEXIBLE
        ]
        self._category_patterns = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in self.CATEGORIES.items()
        }

    def _extract_resolution_section(self, text: str) -> Optional[tuple[str, str]]:
        """
        Extrae la sección ACUERDA o RESUELVE del documento.

        Estrategia:
        1. Primero intenta con patrones ESTRICTOS (título en mayúsculas + punto numerado)
        2. Si no encuentra, usa patrones FLEXIBLES
        3. Toma la ÚLTIMA ocurrencia del patrón estricto (o flexible si no hay estricto)

        Returns:
            Tupla (tipo_seccion, contenido) o None si no se encuentra
        """
        # Primero intentar con patrones estrictos
        strict_matches = []
        for pattern in self._section_patterns_strict:
            for match in pattern.finditer(text):
                strict_matches.append((match.start(), match.group(1), match.group(2)))

        if strict_matches:
            # Ordenar por posición y tomar la última coincidencia estricta
            strict_matches.sort(key=lambda x: x[0])
            _, section_type, content = strict_matches[-1]
            return self._clean_section(section_type, content)

        # Si no hay matches estrictos, intentar con flexibles
        flexible_matches = []
        for pattern in self._section_patterns_flexible:
            for match in pattern.finditer(text):
                flexible_matches.append((match.start(), match.group(1), match.group(2)))

        if flexible_matches:
            flexible_matches.sort(key=lambda x: x[0])
            _, section_type, content = flexible_matches[-1]
            return self._clean_section(section_type, content)

        return None

    def _clean_section(self, section_type: str, content: str) -> tuple[str, str]:
        """Limpia y normaliza el contenido de la sección."""
        section_type = section_type.upper()
        content = content.strip()
        # Limpiar saltos de línea excesivos
        content = re.sub(r'\n{3,}', '\n\n', content)
        return section_type, content

    def _extract_first_point(self, section_content: str) -> str:
        """
        Extrae el primer punto de la resolución (ÚNICO, PRIMERO, etc.)
        que es donde está la decisión principal.
        """
        # Buscar hasta el siguiente punto numerado o fin
        patterns = [
            r'^((?:ÚNICO|ÚNICA|PRIMERO|PRIMERA|1º|1\.|I\.)[^\n]*(?:\n(?![A-Z]{4,}\.?\s|SEGUNDO|SEGUNDA|2º|2\.|II\.).*)*)',
            r'^(.{50,500}?)(?=SEGUNDO|SEGUNDA|2º|2\.|II\.|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, section_content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        # Si no hay puntos, devolver los primeros 500 caracteres
        return section_content[:500]

    def classify(self, text: str) -> ClassificationResult:
        """
        Clasifica una resolución.

        Args:
            text: Texto completo del documento PDF

        Returns:
            ClassificationResult con la categoría y detalles
        """
        # 1. Extraer sección ACUERDA/RESUELVE
        section_result = self._extract_resolution_section(text)

        if not section_result:
            # Fallback: buscar en todo el texto
            logger.warning("No se encontró sección ACUERDA/RESUELVE")
            return self._classify_fallback(text)

        section_type, section_content = section_result

        # 2. Extraer primer punto
        first_point = self._extract_first_point(section_content)

        # 3. Buscar patrones de categoría en orden de prioridad
        for categoria, patterns in self._category_patterns.items():
            for pattern in patterns:
                match = pattern.search(first_point)
                if match:
                    return ClassificationResult(
                        categoria=categoria,
                        confianza="alta",
                        texto_clave=match.group(0),
                        seccion_encontrada=True
                    )

        # 4. Si no se encontró en el primer punto, buscar en toda la sección
        for categoria, patterns in self._category_patterns.items():
            for pattern in patterns:
                match = pattern.search(section_content)
                if match:
                    return ClassificationResult(
                        categoria=categoria,
                        confianza="media",
                        texto_clave=match.group(0),
                        seccion_encontrada=True
                    )

        # 5. No se pudo clasificar
        return ClassificationResult(
            categoria="NO_CLASIFICADO",
            confianza="baja",
            texto_clave=first_point[:100],
            seccion_encontrada=True
        )

    def _classify_fallback(self, text: str) -> ClassificationResult:
        """
        Clasificación de respaldo cuando no se encuentra la sección.
        Busca en los últimos 2000 caracteres del documento.
        """
        last_part = text[-2000:]

        for categoria, patterns in self._category_patterns.items():
            for pattern in patterns:
                match = pattern.search(last_part)
                if match:
                    return ClassificationResult(
                        categoria=categoria,
                        confianza="baja",
                        texto_clave=match.group(0),
                        seccion_encontrada=False
                    )

        return ClassificationResult(
            categoria="NO_CLASIFICADO",
            confianza="baja",
            texto_clave="",
            seccion_encontrada=False
        )

    def classify_with_details(self, text: str) -> tuple[str, dict]:
        """
        Clasifica y devuelve detalles adicionales.
        Compatible con la interfaz anterior.
        """
        result = self.classify(text)
        details = {
            "confianza": result.confianza,
            "texto_clave": result.texto_clave,
            "seccion_encontrada": result.seccion_encontrada,
        }
        return result.categoria, details
