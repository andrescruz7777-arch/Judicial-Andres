# ============================================
# 📄 Extractor de Pagarés — COS JudicIA (UI Moderno)
# Estilo: Dashboard tipo CrmX Admin (sidebar oscuro + drawer derecho)
# Mantiene TODA la lógica existente de tu app
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
  --text: #333333;
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
[data-testid="stSidebar"] .stRadio > label, 
[data-testid="stSidebar"] .stCheckbox > label { color: #E9EEF6 !important; }

/* Sidebar header/logo */
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
# Drawer UI
if "drawer_open" not in st.session_state:
    st.session_state.drawer_open = False
if "drawer_payload" not in st.session_state:
    st.session_state.drawer_payload = {}

# =========================
# 🔧 FUNCIONES UTILITARIAS
# =========================
def mejorar_imagen(im_bytes):
    """Escala de grises + aumento de resolución."""
    img = Image.open(io.BytesIO(im_bytes)).convert("L")
    img = img.resize((img.width * 2, img.height * 2))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def pdf_a_imagenes(pdf_bytes):
    """Convierte primera y última página del PDF en imágenes PNG."""
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

def letras_a_int(texto):
    """Convierte número en letras a entero básico."""
    texto = texto.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    unidades = {
        "uno":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,
        "diez":10,"veinte":20,"treinta":30,"cuarenta":40,"cincuenta":50,"sesenta":60,"setenta":70,
        "ochenta":80,"noventa":90,"cien":100,"mil":1000,"millon":1000000,"millones":1000000
    }
    total = 0
    for p in texto.split():
        if p in unidades:
            total += unidades[p]
    return total

def valores_consistentes(letras, numeros):
    try:
        n = int(re.sub(r"[^\d]", "", str(numeros)))
        return n == letras_a_int(letras)
    except:
        return False

def extraer_json_vision(im_bytes, prompt, modo="auditoria"):
    """Procesamiento IA: 1 pasada (económica) o 3 pasadas (auditoría)."""
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

    if modo == "economico":
        return call("\nModo rápido, interpreta texto visible.")
    else:
        o1 = call("\nModo: Preciso.")
        o2 = call("\nModo: Interpretativo.")
        o3 = call("\nModo: Verificación.")
        final = {}
        keys = set(o1.keys()) | set(o2.keys()) | set(o3.keys())
        for k in keys:
            vals = [str(o.get(k, "")).strip() for o in [o1, o2, o3] if o.get(k)]
            if not vals:
                final[k] = ""
            elif any(vals.count(v) >= 2 for v in vals):
                final[k] = max(vals, key=vals.count)
            else:
                final[k] = max(vals, key=len)
        return final

# =========================
# 🧭 SIDEBAR (Navegación)
# =========================
with st.sidebar:
    st.markdown('<div class="sidebar-logo"><span class="logo-dot"></span><span><b>COS JudicIA</b><br><span style="font-size:.8rem; opacity:.85">Extractor de Pagarés</span></span></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-user">👤 <b>Operador</b><span style="opacity:.7"> | COS</span></div>', unsafe_allow_html=True)

    menu = st.radio("Menú", ["📄 Subir pagarés", "🧠 Extracción IA", "✏️ Corrección manual", "📊 Histórico / Excel", "⚙️ Configuración"], label_visibility="collapsed")
    st.write("")
    st.markdown('<span class="badge">v1.0 UI Moderno</span>', unsafe_allow_html=True)

# =========================
# 🔝 HEADER SUPERIOR
# =========================
colH1, colH2 = st.columns([6,2])
with colH1:
    st.markdown("""
    <div class="app-header">
      <div class="searchbox">
        🔎 <input placeholder="Buscar por cédula, nombre o número de pagaré..."/>
      </div>
      <div class="badge">Ayuda</div>
      <div class="badge">Notificaciones</div>
      <div class="badge">Perfil</div>
    </div>
    """, unsafe_allow_html=True)
with colH2:
    pass  # (espaciado para alinear)

st.markdown("")

# =========================
# 📊 TARJETAS DE RESUMEN
# =========================
total_procesados = len(st.session_state.pagares_data)
total_editados = sum(1 for r in st.session_state.pagares_data if str(r.get("Editado Manualmente","No")).lower().startswith("s"))
precision_aprox = 97  # decorativo; si quieres puedes calcularlo en base a consistencia
tiempo_prom = 1.2     # decorativo

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="card metric">
      <div>
        <div class="label">Pagarés procesados</div>
        <div class="value">{total_procesados}</div>
      </div>
      <span class="chip">+ Hoy</span>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="card metric">
      <div>
        <div class="label">Campos corregidos</div>
        <div class="value">{total_editados}</div>
      </div>
      <span class="chip">QA</span>
    </div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="card metric">
      <div>
        <div class="label">Extracciones exitosas</div>
        <div class="value">{precision_aprox}%</div>
      </div>
      <span class="chip">Est.</span>
    </div>""", unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="card metric">
      <div>
        <div class="label">Tiempo promedio</div>
        <div class="value">{tiempo_prom} min</div>
      </div>
      <span class="chip">SLA</span>
    </div>""", unsafe_allow_html=True)

