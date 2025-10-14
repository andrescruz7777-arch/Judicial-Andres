import streamlit as st
import pandas as pd
from PIL import Image
import io, base64, json, re, datetime
import fitz  # PyMuPDF
import openai

# =========================
# Config
# =========================
st.set_page_config(page_title="Extractor de Pagarés — Alta Precisión", layout="wide")
st.title("✍️ Extractor de Pagarés — Alta Precisión (Nombre / Cédula / Valor blindados)")

openai.api_key = st.secrets["OPENAI_API_KEY"]
CRITICAL_FIELDS = ["Nombre del Deudor", "Cedula", "Valor en letras", "Valor en numeros"]

# =========================
# Utilidades: imagen
# =========================
def mejorar_imagen(im_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(im_bytes)).convert("L")
    img = img.resize((img.width * 2, img.height * 2))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def pdf_primera_y_ultima_a_png(pdf_bytes: bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if len(doc) == 0:
        raise ValueError("PDF vacío o dañado")
    pages = [0, len(doc) - 1]
    pil_imgs = []
    for p in pages:
        pix = doc.load_page(p).get_pixmap(dpi=200)
        pil_imgs.append(Image.open(io.BytesIO(pix.tobytes("png"))))
    b1, b2 = io.BytesIO(), io.BytesIO()
    pil_imgs[0].save(b1, format="PNG")
    pil_imgs[1].save(b2, format="PNG")
    return b1.getvalue(), b2.getvalue(), pil_imgs

# =========================
# Spanish number parser (letras -> int) y verificador (bidireccional)
# =========================
UNIDADES = {
    "cero":0,"uno":1,"una":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,
    "diez":10,"once":11,"doce":12,"trece":13,"catorce":14,"quince":15,"dieciseis":16,"dieciséis":16,
    "diecisiete":17,"dieciocho":18,"diecinueve":19,"veinte":20,"veintiuno":21,"veintidos":22,"veintidós":22,
    "veintitrés":23,"veintitres":23,"veinticuatro":24,"veinticinco":25,"veintiseis":26,"veintiséis":26,
    "veintisiete":27,"veintiocho":28,"veintinueve":29
}
DECENAS = {"treinta":30,"cuarenta":40,"cincuenta":50,"sesenta":60,"setenta":70,"ochenta":80,"noventa":90}
CENTENAS = {
    "cien":100,"ciento":100,"doscientos":200,"trescientos":300,"cuatrocientos":400,
    "quinientos":500,"seiscientos":600,"setecientos":700,"ochocientos":800,"novecientos":900
}

def normaliza_pal(p):
    return p.lower().replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")

def letras_a_int(texto: str) -> int:
    t = normaliza_pal(texto)
    t = re.sub(r"[^a-z\s]"," ", t)
    parts = [p for p in t.split() if p not in {"de","y","con"}]
    total = 0
    tramo = 0
    i = 0
    while i < len(parts):
        w = parts[i]
        if w in UNIDADES:
            tramo += UNIDADES[w]
        elif w in DECENAS:
            val = DECENAS[w]
            if i+1 < len(parts) and parts[i+1] in UNIDADES:
                tramo += val + UNIDADES[parts[i+1]]; i += 1
            else:
                tramo += val
        elif w in CENTENAS:
            tramo += CENTENAS[w]
        elif w == "mil":
            if tramo == 0: tramo = 1
            total += tramo * 1000; tramo = 0
        elif w in {"millon","millones"}:
            if tramo == 0: tramo = 1
            total += tramo * 1_000_000; tramo = 0
        elif w in {"milmillon","milmillones","milesdemillones","milmillardo","milmillardos"}:
            if tramo == 0: tramo = 1
            total += tramo * 1_000_000_000; tramo = 0
        i += 1
    total += tramo
    return total

def numeros_a_letras(n: int) -> str:
    if n == 0: return "cero"
    def _sub(n):
        res = []
        if n >= 100:
            for k in [900,800,700,600,500,400,300,200,100]:
                for palabra,valor in CENTENAS.items():
                    if valor==k and n>=k:
                        if k==100 and n%100!=0 and palabra=="cien":
                            res.append("ciento")
                        else:
                            res.append(palabra)
                        n -= k; break
        if n>=30:
            for d,valor in DECENAS.items():
                if n>=valor:
                    res.append(d); n-=valor; break
            if n>0: res.append("y")
        if 0<n<30:
            for u,valor in UNIDADES.items():
                if valor==n:
                    res.append(u); n=0; break
        return " ".join(res)
    partes = []
    for bloque,valpal in [(1_000_000_000,"mil millones"),(1_000_000,"millones"),(1000,"mil")]:
        if n>=bloque:
            cuantas = n//bloque; n%=bloque
            if bloque==1_000_000 and cuantas==1: partes.append("un millon")
            else: partes.append(_sub(cuantas)+" "+valpal)
    if n>0: partes.append(_sub(n))
    return " ".join([p for p in partes if p]).replace("  "," ").strip()

def valores_consistentes(valor_letras: str, valor_numeros: str|int) -> bool:
    try:
        n_str = re.sub(r"[^\d]", "", str(valor_numeros))
        if not n_str: return False
        n = int(n_str)
        parsed = letras_a_int(valor_letras)
        return n == parsed
    except:
        return False

# =========================
# IA: extracción (3 pasadas, JSON forzado)
# =========================
def limpiar_json_bloque(texto: str) -> str:
    try:
        i0 = texto.index("{"); i1 = texto.rindex("}")+1
        return texto[i0:i1]
    except:
        return "{}"

def extraer_json_vision(im_bytes: bytes, prompt: str):
    def call(msg_extra=""):
        resp = openai.chat.completions.create(
            model="gpt-4o",
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content":"Eres perito en pagarés colombianos. Devuelve SIEMPRE JSON estricto con las claves exactas indicadas."},
                {"role":"user","content":prompt + msg_extra},
                {"role":"user","content":[{"type":"image_url","image_url":{"url":f"data:image/png;base64,{base64.b64encode(im_bytes).decode()}","detail":"high"}}]}
            ],
            max_tokens=1200
        )
        return json.loads(limpiar_json_bloque(resp.choices[0].message.content))
    o1 = call("\nModo: PRECISO. Usa solo lo que leas.")
    o2 = call("\nModo: INTERPRETATIVO. Si algo es dudoso, infiere por formato (años recientes, etc.).")
    o3 = call("\nModo: VERIFICACION. Relee y corrige inconsistencias; si puedes incluye campo 'confianza_por_campo' 0.0–1.0.")
    return o1, o2, o3

