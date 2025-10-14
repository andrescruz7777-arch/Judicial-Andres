# ============================================
# 📄 Extractor de Pagarés — COS JudicIA (UI Moderno Mejorado)
# Estilo CrmX Admin con flujo guiado
# ============================================

import streamlit as st
import pandas as pd
from PIL import Image
import io, base64, json, re, datetime
import fitz  # PyMuPDF
import openai

# =========================
# ⚙️ CONFIGURACIÓN INICIAL
# =========================
st.set_page_config(page_title="Extractor de Pagarés — COS JudicIA", layout="wide")
openai.api_key = st.secrets["OPENAI_API_KEY"]
# =========================
# 🎨 ESTILO (CSS + Fuentes)
# =========================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
:root{
  --bg: #F7F8FA;
  --card: #FFFFFF;
  --text: #1a1a1a;
  --primary: #2F80ED;
  --primary-700:#1F6ED0;
  --accent: #FF6B6B;
  --sidebar: #1F2940;
  --muted:#8A94A6;
  --success:#2ECC71;
}
html, body, .stApp { background: var(--bg) !important; }
* { font-family: 'Poppins', sans-serif; color: var(--text) !important; }

[data-testid="stSidebar"] {
    background: var(--sidebar) !important;
    border-right: 0;
}
[data-testid="stSidebar"] * { color: #E9EEF6 !important; }

.sidebar-logo {
  display:flex; align-items:center; gap:.6rem; margin: .5rem 0 1rem 0;
}
.sidebar-logo .logo-dot{
  width:12px; height:12px; border-radius:50%;
  background: linear-gradient(135deg, var(--primary), var(--accent));
  display:inline-block;
}
.sidebar-user {
  display:flex; align-items:center; gap:.6rem; padding:.6rem .6rem;
  background: rgba(255,255,255,0.05); border-radius:12px; margin-bottom:.6rem;
  font-size:.9rem;
}

.app-header {
  position: sticky; top: 0; z-index: 50;
  background: #ffffff; border-radius: 16px; padding: .9rem 1.2rem;
  box-shadow: 0 6px 18px rgba(0,0,0,.06);
  display:flex; align-items:center; justify-content:space-between; gap:1rem;
}

.searchbox{
  display:flex; align-items:center; gap:.6rem; flex:1;
  background:#F1F4F9; border:1px solid #E6E9F0; border-radius:12px; padding:.55rem .8rem;
}
.searchbox input{
  outline:none; border:none; background:transparent; width:100%;
  font-size:.95rem; color:var(--text);
}

/* ===============================
   🔤 Etiquetas y texto general
=============================== */
label, .stRadio label, .stSelectbox label, .stCheckbox label, .stMarkdown, .stText {
    color: #000000 !important;
}

.card{
  background: var(--card); border-radius: 16px; padding: 1rem 1.1rem;
  box-shadow: 0 8px 24px rgba(31,41,64,0.06);
  border: 1px solid #EEF1F6;
}
.metric{
  display:flex; align-items:flex-start; justify-content:space-between;
}
.metric .label{ color: var(--muted); font-size:.85rem; }
.metric .value{ font-size:1.6rem; font-weight:700; color:var(--text); }

.stButton>button{
  background: var(--primary) !important; color:#fff !important; border:none;
  padding:.6rem 1rem; border-radius: 12px; font-weight:600;
  transition:.2s transform ease;
}
.stButton>button:hover{ background: var(--primary-700) !important; transform: translateY(-1px); }

.stDataFrame{
  border-radius: 12px; overflow: hidden; border:1px solid #EEF1F6;
  box-shadow: 0 8px 24px rgba(31,41,64,0.05);
}

/* ===============================
   📝 Inputs y FileUploader
=============================== */
.stTextInput > div > div > input {
    background-color: #FFFFFF !important;
    color: #000000 !important;
    border-radius: 8px;
    border: 1px solid #CCCCCC !important;
}
.stTextInput > div > div > input:focus {
    border: 1px solid #2F80ED !important;
    box-shadow: 0 0 0 1px #2F80ED !important;
}

/* 🔹 SOLO este bloque ajusta el área del FileUploader */
[data-testid="stFileUploaderDropzone"] {
    background-color: #FFFFFF !important;
    border: 1.5px dashed #CCCCCC !important;
    border-radius: 12px !important;
    color: #000000 !important;
}
[data-testid="stFileUploaderDropzone"] p {
    color: #000000 !important;
}
.stFileUploader button {
    background-color: #2F80ED !important;
    color: #FFFFFF !important;
    border-radius: 10px !important;
    border: none !important;
}
.stFileUploader button:hover {
    background-color: #1B5EC8 !important;
}

/* ===============================
   ⚙️ Loaders y banners
=============================== */
.ia-loader {
    text-align: center;
    font-weight: 600;
    font-size: 1.1rem;
    padding: 1rem;
    border-radius: 12px;
    background: #E8F2FF;
    color: #1F2940;
    border: 1px solid #BFD6FF;
    margin-top: 1rem;
    animation: pulse 2s infinite;
}
@keyframes pulse {
  0% {opacity: 1;}
  50% {opacity: 0.5;}
  100% {opacity: 1;}
}
.success-banner {
    background: #D1FAE5;
    color: #065F46;
    padding: 1.2rem;
    border-radius: 12px;
    font-weight: 600;
    text-align: center;
    margin-top: 1rem;
    box-shadow: 0 6px 16px rgba(0,0,0,0.05);
    animation: fadeIn 1s ease-in-out;
}
@keyframes fadeIn {
    from {opacity:0; transform:translateY(10px);}
    to {opacity:1; transform:translateY(0);}
}
</style>
""",
    unsafe_allow_html=True,
)
# =========================
# 🧠 ESTADO GLOBAL
# =========================
for key in ["pagares_data", "ultimo_registro", "procesando", "drawer_open", "drawer_payload"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "pagares_data" else None if key != "drawer_open" else False

# =========================
# 🔧 FUNCIONES
# =========================
def mejorar_imagen(im_bytes):
    img = Image.open(io.BytesIO(im_bytes)).convert("L")
    img = img.resize((img.width * 2, img.height * 2))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def pdf_a_imagenes(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        raise ValueError("PDF vacío o dañado.")
    pages = [doc.load_page(0), doc.load_page(len(doc) - 1)]
    imgs = []
    for p in pages:
        pix = p.get_pixmap(dpi=200)
        imgs.append(Image.open(io.BytesIO(pix.tobytes("png"))))
    cab, man = io.BytesIO(), io.BytesIO()
    imgs[0].save(cab, format="PNG")
    imgs[1].save(man, format="PNG")
    return cab.getvalue(), man.getvalue(), imgs


def limpiar_json(txt):
    try:
        i0, i1 = txt.index("{"), txt.rindex("}") + 1
        return txt[i0:i1]
    except Exception:
        return "{}"


def extraer_json_vision(im_bytes, prompt):
    resp = openai.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Eres experto en pagarés colombianos. Devuelve solo JSON estricto."},
            {"role": "user", "content": prompt},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(im_bytes).decode()}",
                    "detail": "high",
                }}
            ]},
        ],
        max_tokens=1000,
    )
    return json.loads(limpiar_json(resp.choices[0].message.content))


# =========================
# 🧭 SIDEBAR Y HEADER
# =========================
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo"><span class="logo-dot"></span><span><b>COS JudicIA</b><br><span style="font-size:.8rem; opacity:.85">Extractor de Pagarés</span></span></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-user">👤 <b>Operador</b><span style="opacity:.7"> | COS</span></div>', unsafe_allow_html=True)
    menu = st.radio("Menú", ["📄 Subir pagarés", "🧠 Extracción IA", "✏️ Corrección manual", "📊 Histórico / Excel"], label_visibility="collapsed")
    st.markdown('<span class="badge">v1.3 UI Avanzada</span>', unsafe_allow_html=True)

st.markdown(
    """
<div class="app-header">
  <div class="searchbox">🔎 <input placeholder="Buscar por cédula, nombre o número de pagaré..."/></div>
  <div class="badge">Ayuda</div>
  <div class="badge">Perfil</div>
</div>
""",
    unsafe_allow_html=True,
)

# =========================
# 📄 SUBIR PAGARÉS
# =========================
if menu == "📄 Subir pagarés":
    st.markdown('<div class="section-title">📤 Carga de pagarés</div>', unsafe_allow_html=True)
    tipo_doc = st.radio("Tipo de archivo:", ["📄 PDF", "📸 Imágenes"], horizontal=True)
    modo_label = st.radio("Modo de extracción:", ["🟢 Económico (rápido)", "🧠 Auditoría (alta precisión)"], horizontal=True)
    modo = "economico" if "Económico" in modo_label else "auditoria"
    cabecera_bytes = manuscrita_bytes = None
    pdf = st.file_uploader("Sube el pagaré", type=["pdf", "jpg", "jpeg", "png"])
    if pdf:
        if pdf.name.endswith(".pdf"):
            cab, man, imgs = pdf_a_imagenes(pdf.read())
        else:
            imgs = [Image.open(pdf)]
            cab, man = pdf.read(), pdf.read()
        st.image(imgs, caption=["Cabecera", "Parte manuscrita"], use_container_width=True)
        st.session_state["cab"], st.session_state["man"] = mejorar_imagen(cab), mejorar_imagen(man)
        if st.button("🚀 Analizar con IA"):
            st.markdown('<div class="ia-loader">🧠 Estamos trabajando en ello... analizando tu pagaré, por favor espera unos segundos.</div>', unsafe_allow_html=True)
            prompt_cab = """
Extrae:
- Número de pagaré
- Ciudad
- Día (en letras)
- Día (en número)
- Mes
- Año (en letras)
- Año (en número)
- Valor en letras
- Valor en números
Devuélvelo en JSON.
"""
            prompt_man = """
Extrae:
- Nombre del Deudor
- Cedula
- Direccion
- Ciudad
- Telefono
- Fecha de Firma
- Ciudad de Firma
Devuélvelo en JSON.
"""
            cab = extraer_json_vision(st.session_state["cab"], prompt_cab)
            man = extraer_json_vision(st.session_state["man"], prompt_man)
            st.session_state.ultimo_registro = {**cab, **man}
            st.markdown(
                "<div class='success-banner'>✅ Extracción completada correctamente.<br><small>Haz clic en <b>🧠 Extracción IA</b> para continuar al siguiente paso.</small></div>",
                unsafe_allow_html=True,
            )

# =========================
# 🧠 EXTRACCIÓN IA
# =========================
if menu == "🧠 Extracción IA":
    if st.session_state.ultimo_registro:
        df = pd.DataFrame([st.session_state.ultimo_registro]).T.reset_index()
        df.columns = ["Campo", "Valor"]
        st.dataframe(df, use_container_width=True)
        if st.button("✏️ Abrir editor de campos"):
            st.session_state.drawer_payload = st.session_state.ultimo_registro.copy()
            st.session_state.drawer_open = True
    else:
        st.info("No hay pagarés analizados todavía.")

# =========================
# ✏️ CORRECCIÓN MANUAL
# =========================
if menu == "✏️ Corrección manual":
    if st.session_state.ultimo_registro:
        df = pd.DataFrame([st.session_state.ultimo_registro]).T.reset_index()
        df.columns = ["Campo", "Valor"]
        st.dataframe(df, use_container_width=True)
        if st.button("✏️ Abrir editor de campos"):
            st.session_state.drawer_payload = st.session_state.ultimo_registro.copy()
            st.session_state.drawer_open = True
    else:
        st.info("No hay datos para editar.")

# =========================
# 📊 HISTÓRICO / EXCEL
# =========================
if menu == "📊 Histórico / Excel":
    if st.session_state.pagares_data:
        df_hist = pd.DataFrame(st.session_state.pagares_data)
        st.dataframe(df_hist, use_container_width=True)
        excel_io = io.BytesIO()
        df_hist.to_excel(excel_io, index=False, engine="openpyxl")
        excel_io.seek(0)
        st.download_button("⬇️ Descargar Excel", data=excel_io, file_name="resultados_pagares.xlsx")
    else:
        st.info("Aún no hay registros guardados.")

# =========================
# 🧾 EDITOR INFERIOR
# =========================
def render_editor():
    st.markdown("<hr><div class='section-title'>✏️ Editar campos del pagaré</div>", unsafe_allow_html=True)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    updated = {}
    cols = st.columns(2)
    campos = list(st.session_state.drawer_payload.items())
    mitad = len(campos) // 2 or 1
    for i, (campo, valor) in enumerate(campos):
        col = cols[0] if i < mitad else cols[1]
        with col:
            updated[campo] = st.text_input(campo, str(valor))
    st.markdown("</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        cancel = st.button("❌ Cancelar edición")
    with col2:
        save = st.button("💾 Guardar cambios")
    if cancel:
        st.session_state.drawer_open = False
        st.info("Edición cancelada.")
    if save:
        cambios = [k for k, v in updated.items() if str(v).strip() != str(st.session_state.ultimo_registro.get(k, '')).strip()]
        registro = updated.copy()
        registro["Campos Modificados"] = ", ".join(cambios) if cambios else "Sin cambios"
        registro["Editado Manualmente"] = "Sí" if cambios else "No"
        registro["Fecha Registro"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.pagares_data.append(registro)
        st.session_state.ultimo_registro = updated
        st.session_state.drawer_open = False
        st.success(f"✅ Guardado correctamente ({len(cambios)} cambios).")

if st.session_state.drawer_open:
    render_editor()