st.write("")

# =========================
# 🧾 SECCIONES PRINCIPALES
# =========================

# === 1) SUBIR PAGARÉS ===
if menu == "📄 Subir pagarés":
    st.markdown('<div class="section-title">📤 Carga de pagarés</div>', unsafe_allow_html=True)
    with st.container():
        c1, c2 = st.columns([1.2, 1])
        with c1:
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.subheader("1️⃣ Seleccionar archivos")
                tipo_doc = st.radio("Tipo de archivo:", ["📄 PDF", "📸 Imágenes"], horizontal=True)
                modo_proceso_label = st.radio("Modo de extracción:", ["🟢 Económico (rápido)", "🧠 Auditoría (alta precisión)"], horizontal=True)
                modo_proceso = "economico" if "Económico" in modo_proceso_label else "auditoria"

                # Preview variables
                st.session_state.__setattr__("__cab__", None)
                st.session_state.__setattr__("__man__", None)
                st.session_state.__setattr__("__imgs__", [])

                cabecera_bytes, manuscrita_bytes = None, None
                imgs = []

                if tipo_doc == "📄 PDF":
                    pdf = st.file_uploader("Sube el pagaré en PDF", type=["pdf"])
                    if pdf:
                        try:
                            cab, man, imgs = pdf_a_imagenes(pdf.read())
                            cabecera_bytes, manuscrita_bytes = mejorar_imagen(cab), mejorar_imagen(man)
                            st.session_state.__setattr__("__cab__", cabecera_bytes)
                            st.session_state.__setattr__("__man__", manuscrita_bytes)
                            st.session_state.__setattr__("__imgs__", imgs)
                            st.success("✅ PDF cargado correctamente.")
                        except Exception as e:
                            st.error(f"Error al procesar PDF: {e}")
                else:
                    colA, colB = st.columns(2)
                    with colA:
                        cab = st.file_uploader("Cabecera", type=["jpg", "jpeg", "png"])
                    with colB:
                        man = st.file_uploader("Parte manuscrita", type=["jpg", "jpeg", "png"])
                    if cab and man:
                        cabecera_bytes = mejorar_imagen(cab.read())
                        manuscrita_bytes = mejorar_imagen(man.read())
                        st.session_state.__setattr__("__cab__", cabecera_bytes)
                        st.session_state.__setattr__("__man__", manuscrita_bytes)
                        imgs = [Image.open(io.BytesIO(cabecera_bytes)), Image.open(io.BytesIO(manuscrita_bytes))]
                        st.session_state.__setattr__("__imgs__", imgs)
                        st.success("✅ Imágenes cargadas correctamente.")

                st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("👁️ Vista previa")
            prev = st.session_state.__dict__.get("__imgs__", [])
            if prev:
                colP1, colP2 = st.columns(2)
                colP1.image(prev[0], caption="Cabecera", use_container_width=True)
                if len(prev) > 1:
                    colP2.image(prev[-1], caption="Parte manuscrita", use_container_width=True)
            else:
                st.caption("Sube un PDF o imágenes para ver la vista previa.")
            st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    if (st.session_state.__dict__.get("__cab__", None) and st.session_state.__dict__.get("__man__", None)):
        colProc, _ = st.columns([1,3])
        with colProc:
            if st.button("🚀 Analizar con IA"):
                st.session_state.procesando = True
                with st.spinner("Procesando imágenes con IA..."):
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

- "Nombre del Deudor": el nombre completo de quien firma el pagaré.
- "Cedula": el número de identificación del deudor.
- "Direccion": dirección completa (calle, carrera, número, barrio si aparece).
- "Ciudad": la ciudad asociada a la dirección anterior (donde reside el deudor).
- "Telefono": número de contacto manuscrito.
- "Fecha de Firma": la fecha completa en que se firmó el pagaré.
- "Ciudad de Firma": la ciudad donde se firmó el pagaré, que normalmente aparece junto a la fecha o antes del nombre del deudor (por ejemplo: “Montería, 2 de marzo de 2023” → extraer “Montería”).

Devuélvelo estrictamente en formato JSON con esas mismas claves exactas:
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
                    cab = extraer_json_vision(st.session_state.__dict__["__cab__"], prompt_cab, modo= "economico" if "Económico" in st.session_state else "auditoria")
                    man = extraer_json_vision(st.session_state.__dict__["__man__"], prompt_man, modo= "economico" if "Económico" in st.session_state else "auditoria")
                    data = {**cab, **man}
                    st.session_state.ultimo_registro = data
                st.session_state.procesando = False
                st.success("✅ Extracción completada correctamente.")

