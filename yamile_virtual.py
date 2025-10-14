import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
import openai
import json

# =====================================
# 🧭 CONFIGURACIÓN INICIAL
# =====================================
st.set_page_config(page_title="📄 Extractor Pagarés con IA", layout="wide")
st.title("✍️ Extractor de Pagarés - COS JudicIA 🤖")

# Estilo corporativo
st.markdown("""
<style>
    body, .stApp {
        background-color: #FFFFFF;
        color: #1B168C;
    }
    .stButton button {
        background-color: #1B168C;
        color: white;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #F43B63;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# =====================================
# 🔑 API Key segura
# =====================================
openai.api_key = st.secrets["OPENAI_API_KEY"]

# =====================================
# 🧠 Función para extraer con IA
# =====================================
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

# =====================================
# ⚙️ Utilidades
# =====================================
def limpiar_json(texto):
    try:
        start = texto.index("{")
        end = texto.rindex("}") + 1
        return texto[start:end]
    except:
        return texto

# Inicializar base acumulativa
if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []

# =====================================
# 📍 Paso 0: Tipo de documento
# =====================================
st.header("📍 Paso 0: Selecciona el tipo de documento")
tipo = st.radio("¿Qué tipo de archivo deseas cargar?", ["📸 Imágenes", "📄 PDF"])

cabecera_bytes = None
manuscrita_bytes = None

# =====================================
# 🖼️ Paso 1: Carga de archivos
# =====================================
if tipo == "📸 Imágenes":
    st.header("📌 Paso 1: Subir imagen de la parte superior del pagaré")
    cabecera = st.file_uploader("🧾 Imagen de la cabecera del pagaré", type=["png", "jpg", "jpeg"], key="cabecera")

    st.header("📝 Paso 2: Subir imagen de la parte inferior manuscrita")
    manuscrita = st.file_uploader("✍️ Imagen manuscrita (nombre, firma, etc.)", type=["png", "jpg", "jpeg"], key="manuscrita")

    if cabecera and manuscrita:
        col1, col2 = st.columns(2)
        with col1:
            st.image(cabecera, caption="Cabecera", use_column_width=True)
        with col2:
            st.image(manuscrita, caption="Parte Manuscrita", use_column_width=True)

        cabecera_bytes = cabecera.read()
        manuscrita_bytes = manuscrita.read()

else:
    st.header("📄 Paso 1: Subir el pagaré completo (PDF)")
    archivo_pdf = st.file_uploader("Cargar archivo PDF del pagaré", type=["pdf"])

    if archivo_pdf:
        from pdf2image import convert_from_bytes
        paginas = convert_from_bytes(archivo_pdf.read())
        st.success(f"📚 Se detectaron {len(paginas)} páginas en el PDF.")
        col1, col2 = st.columns(2)
        col1.image(paginas[0], caption="Cabecera detectada", use_column_width=True)
        col2.image(paginas[-1], caption="Parte manuscrita detectada", use_column_width=True)

        cabecera_bytes_io = io.BytesIO()
        paginas[0].save(cabecera_bytes_io, format="PNG")
        cabecera_bytes = cabecera_bytes_io.getvalue()

        manuscrita_bytes_io = io.BytesIO()
        paginas[-1].save(manuscrita_bytes_io, format="PNG")
        manuscrita_bytes = manuscrita_bytes_io.getvalue()

# =====================================
# 🤖 Paso 3: Extracción con doble validación
# =====================================
if cabecera_bytes and manuscrita_bytes:
    st.divider()
    st.header("🤖 Paso 3: Extracción Inteligente con Validación Doble")

    if st.button("🚀 Ejecutar análisis con IA"):
        # Instrucciones
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

        # 🧩 Doble ejecución para precisión
        st.info("⌛ Procesando dos interpretaciones de la IA (esto puede tardar unos segundos)...")
        resultado_cab_1 = extraer_con_ia(cabecera_bytes, instruccion_cabecera)
        resultado_cab_2 = extraer_con_ia(cabecera_bytes, instruccion_cabecera + "\nIntenta interpretar incluso si los datos son poco legibles.")

        resultado_man_1 = extraer_con_ia(manuscrita_bytes, instruccion_manuscrita)
        resultado_man_2 = extraer_con_ia(manuscrita_bytes, instruccion_manuscrita + "\nSé más interpretativo en nombres o números ilegibles.")

        # Mostrar comparativo
        st.subheader("🧾 Comparativo de Resultados")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🧠 Opción 1 (Precisa)")
            st.code(resultado_cab_1, language="json")
            st.code(resultado_man_1, language="json")
        with col2:
            st.markdown("### 🤔 Opción 2 (Interpretativa)")
            st.code(resultado_cab_2, language="json")
            st.code(resultado_man_2, language="json")

        # Elección del usuario
        opcion = st.radio("Selecciona la versión que deseas guardar:", ["Opción 1 (Precisa)", "Opción 2 (Interpretativa)"])
        if st.button("💾 Guardar resultado seleccionado"):
            try:
                if opcion.startswith("Opción 1"):
                    data_cab = json.loads(limpiar_json(resultado_cab_1))
                    data_man = json.loads(limpiar_json(resultado_man_1))
                else:
                    data_cab = json.loads(limpiar_json(resultado_cab_2))
                    data_man = json.loads(limpiar_json(resultado_man_2))

                data_combined = {**data_cab, **data_man}
                st.session_state.pagares_data.append(data_combined)
                st.success("✅ Datos extraídos y almacenados correctamente.")
            except Exception as e:
                st.error(f"Error al procesar los datos seleccionados: {e}")

# =====================================
# 📊 Paso 4: Exportar a Excel
# =====================================
if st.session_state.pagares_data:
    st.divider()
    st.header("📊 Paso 4: Exportar los resultados")

    df = pd.DataFrame(st.session_state.pagares_data)
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

    st.success("✅ Exportación lista. Puedes seguir agregando más pagarés.")


    if st.button("🗑️ Reiniciar"):
        st.session_state.pagares_data = []
        st.experimental_rerun()
