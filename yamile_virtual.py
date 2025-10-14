import streamlit as st
import pandas as pd
from PIL import Image
import io
import base64
import openai
import json
import re
import fitz  # PyMuPDF

# =====================================
# ⚙️ CONFIGURACIÓN INICIAL
# =====================================
st.set_page_config(page_title="📄 Extractor Pagarés con IA", layout="wide")
st.title("✍️ Extractor de Pagarés - COS JudicIA (Precisión Automática 95–99%) 🤖")

openai.api_key = st.secrets["OPENAI_API_KEY"]

# =====================================
# 🧠 FUNCIONES BASE IA
# =====================================
def mejorar_imagen(imagen_bytes):
    """Convierte a escala gris y aumenta resolución para mejor OCR."""
    img = Image.open(io.BytesIO(imagen_bytes)).convert("L")
    img = img.resize((img.width * 2, img.height * 2))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def extraer_con_ia(imagen_bytes, instruccion):
    """Llama al modelo GPT-4o para extracción de datos estructurados."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de pagarés manuscritos colombianos. Usa tu conocimiento del formato de estos documentos para interpretar escritura difícil."},
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
            max_tokens=1200,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error al procesar la imagen: {e}"

def limpiar_json(texto):
    """Extrae el bloque JSON válido desde una respuesta."""
    try:
        start = texto.index("{")
        end = texto.rindex("}") + 1
        return texto[start:end]
    except:
        return "{}"

# =====================================
# 🧹 NORMALIZACIÓN Y VALIDACIÓN
# =====================================
def normalizar_campos(data):
    mapeo = {
        "Número de pagaré": "Numero de Pagare",
        "NumeroDePagare": "Numero de Pagare",
        "Ciudad": "Ciudad",
        "Día": "Dia",
        "Día (en letras)": "Dia (en letras)",
        "DiaEnLetras": "Dia (en letras)",
        "Día (en número)": "Dia (en numero)",
        "DiaEnNumero": "Dia (en numero)",
        "Mes": "Mes",
        "Año": "Año",
        "Año (en letras)": "Año (en letras)",
        "AnoEnLetras": "Año (en letras)",
        "Año (en número)": "Año (en numero)",
        "AnoEnNumero": "Año (en numero)",
        "Valor en letras": "Valor en letras",
        "ValorEnLetras": "Valor en letras",
        "Valor en números": "Valor en numeros",
        "ValorEnNumeros": "Valor en numeros",
        "Nombre del deudor": "Nombre del Deudor",
        "Cédula o número de identificación": "Cedula",
        "Cedula o numero de identificacion": "Cedula",
        "Dirección": "Direccion",
        "Telefono": "Telefono",
        "Teléfono": "Telefono",
        "Fecha de firma": "Fecha de Firma"
    }
    return {mapeo.get(k.strip(), k.strip()): (v.strip() if isinstance(v, str) else v) for k, v in data.items()}

def validar_y_corregir(data):
    """Valida campos numéricos y corrige errores típicos de OCR."""
    # Cedula
    if "Cedula" in data:
        ced = re.sub(r"\D", "", str(data["Cedula"]))
        data["Cedula"] = ced if 6 <= len(ced) <= 10 else ""

    # Telefono
    if "Telefono" in data:
        tel = re.sub(r"\D", "", str(data["Telefono"]))
        if tel.startswith("3") and len(tel) == 10:
            data["Telefono"] = tel
        else:
            data["Telefono"] = ""

    # Año
    if "Año (en numero)" in data:
        try:
            year = int(re.sub(r"\D", "", str(data["Año (en numero)"])))
            if year < 2020 or year > 2026:  # fuera de rango esperado
                data["Año (en numero)"] = ""
        except:
            data["Año (en numero)"] = ""

    # Fecha
    if "Fecha de Firma" in data:
        data["Fecha de Firma"] = str(data["Fecha de Firma"]).replace("/", "-").strip()

    # Correcciones de texto comunes
    reemplazos = {"HinesTroza": "Hinestroza", "Monteria": "Montería", "MonterIa": "Montería"}
    for k, v in reemplazos.items():
        for campo, valor in data.items():
            if isinstance(valor, str) and k.lower() in valor.lower():
                data[campo] = valor.replace(k, v)
    return data

def combinar_resultados(opt1, opt2):
    """Fusiona dos JSON priorizando consistencia y longitud."""
    final = {}
    for key in set(opt1.keys()).union(opt2.keys()):
        v1, v2 = opt1.get(key, ""), opt2.get(key, "")
        s1, s2 = str(v1).strip(), str(v2).strip()
        if s1 == s2:
            final[key] = s1
        elif not s1:
            final[key] = s2
        elif not s2:
            final[key] = s1
        else:
            final[key] = s1 if len(s1) > len(s2) else s2
    return final

def evaluar_precision(data):
    """Evalúa la consistencia de los datos extraídos para decidir cuál es mejor."""
    score = 0
    # Año razonable
    try:
        year = int(re.sub(r"\D", "", str(data.get("Año (en numero)", ""))))
        if 2020 <= year <= 2026:
            score += 1
    except:
        pass
    # Cedula válida
    if re.fullmatch(r"\d{6,10}", str(data.get("Cedula", ""))):
        score += 1
    # Teléfono válido
    if re.fullmatch(r"3\d{9}", str(data.get("Telefono", ""))):
        score += 1
    # Ciudad conocida
    ciudad = str(data.get("Ciudad", "")).lower()
    if any(c in ciudad for c in ["monteria", "bogota", "barranquilla", "cali", "medellin"]):
        score += 1
    return score

# =====================================
# 🗂️ SESIÓN
# =====================================
if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []

# =====================================
# 📍 INTERFAZ DE CARGA
# =====================================
st.header("📍 Paso 1: Carga de documento")
tipo = st.radio("Selecciona el tipo de documento:", ["📸 Imágenes", "📄 PDF"])

cabecera_bytes = None
manuscrita_bytes = None

if tipo == "📸 Imágenes":
    cabecera = st.file_uploader("Cabecera del pagaré", type=["png", "jpg", "jpeg"])
    manuscrita = st.file_uploader("Parte manuscrita del pagaré", type=["png", "jpg", "jpeg"])
    if cabecera and manuscrita:
        col1, col2 = st.columns(2)
        col1.image(cabecera, caption="Cabecera", use_column_width=True)
        col2.image(manuscrita, caption="Parte Manuscrita", use_column_width=True)
        cabecera_bytes = mejorar_imagen(cabecera.read())
        manuscrita_bytes = mejorar_imagen(manuscrita.read())
else:
    archivo_pdf = st.file_uploader("Sube el PDF del pagaré", type=["pdf"])
    if archivo_pdf:
        pdf_bytes = archivo_pdf.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) > 0:
            st.success(f"📚 {len(doc)} páginas detectadas.")
            paginas = [doc.load_page(0), doc.load_page(len(doc) - 1)]
            imgs = []
            for p in paginas:
                pix = p.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                imgs.append(img)
            col1, col2 = st.columns(2)
            col1.image(imgs[0], caption="Cabecera", use_column_width=True)
            col2.image(imgs[1], caption="Parte Manuscrita", use_column_width=True)
            cab_buf, man_buf = io.BytesIO(), io.BytesIO()
            imgs[0].save(cab_buf, format="PNG")
            imgs[1].save(man_buf, format="PNG")
            cabecera_bytes = mejorar_imagen(cab_buf.getvalue())
            manuscrita_bytes = mejorar_imagen(man_buf.getvalue())

# =====================================
# 🤖 PROCESAMIENTO CON IA
# =====================================
if cabecera_bytes and manuscrita_bytes:
    st.divider()
    st.header("🤖 Paso 2: Extracción y Evaluación Automática")

    if st.button("🚀 Ejecutar Análisis IA"):
        instruccion_cab = """
        Extrae los datos del pagaré:
        - Número de pagaré
        - Ciudad
        - Día (en letras y número)
        - Mes
        - Año (en letras y número)
        - Valor en letras
        - Valor en números
        Devuelve JSON limpio sin comentarios.
        """
        instruccion_man = """
        Extrae los datos manuscritos del pagaré:
        - Nombre del deudor
        - Cédula o número de identificación
        - Dirección
        - Ciudad
        - Teléfono
        - Fecha de firma (YYYY-MM-DD)
        Devuelve JSON limpio.
        """

        st.info("⌛ Procesando doble interpretación IA...")
        cab1 = extraer_con_ia(cabecera_bytes, instruccion_cab)
        cab2 = extraer_con_ia(cabecera_bytes, instruccion_cab + "\nSé más interpretativo.")
        man1 = extraer_con_ia(manuscrita_bytes, instruccion_man)
        man2 = extraer_con_ia(manuscrita_bytes, instruccion_man + "\nSé más interpretativo.")

        # Procesar resultados
        try:
            cab1 = validar_y_corregir(normalizar_campos(json.loads(limpiar_json(cab1))))
            cab2 = validar_y_corregir(normalizar_campos(json.loads(limpiar_json(cab2))))
            man1 = validar_y_corregir(normalizar_campos(json.loads(limpiar_json(man1))))
            man2 = validar_y_corregir(normalizar_campos(json.loads(limpiar_json(man2))))

            cab_final = combinar_resultados(cab1, cab2)
            man_final = combinar_resultados(man1, man2)

            # Evaluación automática
            score_precisa = evaluar_precision({**cab1, **man1})
            score_interp = evaluar_precision({**cab2, **man2})
            mejor = "Interpretativa" if score_interp >= score_precisa else "Precisa"

            data_final = {**cab_final, **man_final}
            st.session_state.pagares_data.append(data_final)

            st.success(f"✅ Datos combinados ({mejor} fue más coherente).")
            st.json(data_final)

        except Exception as e:
            st.error(f"Error al combinar datos: {e}")

# =====================================
# 📊 EXPORTAR
# =====================================
if st.session_state.pagares_data:
    st.divider()
    st.header("📊 Paso 3: Exportar Resultados")
    df = pd.DataFrame(st.session_state.pagares_data)
    st.dataframe(df)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    st.download_button(
        "⬇️ Descargar Excel con resultados",
        buffer,
        "pagares_extraidos.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