# =========================
# Normalización, validación y consenso
# =========================
MAP = {
    "Número de pagaré":"Numero de Pagare","NumeroDePagare":"Numero de Pagare","Numero de Pagare":"Numero de Pagare",
    "Ciudad":"Ciudad",
    "Día (en letras)":"Dia (en letras)","DiaEnLetras":"Dia (en letras)","Dia (en letras)":"Dia (en letras)",
    "Día (en número)":"Dia (en numero)","DiaEnNumero":"Dia (en numero)","Dia (en numero)":"Dia (en numero)",
    "Mes":"Mes",
    "Año (en letras)":"Año (en letras)","AnoEnLetras":"Año (en letras)",
    "Año (en número)":"Año (en numero)","AnoEnNumero":"Año (en numero)",
    "Valor en letras":"Valor en letras","ValorEnLetras":"Valor en letras",
    "Valor en números":"Valor en numeros","ValorEnNumeros":"Valor en numeros",
    "Nombre del deudor":"Nombre del Deudor","Nombre del Deudor":"Nombre del Deudor",
    "Cédula o número de identificación":"Cedula","Cedula o numero de identificacion":"Cedula","Cedula":"Cedula",
    "Dirección":"Direccion","Direccion":"Direccion",
    "Teléfono":"Telefono","Telefono":"Telefono",
    "Fecha de firma":"Fecha de Firma","Fecha de Firma":"Fecha de Firma"
}
def normaliza_claves(d):
    out={}
    for k,v in d.items():
        k2 = MAP.get(k,k).strip()
        out[k2] = v.strip() if isinstance(v,str) else v
    return out

