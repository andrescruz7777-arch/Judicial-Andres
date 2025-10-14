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

html, body, .stApp { background: var(--bg) !important; }
* { font-family: 'Poppins', sans-serif; }

/* SIDEBAR */
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

/* HEADER */
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

/* TARJETAS */
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

/* BOTONES */
.stButton>button{
  background: var(--primary) !important; color:#fff !important; border:none;
  padding:.6rem 1rem; border-radius: 12px; font-weight:600;
  transition:.2s transform ease;
}
.stButton>button:hover{ background: var(--primary-700) !important; transform: translateY(-1px); }
.btn-sec>button{ background: #EEF2F7 !important; color:#334155 !important; }

/* TABLAS */
.stDataFrame{
  border-radius: 12px; overflow: hidden; border:1px solid #EEF1F6;
  box-shadow: 0 8px 24px rgba(31,41,64,0.05);
}

/* INPUTS EDITOR */
.stTextInput > div > div > input {
    background-color: #1F1F1F !important;
    color: #FFFFFF !important;
    border-radius: 8px;
    border: 1px solid #333 !important;
}
.stTextInput > div > div > input:focus {
    border: 1px solid #2F80ED !important;
    box-shadow: 0 0 0 1px #2F80ED !important;
}

/* UPLOADER VISIBLE */
.stFileUploader, .stFileUploader div, .stFileUploader label, .stFileUploader span {
    color: #FFFFFF !important;
}
.stFileUploader > div:first-child {
    background-color: #2F2F2F !important;
    border-radius: 12px !important;
    border: 1px solid #3A3A3A !important;
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

/* MENSAJES IA */
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

/* BANNER FINAL */
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
    st.markdown('<span class="badge">v1.2 UI Avanzada</span>', unsafe_allow_html=True)

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
                st.success(f"✅ PDF '{pdf.name}' cargado correctamente.")
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
            st.markdown('<div class="ia-loader">🧠 Estamos trabajando en ello... analizando tu pagaré, por favor espera unos segundos.</div>', unsafe_allow_html=True)
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
Extrae los siguientes datos manuscritos del pagaré, prestando atención a cualquier texto al final o junto a la firma:
- "Nombre del Deudor": nombre completo de quien firma el pagaré.
- "Cedula": número de identificación.
- "Direccion": dirección completa (calle, carrera, número, barrio si aparece).
- "Ciudad": ciudad asociada a la dirección (residencia del deudor).
- "Telefono": número de contacto manuscrito.
- "Fecha de Firma": fecha completa en que se firmó el pagaré.
- "Ciudad de Firma": ciudad que acompaña la fecha de firma o que esté escrita antes del nombre del deudor (por ejemplo: “Montería, 2 de marzo de 2023” → extraer “Montería”).

Devuélvelo estrictamente en formato JSON con las claves:
{
  "Nombre del Deudor": "",
  "Cedula": "",
  "Direccion": "",
  "Ciudad": "",
  "Telefono": "",
  "Fecha de Firma": "",
  "Ciudad de Firma": ""
}
"""
                cab = extraer_json_vision(st.session_state["cab"], prompt_cab, modo)
                man = extraer_json_vision(st.session_state["man"], prompt_man, modo)
                st.session_state.ultimo_registro = {**cab, **man}
            st.session_state.procesando = False

            st.markdown("""
            <div class='success-banner'>
                ✅ Extracción completada correctamente.<br>
                <small>Haz clic en <b>🧠 Extracción IA</b> en el menú lateral para continuar al siguiente paso.</small>
            </div>
            """, unsafe_allow_html=True)

# =========================
# 🧠 EXTRACCIÓN IA
# =========================
if menu == "🧠 Extracción IA":
    if st.session_state.ultimo_registro:
        df_view = pd.DataFrame([st.session_state.ultimo_registro]).T.reset_index()
        df_view.columns = ["Campo", "Valor"]
        st.dataframe(df_view, use_container_width=True, height=420)
        if st.button("✏️ Abrir editor de campos"):
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
        st.dataframe(df_hist, use_container_width=True, height=440)
        excel_io = io.BytesIO()
        df_hist.to_excel(excel_io, index=False, engine="openpyxl")
        excel_io.seek(0)
        st.download_button("⬇️ Descargar Excel", data=excel_io, file_name="resultados_pagares.xlsx")
    else:
        st.info("Aún no hay registros guardados.")

# =========================
# 🧾 FORMULARIO INFERIOR DE EDICIÓN
# =========================
def render_editor():
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">✏️ Editar campos del pagaré</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    updated = {}
    cols = st.columns(2)
    campos = list(st.session_state.drawer_payload.items())

    mitad = len(campos)//2 or 1
    with cols[0]:
        for campo, valor in campos[:mitad]:
            updated[campo] = st.text_input(campo, str(valor))
    with cols[1]:
        for campo, valor in campos[mitad:]:
            updated[campo] = st.text_input(campo, str(valor))

    st.markdown('</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])
    with col1:
        cancel = st.button("❌ Cancelar edición", use_container_width=True)
    with col2:
        save = st.button("💾 Guardar cambios", use_container_width=True)

    if cancel:
        st.session_state.drawer_open = False
        st.info("Edición cancelada.")
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
        st.success(f"✅ Guardado correctamente ({len(cambios)} cambios).")

if st.session_state.drawer_open:
    render_editor()

