import streamlit as st
import pandas as pd
from PIL import Image
import io, base64, json, re, datetime, fitz
import openai

# =========================
# ⚙️ CONFIGURACIÓN INICIAL
# =========================
st.set_page_config(page_title="Extractor de Pagarés IA — Modo Dual", layout="wide")
st.title("✍️ Extractor de Pagarés — COS JudicIA (Modo Dual 🤖 / ⚡)")

openai.api_key = st.secrets["OPENAI_API_KEY"]

# =========================
# 🔧 VARIABLES GLOBALES
# =========================
CRITICAL_FIELDS = ["Nombre del Deudor", "Cedula", "Valor en letras", "Valor en numeros"]

if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []
if "procesando" not in st.session_state:
    st.session_state.procesando = False

# =========================
# 🧩 FUNCIONES DE UTILIDAD
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

def letras_a_int(texto):
    texto = texto.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
    partes = texto.split()
    n = 0
    unidades = {"uno":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9}
    decenas = {"diez":10,"veinte":20,"treinta":30,"cuarenta":40,"cincuenta":50,"sesenta":60,"setenta":70,"ochenta":80,"noventa":90}
    for p in partes:
        if p in unidades: n += unidades[p]
        elif p in decenas: n += decenas[p]
    return n

def valores_consistentes(letras, numeros):
    try:
        n = int(re.sub(r"[^\d]", "", str(numeros)))
        return n == letras_a_int(letras)
    except:
        return False

# =========================
# 🧠 FUNCIÓN IA CENTRAL
# =========================
def extraer_json_vision(im_bytes, prompt, modo="auditoria"):
    """Ejecuta 1 o 3 pasadas según el modo."""
    def call(extra=""):
        resp = openai.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Eres perito en lectura de pagarés colombianos. Devuelve SIEMPRE JSON estricto."},
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
        return call("\nModo rápido, interpreta directamente el texto visible.")
    else:
        o1 = call("\nModo: PRECISO.")
        o2 = call("\nModo: INTERPRETATIVO.")
        o3 = call("\nModo: VERIFICACIÓN.")
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
# 📁 INTERFAZ DE CARGA
# =========================
st.header("1️⃣ Carga del pagaré")
modo_doc = st.radio("Tipo de documento:", ["📄 PDF", "📸 Imágenes"])
modo_proceso = st.radio("Modo de extracción:", ["🟢 Económico (rápido)", "🧠 Auditoría (alta precisión)"])
modo_proceso = "economico" if "Económico" in modo_proceso else "auditoria"

cabecera_bytes, manuscrita_bytes = None, None
if modo_doc == "📄 PDF":
    pdf = st.file_uploader("Sube el pagaré (PDF)", type=["pdf"])
    if pdf:
        try:
            cab, man, thumbs = pdf_a_imagenes(pdf.read())
            st.image(thumbs, caption=["Cabecera", "Parte manuscrita"], width=300)
            cabecera_bytes, manuscrita_bytes = mejorar_imagen(cab), mejorar_imagen(man)
        except Exception as e:
            st.error(f"Error al procesar PDF: {e}")
else:
    cab = st.file_uploader("Cabecera", type=["jpg", "jpeg", "png"])
    man = st.file_uploader("Parte manuscrita", type=["jpg", "jpeg", "png"])
    if cab and man:
        col1, col2 = st.columns(2)
        col1.image(cab, caption="Cabecera")
        col2.image(man, caption="Parte manuscrita")
        cabecera_bytes, manuscrita_bytes = mejorar_imagen(cab.read()), mejorar_imagen(man.read())

# =========================
# 🤖 PROCESAMIENTO
# =========================
if cabecera_bytes and manuscrita_bytes:
    st.divider()
    st.header("2️⃣ Extracción automática")

    if st.button("🚀 Ejecutar IA") and not st.session_state.procesando:
        st.session_state.procesando = True
        with st.spinner("Procesando pagaré..."):
            prompt_cab = '{"Numero de Pagare":"","Ciudad":"","Dia (en letras)":"","Dia (en numero)":"","Mes":"","Año (en letras)":"","Año (en numero)":"","Valor en letras":"","Valor en numeros":""}'
            prompt_man = '{"Nombre del Deudor":"","Cedula":"","Direccion":"","Ciudad":"","Telefono":"","Fecha de Firma":""}'
            cab = extraer_json_vision(cabecera_bytes, prompt_cab, modo=modo_proceso)
            man = extraer_json_vision(manuscrita_bytes, prompt_man, modo=modo_proceso)
            data = {**cab, **man}
        st.session_state.procesando = False

        st.json(data)
        st.success("✅ Extracción completada")

        # Validación crítica
        errores = []
        if not re.fullmatch(r"\d{6,10}", str(data.get("Cedula",""))):
            errores.append("Cédula inválida")
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]{5,60}", str(data.get("Nombre del Deudor",""))):
            errores.append("Nombre inválido")
        if not valores_consistentes(data.get("Valor en letras",""), data.get("Valor en numeros","")):
            errores.append("Valor letras ≠ números")
        if errores:
            st.error("⚠️ Errores críticos: " + " | ".join(errores))

        # Edición manual
        st.subheader("✏️ Corrección manual y trazabilidad")
        cambios = []
        data_edit = {}
        for campo, valor in data.items():
            nuevo = st.text_input(campo, str(valor))
            data_edit[campo] = nuevo
            if str(nuevo).strip() != str(valor).strip():
                cambios.append(campo)

        if st.button("💾 Guardar registro"):
            registro = data_edit.copy()
            registro["Campos Modificados"] = ", ".join(cambios) if cambios else "Sin cambios"
            registro["Editado Manualmente"] = "Sí" if cambios else "No"
            registro["Modo"] = modo_proceso
            registro["Fecha Registro"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.pagares_data.append(registro)
            st.success(f"✅ Guardado con éxito. Cambios: {len(cambios)} campo(s).")

# =========================
# 📊 EXPORTAR
# =========================
if st.session_state.pagares_data:
    st.divider()
    st.header("3️⃣ Exportar resultados")
    df = pd.DataFrame(st.session_state.pagares_data)
    st.dataframe(df, use_container_width=True)
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    st.download_button(
        "⬇️ Descargar Excel",
        buf,
        "pagares_extraidos.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
