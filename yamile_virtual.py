import streamlit as st
import pandas as pd
from PIL import Image
import io, base64, json, re, datetime, fitz
import openai

# =========================
# ⚙️ CONFIGURACIÓN INICIAL
# =========================
st.set_page_config(page_title="Extractor de Pagarés — COS JudicIA", layout="wide")
st.title("✍️ Extractor de Pagarés con IA — Modo Dual (Precisión y Trazabilidad)")

openai.api_key = st.secrets["OPENAI_API_KEY"]

# =========================
# VARIABLES GLOBALES
# =========================
if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []
if "ultimo_registro" not in st.session_state:
    st.session_state.ultimo_registro = None
if "procesando" not in st.session_state:
    st.session_state.procesando = False

# =========================
# FUNCIONES UTILITARIAS
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
            max_tokens=900,
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
# INTERFAZ DE USUARIO
# =========================
st.header("1️⃣ Subir pagaré")
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
# PROCESAR
# =========================
if cabecera_bytes and manuscrita_bytes:
    st.divider()
    st.header("2️⃣ Extracción IA y Validación")

    if st.button("🚀 Ejecutar IA") and not st.session_state.procesando:
        st.session_state.procesando = True
        with st.spinner("Procesando imágenes..."):
            prompt_cab = '{"Numero de Pagare":"","Ciudad":"","Dia (en letras)":"","Dia (en numero)":"","Mes":"","Año (en letras)":"","Año (en numero)":"","Valor en letras":"","Valor en numeros":""}'
            
            # 👇 Aquí se agregó “Ciudad de Firma”
            prompt_man = '{"Nombre del Deudor":"","Cedula":"","Direccion":"","Ciudad":"","Ciudad de Firma":"","Telefono":"","Fecha de Firma":""}'
            
            cab = extraer_json_vision(cabecera_bytes, prompt_cab, modo=modo_proceso)
            man = extraer_json_vision(manuscrita_bytes, prompt_man, modo=modo_proceso)
            data = {**cab, **man}
            st.session_state.ultimo_registro = data
        st.session_state.procesando = False
        st.success("✅ Extracción completada correctamente.")
        st.json(data)

# =========================
# CORRECCIÓN Y GUARDADO
# =========================
if st.session_state.ultimo_registro:
    st.divider()
    st.header("3️⃣ Validación y Corrección Manual")

    data = st.session_state.ultimo_registro
    data_edit = {}
    cambios = []

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
        st.success(f"✅ Registro guardado correctamente ({len(cambios)} cambios).")

# =========================
# EXPORTACIÓN A EXCEL
# =========================
if st.session_state.pagares_data:
    st.divider()
    st.header("4️⃣ Exportar resultados a Excel")

    df = pd.DataFrame(st.session_state.pagares_data)
    st.dataframe(df, use_container_width=True)

    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False, engine="openpyxl")
    excel_io.seek(0)

    st.download_button(
        "⬇️ Descargar Excel con resultados",
        excel_io,
        file_name="pagares_extraidos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
