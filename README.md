# CNMC Analyzer

Herramienta para extraer, analizar y clasificar resoluciones de la Comisión Nacional de los Mercados y la Competencia (CNMC).

## Descripcion

Este proyecto automatiza el proceso de:
1. **Extraccion** de expedientes desde la web de la CNMC
2. **Analisis** y clasificacion de documentos PDF mediante reglas
3. **Generacion de informes** en Excel y visualizaciones
4. **Dashboard interactivo** con Streamlit para explorar los datos

## Requisitos

- Python >= 3.11
- Conda (recomendado) o pip

## Instalacion

### Con Conda (recomendado)

```bash
# Crear entorno
conda create -n cnmc_analyzer python=3.11

# Activar entorno
conda activate cnmc_analyzer

# Instalar dependencias
pip install -r requirements.txt
```

### Con pip

```bash
pip install -r requirements.txt
```

### Instalacion en modo desarrollo

```bash
pip install -e .
```

## Uso

### Pipeline completo

Ejecuta extraccion, analisis y generacion de informes en un solo comando:

```bash
conda activate cnmc_analyzer
python scripts/run_all.py
```

### Opciones del pipeline

| Opcion | Descripcion | Valor por defecto |
|--------|-------------|-------------------|
| `--year-from` | Año inicial de busqueda | 2024 |
| `--year-to` | Año final de busqueda | Año actual |
| `--tipo` | Tipo de expediente | Todos |
| `--ambito` | Ambito (Energia, Competencia, etc.) | Todos |
| `--max-pages` | Maximo de paginas a procesar | Sin limite |
| `--skip-extraction` | Omitir paso de extraccion | False |
| `--skip-analysis` | Omitir paso de analisis | False |
| `--skip-reporting` | Omitir generacion de informes | False |

### Ejemplos de uso

```bash
# Pipeline completo desde el año 2000
python scripts/run_all.py --year-from 2000

# Pipeline desde 2020 hasta 2024
python scripts/run_all.py --year-from 2020 --year-to 2024

# Solo expedientes de Energia desde 2023
python scripts/run_all.py --year-from 2023 --ambito Energia

# Prueba rapida (limitar a 5 paginas)
python scripts/run_all.py --year-from 2020 --max-pages 5

# Usar datos existentes (omitir extraccion)
python scripts/run_all.py --skip-extraction

# Solo generar informes (omitir extraccion y analisis)
python scripts/run_all.py --skip-extraction --skip-analysis
```

### Scripts individuales

Cada paso del pipeline puede ejecutarse por separado:

```bash
# Solo extraccion
python scripts/run_extraction.py --year-from 2023

# Solo analisis (clasificar PDFs existentes)
python scripts/run_analysis.py --input expedientes_raw.json

# Solo generacion de informes
python scripts/run_reporting.py

# Enriquecer datos de PDFs
python scripts/enrich_pdfs.py
```

### Dashboard

Visualiza los datos procesados con el dashboard interactivo:

```bash
streamlit run dashboard.py
```

## Estructura del proyecto

```
cnmc_jm/
├── config/                 # Configuracion
├── data/
│   ├── raw/               # Datos crudos extraidos
│   ├── processed/         # Datos procesados
│   └── output/            # Informes generados
├── scripts/
│   ├── run_all.py         # Pipeline completo
│   ├── run_extraction.py  # Extraccion web
│   ├── run_analysis.py    # Clasificacion PDFs
│   ├── run_reporting.py   # Generacion de informes
│   └── enrich_pdfs.py     # Enriquecimiento de datos
├── src/
│   ├── analysis/          # Modulo de clasificacion
│   │   └── classifier.py  # Clasificador de documentos
│   ├── extraction/        # Modulo de scraping
│   ├── reporting/         # Modulo de informes
│   └── utils/             # Utilidades comunes
├── tests/                 # Tests
├── dashboard.py           # Dashboard Streamlit
├── requirements.txt       # Dependencias
└── pyproject.toml         # Configuracion del proyecto
```

## Pipeline de procesamiento

### 1. Extraccion

Realiza scraping de la web de la CNMC para obtener:
- Listado de expedientes
- Metadatos (fecha, tipo, ambito, estado)
- URLs de documentos PDF

### 2. Analisis

Procesa los PDFs descargados y los clasifica segun:
- Tipo de resolucion
- Sentido del fallo
- Verificacion de cumplimiento
- Deteccion de falta de competencia

### 3. Reporting

Genera:
- Archivos Excel con los datos procesados
- Graficas y visualizaciones
- Estadisticas agregadas

## Datos de salida

Los resultados se guardan en `data/output/`:
- `expedientes_clasificados.json` - Datos en formato JSON
- `expedientes_clasificados.xlsx` - Datos en formato Excel
- Graficas en formato PNG

## Dependencias principales

- `requests`, `beautifulsoup4` - Scraping web
- `pypdf`, `pdfplumber` - Procesamiento de PDFs
- `pandas` - Analisis de datos
- `openpyxl`, `matplotlib` - Generacion de informes
- `streamlit`, `plotly` - Dashboard interactivo

## Desarrollo

### Ejecutar tests

```bash
pip install -e ".[dev]"
pytest tests/
```

## Licencia

Proyecto interno.
