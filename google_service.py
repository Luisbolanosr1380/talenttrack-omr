import streamlit as st
import os
import json
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes necesarios para acceder a Hojas de Cálculo y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def is_google_configured():
    """Verifica si las credenciales de Google Cloud están configuradas en st.secrets."""
    try:
        return (
            "gcp_service_account" in st.secrets and
            "spreadsheet_url" in st.secrets
        )
    except:
        return False

def get_credentials():
    """Obtiene el objeto Credentials desde los secretos de Streamlit."""
    if not is_google_configured():
        raise ValueError("Google Service Account credentials not configured in Streamlit secrets.")
    
    # st.secrets["gcp_service_account"] puede ser un diccionario directamente
    info = dict(st.secrets["gcp_service_account"])
    # Reparar posibles saltos de línea en la clave privada si viene formateada incorrectamente
    if "private_key" in info and "\\n" in info["private_key"]:
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        
    return Credentials.from_service_account_info(info, scopes=SCOPES)

def get_drive_folder_id():
    """Obtiene el ID de carpeta de Google Drive configurado en los secretos."""
    try:
        return st.secrets.get("drive_folder_id", None)
    except:
        return None

def upload_to_drive(file_path, file_name):
    """
    Sube un archivo a Google Drive, le otorga permisos públicos de lectura
    y retorna la URL pública del archivo.
    """
    if not is_google_configured():
        return f"(Modo Local) {file_name}"
        
    folder_id = get_drive_folder_id()
    if not folder_id or folder_id.strip() == "" or folder_id.lower() == "none":
        # Si no se configuró carpeta de Drive, omitir subida y guardar local
        return f"Local: {file_name}"
        
    try:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)
        
        file_metadata = {
            "name": file_name,
            "parents": [folder_id]
        }
            
        media = MediaFileUpload(file_path, mimetype="image/jpeg", resumable=True)
        
        # Subir archivo
        drive_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()
        
        file_id = drive_file.get("id")
        
        # Asignar permisos públicos de lectura
        permission = {
            "type": "anyone",
            "role": "reader",
        }
        service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
        
        # Consultar la URL pública final
        updated_file = service.files().get(
            fileId=file_id,
            fields="webViewLink"
        ).execute()
        
        return updated_file.get("webViewLink")
        
    except Exception as e:
        error_msg = str(e)
        if "storageQuotaExceeded" in error_msg or "quota" in error_msg.lower():
            # Advertencia amigable sobre cuota de Cuenta de Servicio en cuentas personales de Drive
            st.warning(
                "⚠️ **Almacenamiento en Drive omitido:** Las cuentas de servicio de Google no tienen cuota "
                "de almacenamiento propia en cuentas personales de Google Drive. **Tus respuestas de texto SÍ se guardaron en Google Sheets.** "
                "Para evitar este mensaje de advertencia, puedes eliminar el campo 'drive_folder_id' de los secretos de tu aplicación en Streamlit."
            )
        else:
            st.error(f"⚠️ Error al subir imagen a Google Drive: {error_msg}")
        # Retornar valor local seguro
        return f"Local (No subido a Drive): {file_name}"

def append_to_sheet(row_dict):
    """
    Conecta a Google Sheets y añade una nueva fila con los datos del diccionario.
    Crea los encabezados si la hoja está vacía.
    """
    if not is_google_configured():
        return False
        
    try:
        creds = get_credentials()
        gc = gspread.authorize(creds)
        
        spreadsheet_url = st.secrets["spreadsheet_url"]
        sh = gc.open_by_url(spreadsheet_url)
        worksheet = sh.get_worksheet(0) # Abrir la primera pestaña
        
        # Definir el orden estándar de las columnas
        headers = [
            "formulario", "nombre", "telefono", "fecha_hora",
            "respuestas_detectadas", "respuestas_corregidas",
            "confianza", "ruta_original", "ruta_procesada"
        ]
        
        # Verificar si la hoja está vacía o le faltan encabezados estructurados
        existing_values = worksheet.get_all_values()
        is_empty_or_no_headers = (
            not existing_values or 
            not existing_values[0] or 
            existing_values[0][0] != "formulario"
        )
        if is_empty_or_no_headers:
            # Si es una hoja recién creada que suele venir con una fila vacía
            if len(existing_values) <= 1 and (not existing_values or not existing_values[0] or existing_values[0][0] == ""):
                worksheet.insert_row(headers, 1)
                try:
                    worksheet.delete_rows(2) # Eliminar la fila vacía desplazada
                except:
                    pass
            else:
                # Si tiene datos pero no la fila de encabezados, la insertamos al inicio
                worksheet.insert_row(headers, 1)
            
        # Preparar la fila en base al orden de columnas
        row_data = [row_dict.get(h, "") for h in headers]
        worksheet.append_row(row_data)
        return True
        
    except Exception as e:
        st.error(f"⚠️ Error al guardar registro en Google Sheets: {str(e)}")
        return False