def valida_y_arregla_basico(d):
    # Cédula
    if "Cedula" in d:
        ced = re.sub(r"\D","",str(d["Cedula"]))
        d["Cedula"] = ced if 6<=len(ced)<=10 else ""
    # Teléfono
    if "Telefono" in d:
        tel = re.sub(r"\D","",str(d["Telefono"]))
        d["Telefono"] = tel if len(tel)==10 and tel.startswith("3") else ""
    # Año (en numero) en rango razonable
    if "Año (en numero)" in d:
        yn = re.sub(r"\D","",str(d["Año (en numero)"]))
        if yn: 
            y = int(yn)
            if not (2020<=y<=2026): d["Año (en numero)"] = ""
        else:
            d["Año (en numero)"] = ""
    # Fecha formato
    if "Fecha de Firma" in d:
        d["Fecha de Firma"] = str(d["Fecha de Firma"]).replace("/","-")
    # Tildes frecuentes
    for k in list(d.keys()):
        if isinstance(d[k],str):
            d[k] = d[k].replace("Monteria","Montería")
    return d

def consenso_campo(v1,v2,v3):
    s = [str(v).strip() for v in (v1,v2,v3) if str(v).strip()!=""]
    if not s: return ""
    for v in s:
        if s.count(v)>=2: return v
    return max(s,key=len)

def consenso_dict(a,b,c):
    keys = set(a.keys())|set(b.keys())|set(c.keys())
    out={}
    for k in keys:
        out[k]=consenso_campo(a.get(k,""),b.get(k,""),c.get(k,""))
    return out

def score_coherencia(d):
    score=0; alerts=[]
    nom = d.get("Nombre del Deudor","")
    if re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]{6,60}", nom): score+=2
    else: alerts.append("Nombre dudoso")
    if re.fullmatch(r"\d{6,10}", d.get("Cedula","")): score+=3
    else: alerts.append("Cédula inválida")
    if d.get("Valor en letras") and d.get("Valor en numeros"):
        if valores_consistentes(d["Valor en letras"], d["Valor en numeros"]):
            score+=4
        else:
            alerts.append("Valor letras ≠ números")
    else:
        alerts.append("Valor faltante")
    if re.fullmatch(r"\d{4}", d.get("Año (en numero)","")): score+=1
    else: alerts.append("Año (en número) inválido")
    return score, alerts

# =========================
# UI: carga
# =========================
if "pagares_data" not in st.session_state:
    st.session_state.pagares_data = []

st.header("1) Carga del pagaré")
modo = st.radio("Tipo de archivo:", ["📄 PDF","📸 Imágenes"])

cabecera_bytes = None
manuscrita_bytes = None

if modo=="📄 PDF":
    up = st.file_uploader("Sube el PDF", type=["pdf"])
    if up:
        try:
            cab, man, thumbs = pdf_primera_y_ultima_a_png(up.read())
            col1,col2 = st.columns(2)
            col1.image(thumbs[0], caption="Cabecera")
            col2.image(thumbs[1], caption="Parte manuscrita")
            cabecera_bytes = mejorar_imagen(cab)
            manuscrita_bytes = mejorar_imagen(man)
        except Exception as e:
            st.error(f"Error con PDF: {e}")
else:
    cab = st.file_uploader("Imagen — Cabecera", type=["png","jpg","jpeg"])
    man = st.file_uploader("Imagen — Parte manuscrita", type=["png","jpg","jpeg"])
    if cab and man:
        col1,col2 = st.columns(2)
        col1.image(cab, caption="Cabecera")
        col2.image(man, caption="Parte manuscrita")
        cabecera_bytes = mejorar_imagen(cab.read())
        manuscrita_bytes = mejorar_imagen(man.read())

