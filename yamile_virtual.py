import streamlit as st
import pandas as pd
from PIL import Image
import io, base64, json, re, datetime, fitz
import openai

# =========================
# ⚙️ CONFIGURACIÓN INICIAL
# =========================
st.set_page_config(page_title="Extractor de Pagarés — COS JudicIA", layout="wide")
st.title("✍️ Extractor de Pagarés con IA JUDIC-IA-L ⚖️")

openai.api_key = st.secrets["OPENAI_API_KEY"]

# =========================
# 🎨 ESTILOS (CSS + FUENTES)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
html, body, .stApp { background: #F7F8FA !important; color: #1a1a1a !important; font-family: 'Poppins', sans-serif; }
h1, h2, h3, h4 { color: #1a1a1a !important; }
[data-testid="stSidebar"] { background-color: #1F2940 !important; }
[data-testid="stSidebar"] * { color: #E9EEF6 !important; }

/* ===============================
   📂 FileUploader
=============================== */
[data-testid="stFileUploaderDropzone"] {
    background-color: #FFFFFF !important;
    border: 1.5px dashed #CCCCCC !important;
    border-radius: 12px !important;
    color: #000000 !important;
}
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] div {
    color: #000000 !important;
}

/* Botón “Browse files” */
[data-testid="stFileUploader"] button {
    background-color: #E0E0E0 !important;
    color: #000000 !important;
    border-radius: 10px !important;
    border: none !important;
    font-weight: 600 !important;
}
[data-testid="stFileUploader"] button:hover {
    background-color: #000000 !important;
    color: #FFFFFF !important;
}

/* ===============================
   📋 Inputs y botones normales
=============================== */
.stTextInput > div > div > input {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border-radius: 8px;
    border: 1px solid #CCCCCC !important;
}
.stButton>button {
    background: #2F80ED !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.5rem 1rem !important;
    font-weight: 600 !important;
}
.stButton>button:hover { background: #1F6ED0 !important; }
</style>
""", unsafe_allow_html=True)

# =========================
# 🧭 SIDEBAR (NAVEGACIÓN)
# =========================
st.sidebar.title("📚 Navegación")
st.sidebar.markdown("""
<a href="#subir" style="text-decoration:none;">📤 Subir pagaré</a><br>
<a href="#ia" style="text-decoration:none;">🤖 Extracción IA</a><br>
<a href="#correccion" style="text-decoration:none;">✏️ Corrección manual</a><br>
<a href="#exportar" style="text-decoration:none;">📊 Exportar resultados</a>
""", unsafe_allow_html=True)

# Script para scroll suave
st.markdown("""
<script>
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    e.preventDefault();
    document.querySelector(this.getAttribute('href')).scrollIntoView({
      behavior: 'smooth'
    });
  });
});
</script>
""", unsafe_allow_html=True)

# =========================
# 📤 SUBIR PAGARÉ
# =========================
st.markdown('<h2 id="subir">📤 1️⃣ Subir pagaré</h2>', unsafe_allow_html=True)
tipo_doc = st.radio("Tipo de archivo:", ["📄 PDF", "📸 Imágenes"])
modo_proceso = st.radio("Modo de extracción:", ["🟢 Económico (rápido)", "🧠 Auditoría (alta precisión)"])
modo_proceso = "economico" if "Económico" in modo_proceso else "auditoria"

cabecera_bytes, manuscrita_bytes = None, None
if tipo_doc == "📄 PDF":
    pdf = st.file_uploader("Sube el pagaré en PDF", type=["pdf"])
    if pdf:
        try:
            cab, man, imgs = pdf_a_imagenes(pdf.read())
            st.image(imgs, caption=["Cabecera", "Parte manuscrita"], use_container_width=True)
            cabecera_bytes, manuscrita_bytes = mejorar_imagen(cab), mejorar_imagen(man)
        except Exception as e:
            st.error(f"Error al procesar PDF: {e}")
else:
    cab = st.file_uploader("Cabecera", type=["jpg", "jpeg", "png"])
    man = st.file_uploader("Parte manuscrita", type=["jpg", "jpeg", "png"])
    if cab and man:
        col1, col2 = st.columns(2)
        col1.image(cab, caption="Cabecera", use_container_width=True)
        col2.image(man, caption="Parte manuscrita", use_container_width=True)
        cabecera_bytes, manuscrita_bytes = mejorar_imagen(cab.read()), mejorar_imagen(man.read())

# =========================
# 🤖 EXTRACCIÓN IA
# =========================
st.markdown('<h2 id="ia">🤖 2️⃣ Extracción IA y Validación</h2>', unsafe_allow_html=True)
if cabecera_bytes and manuscrita_bytes:
    if st.button("🚀 Ejecutar IA") and not st.session_state.procesando:
        st.session_state.procesando = True
        with st.spinner("Procesando imágenes..."):
            prompt_cab = """
