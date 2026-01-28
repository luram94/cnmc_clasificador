"""
Clasificador de resoluciones CNMC.

Extrae la sección ACUERDA/RESUELVE de los PDFs y clasifica
según patrones de texto en: ESTIMADO, DESESTIMADO, ARCHIVADO.
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


class ResolutionClassifier:
    """Clasificador de resoluciones CNMC."""

    # Patrones para extraer la sección de resolución
    SECTION_PATTERNS_STRICT = [
        # Patrón estricto: ACUERDA o RESUELVE seguido de punto numerado (mayúsculas o minúsculas en ordinal)
        r'(?:^|\n)\s*(ACUERDA|RESUELVE)\s*[:\.]?\s*\n+((?:PRIMERO|ÚNICO|ÚNICA|PRIMERA|SEGUNDO|Primero|Único|Única|Primera|Segundo|1º|1\.|I\.)[.\-:\s][^\n]*[\s\S]+?)(?=Comuníquese|El presente acuerdo|El presente resolución|Madrid,|Notifíquese|COMISIÓN NACIONAL|\Z)',
    ]

    SECTION_PATTERNS_FLEXIBLE = [
        # Patrón flexible: ACUERDA o RESUELVE en mayúsculas, contenido más libre
        r'(?:^|\n)\s*(ACUERDA|RESUELVE)\s*[:\.]?\s*\n+(.{50,}?)(?=Comuníquese|El presente|Madrid,|Notifíquese|\Z)',
        # Patrón inline: ACUERDA/RESUELVE seguido directamente de verbo
        r'\b(ACUERDA|RESUELVE)\s+(declarar|desestimar|estimar|archivar|inadmitir|aceptar|informar|tener)(.{50,800}?)(?=Comuníquese|El presente|Madrid,|Notifíquese|\Z)',
    ]

    # Categorías y sus patrones (orden de prioridad)
    # IMPORTANTE: Solo hay 3 categorías válidas: ESTIMADO, DESESTIMADO, ARCHIVADO
    CATEGORIES = {
        "ARCHIVADO": [
            # Declarar concluso/concluido (ambas formas)
            r'declarar?\s+(?:el\s+)?(?:procedimiento\s+)?conclu(?:so|ido)',
            r'declare\s+concluso',
            r'aceptar?\s+(?:de\s+plano\s+)?(?:el\s+)?desistimiento',
            r'aceptar,?\s+conforme\s+al\s+artículo\s+94',  # Desistimiento según Ley 39/2015
            r'archivar?\s+(?:las\s+|el\s+)?(?:actuaciones|procedimiento)',
            r'archivo\s+(?:de\s+las\s+)?actuaciones',
            r'proceder\s+al\s+archivo',
            r'desaparición\s+(?:sobrevenida\s+)?(?:de\s+(?:su\s+)?)?objeto',
            r'declarar?\s+la\s+desaparición',
            r'pérdida\s+(?:sobrevenida\s+)?(?:de[l]?\s+)?(?:su\s+)?objeto',
            r'falta\s+de\s+objeto',
            r'inadmitir?\s+(?:a\s+trámite)?',
            r'tener\s+por\s+desistid[oa]',
            r'declarar?\s+la\s+falta\s+de\s+competencia',
            r'falta\s+de\s+competencia\s+de\s+esta\s+comisión',
            # Terminación/finalización del procedimiento
            r'terminación\s+(?:del\s+)?procedimiento',
            r'declarar?\s+(?:la\s+)?(?:terminación|finalización)',
            r'declarar?\s+finalizado\s+(?:el\s+)?procedimiento',
            # Verificación de seguimiento sin incidencias
            r'considerar\s+que.{0,100}no\s+se\s+ha\s+(?:producido|detectado)',
            r'considerar\s+que.{0,50}a\s+la\s+vista.{0,50}no',
            r'no\s+procede\s+(?:la\s+)?(?:suspensión|actuación)',
            # Declarar infrautilización (cierra el procedimiento)
            r'declarar?\s+(?:la\s+)?infrautilización',
            # Casos informativos/aclaratorios (antes en RESUELTO)
            r'informar\s+a\s+.{5,80}\s+que',
            r'dar\s+traslado',
            r'corregir\s+(?:el\s+)?(?:párrafo|error)',
            r'aclarar\s+(?:que\s+)?(?:la\s+)?(?:referencia|resolución)',
            r'declarar?\s+completa\s+(?:la\s+)?solicitud',
            r'considerar\s+que,?\s+conforme\s+a\s+(?:la\s+)?información',
            r'considerar\s+que\s+(?:el\s+)?(?:reparto|reconocimiento)',
            # Remisión a otro órgano
            r'remitir\s+(?:el\s+)?(?:expediente|actuaciones)',
        ],
        "DESESTIMADO": [
            # Patrones flexibles que permiten texto intermedio
            r'desestim(?:ar?|e)(?:\s+\S+){0,5}\s+(?:el\s+)?(?:presente\s+)?(?:conflicto|recurso|reclamación|solicitud|pretensión)',
            r'desestim(?:ar?|e)\s+(?:íntegramente\s+)?(?:el\s+)?(?:presente\s+)?(?:conflicto|recurso|reclamación)',
            r'desestim(?:ar?|e)\s+(?:los\s+)?conflictos',
            r'desestim(?:ar?|e)\s+(?:las\s+)?(?:reclamaciones|solicitudes|pretensiones)',
            # Desestimar con texto intermedio largo (fundamentos jurídicos, etc.)
            r'(?:ÚNICO|Único|PRIMERO|Primero)[.\s:-]+\s*[Dd]esestim(?:ar?|e)',
            r'no\s+(?:ha\s+)?lugar\s+(?:a\s+)?(?:la\s+)?(?:estimación|reclamación)',
            r'desestimación\s+(?:de\s+)?(?:los?\s+)?(?:conflictos?|recursos?)',
            r'desestimar?,?\s+sin\s+perjuicio',
            # Confirmar denegación/comunicación = desestimar al reclamante
            r'declarar\s+conforme\s+a\s+derecho\s+(?:la\s+)?(?:denegación|respuesta|comunicación|actuación)',
            r'confirmar?\s+la\s+(?:denegación|actuación)',
            # Denegar directamente
            r'denegar\s+(?:la\s+)?(?:autorización|petición|solicitud|acceso)',
            r'denegar\s+a\s+\w+',
            r'queda\s+justificada\s+(?:la\s+)?denegación',
            # Sentencias judiciales que confirman (desestiman recurso)
            r'(?:fallo|fallamos).{0,100}desestim(?:ar?|amos?)',
            r'(?:fallo|fallamos).{0,100}confirmar?\s+(?:la\s+)?resolución',
        ],
        "ESTIMADO": [
            # Patrones flexibles que permiten texto intermedio (comas, fundamentos jurídicos, etc.)
            r'estim(?:ar?|e)(?:,?\s*[^.]{0,100}?,?)?\s*(?:el\s+)?(?:conflicto|recurso|reclamación|solicitud)',
            r'estim(?:ar?|e)\s+(?:parcialmente\s+)?(?:íntegramente\s+)?(?:el\s+)?(?:presente\s+)?(?:conflicto|recurso|reclamación)',
            r'estim(?:ar?|e)\s+(?:la\s+)?pretensión',
            r'estim(?:ar?|e)\s+(?:el\s+)?escrito\s+de\s+disconformidad',
            r'estim(?:ar?|e)\s+(?:parcialmente\s+)?(?:los\s+)?conflictos',
            r'estim(?:ar?|e)\s+(?:las\s+)?(?:reclamaciones|solicitudes)',
            r'estim(?:ar?|e),?\s+exclusivamente',
            r'estimación\s+(?:parcial\s+)?(?:de\s+)?(?:los?\s+)?(?:conflictos?|recursos?)',
            r'declarar?\s+(?:la\s+)?(?:nulidad|vulneración)',
            r'ordenar?\s+a\s+.{5,50}\s+(?:que|el\s+cumplimiento)',
            r'dejar?\s+sin\s+efecto',
            r'requerir?\s+a\s+.{5,50}\s+(?:que|para\s+que)',
            # Reconocer derecho = favorable al reclamante
            r'reconocer\s+(?:el\s+)?derecho',
            r'reconocer\s+a\s+(?:la\s+)?(?:empresa|sociedad|particular|fundación|distribuidora)',
            r'reconocer\s+a\s+[A-Z\"\'\"\[\(]',  # Incluir comillas tipográficas y corchetes
            r'(?:se\s+)?reconoce\s+el\s+derecho',
            # Anular = favorable al reclamante
            r'anular\s+(?:el\s+)?(?:la\s+)?(?:comunicación|resolución|acto|denegación|contenido)',
            r'declarar?\s+no\s+(?:conforme|ajustad[oa]s?)\s+a\s+(?:d|D)erecho',
            # Sin efecto = anulación
            r'(?:se\s+)?considera\s+sin\s+efecto',
            # Hacer efectivo/conceder derecho
            r'hacer\s+efectivo\s+el\s+derecho',
            r'declarar?\s+el\s+derecho\s+de',
            # Dar conformidad a operación solicitada
            r'dar\s+conformidad\s+(?:previa\s+)?(?:a\s+)?(?:la\s+)?(?:decisión|operación|solicitud)',
            # Verificación de cumplimiento (resolución favorable)
            r'declarar?\s+que\s+(?:las\s+)?condiciones.{5,500}dan\s+(?:adecuado\s+)?cumplimiento',
            # Sentencias judiciales que anulan (estiman recurso)
            r'(?:fallo|fallamos).{0,100}estim(?:ar?|amos?)',
            r'(?:fallo|fallamos).{0,100}anular?\s+(?:la\s+)?resolución',
            # Resolver conflicto/discrepancias (antes en RESUELTO, favorable al reclamante)
            r'resolver\s+(?:las\s+)?discrepancias',
            r'resolver\s+(?:el\s+)?conflicto.{0,50}(?:declarando|a\s+favor)',
            r'al\s+objeto\s+de\s+garantizar',
        ],
    }

    def __init__(self):
        self._section_patterns_strict = [
            re.compile(p, re.MULTILINE | re.DOTALL) for p in self.SECTION_PATTERNS_STRICT
        ]
        self._section_patterns_flexible = [
            re.compile(p, re.MULTILINE | re.DOTALL) for p in self.SECTION_PATTERNS_FLEXIBLE
        ]
        self._category_patterns = {
            cat: [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]
            for cat, patterns in self.CATEGORIES.items()
        }

    def _normalize_text(self, text: str) -> str:
        """Normaliza el texto para mejorar la detección de patrones."""
        # Reemplazar guiones especiales (em-dash, en-dash) por guión normal
        text = text.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
        text = text.replace('–', '-').replace('—', '-').replace('−', '-')
        # Normalizar comillas tipográficas Unicode a comillas ASCII
        text = text.replace('\u201c', '"').replace('\u201d', '"')  # " y "
        text = text.replace('\u2018', "'").replace('\u2019', "'")  # ' y '
        text = text.replace('\u00ab', '"').replace('\u00bb', '"')  # « y »
        # Eliminar números de página sueltos al inicio (ej: "21\nÚNICO")
        text = re.sub(r'^\d+\s*\n', '', text)
        text = re.sub(r'^\d+\s+(?=ÚNICO|PRIMERO|Único|Primero)', '', text)
        # Normalizar espacios múltiples en cada línea (preservando saltos de línea)
        text = re.sub(r'[^\S\n]+', ' ', text)  # Espacios múltiples -> uno solo (sin tocar \n)
        text = re.sub(r'\n{3,}', '\n\n', text)  # Múltiples líneas vacías -> máximo 2
        # Normalizar puntos suspensivos
        text = text.replace('\u2026', '...')
        return text

    def _extract_resolution_section(self, text: str) -> Optional[tuple[str, str]]:
        """
        Extrae la sección ACUERDA o RESUELVE del documento.

        Returns:
            Tupla (tipo_seccion, contenido) o None si no se encuentra
        """
        # Primero intentar con patrones estrictos
        strict_matches = []
        for pattern in self._section_patterns_strict:
            for match in pattern.finditer(text):
                strict_matches.append((match.start(), match.group(1), match.group(2)))

        if strict_matches:
            strict_matches.sort(key=lambda x: x[0])
            _, section_type, content = strict_matches[-1]
            return self._clean_section(section_type, content)

        # Si no hay matches estrictos, intentar con flexibles
        flexible_matches = []
        for pattern in self._section_patterns_flexible:
            for match in pattern.finditer(text):
                if match.lastindex >= 3:
                    content = match.group(2) + match.group(3)
                else:
                    content = match.group(2)
                flexible_matches.append((match.start(), match.group(1), content))

        if flexible_matches:
            flexible_matches.sort(key=lambda x: x[0])
            _, section_type, content = flexible_matches[-1]
            return self._clean_section(section_type, content)

        return None

    def _clean_section(self, section_type: str, content: str) -> tuple[str, str]:
        """Limpia y normaliza el contenido de la sección."""
        section_type = section_type.upper()
        content = content.strip()
        content = re.sub(r'\n{3,}', '\n\n', content)
        return section_type, content

    def _extract_first_point(self, section_content: str) -> str:
        """Extrae el primer punto de la resolución (ÚNICO, PRIMERO, etc.)."""
        patterns = [
            r'^((?:ÚNICO|ÚNICA|PRIMERO|PRIMERA|1º|1\.|I\.)[^\n]*(?:\n(?![A-Z]{4,}\.?\s|SEGUNDO|SEGUNDA|2º|2\.|II\.).*)*)',
            r'^(.{50,500}?)(?=SEGUNDO|SEGUNDA|2º|2\.|II\.|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, section_content, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()

        return section_content[:500]

    def classify(self, text: str) -> ClassificationResult:
        """
        Clasifica una resolución.

        Args:
            text: Texto completo del documento PDF

        Returns:
            ClassificationResult con la categoría y detalles
        """
        # Normalizar texto antes de procesar
        text = self._normalize_text(text)

        section_result = self._extract_resolution_section(text)

        if not section_result:
            logger.warning("No se encontró sección ACUERDA/RESUELVE")
            return self._classify_fallback(text)

        section_type, section_content = section_result
        first_point = self._extract_first_point(section_content)

        # Buscar patrones de categoría en el primer punto
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

        # Si no se encontró en el primer punto, buscar en toda la sección
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

        return ClassificationResult(
            categoria="NO_CLASIFICADO",
            confianza="baja",
            texto_clave=first_point[:100],
            seccion_encontrada=True
        )

    def _classify_fallback(self, text: str) -> ClassificationResult:
        """Clasificación de respaldo cuando no se encuentra la sección."""
        # Detectar si es una sentencia judicial
        is_sentencia = bool(re.search(r'(?:FALLO|FALLAMOS|Audiencia\s+Nacional|Tribunal\s+Supremo|SENTENCIA)', text, re.IGNORECASE))

        # Para sentencias, buscar en la sección FALLO
        if is_sentencia:
            fallo_match = re.search(r'(?:FALLO|FALLAMOS)[:\s]*(.{50,1500}?)(?:Notifíquese|Así\s+(?:por\s+esta|lo\s+pronunciamos)|firmamos|\Z)', text, re.IGNORECASE | re.DOTALL)
            if fallo_match:
                fallo_text = fallo_match.group(1)
                for categoria, patterns in self._category_patterns.items():
                    for pattern in patterns:
                        match = pattern.search(fallo_text)
                        if match:
                            return ClassificationResult(
                                categoria=categoria,
                                confianza="media",
                                texto_clave=f"[SENTENCIA] {match.group(0)}",
                                seccion_encontrada=False
                            )

        # Buscar en los últimos 3000 caracteres (aumentado)
        last_part = text[-3000:]
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

        # Buscar en todo el texto con patrones de alta confianza
        high_confidence_patterns = {
            "ESTIMADO": [
                r'(?:se\s+)?estima\s+(?:el\s+)?(?:recurso|conflicto)',
                r'anulamos\s+(?:la\s+)?resolución',
                r'reconocer\s+(?:el\s+)?derecho',
            ],
            "DESESTIMADO": [
                r'(?:se\s+)?desestima\s+(?:el\s+)?(?:recurso|conflicto)',
                r'confirmamos\s+(?:la\s+)?resolución',
                r'no\s+ha\s+lugar',
            ],
            "ARCHIVADO": [
                r'archivo\s+del\s+procedimiento',
                r'procedimiento\s+(?:ha\s+)?concluido',
                r'declarar?\s+concluso',
                r'informar\s+a\s+.{5,50}\s+que',
                r'dar\s+traslado',
                r'se\s+acomoda\s+a\s+(?:la\s+)?(?:citada\s+)?resolución',
            ],
        }

        for categoria, patterns in high_confidence_patterns.items():
            for p in patterns:
                match = re.search(p, text, re.IGNORECASE)
                if match:
                    return ClassificationResult(
                        categoria=categoria,
                        confianza="baja",
                        texto_clave=match.group(0),
                        seccion_encontrada=False
                    )

        # Último intento: buscar verbos clave en cualquier parte del texto
        last_resort_patterns = {
            "DESESTIMADO": r'\bdesestim(?:ar?|e|ó|ado)\b',
            "ESTIMADO": r'\bestim(?:ar?|e|ó|ado)\b(?!\s*(?:que|conveniente))',
            "ARCHIVADO": r'\b(?:archiv(?:ar?|e|ó|ado)|conclus[oa]|inadmit)\b',
        }

        for categoria, pattern in last_resort_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                match = re.search(pattern, text, re.IGNORECASE)
                return ClassificationResult(
                    categoria=categoria,
                    confianza="baja",
                    texto_clave=f"[ÚLTIMO RECURSO] {match.group(0)}",
                    seccion_encontrada=False
                )

        return ClassificationResult(
            categoria="NO_CLASIFICADO",
            confianza="baja",
            texto_clave="",
            seccion_encontrada=False
        )
