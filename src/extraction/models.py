"""
Modelos de datos para expedientes de la CNMC.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Expediente:
    """Representa un expediente de la CNMC."""

    id: str
    titulo: str
    fecha: Optional[date] = None
    tipo: str = ""
    sector: str = ""
    ambito: str = ""
    estado: str = ""
    ultimo_resultado: str = ""
    url: str = ""
    url_resolucion: Optional[str] = None

    # Campos que se rellenan tras el análisis
    resultado_clasificado: Optional[str] = None
    keywords_encontradas: list[str] = field(default_factory=list)
    texto_resolucion: Optional[str] = None

    def to_dict(self) -> dict:
        """Convierte el expediente a diccionario."""
        return {
            "id": self.id,
            "titulo": self.titulo,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "tipo": self.tipo,
            "sector": self.sector,
            "ambito": self.ambito,
            "estado": self.estado,
            "ultimo_resultado": self.ultimo_resultado,
            "url": self.url,
            "url_resolucion": self.url_resolucion,
            "resultado_clasificado": self.resultado_clasificado,
            "keywords_encontradas": self.keywords_encontradas,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Expediente":
        """Crea un expediente desde un diccionario."""
        fecha = None
        if data.get("fecha"):
            fecha = date.fromisoformat(data["fecha"])

        return cls(
            id=data["id"],
            titulo=data.get("titulo", ""),
            fecha=fecha,
            tipo=data.get("tipo", ""),
            sector=data.get("sector", ""),
            ambito=data.get("ambito", ""),
            estado=data.get("estado", ""),
            ultimo_resultado=data.get("ultimo_resultado", ""),
            url=data.get("url", ""),
            url_resolucion=data.get("url_resolucion"),
            resultado_clasificado=data.get("resultado_clasificado"),
            keywords_encontradas=data.get("keywords_encontradas", []),
        )
