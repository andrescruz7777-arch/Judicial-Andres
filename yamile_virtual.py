# ============================================
# 📄 Extractor de Pagarés — COS JudicIA (UI Moderno)
# Estilo: Dashboard tipo CrmX Admin (sidebar oscuro + drawer derecho)
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
st.markdown("""
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

/* ===== App Layout ===== */
html, body, .stApp { background: var(--bg) !important; }
* { font-family: 'Poppins', sans-serif; }

[data-testid="stSidebar"] {
    background: var(--sidebar) !important;
    border-right: 0;
}
[data-testid="stSidebar"] * { color: #E9EEF6 !important; }

/* Sidebar */
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

/* Top header bar */
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

/* Cards */
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
.metric .chip{
  font-size:.78rem; padding:.2rem .55rem; border-radius:999px;
  background:#E8F2FF; color: var(--primary); border:1px solid #D6E6FF;
}

/* Buttons */
.stButton>button{
  background: var(--primary) !important; color:#fff !important; border:none;
  padding:.6rem 1rem; border-radius: 12px; font-weight:600;
  transition:.2s transform ease;
}
.stButton>button:hover{ background: var(--primary-700) !important; transform: translateY(-1px); }
.btn-sec>button{ background: #EEF2F7 !important; color:#334155 !important; }

/* Dataframe and tables */
.stDataFrame{
  border-radius: 12px; overflow: hidden; border:1px solid #EEF1F6;
  box-shadow: 0 8px 24px rgba(31,41,64,0.05);
}

/* Image previews */
.preview-wrap img{ border-radius: 12px; border:1px solid #EEF1F6; }

/* Drawer right */
.drawer-mask{
  position: fixed; inset:0; background: rgba(15,23,42,0.35); 
  backdrop-filter: blur(1.5px); z-index: 1000;
}
.drawer{
  position: fixed; top:0; right:0; height:100vh; width: 420px; max-width: 92vw;
  background: #ffffff; box-shadow: -12px 0 28px rgba(31,41,64,.15);
  border-left:1px solid #EEF1F6; z-index: 1001; padding: 1rem 1.2rem;
  display:flex; flex-direction:column; gap:.6rem;
  animation: slideIn .18s ease-out;
}
@keyframes slideIn{ from{ transform: translateX(20px); opacity:0;} to{ transform: translateX(0); opacity:1; } }
.drawer h3{ margin:.2rem 0 .2rem 0; }
.drawer .footer{
  margin-top:auto; display:flex; gap:.6rem; justify-content:flex-end; padding-top:.6rem;
  border-top:1px dashed #EAEAEA;
}

/* Section titles */
.section-title{ font-weight:700; font-size:1.05rem; color:#0F172A; margin-bottom:.4rem; }

/* Small badges */
.badge{
  display:inline-block; padding:.2rem .5rem; border-radius:8px; font-size:.75rem;
  border:1px solid #E6E9F0; color:#475569; background:#F8FAFC;
}

/* Divider prettier */
hr{ border: none; border-top: 1px dashed #E6E9F0; margin: 1rem 0; }

/* ==== Contraste de texto ==== */
label, .stRadio label, .stFileUploader label, .stTextInput label,
.stMarkdown p, .stMarkdown span, .stCaption, .stRadio div, .stSelectbox label,
.stCheckbox label, .stTextInput input, .stTextInput div, .stMarkdown li {
    color: #1a1a1a !important;
    font-weight: 500 !important;
}
.stRadio > div[role='radiogroup'] label, 
.stRadio > div[role='radiogroup'] div {
    color: #1a1a1a !important;
}
.stFileUploader > div, .stFileUploader label, .stFileUploader span {
    color: #1a1a1a !important;
}
.css-10trblm, .stSubheader, .stMarkdown h3, .stMarkdown h4 {
    color: #0F172A !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 🧠 ESTADO GLOBAL
# =========================
if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []
if "ultimo_registro" not in st.session_state:
    st.session_state.ultimo_registro = None
if "procesando" not in st.session_state:
    st.session_state.procesando = False
if "drawer_open" not in st.session_state:
    st.session_state.drawer_open = False
if "drawer_payload" not in st.session_state:
    st.session_state.drawer_payload = {}

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
    pages = [doc.load_page(0), doc.load_page(len(doc)-1)]
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
    except:
        return "{}"

def extraer_json_vision(im_bytes, prompt, modo="auditoria"):
    def call(extra=""):
        resp = openai.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Eres experto en pagarés colombianos. Devuelve solo JSON estricto."},
                {"role": "user", "content": prompt + extra},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64.b64encode(im_bytes).decode()}",
                        "detail": "high"
                    }}
                ]}
            ],
            max_tokens=1000,
        )
        return json.loads(limpiar_json(resp.choices[0].message.content))
    return call()

# =========================
# 🧭 SIDEBAR
# =========================
with st.sidebar:
    st.markdown('<div class="sidebar-logo"><span class="logo-dot"></span><span><b>COS JudicIA</b><br><span style="font-size:.8rem; opacity:.85">Extractor de Pagarés</span></span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-user">👤 <b>Operador</b><span style="opacity:.7"> | COS</span></div>', unsafe_allow_html=True)
    menu = st.radio("Menú", ["📄 Subir pagarés", "🧠 Extracción IA", "✏️ Corrección manual", "📊 Histórico / Excel"], label_visibility="collapsed")
    st.markdown('<span class="badge">v1.0 UI Moderno</span>', unsafe_allow_html=True)

# =========================
# 🔝 HEADER
# =========================
st.markdown("""
<div class="app-header">
  <div class="searchbox">
    🔎 <input placeholder="Buscar por cédula, nombre o número de pagaré..."/>
  </div>
  <div class="badge">Ayuda</div>
  <div class="badge">Perfil</div>
</div>
""", unsafe_allow_html=True)

# =========================
# 📊 TARJETAS
# =========================
total_procesados = len(st.session_state.pagares_data)
total_editados = sum(1 for r in st.session_state.pagares_data if "Sí" in str(r.get("Editado Manualmente", "")))
precision_aprox = 97
tiempo_prom = 1.2
cols = st.columns(4)
for i, (t, v) in enumerate({
    "Pagarés procesados": total_procesados,
    "Campos corregidos": total_editados,
    "Extracciones exitosas": f"{precision_aprox}%",
    "Tiempo promedio": f"{tiempo_prom} min"
}.items()):
    with cols[i]:
        st.markdown(f"""<div class="card metric"><div><div class="label">{t}</div><div class="value">{v}</div></div></div>""", unsafe_allow_html=True)

# =========================
# 📁 SUBIR PAGARÉS
# =========================
if menu == "📄 Subir pagarés":
    st.markdown('<div class="section-title">📤 Carga de pagarés</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.subheader("1️⃣ Seleccionar archivos")
        tipo_doc = st.radio("Tipo de archivo:", ["📄 PDF", "📸 Imágenes"], horizontal=True)
        modo_label = st.radio("Modo de extracción:", ["🟢 Económico (rápido)", "🧠 Auditoría (alta precisión)"], horizontal=True)
        modo = "economico" if "Económico" in modo_label else "auditoria"

        cabecera_bytes, manuscrita_bytes, imgs = None, None, []
        if tipo_doc == "📄 PDF":
            pdf = st.file_uploader("Sube el pagaré en PDF", type=["pdf"])
            if pdf:
                cab, man, imgs = pdf_a_imagenes(pdf.read())
                cabecera_bytes, manuscrita_bytes = mejorar_imagen(cab), mejorar_imagen(man)
                st.session_state["cab"], st.session_state["man"], st.session_state["imgs"] = cabecera_bytes, manuscrita_bytes, imgs
                st.success("✅ PDF cargado correctamente.")
        else:
            cab = st.file_uploader("Cabecera", type=["jpg", "jpeg", "png"])
            man = st.file_uploader("Parte manuscrita", type=["jpg", "jpeg", "png"])
            if cab and man:
                cabecera_bytes, manuscrita_bytes = mejorar_imagen(cab.read()), mejorar_imagen(man.read())
                imgs = [Image.open(io.BytesIO(cabecera_bytes)), Image.open(io.BytesIO(manuscrita_bytes))]
                st.session_state["cab"], st.session_state["man"], st.session_state["imgs"] = cabecera_bytes, manuscrita_bytes, imgs
                st.success("✅ Imágenes cargadas correctamente.")

    with c2:
        st.subheader("👁️ Vista previa")
        prev = st.session_state.get("imgs", [])
        if prev:
            colP1, colP2 = st.columns(2)
            colP1.image(prev[0], caption="Cabecera", use_container_width=True)
            if len(prev) > 1:
                colP2.image(prev[-1], caption="Parte manuscrita", use_container_width=True)
        else:
            st.caption("Sube un PDF o imágenes para ver la vista previa.")

    if st.session_state.get("cab") and st.session_state.get("man"):
        if st.button("🚀 Analizar con IA"):
            st.session_state.procesando = True
            with st.spinner("Procesando imágenes con IA..."):
                prompt_cab = """
Extrae los siguientes datos del pagaré:
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
Extrae del pagaré manuscrito:
- Nombre del Deudor
- Cedula
- Direccion
- Ciudad
- Telefono
- Fecha de Firma
- Ciudad de Firma
Devuélvelo en JSON.
"""
                cab = extraer_json_vision(st.session_state["cab"], prompt_cab, modo)
                man = extraer_json_vision(st.session_state["man"], prompt_man, modo)
                st.session_state.ultimo_registro = {**cab, **man}
            st.session_state.procesando = False
            st.success("✅ Extracción completada correctamente.")

# =========================
# 🧠 EXTRACCIÓN IA
# =========================
if menu == "🧠 Extracción IA":
    if st.session_state.ultimo_registro:
        df_view = pd.DataFrame([st.session_state.ultimo_registro]).T.reset_index()
        df_view.columns = ["Campo", "Valor"]
        st.dataframe(df_view, use_container_width=True, height=420)
        if st.button("✏️ Editar registro"):
            st.session_state.drawer_payload = st.session_state.ultimo_registro.copy()
            st.session_state.drawer_open = True
    else:
        st.info("Sube y analiza un pagaré para ver los resultados.")

# =========================
# ✏️ CORRECCIÓN MANUAL
# =========================
if menu == "✏️ Corrección manual":
    if st.session_state.ultimo_registro:
        df_view = pd.DataFrame([st.session_state.ultimo_registro]).T.reset_index()
        df_view.columns = ["Campo", "Valor"]
        st.dataframe(df_view, use_container_width=True)
        if st.button("✏️ Abrir editor lateral"):
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
        st.dataframe(df_hist, use_container_width=True, height=440)
        excel_io = io.BytesIO()
        df_hist.to_excel(excel_io, index=False, engine="openpyxl")
        excel_io.seek(0)
        st.download_button("⬇️ Descargar Excel", data=excel_io, file_name="resultados_pagares.xlsx")
    else:
        st.info("Aún no hay registros guardados.")

# =========================
# 🪟 DRAWER LATERAL (versión corregida)
# =========================
def render_drawer():
    drawer_html = """
    <div class="drawer-mask"></div>
    <div class="drawer">
      <h3>✏️ Editar campos del pagaré</h3>
      <div id="drawer-form"></div>
    </div>
    """
    st.markdown(drawer_html, unsafe_allow_html=True)

    # Contenedor Streamlit (para inputs)
    form_placeholder = st.empty()
    with form_placeholder.container():
        updated = {}
        for campo, valor in st.session_state.drawer_payload.items():
            updated[campo] = st.text_input(campo, str(valor))

        col1, col2 = st.columns(2)
        cancel = col1.button("❌ Cancelar", key="drawer_cancel")
        save = col2.button("💾 Guardar cambios", key="drawer_save")

        if cancel:
            st.session_state.drawer_open = False

        if save:
            orig = st.session_state.ultimo_registro or {}
            cambios = [k for k in updated if str(updated[k]).strip() != str(orig.get(k, "")).strip()]
            st.session_state.ultimo_registro = updated.copy()
            registro = updated.copy()
            registro["Campos Modificados"] = ", ".join(cambios) if cambios else "Sin cambios"
            registro["Editado Manualmente"] = "Sí" if cambios else "No"
            registro["Fecha Registro"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.pagares_data.append(registro)
            st.session_state.drawer_open = False
            st.success(f"✅ Guardado ({len(cambios)} cambios).")

if st.session_state.drawer_open:
    # Renderiza el drawer arriba del resto del contenido
    st.markdown(
        "<style>section.main > div {filter: blur(1px);} </style>",
        unsafe_allow_html=True
    )
    render_drawer()

if st.session_state.drawer_open:
    render_drawer()