Extrae los siguientes datos del pagaré (parte superior):
- Número de pagaré (si aparece)
- Ciudad
- Día (en letras)
- Día (en número)
- Mes
- Año (en letras)
- Año (en número)
- Valor en letras
- Valor en números

Devuélvelo en formato JSON con esas claves exactas:
{
  "Numero de Pagare": "",
  "Ciudad": "",
  "Dia (en letras)": "",
  "Dia (en numero)": "",
  "Mes": "",
  "Año (en letras)": "",
  "Año (en numero)": "",
  "Valor en letras": "",
  "Valor en numeros": ""
}
"""
            prompt_man = """
Extrae los siguientes datos manuscritos del pagaré:
- "Nombre del Deudor"
- "Cedula"
- "Direccion"
- "Ciudad"
- "Telefono"
- "Fecha de Firma"
- "Ciudad de Firma"
Devuélvelo estrictamente en formato JSON con esas mismas claves exactas.
"""
            cab = extraer_json_vision(cabecera_bytes, prompt_cab, modo=modo_proceso)
            man = extraer_json_vision(manuscrita_bytes, prompt_man, modo=modo_proceso)
            data = {**cab, **man}
            st.session_state.ultimo_registro = data
        st.session_state.procesando = False
        st.success("✅ Extracción completada correctamente.")
        st.json(data)

# =========================
# ✏️ CORRECCIÓN MANUAL
# =========================
st.markdown('<h2 id="correccion">✏️ 3️⃣ Validación y Corrección Manual</h2>', unsafe_allow_html=True)
if st.session_state.ultimo_registro:
    data = st.session_state.ultimo_registro
    data_edit = {}
    cambios = []
    for campo, valor in data.items():
        nuevo = st.text_input(campo, str(valor))
        data_edit[campo] = nuevo
        if str(nuevo).strip() != str(valor).strip():
            cambios.append(campo)
    col_guardar, col_limpiar = st.columns([2,1])
    with col_guardar:
        if st.button("💾 Guardar registro"):
            registro = data_edit.copy()
            registro["Campos Modificados"] = ", ".join(cambios) if cambios else "Sin cambios"
            registro["Editado Manualmente"] = "Sí" if cambios else "No"
            registro["Modo"] = modo_proceso
            registro["Fecha Registro"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.pagares_data.append(registro)
            st.success(f"✅ Registro guardado correctamente ({len(cambios)} cambios).")
    with col_limpiar:
        if st.button("🧹 Limpiar tabla"):
            st.session_state.pagares_data = []
            st.session_state.ultimo_registro = None
            st.success("🧾 Tabla vaciada correctamente. Puedes empezar de nuevo.")

# =========================
# 📊 EXPORTAR RESULTADOS
# =========================
st.markdown('<h2 id="exportar">📊 4️⃣ Exportar resultados a Excel</h2>', unsafe_allow_html=True)
if st.session_state.pagares_data:
    df = pd.DataFrame(st.session_state.pagares_data)
    st.dataframe(df, use_container_width=True)
    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False, engine="openpyxl")
    excel_io.seek(0)
    st.download_button("⬇️ Descargar Excel con resultados", data=excel_io, file_name="resultados_pagares.xlsx")
