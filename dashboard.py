"""
Dashboard interactivo para análisis de expedientes CNMC.
Ejecutar con: streamlit run dashboard.py
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="CNMC Analyzer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Colores por categoría
COLORS = {
    "DESESTIMADO": "#E74C3C",
    "ESTIMADO": "#27AE60",
    "ARCHIVADO": "#3498DB",
    "NO_CLASIFICADO": "#95A5A6",
}


def normalize_empresa(nombre: str) -> str:
    """Normaliza el nombre de una empresa para evitar duplicados."""
    import re

    if not nombre or not isinstance(nombre, str):
        return ""

    # Quitar espacios extra
    nombre = " ".join(nombre.split())

    # Ignorar patrones que no son empresas (ej: "2007- .")
    if re.match(r'^\d{4}-?\s*\.?$', nombre):
        return ""

    # Normalizar variaciones conocidas
    normalizaciones = {
        # REE
        "RED ELECTRICA DE ESPANA": "REE",
        "RED ELECTRICA DE ESPAÑA": "REE",
        "RED ELÉCTRICA DE ESPAÑA": "REE",
        "REE.": "REE",
        # E-DISTRIBUCIÓN
        "EDISTRIBUCIÓN REDES DIGITALES S.L.U.": "E-DISTRIBUCIÓN",
        "EDISTRIBUCION REDES DIGITALES S.L.U.": "E-DISTRIBUCIÓN",
        "E-DISTRIBUCIÓN REDES DIGITALES S.L.U.": "E-DISTRIBUCIÓN",
        "E-DISTRIBUCION REDES DIGITALES S.L.U.": "E-DISTRIBUCIÓN",
        "EDISTRIBUCIÓN REDES DIGITALES": "E-DISTRIBUCIÓN",
        "E-DISTRIBUCIÓN REDES DIGITALES": "E-DISTRIBUCIÓN",
        "E-DISTRIBUCION REDES DIGITALES": "E-DISTRIBUCIÓN",
        "EDISTRIBUCIÓN": "E-DISTRIBUCIÓN",
        "EDISTRIBUCION": "E-DISTRIBUCIÓN",
        # I-DE
        "I-DE REDES ELÉCTRICAS INTELIGENTES S.A.U.": "I-DE",
        "I-DE REDES ELECTRICAS INTELIGENTES S.A.U.": "I-DE",
        "I-DE REDES ELÉCTRICAS INTELIGENTES S.A.": "I-DE",
        "I-DE REDES ELECTRICAS INTELIGENTES S.A.": "I-DE",
        "I-DE REDES ELECTRICAS INTELIGENTES": "I-DE",
        "I-DE REDES ELÉCTRICAS INTELIGENTES": "I-DE",
        # UFD
        "UFD DISTRIBUCIÓN ELECTRICIDAD S.A.": "UFD",
        "UFD DISTRIBUCION ELECTRICIDAD S.A.": "UFD",
        "UFD DISTRIBUCIÓN ELECTRICIDAD": "UFD",
        # IBERDROLA
        "IBERDROLA DISTRIBUCIÓN ELÉCTRICA S.A.U.": "IBERDROLA DISTRIBUCIÓN",
        "IBERDROLA DISTRIBUCION ELECTRICA S.A.U.": "IBERDROLA DISTRIBUCIÓN",
        "IBERDROLA DISTRIBUCIÓN ELÉCTRICA": "IBERDROLA DISTRIBUCIÓN",
        "IBERDROLA S": "IBERDROLA",
        # ENAGÁS
        "ENAGÁS TRANSPORTE S.A.": "ENAGÁS",
        "ENAGÁS TRANSPORTES S.A.": "ENAGÁS",
        "ENAGÁS TRANSPORTE": "ENAGÁS",
        "ENAGÁS GTS": "ENAGÁS",
        "ENAGÁS TRANSPORTE Y ENAGÁS GTS": "ENAGÁS",
        "ENAGAS S": "ENAGÁS",
        "ENAGAS": "ENAGÁS",
        # ENDESA
        "ENDESA DISTRIBUCIÓN": "ENDESA",
        "ENDESA DISTRIBUCIÓN ELÉCTRICA": "ENDESA",
        "ENDESA DISTRIBUCIÓN ELÉCTRICA S": "ENDESA",
        # NATURGY / UNIÓN FENOSA
        "NATURGY IBERIA": "NATURGY",
        "GAS NATURAL FENOSA": "NATURGY",
        "UNIÓN FENOSA DISTRIBUCIÓN": "NATURGY",
        "UNIÓN FENOSA DISTRIBUCIÓN S": "NATURGY",
        # VIESGO
        "VIESGO DISTRIBUCIÓN ELÉCTRICA": "VIESGO",
        # I-DE variaciones
        "IDE": "I-DE",
    }

    nombre_upper = nombre.upper()
    for variacion, normalizado in normalizaciones.items():
        if variacion in nombre_upper or nombre_upper in variacion:
            return normalizado

    # Limpiar sufijos comunes para nombres no normalizados
    nombre = re.sub(r'\s*S\.?L\.?U?\.?\s*$', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'\s*S\.?A\.?U?\.?\s*$', '', nombre, flags=re.IGNORECASE)

    return nombre.strip()


def extract_empresas(titulo: str) -> tuple[str, str]:
    """Extrae reclamante y demandado del título."""
    import re

    if not titulo or not isinstance(titulo, str):
        return ("", "")

    # Caso 1: Títulos descriptivos largos - buscar patrones "INSTADO POR X FRENTE A Y"
    match = re.search(
        r'(?:INSTADO|INTERPUESTO|PRESENTADO)\s+POR\s+(.+?)\s+(?:FRENTE\s+A|CONTRA)\s+(.+?)(?:\s*[-,\.]|$)',
        titulo, re.IGNORECASE
    )
    if match:
        reclamante = match.group(1).strip()
        demandado = match.group(2).strip()
        # Limpiar sufijos
        demandado = re.split(r'\s+(?:EN|PARA|POR|SOBRE|RELAT)', demandado, flags=re.IGNORECASE)[0]
        return (normalize_empresa(reclamante), normalize_empresa(demandado))

    # Caso 2: Patrón "X VS Y" o "X FRENTE A Y"
    for sep_pattern in [r'\s+VS\.?\s+', r'\s+FRENTE\s+A\s+', r'\s+CONTRA\s+']:
        match = re.search(sep_pattern, titulo, re.IGNORECASE)
        if match:
            partes = re.split(sep_pattern, titulo, maxsplit=1, flags=re.IGNORECASE)
            if len(partes) == 2:
                reclamante = partes[0].strip()
                demandado = partes[1].strip()
                # Limpiar prefijos comunes del reclamante
                reclamante = re.sub(r'^(?:CATR|CONFLICTO DE ACCESO)\s+', '', reclamante, flags=re.IGNORECASE)
                # Limpiar sufijos del demandado
                demandado = re.split(r'\s+[-\(]', demandado)[0].strip()
                return (normalize_empresa(reclamante), normalize_empresa(demandado))

    # Caso 3: Patrón "CATR X  - Y" (doble espacio + guión)
    if re.match(r'^CATR\s+', titulo, re.IGNORECASE):
        match = re.search(r'^CATR\s+(.+?)\s{2,}-\s*(.+?)(?:\s*[-\(]|$)', titulo, re.IGNORECASE)
        if match:
            reclamante = match.group(1).strip()
            demandado = match.group(2).strip()
            return (normalize_empresa(reclamante), normalize_empresa(demandado))
        # Si no hay demandado explícito, buscar empresas conocidas
        empresas_conocidas = ['REE', 'UFD', 'I-DE', 'E-DISTRIBUCIÓN', 'IBERDROLA', 'ENDESA', 'ENAGÁS']
        for emp in empresas_conocidas:
            if emp in titulo.upper():
                # El demandado es la empresa conocida, el reclamante es el resto
                reclamante = re.sub(r'^CATR\s+', '', titulo, flags=re.IGNORECASE)
                reclamante = re.sub(rf'\s*-?\s*{emp}.*$', '', reclamante, flags=re.IGNORECASE).strip()
                return (normalize_empresa(reclamante), emp)

    # Caso 4: Separador "/" pero verificar que no sea parte de un número
    if '/' in titulo:
        # Si el "/" va seguido de un número (ej: "11/2005"), no es separador de empresas
        if not re.search(r'/\s*\d', titulo):
            separadores = [" / ", "/ ", " /", "/"]
            for sep in separadores:
                if sep in titulo:
                    partes = titulo.split(sep, 1)
                    reclamante = partes[0].strip()
                    resto = partes[1] if len(partes) > 1 else ""

                    # El demandado puede tener " -" al final con más info
                    if " -" in resto:
                        demandado = resto.split(" -")[0].strip()
                    elif " (" in resto:
                        demandado = resto.split(" (")[0].strip()
                    else:
                        demandado = resto.strip()

                    return (normalize_empresa(reclamante), normalize_empresa(demandado))

    # Caso 5: Buscar empresas conocidas en títulos sin separador claro
    empresas_conocidas_patrones = [
        (r'\bREE\b', 'REE'),
        (r'\bUFD\b', 'UFD'),
        (r'I-DE', 'I-DE'),
        (r'E-DISTRIBUCIÓN', 'E-DISTRIBUCIÓN'),
        (r'IBERDROLA', 'IBERDROLA'),
        (r'ENDESA', 'ENDESA'),
        (r'ENAGÁS', 'ENAGÁS'),
        (r'VIESGO', 'VIESGO'),
    ]

    for patron, nombre in empresas_conocidas_patrones:
        if re.search(patron, titulo, re.IGNORECASE):
            # Si encontramos una empresa conocida, asumimos que es el demandado
            # y el resto es el reclamante (limpiando prefijos)
            reclamante = re.sub(rf'\s*[-/]?\s*{patron}.*$', '', titulo, flags=re.IGNORECASE)
            reclamante = re.sub(r'^(?:CATR|CONFLICTO[^/]*)\s+', '', reclamante, flags=re.IGNORECASE)
            if reclamante.strip():
                return (normalize_empresa(reclamante.strip()), nombre)

    # Si no hay separador ni empresa conocida, solo devolver el título como reclamante
    reclamante = re.sub(r'^(?:CATR|CONFLICTO[^/]*)\s+', '', titulo, flags=re.IGNORECASE)
    return (normalize_empresa(reclamante), "")


@st.cache_data
def load_data() -> pd.DataFrame:
    """Carga los datos de expedientes analizados."""
    data_path = Path(__file__).parent / "data" / "processed" / "expedientes_analyzed.json"

    if not data_path.exists():
        st.error(f"No se encontró el archivo de datos: {data_path}")
        return pd.DataFrame()

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # Convertir fecha a datetime
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # Extraer año y mes para análisis temporal
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["año_mes"] = df["fecha"].dt.to_period("M").astype(str)

    # Extraer empresas del título con normalización
    empresas = df["titulo"].apply(extract_empresas)
    df["reclamante"] = empresas.apply(lambda x: x[0])
    df["demandado"] = empresas.apply(lambda x: x[1])

    # Filtrar filas con demandado vacío para análisis de empresas
    df["tiene_demandado"] = df["demandado"] != ""

    return df


def render_kpis(df: pd.DataFrame, df_filtered: pd.DataFrame):
    """Renderiza los KPIs principales."""
    col1, col2, col3, col4, col5 = st.columns(5)

    total = len(df_filtered)
    estimados = len(df_filtered[df_filtered["resultado_clasificado"] == "ESTIMADO"])
    desestimados = len(df_filtered[df_filtered["resultado_clasificado"] == "DESESTIMADO"])
    archivados = len(df_filtered[df_filtered["resultado_clasificado"] == "ARCHIVADO"])
    no_clasif = len(df_filtered[df_filtered["resultado_clasificado"] == "NO_CLASIFICADO"])

    with col1:
        st.metric("Total Expedientes", f"{total:,}")

    with col2:
        pct = (estimados / total * 100) if total > 0 else 0
        st.metric("Estimados", f"{estimados:,}", f"{pct:.1f}%")

    with col3:
        pct = (desestimados / total * 100) if total > 0 else 0
        st.metric("Desestimados", f"{desestimados:,}", f"{pct:.1f}%")

    with col4:
        pct = (archivados / total * 100) if total > 0 else 0
        st.metric("Archivados", f"{archivados:,}", f"{pct:.1f}%")

    with col5:
        pct = (no_clasif / total * 100) if total > 0 else 0
        st.metric("Sin Clasificar", f"{no_clasif:,}", f"{pct:.1f}%")


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """Renderiza los filtros en la barra lateral y devuelve el DataFrame filtrado."""
    st.sidebar.header("🔍 Filtros")

    # Filtro de fechas
    st.sidebar.subheader("Rango de fechas")
    min_date = df["fecha"].min()
    max_date = df["fecha"].max()

    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.sidebar.date_input(
            "Seleccionar rango",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[
                (df["fecha"].dt.date >= start_date) &
                (df["fecha"].dt.date <= end_date)
            ]

    # Filtro de resultado
    st.sidebar.subheader("Resultado")
    resultados = ["Todos"] + sorted(df["resultado_clasificado"].dropna().unique().tolist())
    resultado_sel = st.sidebar.selectbox("Clasificación", resultados)
    if resultado_sel != "Todos":
        df = df[df["resultado_clasificado"] == resultado_sel]

    # Filtro de confianza
    st.sidebar.subheader("Confianza")
    confianzas = ["Todas"] + sorted(df["confianza"].dropna().unique().tolist())
    confianza_sel = st.sidebar.selectbox("Nivel de confianza", confianzas)
    if confianza_sel != "Todas":
        df = df[df["confianza"] == confianza_sel]

    # Filtro de año
    st.sidebar.subheader("Año")
    años = ["Todos"] + sorted(df["año"].dropna().unique().astype(int).tolist(), reverse=True)
    año_sel = st.sidebar.selectbox("Año", años)
    if año_sel != "Todos":
        df = df[df["año"] == año_sel]

    # Filtro de demandado (empresa contra la que se reclama)
    st.sidebar.subheader("Demandado")
    demandados = df["demandado"].value_counts()
    top_demandados = ["Todos"] + demandados.head(20).index.tolist()
    demandado_sel = st.sidebar.selectbox("Empresa demandada", top_demandados)
    if demandado_sel != "Todos":
        df = df[df["demandado"] == demandado_sel]

    # Búsqueda por texto
    st.sidebar.subheader("Búsqueda")
    search_text = st.sidebar.text_input("Buscar en título o ID")
    if search_text:
        mask = (
            df["titulo"].str.contains(search_text, case=False, na=False) |
            df["id"].str.contains(search_text, case=False, na=False)
        )
        df = df[mask]

    return df


def render_distribution_chart(df: pd.DataFrame):
    """Renderiza gráfico de distribución de resultados."""
    st.subheader("📊 Distribución de Resultados")

    # Contar por resultado
    counts = df["resultado_clasificado"].value_counts()

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de pastel con Streamlit nativo
        import plotly.express as px

        fig = px.pie(
            values=counts.values,
            names=counts.index,
            color=counts.index,
            color_discrete_map=COLORS,
            hole=0.4,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Gráfico de barras
        fig = px.bar(
            x=counts.index,
            y=counts.values,
            color=counts.index,
            color_discrete_map=COLORS,
            labels={"x": "Resultado", "y": "Cantidad"},
        )
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)


def render_timeline_chart(df: pd.DataFrame):
    """Renderiza evolución temporal."""
    st.subheader("📈 Evolución Temporal")

    # Agrupar por mes y resultado
    timeline = df.groupby(["año_mes", "resultado_clasificado"]).size().unstack(fill_value=0)
    timeline = timeline.sort_index()

    if not timeline.empty:
        import plotly.express as px

        # Preparar datos para plotly
        timeline_reset = timeline.reset_index().melt(
            id_vars="año_mes",
            var_name="Resultado",
            value_name="Cantidad"
        )

        fig = px.line(
            timeline_reset,
            x="año_mes",
            y="Cantidad",
            color="Resultado",
            color_discrete_map=COLORS,
            markers=True,
        )
        fig.update_layout(
            xaxis_title="Período",
            yaxis_title="Número de expedientes",
            legend_title="Resultado",
            margin=dict(t=20, b=20, l=20, r=20),
        )
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)


def render_empresas_section(df: pd.DataFrame):
    """Renderiza la sección completa de análisis de empresas."""
    st.subheader("🏢 Análisis de Empresas")

    # Filtrar solo expedientes con demandado válido para análisis
    df_empresas = df[df["tiene_demandado"]].copy()

    if df_empresas.empty:
        st.warning("No hay datos de empresas para mostrar.")
        return

    # Filtro de mínimo de conflictos
    min_conflictos = st.slider(
        "Mínimo de conflictos para incluir empresa",
        min_value=1, max_value=20, value=3,
        help="Filtra empresas con menos conflictos del umbral seleccionado"
    )

    # Sub-tabs para organizar
    tab_demandados, tab_reclamantes, tab_detalle = st.tabs([
        "📊 Demandados",
        "📈 Reclamantes",
        "🔎 Detalle Empresa"
    ])

    with tab_demandados:
        render_demandados_tab(df_empresas, min_conflictos)

    with tab_reclamantes:
        render_reclamantes_tab(df_empresas, min_conflictos)

    with tab_detalle:
        render_empresa_detalle_tab(df_empresas)


def render_demandados_tab(df: pd.DataFrame, min_conflictos: int):
    """Tab de análisis de empresas demandadas."""
    import plotly.express as px

    # Calcular estadísticas por demandado
    stats = df.groupby("demandado").agg({
        "id": "count",
        "resultado_clasificado": [
            lambda x: (x == "ESTIMADO").sum(),
            lambda x: (x == "DESESTIMADO").sum(),
            lambda x: (x == "ARCHIVADO").sum(),
        ]
    })
    stats.columns = ["Total", "Estimados", "Desestimados", "Archivados"]
    stats = stats[stats["Total"] >= min_conflictos].copy()

    # Calcular tasas
    stats["Tasa Estimacion"] = (stats["Estimados"] / stats["Total"] * 100).round(1)
    stats["Tasa Desestimacion"] = (stats["Desestimados"] / stats["Total"] * 100).round(1)
    stats = stats.sort_values("Total", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Top 10 - Empresas más demandadas**")
        top10 = stats.head(10)

        # Gráfico de barras stacked
        plot_data = top10[["Estimados", "Desestimados", "Archivados"]].reset_index()
        plot_data = plot_data.melt(
            id_vars="demandado",
            var_name="Resultado",
            value_name="Cantidad"
        )

        fig = px.bar(
            plot_data,
            y="demandado",
            x="Cantidad",
            color="Resultado",
            orientation="h",
            color_discrete_map={
                "Estimados": COLORS["ESTIMADO"],
                "Desestimados": COLORS["DESESTIMADO"],
                "Archivados": COLORS["ARCHIVADO"],
            },
        )
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            margin=dict(t=20, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("**Top 10 - Mayor tasa de estimación (favorable al reclamante)**")
        top_estimacion = stats.sort_values("Tasa Estimacion", ascending=False).head(10)

        fig = px.bar(
            top_estimacion.reset_index(),
            y="demandado",
            x="Tasa Estimacion",
            orientation="h",
            color="Tasa Estimacion",
            color_continuous_scale=["#E74C3C", "#F39C12", "#27AE60"],
            text="Tasa Estimacion",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
            height=400,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tabla completa
    st.write("**Tabla completa de empresas demandadas**")
    tabla = stats.reset_index().rename(columns={
        "demandado": "Empresa",
        "Tasa Estimacion": "% Estimación",
        "Tasa Desestimacion": "% Desestimación",
    })
    st.dataframe(
        tabla,
        hide_index=True,
        use_container_width=True,
        column_config={
            "% Estimación": st.column_config.ProgressColumn(
                "% Estimación", min_value=0, max_value=100, format="%.1f%%"
            ),
            "% Desestimación": st.column_config.ProgressColumn(
                "% Desestimación", min_value=0, max_value=100, format="%.1f%%"
            ),
        }
    )


def render_reclamantes_tab(df: pd.DataFrame, min_conflictos: int):
    """Tab de análisis de empresas reclamantes."""
    import plotly.express as px

    # Calcular estadísticas por reclamante
    stats = df.groupby("reclamante").agg({
        "id": "count",
        "resultado_clasificado": [
            lambda x: (x == "ESTIMADO").sum(),
            lambda x: (x == "DESESTIMADO").sum(),
            lambda x: (x == "ARCHIVADO").sum(),
        ]
    })
    stats.columns = ["Total", "Estimados", "Desestimados", "Archivados"]
    stats = stats[stats["Total"] >= min_conflictos].copy()

    # Calcular tasa de éxito (estimaciones conseguidas)
    stats["Tasa Exito"] = (stats["Estimados"] / stats["Total"] * 100).round(1)
    stats = stats.sort_values("Total", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Top 10 - Empresas que más reclaman**")
        top10 = stats.head(10)

        fig = px.bar(
            top10.reset_index(),
            y="reclamante",
            x="Total",
            orientation="h",
            color="Tasa Exito",
            color_continuous_scale=["#E74C3C", "#F39C12", "#27AE60"],
            text="Total",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            margin=dict(t=20, b=20, l=20, r=20),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("**Top 10 - Mayor tasa de éxito (reclamaciones estimadas)**")
        top_exito = stats.sort_values("Tasa Exito", ascending=False).head(10)

        fig = px.bar(
            top_exito.reset_index(),
            y="reclamante",
            x="Tasa Exito",
            orientation="h",
            color="Tasa Exito",
            color_continuous_scale=["#E74C3C", "#F39C12", "#27AE60"],
            text="Tasa Exito",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            yaxis={"categoryorder": "total ascending"},
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
            height=400,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Tabla completa
    st.write("**Tabla completa de empresas reclamantes**")
    tabla = stats.reset_index().rename(columns={
        "reclamante": "Empresa",
        "Tasa Exito": "% Éxito",
    })
    st.dataframe(
        tabla,
        hide_index=True,
        use_container_width=True,
        column_config={
            "% Éxito": st.column_config.ProgressColumn(
                "% Éxito", min_value=0, max_value=100, format="%.1f%%"
            ),
        }
    )


def render_empresa_detalle_tab(df: pd.DataFrame):
    """Tab de detalle de una empresa específica."""
    import plotly.express as px

    # Obtener lista de empresas (demandados y reclamantes)
    todas_empresas = set(df["demandado"].unique()) | set(df["reclamante"].unique())
    todas_empresas = sorted([e for e in todas_empresas if e])

    empresa_sel = st.selectbox("Seleccionar empresa", options=todas_empresas)

    if not empresa_sel:
        return

    # Filtrar expedientes donde la empresa es demandada o reclamante
    df_demandado = df[df["demandado"] == empresa_sel]
    df_reclamante = df[df["reclamante"] == empresa_sel]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Como demandado", len(df_demandado))
    with col2:
        st.metric("Como reclamante", len(df_reclamante))
    with col3:
        if len(df_demandado) > 0:
            tasa_est = (df_demandado["resultado_clasificado"] == "ESTIMADO").sum() / len(df_demandado) * 100
            st.metric("% Estimación (demandado)", f"{tasa_est:.1f}%")
        else:
            st.metric("% Estimación (demandado)", "N/A")
    with col4:
        if len(df_reclamante) > 0:
            tasa_exito = (df_reclamante["resultado_clasificado"] == "ESTIMADO").sum() / len(df_reclamante) * 100
            st.metric("% Éxito (reclamante)", f"{tasa_exito:.1f}%")
        else:
            st.metric("% Éxito (reclamante)", "N/A")

    col1, col2 = st.columns(2)

    with col1:
        if len(df_demandado) > 0:
            st.write("**Distribución como demandado**")
            counts = df_demandado["resultado_clasificado"].value_counts()
            fig = px.pie(
                values=counts.values,
                names=counts.index,
                color=counts.index,
                color_discrete_map=COLORS,
                hole=0.4,
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if len(df_reclamante) > 0:
            st.write("**Distribución como reclamante**")
            counts = df_reclamante["resultado_clasificado"].value_counts()
            fig = px.pie(
                values=counts.values,
                names=counts.index,
                color=counts.index,
                color_discrete_map=COLORS,
                hole=0.4,
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Evolución temporal
    df_empresa = pd.concat([df_demandado, df_reclamante]).drop_duplicates(subset=["id"])
    if len(df_empresa) > 0 and df_empresa["fecha"].notna().any():
        st.write("**Evolución temporal de conflictos**")
        timeline = df_empresa.groupby(["año", "resultado_clasificado"]).size().unstack(fill_value=0)

        if not timeline.empty:
            timeline_reset = timeline.reset_index().melt(
                id_vars="año",
                var_name="Resultado",
                value_name="Cantidad"
            )
            fig = px.bar(
                timeline_reset,
                x="año",
                y="Cantidad",
                color="Resultado",
                color_discrete_map=COLORS,
                barmode="stack",
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig, use_container_width=True)

    # Lista de expedientes
    st.write("**Expedientes relacionados**")
    df_display = df_empresa[["id", "fecha", "titulo", "resultado_clasificado", "demandado", "reclamante"]].copy()
    df_display["fecha"] = df_display["fecha"].dt.strftime("%Y-%m-%d")
    df_display["Rol"] = df_display.apply(
        lambda x: "Demandado" if x["demandado"] == empresa_sel else "Reclamante", axis=1
    )
    st.dataframe(
        df_display[["id", "fecha", "Rol", "resultado_clasificado", "titulo"]].rename(columns={
            "id": "ID",
            "fecha": "Fecha",
            "resultado_clasificado": "Resultado",
            "titulo": "Título",
        }),
        hide_index=True,
        use_container_width=True,
        height=300,
    )


def render_expedientes_table(df: pd.DataFrame):
    """Renderiza la tabla de expedientes."""
    st.subheader("📋 Listado de Expedientes")

    # Preparar columnas para mostrar
    display_cols = [
        "id", "fecha", "titulo", "resultado_clasificado",
        "confianza", "texto_clave", "demandado"
    ]

    df_display = df[display_cols].copy()
    df_display["fecha"] = df_display["fecha"].dt.strftime("%Y-%m-%d")
    df_display = df_display.rename(columns={
        "id": "ID",
        "fecha": "Fecha",
        "titulo": "Título",
        "resultado_clasificado": "Resultado",
        "confianza": "Confianza",
        "texto_clave": "Texto Clave",
        "demandado": "Demandado",
    })

    # Colorear por resultado
    def highlight_resultado(row):
        color = COLORS.get(row["Resultado"], "#FFFFFF")
        return [f"background-color: {color}20" if col == "Resultado" else "" for col in row.index]

    st.dataframe(
        df_display.style.apply(highlight_resultado, axis=1),
        use_container_width=True,
        height=400,
    )

    # Botón de descarga
    csv = df_display.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"expedientes_cnmc_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )


def render_expediente_detail(df: pd.DataFrame):
    """Renderiza detalle de un expediente específico."""
    st.subheader("🔎 Detalle de Expediente")

    # Selector de expediente
    expediente_id = st.selectbox(
        "Seleccionar expediente",
        options=df["id"].tolist(),
        format_func=lambda x: f"{x} - {df[df['id'] == x]['titulo'].values[0][:50]}..."
    )

    if expediente_id:
        exp = df[df["id"] == expediente_id].iloc[0]

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**ID:** {exp['id']}")
            st.write(f"**Fecha:** {exp['fecha'].strftime('%Y-%m-%d') if pd.notna(exp['fecha']) else 'N/A'}")
            st.write(f"**Tipo:** {exp['tipo']}")
            st.write(f"**Sector:** {exp['sector']}")
            st.write(f"**Ámbito:** {exp['ambito']}")

        with col2:
            resultado = exp["resultado_clasificado"]
            color = COLORS.get(resultado, "#95A5A6")
            st.markdown(
                f"**Resultado:** <span style='background-color:{color};padding:2px 8px;border-radius:4px;color:white'>{resultado}</span>",
                unsafe_allow_html=True
            )
            st.write(f"**Confianza:** {exp['confianza']}")
            st.write(f"**Texto clave:** _{exp['texto_clave']}_")

        st.write(f"**Título completo:** {exp['titulo']}")

        # Links
        col1, col2 = st.columns(2)
        with col1:
            if exp["url"]:
                st.link_button("🔗 Ver en CNMC", exp["url"])
        with col2:
            if exp["url_resolucion"]:
                st.link_button("📄 Ver PDF Resolución", exp["url_resolucion"])


def render_confianza_analysis(df: pd.DataFrame):
    """Análisis de confianza de clasificación."""
    st.subheader("🎯 Análisis de Confianza")

    # Cruzar confianza con resultado
    cross = pd.crosstab(
        df["resultado_clasificado"],
        df["confianza"],
        margins=True,
        margins_name="Total"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Matriz Resultado x Confianza**")
        st.dataframe(cross, use_container_width=True)

    with col2:
        # Porcentaje de confianza por resultado
        conf_pct = df.groupby("resultado_clasificado")["confianza"].value_counts(normalize=True).unstack() * 100

        import plotly.express as px

        conf_pct_reset = conf_pct.reset_index().melt(
            id_vars="resultado_clasificado",
            var_name="Confianza",
            value_name="Porcentaje"
        )

        fig = px.bar(
            conf_pct_reset,
            x="resultado_clasificado",
            y="Porcentaje",
            color="Confianza",
            barmode="stack",
            labels={"resultado_clasificado": "Resultado"},
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)


def main():
    """Función principal del dashboard."""
    st.title("⚖️ CNMC Analyzer Dashboard")
    st.markdown("Análisis interactivo de expedientes de conflictos de acceso en energía")

    # Cargar datos
    df = load_data()

    if df.empty:
        st.warning("No hay datos para mostrar. Ejecuta primero el pipeline de análisis.")
        return

    # Aplicar filtros
    df_filtered = render_sidebar(df)

    # Mostrar mensaje si no hay resultados
    if df_filtered.empty:
        st.warning("No hay expedientes que coincidan con los filtros seleccionados.")
        return

    # KPIs
    render_kpis(df, df_filtered)

    st.divider()

    # Tabs para organizar contenido
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Distribución",
        "📈 Temporal",
        "🏢 Empresas",
        "📋 Expedientes",
        "🔎 Detalle"
    ])

    with tab1:
        render_distribution_chart(df_filtered)
        render_confianza_analysis(df_filtered)

    with tab2:
        render_timeline_chart(df_filtered)

    with tab3:
        render_empresas_section(df_filtered)

    with tab4:
        render_expedientes_table(df_filtered)

    with tab5:
        render_expediente_detail(df_filtered)

    # Footer
    st.divider()
    st.caption(
        f"📊 Datos cargados: {len(df):,} expedientes | "
        f"Filtrados: {len(df_filtered):,} | "
        f"Última actualización: {df['fecha'].max().strftime('%Y-%m-%d') if pd.notna(df['fecha'].max()) else 'N/A'}"
    )


if __name__ == "__main__":
    main()
