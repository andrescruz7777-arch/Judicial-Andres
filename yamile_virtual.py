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
st.title("✍️ Extractor de Pagarés - COS JudicIA (Alta Precisión) 🤖")

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
    """Llama al modelo GPT-4o para extracción."""
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Eres un experto en lectura de pagarés y documentos manuscritos colombianos."},
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
    """Extrae y limpia el bloque JSON."""
    try:
        start = texto.index("{")
        end = texto.rindex("}") + 1
        return texto[start:end]
    except:
        return texto

# =====================================
# 🧹 NORMALIZACIÓN Y VALIDACIÓN
# =====================================
def normalizar_campos(data):
    mapeo = {
        "Número de pagaré": "Numero de Pagare",
        "NumeroDePagare": "Numero de Pagare",
        "Ciudad": "Ciudad",
        "Día (en letras)": "Dia (en letras)",
        "DiaEnLetras": "Dia (en letras)",
        "Día (en número)": "Dia (en numero)",
        "DiaEnNumero": "Dia (en numero)",
        "Mes": "Mes",
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
        "Direccion": "Direccion",
        "Teléfono": "Telefono",
        "Telefono": "Telefono",
        "Fecha de firma": "Fecha de Firma"
    }
    return {mapeo.get(k.strip(), k.strip()): (v.strip() if isinstance(v, str) else v) for k, v in data.items()}

def validar_y_corregir(data):
    """Aplica validaciones y corrige errores comunes."""
    # Cédula
    if "Cedula" in data:
        ced = re.sub(r"\D", "", data["Cedula"])
        if 6 <= len(ced) <= 10:
            data["Cedula"] = ced
        else:
            data["Cedula"] = ""
    # Teléfono
    if "Telefono" in data:
        tel = re.sub(r"\D", "", data["Telefono"])
        if tel.startswith("3") and len(tel) == 10:
            data["Telefono"] = tel
        else:
            data["Telefono"] = ""
    # Fecha
    if "Fecha de Firma" in data:
        data["Fecha de Firma"] = data["Fecha de Firma"].replace("/", "-").strip()
    # Corrección semántica
    reemplazos = {"HinesTroza": "Hinestroza", "Monteria": "Montería"}
    for k, v in reemplazos.items():
        for campo, valor in data.items():
            if isinstance(valor, str) and k.lower() in valor.lower():
                data[campo] = valor.replace(k, v)
    return data

def combinar_resultados(opt1, opt2):
    """Fusiona dos extracciones IA para obtener el mejor resultado."""
    final = {}
    for key in set(opt1.keys()).union(opt2.keys()):
        v1, v2 = opt1.get(key, ""), opt2.get(key, "")
        if v1 == v2:
            final[key] = v1
        elif not v1:
            final[key] = v2
        elif not v2:
            final[key] = v1
        else:
            final[key] = v1 if len(v1) > len(v2) else v2
    return final

# =====================================
# 🗂️ SESIÓN
# =====================================
if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []

# =====================================
# 📍 INTERFAZ DE CARGA
# =====================================
st.header("📍 Paso 1: Selecciona tipo de documento")
tipo = st.radio("¿Qué deseas cargar?", ["📸 Imágenes", "📄 PDF"])

cabecera_bytes = None
manuscrita_bytes = None

if tipo == "📸 Imágenes":
    st.header("📌 Cargar Cabecera y Parte Manuscrita")
    cabecera = st.file_uploader("Cabecera del pagaré", type=["png", "jpg", "jpeg"], key="cabecera")
    manuscrita = st.file_uploader("Parte manuscrita", type=["png", "jpg", "jpeg"], key="manuscrita")
    if cabecera and manuscrita:
        col1, col2 = st.columns(2)
        with col1: st.image(cabecera, caption="Cabecera", use_column_width=True)
        with col2: st.image(manuscrita, caption="Manuscrita", use_column_width=True)
        cabecera_bytes = mejorar_imagen(cabecera.read())
        manuscrita_bytes = mejorar_imagen(manuscrita.read())
