import streamlit as st
import pandas as pd
import io

# =========================
# ⚙️ CONFIGURACIÓN INICIAL
# =========================
st.set_page_config(page_title="💼 Extractor de Pagarés", layout="wide")

st.title("💼 EXTRACTOR DE PAGARÉS - CONTACTO SOLUTIONS")

# =========================
# 🧭 MENÚ PRINCIPAL
# =========================
menu = st.sidebar.radio(
    "Menú principal",
    ["🏠 Inicio", "📤 Cargar pagarés", "📊 Histórico / Excel"],
    index=2  # por defecto abre el histórico
)

# =========================
# 🏠 SECCIÓN INICIO (Opcional)
# =========================
if menu == "🏠 Inicio":
    st.markdown("""
    ### 👋 Bienvenido al sistema Extractor de Pagarés
    Carga, analiza y consolida los datos de los pagarés de forma automática con IA.
    Usa el menú lateral para navegar entre las secciones.
    """)

# =========================
# 📤 SECCIÓN DE CARGA (Ejemplo)
# =========================
elif menu == "📤 Cargar pagarés":
    st.info("Aquí iría tu módulo actual de carga de archivos y extracción con IA.")

# =========================
# 📊 HISTÓRICO / EXCEL (CON REPORTERÍA SUPERIOR)
# =========================
elif menu == "📊 Histórico / Excel":
    if st.session_state.get("pagares_data"):
        # Convertir la lista de pagarés a DataFrame
        df_hist = pd.DataFrame(st.session_state["pagares_data"])

        # =========================
        # 📈 ENCABEZADO DE REPORTERÍA
        # =========================
        total_pagares = len(df_hist)

        # Contar pagarés modificados (según campo disponible)
        if "modified" in df_hist.columns:
            modificados = int(df_hist["modified"].astype(bool).sum())
        elif "status" in df_hist.columns:
            modificados = int(df_hist["status"].astype(str).str.lower().str.contains("modific").sum())
        else:
            modificados = 0

        # Calcular promedio de score o match_score
        if "match_score" in df_hist.columns:
            promedio_score = pd.to_numeric(df_hist["match_score"], errors="coerce").mean()
        elif "score" in df_hist.columns:
            promedio_score = pd.to_numeric(df_hist["score"], errors="coerce").mean()
        else:
            promedio_score = None

        # Convertir score de 0–1 a porcentaje si aplica
        if promedio_score and promedio_score <= 1:
            promedio_score *= 100

        # Calcular porcentaje de modificados
        porcentaje_modificados = (modificados / total_pagares * 100) if total_pagares else 0

        # Mostrar resumen superior con métricas
        st.markdown("---")
        st.subheader("📈 Resumen de extracción")

        col1, col2, col3 = st.columns(3)
        col1.metric("🧾 Pagarés procesados", total_pagares)
        col2.metric("✏️ Pagarés modificados", f"{modificados}", f"{porcentaje_modificados:.1f}%")
        if promedio_score is not None:
            col3.metric("✅ Efectividad promedio", f"{promedio_score:.1f}%", help="Promedio de coincidencia OCR / campos extraídos")
        else:
            col3.metric("✅ Efectividad promedio", "N/A")

        st.markdown("---")

        # =========================
        # 📜 TABLA DE HISTÓRICO
        # =========================
        st.subheader("📜 Histórico de pagarés procesados")
        st.dataframe(df_hist, use_container_width=True, height=440)

        # =========================
        # 💾 DESCARGA DE EXCEL
        # =========================
        excel_io = io.BytesIO()
        df_hist.to_excel(excel_io, index=False, engine="openpyxl")
        excel_io.seek(0)
        st.download_button(
            "⬇️ Descargar Excel",
            data=excel_io,
            file_name="resultados_pagares.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("Aún no hay registros guardados.")

# =========================
# 🧾 FORMULARIO INFERIOR DE EDICIÓN
# =========================
def render_editor():
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">✏️ Editar registro seleccionado</div>', unsafe_allow_html=True)

    if "selected_index" not in st.session_state or st.session_state.selected_index is None:
        st.warning("Selecciona un pagaré en la tabla para editarlo.")
        return

    idx = st.session_state.selected_index
    df_hist = pd.DataFrame(st.session_state.pagares_data)
    pagaré = df_hist.iloc[idx].to_dict()

    with st.form("editar_pagares_form"):
        st.write("Modifica los datos del pagaré y guarda los cambios.")
        for key, value in pagaré.items():
            pagaré[key] = st.text_input(key, value if pd.notna(value) else "")
        submitted = st.form_submit_button("💾 Guardar cambios")
        if submitted:
            df_hist.iloc[idx] = pagaré
            st.session_state.pagares_data = df_hist.to_dict(orient="records")
            st.success("✅ Registro actualizado correctamente.")

