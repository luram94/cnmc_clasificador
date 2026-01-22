#!/usr/bin/env python3
"""
Script para depurar el clasificador en casos NO_CLASIFICADO.
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

# Agrupar por keyword encontrada para entender patrones
keyword_groups = {}
for exp in no_clasificados:
    keywords = exp.get("keywords_encontradas", [])
    key = keywords[0] if keywords else "sin_keyword"
    if key not in keyword_groups:
        keyword_groups[key] = []
    keyword_groups[key].append(exp)

print("\nAgrupación por keyword encontrada:")
for key, exps in sorted(keyword_groups.items(), key=lambda x: -len(x[1])):
    print(f"  {key}: {len(exps)} casos")

# Analizar unos pocos casos en detalle
classifier = ResolutionClassifierV2()
pdf_handler = PDFHandler()

print("\n" + "=" * 80)
print("ANÁLISIS DETALLADO DE CASOS")
print("=" * 80)

# Tomar 3 muestras de cada grupo principal
samples_to_analyze = []

# Casos con "Desestimar los conflict" (plural)
plural_desestimar = [e for e in no_clasificados if "Desestimar los conflict" in str(e.get("keywords_encontradas", []))]
if plural_desestimar:
    samples_to_analyze.append(("PLURAL_DESESTIMAR", plural_desestimar[0]))

# Casos con "Estimar los conflicto"
plural_estimar = [e for e in no_clasificados if "Estimar los conflicto" in str(e.get("keywords_encontradas", []))]
if plural_estimar:
    samples_to_analyze.append(("PLURAL_ESTIMAR", plural_estimar[0]))

# Casos con "Avocar"
avocar = [e for e in no_clasificados if "Avocar" in str(e.get("keywords_encontradas", []))]
if avocar:
    samples_to_analyze.append(("AVOCAR", avocar[0]))

# Casos con "n técnicamente" (fragmento raro)
tecnico = [e for e in no_clasificados if "n técnicamente" in str(e.get("keywords_encontradas", []))]
if tecnico:
    samples_to_analyze.append(("TECNICO_FRAGMENT", tecnico[0]))

for case_type, exp in samples_to_analyze:
    print(f"\n{'='*80}")
    print(f"CASO: {case_type}")
    print(f"Expediente: {exp['id']}")
    print(f"URL: {exp.get('url_resolucion', 'N/A')}")
    print(f"Keyword original: {exp.get('keywords_encontradas', [])}")

    if not exp.get('url_resolucion'):
        continue

    text = pdf_handler.extract_text_from_url(exp['url_resolucion'])
    if not text:
        print("No se pudo extraer texto")
        continue

    # Ejecutar clasificador y ver resultado
    result = classifier.classify(text)
    print(f"\nResultado clasificador:")
    print(f"  Categoría: {result.categoria}")
    print(f"  Confianza: {result.confianza}")
    print(f"  Texto clave: {result.texto_clave}")
    print(f"  Sección encontrada: {result.seccion_encontrada}")

    # Buscar sección manualmente
    print(f"\nBúsqueda manual de sección:")
    section_result = classifier._extract_resolution_section(text)
    if section_result:
        section_type, content = section_result
        print(f"  Sección: {section_type}")
        print(f"  Contenido (primeros 500 chars):")
        print(f"  {content[:500]}")

        # Buscar patrón específico en el contenido
        print(f"\n  Búsqueda de patrones en contenido:")
        for cat, patterns in classifier.CATEGORIES.items():
            for p in patterns:
                compiled = re.compile(p, re.IGNORECASE)
                match = compiled.search(content)
                if match:
                    print(f"    ✓ {cat}: '{match.group(0)}'")
    else:
        print("  No se encontró sección ACUERDA/RESUELVE")
        # Mostrar últimas ocurrencias de ACUERDA/RESUELVE
        acuerda_matches = list(re.finditer(r'ACUERDA|RESUELVE', text, re.IGNORECASE))
        print(f"  Ocurrencias de ACUERDA/RESUELVE: {len(acuerda_matches)}")
        for i, m in enumerate(acuerda_matches[-3:]):
            pos = m.start()
            context = text[pos:pos+200].replace('\n', ' ')
            print(f"    [{i}] pos={pos}: {context}...")

pdf_handler.close()