else:
    st.header("📄 Cargar PDF del pagaré")
    archivo_pdf = st.file_uploader("Sube el archivo PDF", type=["pdf"])
    if archivo_pdf:
        try:
            pdf_bytes = archivo_pdf.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if len(doc) == 0:
                st.error("⚠️ El PDF está vacío o dañado.")
            else:
                st.success(f"📚 {len(doc)} páginas detectadas.")
                paginas = [doc.load_page(0), doc.load_page(len(doc) - 1)]
                imgs = []
                for p in paginas:
                    pix = p.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    imgs.append(img)
                col1, col2 = st.columns(2)
                col1.image(imgs[0], caption="Cabecera", use_column_width=True)
                col2.image(imgs[1], caption="Manuscrita", use_column_width=True)
                cab_buf, man_buf = io.BytesIO(), io.BytesIO()
                imgs[0].save(cab_buf, format="PNG")
                imgs[1].save(man_buf, format="PNG")
                cabecera_bytes = mejorar_imagen(cab_buf.getvalue())
                manuscrita_bytes = mejorar_imagen(man_buf.getvalue())
        except Exception as e:
            st.error(f"❌ Error al procesar PDF: {e}")

# =====================================
# 🤖 PROCESAMIENTO CON IA
# =====================================
if cabecera_bytes and manuscrita_bytes:
    st.divider()
    st.header("🤖 Paso 2: Extracción con Validación Inteligente")

    if st.button("🚀 Ejecutar Análisis IA"):
        # Prompts avanzados
        instruccion_cabecera = """
        Extrae estos datos de la imagen (cabecera del pagaré):
        - Número de pagaré
        - Ciudad
        - Día (en letras y en número)
        - Mes
        - Año (en letras y en número)
        - Valor en letras
        - Valor en números
        Devuelve un JSON limpio y correcto.
        """
        instruccion_manuscrita = """
        Analiza la imagen que contiene datos manuscritos de un pagaré.
        Extrae los campos con máxima precisión:
        - Nombre del deudor
        - Cédula o número de identificación
        - Dirección
        - Ciudad
        - Teléfono
        - Fecha de firma (YYYY-MM-DD)
        Si un dígito o letra es poco claro, infiere usando formato colombiano.
        Devuelve solo JSON, sin comentarios.
        """

        st.info("⌛ Procesando dos interpretaciones IA, esto puede tardar unos segundos...")
        cab_1 = extraer_con_ia(cabecera_bytes, instruccion_cabecera)
        cab_2 = extraer_con_ia(cabecera_bytes, instruccion_cabecera + "\nSé más literal e inferente.")
        man_1 = extraer_con_ia(manuscrita_bytes, instruccion_manuscrita)
        man_2 = extraer_con_ia(manuscrita_bytes, instruccion_manuscrita + "\nSé más interpretativo en escritura.")

        # Mostrar resultados crudos
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🧠 Opción 1 (Precisa)")
            st.code(cab_1, language="json")
            st.code(man_1, language="json")
        with col2:
            st.markdown("### 🤔 Opción 2 (Interpretativa)")
            st.code(cab_2, language="json")
            st.code(man_2, language="json")

        try:
            # Cargar y normalizar
            cab1 = normalizar_campos(json.loads(limpiar_json(cab_1)))
            cab2 = normalizar_campos(json.loads(limpiar_json(cab_2)))
            man1 = normalizar_campos(json.loads(limpiar_json(man_1)))
            man2 = normalizar_campos(json.loads(limpiar_json(man_2)))

            # Fusionar resultados
            cab_final = combinar_resultados(cab1, cab2)
            man_final = combinar_resultados(man1, man2)

            # Validar y corregir
            cab_final = validar_y_corregir(cab_final)
            man_final = validar_y_corregir(man_final)

            data_final = {**cab_final, **man_final}
            st.session_state.pagares_data.append(data_final)

            st.success("✅ Datos combinados, validados y almacenados con alta precisión.")
            st.json(data_final)
        except Exception as e:
            st.error(f"Error al combinar datos: {e}")

# =====================================
# 📊 EXPORTAR RESULTADOS
# =====================================
if st.session_state.pagares_data:
    st.divider()
    st.header("📊 Paso 3: Exportar Resultados")
    df = pd.DataFrame(st.session_state.pagares_data)
    st.dataframe(df)
    excel_io = io.BytesIO()
    df.to_excel(excel_io, index=False, engine="openpyxl")
    excel_io.seek(0)
    st.download_button(
        label="⬇️ Descargar Excel",
        data=excel_io,
        file_name="pagares_extraidos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
