#!/usr/bin/env python3
"""
Debug específico para el caso "técnicamente" que afecta 55 casos.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extraction.pdf_handler import PDFHandler

pdf_handler = PDFHandler()

# Un caso problemático
url = "https://www.cnmc.es/sites/default/files/6014416.pdf"
print(f"Analizando: {url}")

text = pdf_handler.extract_text_from_url(url)
if not text:
    print("No se pudo extraer texto")
    sys.exit(1)

print(f"\nLongitud del texto: {len(text)} caracteres")

# Buscar TODAS las ocurrencias de RESUELVE y ACUERDA
print("\n" + "=" * 80)
print("TODAS las ocurrencias de RESUELVE/ACUERDA:")
print("=" * 80)

for keyword in ["RESUELVE", "ACUERDA"]:
    matches = list(re.finditer(keyword, text, re.IGNORECASE))
    print(f"\n{keyword}: {len(matches)} ocurrencias")
    for i, m in enumerate(matches):
        pos = m.start()
        # Mostrar contexto antes y después
        before = text[max(0, pos-50):pos].replace('\n', '↵')
        after = text[pos:pos+100].replace('\n', '↵')
        print(f"  [{i}] pos={pos}: ...{before}[>>>{m.group()}<<<]{after}...")

# Buscar el patrón completo usado por el clasificador
print("\n" + "=" * 80)
print("Patrones del clasificador:")
print("=" * 80)

SECTION_PATTERNS = [
    r'(ACUERDA|RESUELVE)\s*[:\.]?\s*\n*((?:PRIMERO|ÚNICO|ÚNICA|PRIMERA|SEGUNDO|1º|1\.|I\.)[\s\S]+?)(?=Comuníquese|El presente acuerdo|El presente resolución|Madrid,|Notifíquese|COMISIÓN NACIONAL|\\Z)',
    r'(ACUERDA|RESUELVE)\s*[:\.]?\s*\n*(.+?)(?=Comuníquese|El presente|Madrid,|Notifíquese|\\Z)',
]

for i, pattern in enumerate(SECTION_PATTERNS):
    compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
    matches = list(compiled.finditer(text))
    print(f"\nPatrón {i+1}: {len(matches)} matches")
    for j, m in enumerate(matches):
        print(f"  Match {j}: pos={m.start()}, tipo={m.group(1)}")
        content = m.group(2)[:150].replace('\n', '↵')
        print(f"    Contenido: {content}...")

# Mostrar la parte final del documento donde debería estar la resolución real
print("\n" + "=" * 80)
print("ÚLTIMOS 2000 caracteres del documento:")
print("=" * 80)
print(text[-2000:])

pdf_handler.close()