# =========================
# Extracción y validación
# =========================
if cabecera_bytes and manuscrita_bytes:
    st.divider()
    st.header("2) Extracción automática + validación crítica")

    if st.button("🚀 Ejecutar extracción IA"):
        prompt_cab = (
            "Extrae en JSON las claves EXACTAS: "
            '{"Numero de Pagare":"","Ciudad":"","Dia (en letras)":"","Dia (en numero)":"","Mes":"",'
            '"Año (en letras)":"","Año (en numero)":"","Valor en letras":"","Valor en numeros":""}'
            " — Solo JSON."
        )
        prompt_man = (
            "Extrae en JSON las claves EXACTAS: "
            '{"Nombre del Deudor":"","Cedula":"","Direccion":"","Ciudad":"","Telefono":"","Fecha de Firma":""}'
            " — Solo JSON."
        )

        c1,c2,c3 = extraer_json_vision(cabecera_bytes, prompt_cab)
        m1,m2,m3 = extraer_json_vision(manuscrita_bytes, prompt_man)

        c1,c2,c3 = [valida_y_arregla_basico(normaliza_claves(x)) for x in (c1,c2,c3)]
        m1,m2,m3 = [valida_y_arregla_basico(normaliza_claves(x)) for x in (m1,m2,m3)]

        cab_final = consenso_dict(c1,c2,c3)
        man_final = consenso_dict(m1,m2,m3)
        data_auto = {**cab_final, **man_final}

        ok_valor = valores_consistentes(data_auto.get("Valor en letras",""), data_auto.get("Valor en numeros",""))
        score, alerts = score_coherencia(data_auto)

        st.subheader("🧾 Resultado automático (consenso)")
        st.json(data_auto)
        st.write(f"**Score de coherencia:** {score}/10")
        if alerts:
            st.warning("⚠️ Alertas: " + " | ".join(alerts))
        if not ok_valor:
            st.error("❌ El valor en letras NO coincide con el valor en números. Revisión obligatoria.")

        # =========================
        # Edición manual + trazabilidad
        # =========================
        st.divider()
        st.header("3) Corrección manual (trazabilidad obligatoria en críticos)")

        data_edit = {}
        cambios = []
        cols = list(data_auto.keys())
        orden = [*CRITICAL_FIELDS] + [c for c in cols if c not in CRITICAL_FIELDS]

        for campo in orden:
            val_inicial = str(data_auto.get(campo,""))
            nuevo = st.text_input(campo, val_inicial)
            data_edit[campo] = nuevo
            if nuevo.strip() != val_inicial.strip():
                cambios.append(campo)

        def criticos_ok(d):
            ok = True; msgs=[]
            if not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s]{6,60}", d.get("Nombre del Deudor","")):
                ok=False; msgs.append("Nombre inválido")
            if not re.fullmatch(r"\d{6,10}", re.sub(r"\D","", d.get("Cedula",""))):
                ok=False; msgs.append("Cédula inválida")
            if not valores_consistentes(d.get("Valor en letras",""), d.get("Valor en numeros","")):
                ok=False; msgs.append("Valor letras ≠ números")
            return ok, msgs

        if st.button("💾 Guardar registro"):
            data_edit["Cedula"] = re.sub(r"\D","", data_edit.get("Cedula",""))
            data_edit["Telefono"] = re.sub(r"\D","", data_edit.get("Telefono",""))
            data_edit["Fecha de Firma"] = str(data_edit.get("Fecha de Firma","")).replace("/","-")

            ok, msgs = criticos_ok(data_edit)
            if not ok:
                st.error("No se puede guardar: " + " | ".join(msgs))
            else:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                registro = data_edit.copy()
                registro["Campos Modificados"] = ", ".join(cambios) if cambios else "Sin cambios"
                registro["Editado Manualmente"] = "Sí" if cambios else "No"
                registro["Alertas"] = " | ".join(alerts) if alerts else ""
                registro["Score Coherencia"] = score
                registro["Origen"] = "Consenso (3 pasadas)"
                registro["Timestamp"] = timestamp
                st.session_state.pagares_data.append(registro)
                st.success(f"✅ Registro guardado. Cambios manuales: {len(cambios)} campo(s).")

# =========================
# Exportación
# =========================
if st.session_state.pagares_data:
    st.divider()
    st.header("4) Exportar resultados")
    df = pd.DataFrame(st.session_state.pagares_data)
    st.dataframe(df, use_container_width=True)

    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    st.download_button(
        "⬇️ Descargar Excel con trazabilidad",
        buf,
        "pagares_extraidos.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
