# TalentTrack OMR - MVP

Este es un MVP (Producto Mínimo Viable) de un lector óptico de marcas (OMR) diseñado para ejecutarse localmente y ser accedido desde un teléfono móvil en ferias de empleo. El sistema procesa hojas de respuesta físicas de 10 preguntas impresas en tamaño carta, detecta las marcas mediante visión artificial (OpenCV) y almacena los resultados localmente en un archivo CSV.

## Requisitos del Sistema

* **Sistema Operativo:** macOS, Windows o Linux.
* **Intérprete:** Python 3.13 (disponible como `python3.13`).
* **Bibliotecas principales:** Streamlit, OpenCV, NumPy, Pandas, Pillow, ReportLab.

---

## Estructura de Archivos

El proyecto está organizado de la siguiente manera:

```
talenttrack-omr/
├── app.py                  # Servidor de la aplicación web Streamlit
├── omr.py                  # Motor de procesamiento de imagen OMR (OpenCV)
├── generar_plantilla.py    # Script que genera el PDF imprimible y las coordenadas JSON
├── template_config.json    # Mapa de coordenadas generadas dinámicamente
├── plantilla_omr.pdf       # Hoja tamaño carta imprimible para los candidatos
├── test_omr.py             # Script de validación local mediante simulación
├── requirements.txt        # Dependencias de paquetes Python
├── README.md               # Este manual de uso
└── data/
    ├── respuestas.csv      # Base de datos local en formato CSV
    ├── originales/         # Fotos originales subidas (guardadas con marca de tiempo)
    └── procesadas/         # Hojas corregidas visualmente con círculos verdes/amarillos
```

---

## Instrucciones de Configuración e Instalación

### 1. Clonar o acceder a la carpeta del proyecto
Asegúrese de estar ubicado en la carpeta del proyecto:
```bash
cd /Users/luisbolanos/Desktop/talenttrack-omr
```

### 2. Configurar el Entorno Virtual
Cree un entorno virtual de Python 3.13 e instale las dependencias:
```bash
# Crear entorno virtual
python3.13 -m venv .venv

# Activar el entorno
source .venv/bin/activate

# Instalar dependencias requeridas
pip install -r requirements.txt
```

### 3. Generar la Plantilla y Configuración
El proyecto ya incluye la plantilla generada, pero si desea reconstruirla o cambiar coordenadas, ejecute:
```bash
python generar_plantilla.py
```
Esto creará el documento PDF imprimible `plantilla_omr.pdf` y exportará el archivo de coordenadas `template_config.json`.

---

## Cómo Ejecutar la Aplicación

Inicie el servidor web Streamlit:
```bash
streamlit run app.py
```

### Acceso desde su Teléfono Móvil
Al iniciar la aplicación, Streamlit mostrará dos direcciones en la terminal:
1. **Local URL:** `http://localhost:8501` (para acceder desde la computadora donde corre el servidor).
2. **Network URL:** `http://<IP_LOCAL>:8501` (ejemplo: `http://192.168.1.15:8501`).

**Para abrir la aplicación en su teléfono móvil:**
1. Conecte su teléfono y la computadora a la **misma red Wi-Fi**.
2. Abra el navegador web en su teléfono.
3. Ingrese la dirección **Network URL** mostrada en la terminal.

---

## Flujo de Trabajo en la Feria de Empleo

### Paso 1: Rellenar la Hoja
El candidato recibe la hoja impresa `plantilla_omr.pdf` y marca sus respuestas rellenando los círculos correspondientes con un bolígrafo negro o azul oscuro.

### Paso 2: Datos del Candidato
En la aplicación en su teléfono, ingrese:
* Número de formulario.
* Nombre completo del candidato.
* Número de teléfono.

### Paso 3: Fotografía e Inspección
1. Seleccione la opción de **Cámara** en la aplicación y tome una foto del formulario. Asegúrese de que:
   * La hoja esté bien iluminada y plana.
   * Los **4 marcadores negros de las esquinas** estén completamente visibles dentro de la foto.
2. Presione **Procesar Hoja OMR**.
3. El motor alineará la perspectiva de la imagen de manera automática.

### Paso 4: Revisión y Guardado
1. La aplicación le presentará una imagen con círculos de colores:
   * **Círculo Verde:** Casilla detectada con éxito.
   * **Círculo Naranja/Amarillo:** Advertencia (ej. marcas débiles, doble marca o sin marca).
2. Justo debajo de las imágenes, se pre-seleccionará la opción que el sistema leyó. Si hay alguna discrepancia o advertencia, corríjala manualmente usando los desplegables interactivos.
3. Haga clic en **Guardar Registro en Base de Datos**. El registro se agregará a `data/respuestas.csv` y las imágenes se guardarán para auditorías.

---

## Exportar Datos
En la barra lateral (sidebar) de la aplicación, o en la pestaña **Registro Histórico**, encontrará el botón **Descargar Respuestas (CSV)** para descargar la base de datos completa a su dispositivo en formato Excel/CSV.
