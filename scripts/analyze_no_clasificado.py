#!/usr/bin/env python3
"""
Script para analizar casos NO_CLASIFICADO y encontrar patrones faltantes.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.pdf_handler import PDFHandler
from src.analysis.classifier_v2 import ResolutionClassifierV2

# Cargar expedientes
data_file = Path(__file__).parent.parent / "data" / "processed" / "expedientes_2024_v2.json"
with open(data_file, "r", encoding="utf-8") as f:
    expedientes = json.load(f)

# Filtrar NO_CLASIFICADO
no_clasificados = [e for e in expedientes if e.get("resultado_clasificado") == "NO_CLASIFICADO"]
print(f"Total NO_CLASIFICADO: {len(no_clasificados)}")

# Analizar una muestra
classifier = ResolutionClassifierV2()
pdf_handler = PDFHandler()

# Tomar 10 muestras diversas
sample_indices = [0, 2, 4, 6, 8, 10, 15, 20, 30, 40]
samples = [no_clasificados[i] for i in sample_indices if i < len(no_clasificados)]

print(f"\nAnalizando {len(samples)} muestras...\n")
print("=" * 80)

for i, exp in enumerate(samples):
    print(f"\n[{i+1}] Expediente: {exp['id']}")
    print(f"URL PDF: {exp.get('url_resolucion', 'N/A')}")
    print(f"Keyword encontrada: {exp.get('keywords_encontradas', [])}")

    if not exp.get('url_resolucion'):
        print("Sin URL de resolución")
        continue

    # Descargar y extraer texto
    text = pdf_handler.extract_text_from_url(exp['url_resolucion'])
    if not text:
        print("No se pudo extraer texto")
        continue

    # Buscar sección ACUERDA/RESUELVE
    section_patterns = [
        r'(ACUERDA|RESUELVE)\s*[:\.]?\s*\n*((?:PRIMERO|ÚNICO|ÚNICA|PRIMERA|SEGUNDO|1º|1\.|I\.)[\s\S]+?)(?=Comuníquese|El presente|Madrid,|Notifíquese|\Z)',
    ]

    for pattern in section_patterns:
        matches = list(re.finditer(pattern, text, re.IGNORECASE | re.DOTALL))
        if matches:
            # Tomar el último match
            match = matches[-1]
            section_type = match.group(1).upper()
            content = match.group(2).strip()[:800]

            print(f"\nSección {section_type} encontrada:")
            print("-" * 40)
            # Mostrar primeras líneas
            lines = content.split('\n')[:10]
            for line in lines:
                print(f"  {line.strip()}")
            print("-" * 40)
            break
    else:
        # Buscar más flexible
        simple_pattern = r'(ACUERDA|RESUELVE)[:\s]*\n*(.{100,500})'
        match = re.search(simple_pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            print(f"\nSección {match.group(1)} (flexible):")
            print(f"  {match.group(2)[:300]}...")
        else:
            # Mostrar últimos 500 caracteres
            print("\nNo se encontró sección ACUERDA/RESUELVE")
            print("Últimos 500 caracteres del documento:")
            print(text[-500:])

    print("=" * 80)

pdf_handler.close()