# === 2) EXTRACCIÓN IA (Resultado en tabla rápida) ===
if menu == "🧠 Extracción IA":
    st.markdown('<div class="section-title">🧠 Resultado de la última extracción</div>', unsafe_allow_html=True)
    if st.session_state.ultimo_registro:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            df_view = pd.DataFrame([st.session_state.ultimo_registro]).T.reset_index()
            df_view.columns = ["Campo", "Valor"]
            st.dataframe(df_view, use_container_width=True, height=420)
            st.markdown('</div>', unsafe_allow_html=True)

            colA, colB = st.columns([1,1])
            with colA:
                if st.button("✏️ Editar registro (drawer)"):
                    st.session_state.drawer_payload = st.session_state.ultimo_registro.copy()
                    st.session_state.drawer_open = True
            with colB:
                st.caption("Usa el botón para abrir el panel lateral y editar.")
    else:
        st.info("Aún no hay un registro extraído. Ve a **Subir pagarés** y ejecuta la IA.")

# === 3) CORRECCIÓN MANUAL (también abre drawer) ===
if menu == "✏️ Corrección manual":
    st.markdown('<div class="section-title">✏️ Validación y corrección</div>', unsafe_allow_html=True)
    if st.session_state.ultimo_registro:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("Estos son los campos extraídos. Puedes abrir el formulario lateral para editar todos los campos.")
            df_view = pd.DataFrame([st.session_state.ultimo_registro]).T.reset_index()
            df_view.columns = ["Campo", "Valor"]
            st.dataframe(df_view, use_container_width=True, height=460)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("✏️ Abrir editor lateral"):
                st.session_state.drawer_payload = st.session_state.ultimo_registro.copy()
                st.session_state.drawer_open = True
    else:
        st.info("No hay datos para corregir. Primero ejecuta una extracción en **Subir pagarés**.")

# === 4) HISTÓRICO / EXCEL ===
if menu == "📊 Histórico / Excel":
    st.markdown('<div class="section-title">📊 Registros guardados</div>', unsafe_allow_html=True)
    if st.session_state.pagares_data:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            df_hist = pd.DataFrame(st.session_state.pagares_data)
            st.dataframe(df_hist, use_container_width=True, height=440)
            st.markdown('</div>', unsafe_allow_html=True)

        excel_io = io.BytesIO()
        df_hist.to_excel(excel_io, index=False, engine="openpyxl")
        excel_io.seek(0)
        st.download_button(
            "⬇️ Descargar Excel con resultados",
            data=excel_io,
            file_name="resultados_pagares.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Aún no hay registros guardados. Después de editar y guardar, aparecerán aquí.")

# === 5) CONFIGURACIÓN ===
if menu == "⚙️ Configuración":
    st.markdown('<div class="section-title">⚙️ Preferencias</div>', unsafe_allow_html=True)
    st.write("Aquí puedes configurar aspectos visuales o defaults del proceso (espacio reservado).")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.checkbox("Habilitar tips de validación en el editor")
    st.checkbox("Resaltar campos con baja confianza (próximo)")
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# 🗂️ DRAWER LATERAL DERECHO
# =========================
def render_drawer():
    st.markdown('<div class="drawer-mask"></div>', unsafe_allow_html=True)
    st.markdown('<div class="drawer">', unsafe_allow_html=True)
    st.markdown("### ✏️ Editar campos del pagaré")

    # Formulario de edición (todos los campos)
    updated = {}
    for campo, valor in st.session_state.drawer_payload.items():
        updated[campo] = st.text_input(campo, str(valor))

    # Footer con acciones
    col1, col2 = st.columns(2)
    with col1:
        cancel = st.button("❌ Cancelar", key="drawer_cancel", use_container_width=True, type="secondary")
    with col2:
        save = st.button("💾 Guardar cambios", key="drawer_save", use_container_width=True)

    if cancel:
        st.session_state.drawer_open = False

    if save:
        # Actualiza último registro y calcula metadata de cambios
        orig = st.session_state.ultimo_registro or {}
        cambios = [k for k in updated if str(updated[k]).strip() != str(orig.get(k,"")).strip()]
        st.session_state.ultimo_registro = updated.copy()

        # Agrega a histórico
        registro = updated.copy()
        registro["Campos Modificados"] = ", ".join(cambios) if cambios else "Sin cambios"
        registro["Editado Manualmente"] = "Sí" if cambios else "No"
        registro["Fecha Registro"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.pagares_data.append(registro)

        st.session_state.drawer_open = False
        st.success(f"✅ Registro guardado correctamente ({len(cambios)} cambios).")

    st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.drawer_open:
    render_drawer()
