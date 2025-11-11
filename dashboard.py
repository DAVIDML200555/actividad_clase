import streamlit as st
import pandas as pd
import plotly.express as px

# ----------------------------------------------------------
# CONFIGURACIÓN INICIAL
# ----------------------------------------------------------
st.set_page_config(page_title="Dashboard Nacimientos - San Pedro", layout="wide")
st.title("📊 Dashboard de Nacimientos - San Pedro")

# ----------------------------------------------------------
# ¡¡SE ELIMINA: conn = st.connection("postgres_db", type="sql")!!
# ----------------------------------------------------------

# ----------------------------------------------------------
# FUNCIONES AUXILIARES
# ----------------------------------------------------------
def limpiar_numero_columna(serie: pd.Series) -> pd.Series:
    """Limpia la serie y convierte a numérico."""
    s = serie.astype(str)
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(" ", "", regex=False)
    s = s.str.replace(r"[^\d\-\.]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


@st.cache_data
def cargar_datos():
    """Carga y limpia los datos desde el archivo CSV local."""
    
    # 🚨 CAMBIO CLAVE: Cargar el CSV
    try:
        # Asume que 'nacimientos.csv' está en la misma carpeta que dashboard.py
        df = pd.read_csv("nacimientos.csv") 
    except FileNotFoundError:
        st.error("No se encontró el archivo 'nacimientos.csv'.")
        return pd.DataFrame() # Devuelve un DataFrame vacío si falla
        
    df.columns = df.columns.str.strip().str.upper()

    # Estandarización y limpieza de nombres de columna
    col_mapping = {
        "CANTIDAD DE NACIMIENTOS": "NACIMIENTOS",
        "CATEGORÍA DE NACIMIENTOS": "CATEGORIA",
        # Asegúrate de que los nombres de tu CSV coincidan aquí
    }
    df.rename(columns=col_mapping, inplace=True)

    if "AÑO" in df.columns:
        df["AÑO"] = limpiar_numero_columna(df["AÑO"])
        # Intentamos convertir AÑO a int64 después de la limpieza
        df["AÑO"] = df["AÑO"].dropna().astype("int64", errors='ignore')
    else:
        st.warning("La columna 'AÑO' no existe en los datos CSV.")

    if "NACIMIENTOS" in df.columns:
        df["NACIMIENTOS"] = limpiar_numero_columna(df["NACIMIENTOS"])
    else:
        st.warning("La columna 'NACIMIENTOS' no existe en los datos CSV.")

    return df

# La función cargar_total_filas y los queries SQL adicionales se cambian a Pandas.
# Los queries SQL deben eliminarse ya que ahora usas DataFrames de Pandas.

# ----------------------------------------------------------
# CARGA DE DATOS Y PANDAS
# ----------------------------------------------------------
df = cargar_datos()

if df.empty:
    st.stop() # Detiene la ejecución si no hay datos.
    
total_filas = len(df)

# ----------------------------------------------------------
# MOSTRAR TABLA ORIGINAL (PARCIAL) Y TIPOS
# ----------------------------------------------------------
st.subheader("📋 Vista general de los datos (primeras filas)")
st.dataframe(df.head(30), use_container_width=True)

st.info(f"**Total de filas cargadas:** {total_filas:,}")

st.write("### 🔍 Tipos de datos detectados")
st.write(df.dtypes)

# ----------------------------------------------------------
# NUEVOS CÁLCULOS CON PANDAS (En reemplazo de QUERIES SQL)
# ----------------------------------------------------------
st.header("📊 Cálculos adicionales")

# Total de nacimientos registrados (Reemplaza query_total_nacimientos)
total_nac = df["NACIMIENTOS"].sum()
st.metric("Total de nacimientos registrados", f"{int(total_nac):,}")

# Total por año (Reemplaza query_total_por_año)
df_total_año = df.groupby("AÑO", as_index=False)["NACIMIENTOS"].sum().sort_values("AÑO")
st.write("#### 📆 Total de nacimientos por año")
st.dataframe(df_total_año, use_container_width=True)

# Total por categoría (Reemplaza query_total_categoria)
if "CATEGORIA" in df.columns:
    df_categoria = df.groupby("CATEGORIA", as_index=False)["NACIMIENTOS"].sum().sort_values("NACIMIENTOS", ascending=False)
    st.write("#### 🧩 Total por categoría de nacimiento")
    st.dataframe(df_categoria, use_container_width=True)
else:
    st.warning("No se puede mostrar el Total por Categoría: la columna 'CATEGORIA' no existe o fue renombrada.")


# Detección de Nulos (Reemplaza query_nulos)
st.write("#### 🔎 Verificación de valores nulos")
nulos = {
    "anios_nulos": df["AÑO"].isnull().sum(),
    "nacimientos_nulos": df["NACIMIENTOS"].isnull().sum()
}
df_nulos = pd.DataFrame([nulos])
st.dataframe(df_nulos, use_container_width=True)

# ----------------------------------------------------------
# PREPARAR DATOS VÁLIDOS PARA GRÁFICOS (el código original de gráficos)
# ----------------------------------------------------------
has_ano = "AÑO" in df.columns
has_nac = "NACIMIENTOS" in df.columns

if has_ano and has_nac:
    # df_validos ya se crea al cargar los datos y limpiar nulos
    df_validos = df.dropna(subset=["AÑO", "NACIMIENTOS"]).copy()
    
    # Aseguramos que 'AÑO' sea entero para agrupar
    df_validos['AÑO'] = pd.to_numeric(df_validos['AÑO'], errors='coerce').dropna().astype(int)

    if not df_validos.empty:
        filas_validas = len(df_validos)
        st.write(f"Filas con 'AÑO' y 'NACIMIENTOS' válidos para gráficos: **{filas_validas:,}**")

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
            st.warning("⚠️ No hay filas válidas con valores numéricos en 'AÑO' y 'NACIMIENTOS'.")
    else:
        st.warning("⚠️ El DataFrame está vacío después de limpiar los datos.")
else:
    st.error("❌ No se encontraron las columnas 'AÑO' y/o 'NACIMIENTOS' en el archivo CSV.")