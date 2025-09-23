import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
import openai
import json

# Configuración inicial
st.set_page_config(page_title="📄 Extractor Pagarés con IA", layout="wide")
st.title("✍️ Extractor de Pagarés - COS JudicIA 🤖")

# API Key segura desde Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Llamar IA para extraer texto estructurado
def extraer_con_ia(imagen_bytes, instruccion):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de documentos legales y pagarés."},
                {"role": "user", "content": instruccion},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64.b64encode(imagen_bytes).decode()}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error al procesar la imagen: {e}"

# Inicializar base de datos acumulativa
if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []

# Función para limpiar el JSON devuelto por la IA
def limpiar_json(texto):
    try:
        start = texto.index("{")
        end = texto.rindex("}") + 1
        return texto[start:end]
    except:
        return texto  # Si falla, se devuelve igual

# Paso 1: Cabecera
st.header("📌 Paso 1: Subir imagen de la parte superior del pagaré")
cabecera = st.file_uploader("🧾 Imagen de la cabecera del pagaré (incluye ciudad, fecha, valor en letras y números)", type=["png", "jpg", "jpeg"], key="cabecera")

# Paso 2: Parte manuscrita
st.header("📝 Paso 2: Subir imagen de la parte inferior manuscrita")
manuscrita = st.file_uploader("✍️ Imagen manuscrita (nombre, cédula, dirección, ciudad, teléfono, firma)", type=["png", "jpg", "jpeg"], key="manuscrita")

# Procesar imágenes
if cabecera and manuscrita:
    col1, col2 = st.columns(2)
    with col1:
        st.image(cabecera, caption="Cabecera", use_column_width=True)
    with col2:
        st.image(manuscrita, caption="Parte Manuscrita", use_container_width=True)

    if st.button("🤖 Extraer datos con IA"):
        cabecera_bytes = cabecera.read()
        manuscrita_bytes = manuscrita.read()

        instruccion_cabecera = """
Extrae los siguientes datos del pagaré: 
- Número de pagaré (si aparece)
- Ciudad
- Día (en letras)
- Día (en número)
- Mes
- Año (en letras)
- Año (en número)
- Valor en letras
- Valor en números

Devuélvelo en formato JSON con esos campos.
"""

        instruccion_manuscrita = """
Extrae los siguientes datos manuscritos del pagaré:
- Nombre del deudor
- Cédula o número de identificación
- Dirección
- Ciudad
- Teléfono
- Fecha de firma (completa)

Devuélvelo en formato JSON con esos campos.
"""

        # Procesar con IA
        resultado_cabecera = extraer_con_ia(cabecera_bytes, instruccion_cabecera)
        resultado_manuscrita = extraer_con_ia(manuscrita_bytes, instruccion_manuscrita)

        st.subheader("🧾 Resultado - Cabecera")
        st.code(resultado_cabecera, language="json")
        st.subheader("🧾 Resultado - Parte Manuscrita")
        st.code(resultado_manuscrita, language="json")

        # Convertir y almacenar
        try:
            data_cab = json.loads(limpiar_json(resultado_cabecera))
            data_man = json.loads(limpiar_json(resultado_manuscrita))
            data_combined = {**data_cab, **data_man}
            st.session_state.pagares_data.append(data_combined)
            st.success("✅ Datos extraídos y almacenados correctamente.")
        except Exception as e:
            st.error(f"Error al combinar los datos extraídos: {e}")

# Exportar a Excel
if st.session_state.pagares_data:
    df = pd.DataFrame(st.session_state.pagares_data)
    st.subheader("📊 Vista previa de los datos extraídos")
    st.dataframe(df)

    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False, engine="openpyxl")
    excel_io.seek(0)

    st.download_button(
        label="⬇️ Descargar Excel con todos los pagarés",
        data=excel_io,
        file_name="pagares_extraidos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.button("🗑️ Reiniciar"):
        st.session_state.pagares_data = []
        st.experimental_rerun()
