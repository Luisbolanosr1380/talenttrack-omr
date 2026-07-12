import streamlit as st
import pandas as pd
import numpy as np
import cv2
import json
import os
from datetime import datetime
from PIL import Image
import omr
import google_service

# Configuración de página
st.set_page_config(
    page_title="TalentTrack OMR - MVP",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Crear directorios de datos si no existen
os.makedirs("data/originales", exist_ok=True)
os.makedirs("data/procesadas", exist_ok=True)
CSV_PATH = "data/respuestas.csv"

# Cargar configuración de la plantilla
try:
    template_config = omr.load_template_config()
    PREGUNTAS = template_config["preguntas"]
except Exception as e:
    PREGUNTAS = []
    st.warning("⚠️ No se pudo cargar template_config.json. Ejecute primero generar_plantilla.py.")

# Estilos CSS premium (Aesthetics)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Gradiente en Título */
    .title-gradient {
        background: linear-gradient(135deg, #FF4B4B 0%, #8522e8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    /* Tarjeta de cristal (Glassmorphism) */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
    }
    
    /* Métrica */
    .metric-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        background: linear-gradient(145deg, #1e1e2f, #151522);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #333;
        margin-bottom: 20px;
    }
    
    .metric-val {
        font-size: 2rem;
        font-weight: 700;
        color: #FF4B4B;
    }
    
    .metric-lbl {
        font-size: 0.85rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)

# Título de la Aplicación
st.markdown('<div class="title-gradient">TalentTrack OMR</div>', unsafe_allow_html=True)
st.markdown("##### MVP de Escaneo de Hojas de Respuesta en Campo - Feria de Empleo 🎯")
st.write("---")

# Inicialización de historial en CSV si no existe
if not os.path.exists(CSV_PATH):
    df_empty = pd.DataFrame(columns=[
        "formulario", "nombre", "telefono", "fecha_hora", 
        "respuestas_detectadas", "respuestas_corregidas", 
        "confianza", "ruta_original", "ruta_procesada"
    ])
    df_empty.to_csv(CSV_PATH, index=False, encoding='utf-8')

# Función para cargar historial (remoto de Google Sheets o local de CSV)
def load_historical_data():
    if google_service.is_google_configured():
        try:
            creds = google_service.get_credentials()
            import gspread
            gc = gspread.authorize(creds)
            sh = gc.open_by_url(st.secrets["spreadsheet_url"])
            worksheet = sh.get_worksheet(0)
            records = worksheet.get_all_records()
            if records:
                return pd.DataFrame(records)
            else:
                return pd.DataFrame(columns=[
                    "formulario", "nombre", "telefono", "fecha_hora", 
                    "respuestas_detectadas", "respuestas_corregidas", 
                    "confianza", "ruta_original", "ruta_procesada"
                ])
        except Exception as e:
            st.sidebar.error(f"Falla al conectar Google Sheets: {e}")
            return pd.read_csv(CSV_PATH, encoding='utf-8')
    else:
        return pd.read_csv(CSV_PATH, encoding='utf-8')

# Inicialización de estados de sesión
if "last_processed" not in st.session_state:
    st.session_state.last_processed = None
if "detected_respuestas" not in st.session_state:
    st.session_state.detected_respuestas = None
if "detalles_analisis" not in st.session_state:
    st.session_state.detalles_analisis = None
if "original_path" not in st.session_state:
    st.session_state.original_path = None
if "processed_path" not in st.session_state:
    st.session_state.processed_path = None

# Sidebar - Estadísticas y Acciones
with st.sidebar:
    st.image("https://img.icons8.com/isometric/512/documents-folder.png", width=90)
    st.markdown("### TalentTrack OMR")
    st.markdown("Escaner de hojas OMR optimizado para dispositivos móviles.")
    
    # Cargar historial para estadísticas
    try:
        df_hist = load_historical_data()
        total_registros = len(df_hist)
        baja_conf = len(df_hist[df_hist["confianza"] == "Baja"]) if total_registros > 0 else 0
    except:
        total_registros = 0
        baja_conf = 0
        df_hist = pd.DataFrame()
        
    st.markdown("---")
    st.markdown("#### Métricas del Dispositivo")
    st.markdown(f"""
        <div class="metric-container">
            <div style="text-align: center;">
                <div class="metric-val">{total_registros}</div>
                <div class="metric-lbl">Guardados</div>
            </div>
            <div style="text-align: center;">
                <div class="metric-val" style="color: #FFC107;">{baja_conf}</div>
                <div class="metric-lbl">Por Revisar</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Botón rápido para descargar CSV
    if total_registros > 0:
        csv_data = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Respuestas (CSV)",
            data=csv_data,
            file_name=f"talenttrack_omr_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

# Pestañas principales
tab_escaner, tab_historial = st.tabs(["📷 Escanear Formulario", "📊 Registro Histórico"])

with tab_escaner:
    if not PREGUNTAS:
        st.error("⚠️ La aplicación no está lista. Genere la plantilla primero para configurar las coordenadas.")
    else:
        # Fila de datos del candidato
        st.markdown("### 1. Datos del Candidato")
        c1, c2, c3 = st.columns(3)
        with c1:
            form_no = st.text_input("No. de Formulario *", placeholder="Ej. 1001", key="input_form_no")
        with c2:
            candidate_name = st.text_input("Nombre Completo *", placeholder="Ej. Juan Pérez", key="input_name")
        with c3:
            candidate_phone = st.text_input("Teléfono *", placeholder="Ej. 5555-1234", key="input_phone")

        st.markdown("### 2. Captura de la Hoja de Respuestas")
        
        # Selección de entrada de imagen
        img_source = st.radio(
            "Seleccione método de captura:",
            ["Cámara de Teléfono / Dispositivo", "Subir Archivo de Imagen (Galería)"],
            horizontal=True
        )
        
        uploaded_image = None
        if img_source == "Cámara de Teléfono / Dispositivo":
            camera_img = st.camera_input("Tome una foto centrada de la hoja OMR:")
            if camera_img is not None:
                uploaded_image = camera_img
        else:
            file_img = st.file_uploader("Suba una imagen JPG o PNG:", type=["jpg", "png", "jpeg"])
            if file_img is not None:
                uploaded_image = file_img
                
        # Procesamiento al subir la imagen
        if uploaded_image is not None:
            # Botón para procesar
            if st.button("🔍 Procesar Hoja OMR", type="primary", use_container_width=True):
                if not form_no or not candidate_name or not candidate_phone:
                    st.error("⚠️ Por favor llene todos los campos de datos del candidato antes de escanear.")
                else:
                    with st.spinner("Procesando imagen y alineando perspectiva..."):
                        try:
                            # Guardar la imagen original temporalmente
                            temp_orig_path = f"data/originales/temp_{form_no}.jpg"
                            with open(temp_orig_path, "wb") as f:
                                f.write(uploaded_image.getbuffer())
                            
                            # Ejecutar OMR
                            warped, annotated, resp_detectadas, detalles = omr.process_omr_sheet(temp_orig_path)
                            
                            # Guardar la imagen procesada anotada
                            temp_proc_path = f"data/procesadas/temp_proc_{form_no}.jpg"
                            cv2.imwrite(temp_proc_path, annotated)
                            
                            # Actualizar estado de sesión
                            st.session_state.last_processed = form_no
                            st.session_state.detected_respuestas = resp_detectadas
                            st.session_state.detalles_analisis = detalles
                            st.session_state.original_path = temp_orig_path
                            st.session_state.processed_path = temp_proc_path
                            
                            st.success("✅ ¡Procesamiento completado con éxito!")
                            
                        except Exception as ex:
                            st.error(f"❌ Error al procesar la imagen: {str(ex)}")
                            st.info("💡 Asegúrese de que las 4 esquinas negras de la hoja estén completamente visibles y bien iluminadas.")
        
        # Mostrar y Corregir Respuestas Detectadas
        if st.session_state.last_processed == form_no and st.session_state.detected_respuestas is not None:
            st.markdown("---")
            st.markdown("### 3. Resultados de Detección y Corrección Manual")
            
            # Mostrar imágenes lado a lado
            col_orig, col_proc = st.columns(2)
            with col_orig:
                st.markdown("**Imagen Original Recortada (Perspectiva Alineada)**")
                # Leer y mostrar la imagen alineada
                # Nota: la función omr retorna el frame 'warped'. Vamos a guardarlo
                temp_warp_path = f"data/originales/temp_warp_{form_no}.jpg"
                # Convertimos BGR a RGB para Streamlit
                warp_rgb = cv2.cvtColor(cv2.imread(st.session_state.processed_path), cv2.COLOR_BGR2RGB)
                st.image(warp_rgb, use_container_width=True)
                
            with col_proc:
                st.markdown("**Burbujas Detectadas (Verde=OK, Naranja=Revisar)**")
                # Buscamos si hay marcas con baja confianza
                alertas_confianza = []
                for q_id, det in st.session_state.detalles_analisis.items():
                    if det["confidence"] == "Baja":
                        alertas_confianza.append(f"Pregunta {q_id}: {det['warning']}")
                
                if alertas_confianza:
                    st.warning(f"⚠️ **Se requiere revisión manual en:** {', '.join(alertas_confianza)}")
                else:
                    st.success("✨ Detección limpia. Todas las respuestas tienen alta confianza.")
            
            # Formulario de corrección manual
            st.markdown("#### Editar Respuestas")
            corrected_respuestas = {}
            
            # Dividir las 10 preguntas en dos columnas para mayor legibilidad
            col_preg1, col_preg2 = st.columns(2)
            
            for idx, q in enumerate(PREGUNTAS):
                q_id = str(q["id"])
                detected_val = st.session_state.detected_respuestas.get(q_id, "Sin respuesta")
                det = st.session_state.detalles_analisis.get(q_id, {})
                
                # Opciones disponibles en el formulario (+ Sin respuesta)
                opts = ["Sin respuesta"] + [opt["texto"] for opt in q["opciones"]]
                
                # Índice por defecto para el selectbox
                default_idx = 0
                if detected_val in opts:
                    default_idx = opts.index(detected_val)
                
                # Etiqueta decorada si requiere revisión
                label_prefix = "⚠️ " if det.get("confidence") == "Baja" else ""
                label_suffix = f" (Detectado: {detected_val})" if detected_val != "Sin respuesta" else " (No detectado)"
                label = f"{label_prefix}Pregunta {q_id}. {q['text']}{label_suffix}"
                
                # Colocar en columna 1 o 2
                target_col = col_preg1 if idx < 5 else col_preg2
                
                with target_col:
                    sel_val = st.selectbox(
                        label,
                        options=opts,
                        index=default_idx,
                        key=f"q_edit_{q_id}"
                    )
                    corrected_respuestas[q_id] = sel_val

            st.write("")
            if st.button("💾 Guardar Registro en Base de Datos", type="primary", use_container_width=True):
                # Determinar nivel de confianza general
                general_confidence = "Alta"
                for det in st.session_state.detalles_analisis.values():
                    if det["confidence"] == "Baja":
                        general_confidence = "Baja"
                        break
                
                timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                if google_service.is_google_configured():
                    with st.spinner("Subiendo imágenes a Google Drive y registrando en Google Sheets..."):
                        # Nombres de archivos únicos para Drive
                        file_name_orig = f"original_form_{form_no}_{timestamp_str}.jpg"
                        file_name_proc = f"procesada_form_{form_no}_{timestamp_str}.jpg"
                        
                        # Subir y obtener URLs
                        drive_link_orig = google_service.upload_to_drive(st.session_state.original_path, file_name_orig)
                        drive_link_proc = google_service.upload_to_drive(st.session_state.processed_path, file_name_proc)
                        
                        # Armar fila
                        new_row = {
                            "formulario": int(form_no) if form_no.isdigit() else form_no,
                            "nombre": candidate_name,
                            "telefono": candidate_phone,
                            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "respuestas_detectadas": json.dumps(st.session_state.detected_respuestas, ensure_ascii=False),
                            "respuestas_corregidas": json.dumps(corrected_respuestas, ensure_ascii=False),
                            "confianza": general_confidence,
                            "ruta_original": drive_link_orig,
                            "ruta_procesada": drive_link_proc
                        }
                        
                        # Guardar en la hoja de Google
                        success = google_service.append_to_sheet(new_row)
                        if success:
                            st.success("✅ Datos sincronizados con Google Sheets y Google Drive con éxito.")
                        else:
                            st.warning("⚠️ Error al sincronizar con la nube, los datos se guardarán localmente.")
                            
                        # También guardar localmente como caché de respaldo
                        df_existing = pd.read_csv(CSV_PATH, encoding='utf-8')
                        df_new = pd.DataFrame([new_row])
                        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                        df_combined.to_csv(CSV_PATH, index=False, encoding='utf-8')
                else:
                    # Guardar de forma local clásica
                    final_orig_path = f"data/originales/form_{form_no}_{timestamp_str}.jpg"
                    final_proc_path = f"data/procesadas/form_{form_no}_{timestamp_str}.jpg"
                    
                    os.rename(st.session_state.original_path, final_orig_path)
                    os.rename(st.session_state.processed_path, final_proc_path)
                    
                    new_row = {
                        "formulario": form_no,
                        "nombre": candidate_name,
                        "telefono": candidate_phone,
                        "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "respuestas_detectadas": json.dumps(st.session_state.detected_respuestas, ensure_ascii=False),
                        "respuestas_corregidas": json.dumps(corrected_respuestas, ensure_ascii=False),
                        "confianza": general_confidence,
                        "ruta_original": final_orig_path,
                        "ruta_procesada": final_proc_path
                    }
                    
                    df_existing = pd.read_csv(CSV_PATH, encoding='utf-8')
                    df_new = pd.DataFrame([new_row])
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined.to_csv(CSV_PATH, index=False, encoding='utf-8')
                
                # Eliminar temporales locales
                try:
                    if os.path.exists(st.session_state.original_path) and google_service.is_google_configured():
                        os.remove(st.session_state.original_path)
                    if os.path.exists(st.session_state.processed_path) and google_service.is_google_configured():
                        os.remove(st.session_state.processed_path)
                    os.remove(f"data/originales/temp_warp_{form_no}.jpg")
                except:
                    pass
                
                # Limpiar estado
                st.session_state.last_processed = None
                st.session_state.detected_respuestas = None
                st.session_state.detalles_analisis = None
                st.session_state.original_path = None
                st.session_state.processed_path = None
                
                st.balloons()
                st.success(f"🎉 Registro del Formulario {form_no} para {candidate_name} guardado correctamente.")
                st.info("La página se recargará para un nuevo escaneo.")
                st.rerun()

with tab_historial:
    st.markdown("### Historial de Candidatos Registrados")
    
    try:
        df_hist = load_historical_data()
    except Exception as ex:
        df_hist = pd.DataFrame()
        st.error(f"Error al leer base de datos: {str(ex)}")
        
    if df_hist.empty:
        st.info("Aún no se han guardado registros en esta sesión.")
    else:
        # Opciones de filtro
        search_query = st.text_input("🔍 Buscar por Nombre, Teléfono o Formulario:", "")
        
        # Aplicar filtro
        if search_query:
            df_filtered = df_hist[
                df_hist["nombre"].astype(str).str.contains(search_query, case=False) |
                df_hist["telefono"].astype(str).str.contains(search_query, case=False) |
                df_hist["formulario"].astype(str).str.contains(search_query, case=False)
            ]
        else:
            df_filtered = df_hist
            
        st.write(f"Mostrando {len(df_filtered)} de {len(df_hist)} registros.")
        
        # Formatear visualización
        display_df = df_filtered.copy()
        
        # Formatear las columnas JSON para que sean más legibles
        def format_json_resp(val):
            try:
                res_dict = json.loads(val)
                # Formato legible: Q1: Sí, Q2: No, etc.
                return ", ".join([f"P{k}: {v}" for k, v in res_dict.items()])
            except:
                return val

        display_df["respuestas_detectadas"] = display_df["respuestas_detectadas"].apply(format_json_resp)
        display_df["respuestas_corregidas"] = display_df["respuestas_corregidas"].apply(format_json_resp)
        
        # Reordenar y renombrar columnas para visualización
        display_df = display_df[[
            "formulario", "nombre", "telefono", "fecha_hora", 
            "respuestas_corregidas", "confianza"
        ]]
        
        st.dataframe(
            display_df.rename(columns={
                "formulario": "Formulario",
                "nombre": "Nombre",
                "telefono": "Teléfono",
                "fecha_hora": "Fecha/Hora",
                "respuestas_corregidas": "Respuestas Finales",
                "confianza": "Confianza"
            }),
            use_container_width=True
        )
        
        # Visualizar detalles de un registro específico
        st.markdown("#### Detalle de Registro con Imagen")
        selected_form = st.selectbox(
            "Seleccione un número de formulario para ver las hojas escaneadas:",
            options=df_filtered["formulario"].unique()
        )
        
        if selected_form:
            row = df_filtered[df_filtered["formulario"] == selected_form].iloc[-1]
            st.markdown(f"**Candidato:** {row['nombre']} | **Teléfono:** {row['telefono']} | **Fecha:** {row['fecha_hora']}")
            
            c_img1, c_img2 = st.columns(2)
            with c_img1:
                st.markdown("**Original Escaneada**")
                path_orig = row["ruta_original"]
                if str(path_orig).startswith("http"):
                    st.image(path_orig, use_container_width=True)
                elif os.path.exists(str(path_orig)):
                    st.image(path_orig, use_container_width=True)
                else:
                    st.warning("Imagen original no encontrada.")
            with c_img2:
                st.markdown("**Procesada con Marcas**")
                path_proc = row["ruta_procesada"]
                if str(path_proc).startswith("http"):
                    st.image(path_proc, use_container_width=True)
                elif os.path.exists(str(path_proc)):
                    st.image(path_proc, use_container_width=True)
                else:
                    st.warning("Imagen procesada no encontrada.")
