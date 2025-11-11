import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ----------------------------------------------------------
st.set_page_config(page_title="Dashboard Nacimientos - San Pedro", layout="wide")
st.title("📊 Dashboard de Nacimientos - San Pedro")

# ----------------------------------------------------------
# CONEXIÓN A LA BASE DE DATOS
# ----------------------------------------------------------
conn = st.connection("postgres_db", type="sql")

# ----------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------
def limpiar_numero_columna(serie: pd.Series) -> pd.Series:
    """
    Limpia una serie que representa números con separador de miles (coma),
    espacios u otros caracteres y convierte a numérico (int64 si es posible).
    Ejemplo: "2,003" -> 2003
    """
    s = serie.astype(str)
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.replace(r"[^\d\-\.]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


@st.cache_data
def cargar_datos():
    """Carga y limpia los datos desde PostgreSQL."""
    query = 'SELECT * FROM "public"."histórico_de_nacimientos_san_pedro";'
    df = conn.query(query)

    df.columns = df.columns.str.strip().str.upper()

    if "CANTIDAD DE NACIMIENTOS" in df.columns:
        df.rename(columns={"CANTIDAD DE NACIMIENTOS": "NACIMIENTOS"}, inplace=True)

    if "AÑO" in df.columns:
        df["AÑO"] = df["AÑO"].replace({None: "", "None": ""})
        df["AÑO"] = limpiar_numero_columna(df["AÑO"])
    else:
        st.warning("La columna 'AÑO' no existe en los datos.")

    if "NACIMIENTOS" in df.columns:
        df["NACIMIENTOS"] = df["NACIMIENTOS"].replace({None: "", "None": ""})
        df["NACIMIENTOS"] = limpiar_numero_columna(df["NACIMIENTOS"])
    else:
        st.warning("La columna 'CANTIDAD DE NACIMIENTOS' / 'NACIMIENTOS' no existe en los datos.")

    return df


@st.cache_data
def cargar_total_filas():
    query = 'SELECT COUNT(*) AS total_filas FROM "public"."histórico_de_nacimientos_san_pedro";'
    df = conn.query(query)
    return int(df["total_filas"].iloc[0])


# ----------------------------------------------------------
# CARGA DE DATOS
# ----------------------------------------------------------
df = cargar_datos()
total_filas = cargar_total_filas()

# ----------------------------------------------------------
# MOSTRAR TABLA ORIGINAL (PARCIAL) Y TIPOS
# ----------------------------------------------------------
st.subheader("📋 Vista general de los datos (primeras filas)")
st.dataframe(df.head(30), use_container_width=True)

st.info(f"**Total de filas en la base de datos:** {total_filas:,}")

st.write("### 🔍 Tipos de datos detectados")
st.write(df.dtypes)

# ----------------------------------------------------------
# NUEVOS QUERIES SQL ADICIONALES
# ----------------------------------------------------------
st.header("📊 Consultas adicionales")

# Total de nacimientos registrados
query_total_nacimientos = '''
    SELECT SUM("CANTIDAD DE NACIMIENTOS") AS total_nacimientos_registrados
    FROM "public"."histórico_de_nacimientos_san_pedro";
'''
total_nac = conn.query(query_total_nacimientos)
st.metric("Total de nacimientos registrados", f"{int(total_nac.iloc[0,0]):,}")

# Total por año
query_total_por_año = '''
    SELECT "AÑO", SUM("CANTIDAD DE NACIMIENTOS") AS total_anual
    FROM "public"."histórico_de_nacimientos_san_pedro"
    GROUP BY "AÑO"
    ORDER BY "AÑO";
'''
df_total_año = conn.query(query_total_por_año)
st.write("#### 📆 Total de nacimientos por año")
st.dataframe(df_total_año, use_container_width=True)

# Total por categoría
query_total_categoria = '''
    SELECT "CATEGORÍA DE NACIMIENTOS",
           SUM("CANTIDAD DE NACIMIENTOS") AS total_nacimientos
    FROM "public"."histórico_de_nacimientos_san_pedro"
    GROUP BY "CATEGORÍA DE NACIMIENTOS"
    ORDER BY total_nacimientos DESC;
'''
df_categoria = conn.query(query_total_categoria)
st.write("#### 🧩 Total por categoría de nacimiento")
st.dataframe(df_categoria, use_container_width=True)

# ----------------------------------------------------------
# DETECCIÓN DE NULOS
# ----------------------------------------------------------
query_nulos = '''
    SELECT
        COUNT(*) FILTER (WHERE "AÑO" IS NULL) AS anios_nulos,
        COUNT(*) FILTER (WHERE "CANTIDAD DE NACIMIENTOS" IS NULL) AS nacimientos_nulos
    FROM "public"."histórico_de_nacimientos_san_pedro";
'''
df_nulos = conn.query(query_nulos)
st.write("#### 🔎 Verificación de valores nulos")
st.dataframe(df_nulos, use_container_width=True)

# ----------------------------------------------------------
# PREPARAR DATOS VÁLIDOS PARA GRAFICOS (tu código original)
# ----------------------------------------------------------
has_ano = "AÑO" in df.columns
has_nac = "NACIMIENTOS" in df.columns

if has_ano and has_nac:
    df_validos = df.dropna(subset=["AÑO", "NACIMIENTOS"]).copy()

    if not df_validos.empty:
        if (df_validos["AÑO"].dropna() % 1 == 0).all():
            df_validos["AÑO"] = df_validos["AÑO"].astype("int64")

    filas_validas = len(df_validos)
    st.write(f"Filas con 'AÑO' y 'NACIMIENTOS' válidos: **{filas_validas:,}**")

    if filas_validas > 0:
        df_agrupado = df_validos.groupby("AÑO", as_index=False)["NACIMIENTOS"].sum()

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 Nacimientos por Año (Gráfico de Barras)")
            fig_bar = px.bar(
                df_agrupado.sort_values("AÑO"),
                x="AÑO",
                y="NACIMIENTOS",
                text_auto=True,
                title="Número de Nacimientos por Año",
                labels={"AÑO": "Año", "NACIMIENTOS": "Cantidad de Nacimientos"}
            )
            fig_bar.update_layout(xaxis=dict(dtick=1))
            st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            st.subheader("📈 Tendencia de Nacimientos")
            fig_line = px.line(
                df_agrupado.sort_values("AÑO"),
                x="AÑO",
                y="NACIMIENTOS",
                markers=True,
                title="Tendencia de Nacimientos a lo Largo del Tiempo",
                labels={"AÑO": "Año", "NACIMIENTOS": "Cantidad de Nacimientos"}
            )
            fig_line.update_traces(line=dict(width=3))
            st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.warning("⚠️ No hay filas válidas con valores numéricos en 'AÑO' y 'NACIMIENTOS'. Revisa datos crudos arriba.")
else:
    st.error("❌ No se encontraron las columnas 'AÑO' y/o 'NACIMIENTOS' en la tabla.")
