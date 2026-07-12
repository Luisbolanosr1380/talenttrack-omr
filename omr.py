import cv2
import numpy as np
import json
import os

def load_template_config(path="template_config.json"):
    """Carga la configuración de coordenadas de la plantilla."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def detect_corners(image):
    """
    Detecta los 4 marcadores de esquina negros en el documento.
    Retorna los puntos ordenados: [TL, TR, BR, BL] en las coordenadas de la imagen original.
    """
    H, W = image.shape[:2]
    
    # Redimensionar temporalmente para un procesamiento de contornos uniforme
    target_width = 1000
    scale = target_width / float(W)
    resized = cv2.resize(image, (target_width, int(H * scale)))
    h_res, w_res = resized.shape[:2]
    
    # Preprocesamiento
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Binarización adaptativa: el papel blanco se vuelve negro (0) y los marcadores se vuelven blancos (255)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 15, 7
    )
    
    # Encontrar contornos
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        # Filtrar por área razonable de los marcadores en la resolución normalizada
        # Un marcador de 20x20 en ancho 612 escala a ~32x32 = 1024 px en ancho 1000
        if area < 150 or area > 10000:
            continue
            
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
        
        # Obtener caja delimitadora
        x, y, w_box, h_box = cv2.boundingRect(contour)
        aspect_ratio = float(w_box) / h_box
        
        # Comprobar que sea aproximadamente cuadrado
        if 0.7 <= aspect_ratio <= 1.4:
            # Calcular solidez (relación de área del contorno sobre el área del cuadro delimitador)
            solidity = area / float(w_box * h_box)
            if solidity > 0.7:
                # Calcular centro del marcador
                cx = x + w_box / 2.0
                cy = y + h_box / 2.0
                candidates.append((cx, cy, contour))
                
    # Si tenemos menos de 4 candidatos, no podemos realizar la homografía
    if len(candidates) < 4:
        raise ValueError(
            f"Solo se detectaron {len(candidates)} marcadores de esquina de los 4 requeridos. "
            "Asegúrese de que toda la hoja sea visible, tenga buena iluminación y un fondo contrastante."
        )
        
    # Identificar cuáles candidatos corresponden a cada esquina del papel
    # Distancias a las 4 esquinas de la imagen normalizada
    # TL: (0, 0), TR: (w_res, 0), BL: (0, h_res), BR: (w_res, h_res)
    corners_mapping = {}
    
    # Para cada esquina de la imagen, buscamos el candidato más cercano
    def get_closest(target_x, target_y):
        best_cand = None
        best_dist = float('inf')
        for cand in candidates:
            cx, cy, _ = cand
            dist = (cx - target_x) ** 2 + (cy - target_y) ** 2
            if dist < best_dist:
                best_dist = dist
                best_cand = cand
        return best_cand

    tl_cand = get_closest(0, 0)
    tr_cand = get_closest(w_res, 0)
    bl_cand = get_closest(0, h_res)
    br_cand = get_closest(w_res, h_res)
    
    # Verificar que los candidatos sean distintos
    detected_set = {id(c[-1]) for c in [tl_cand, tr_cand, bl_cand, br_cand] if c is not None}
    if len(detected_set) < 4:
        raise ValueError(
            "No se pudieron resolver los 4 marcadores de esquina independientes. "
            "Verifique que la hoja no esté muy doblada o recortada."
        )
        
    # Mapear los centros encontrados y reescalarlos a las coordenadas de la imagen original
    res = []
    for cand in [tl_cand, tr_cand, br_cand, bl_cand]: # Orden estándar: TL, TR, BR, BL
        cx, cy, _ = cand
        orig_x = cx / scale
        orig_y = cy / scale
        res.append([orig_x, orig_y])
        
    return np.float32(res)

def process_omr_sheet(image_path, config_path="template_config.json"):
    """
    Procesa una imagen de hoja de respuestas.
    Alinea la perspectiva, detecta las marcas de las burbujas, calcula confianza 
    y genera una imagen marcada con los resultados.
    """
    # Cargar configuración
    config = load_template_config(config_path)
    w_tpl = config["page_width"]
    h_tpl = config["page_height"]
    
    # Leer imagen
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"No se pudo cargar la imagen desde la ruta: {image_path}")
        
    # 1. Detección de esquinas
    src_pts = detect_corners(img)
    
    # 2. Corrección de Perspectiva (Warp)
    # Puntos destino definidos en la configuración de la plantilla (OpenCV space)
    dst_pts = np.float32([
        config["corners"]["TL"],
        config["corners"]["TR"],
        config["corners"]["BR"],
        config["corners"]["BL"]
    ])
    
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img, M, (w_tpl, h_tpl))
    
    # 3. Preprocesamiento de la imagen alineada
    warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    
    # Umbralización adaptativa local para robustez ante sombras
    warped_thresh = cv2.adaptiveThreshold(
        warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 5
    )
    
    # Crear imagen para anotaciones visuales
    annotated = warped.copy()
    
    respuestas_detectadas = {}
    detalles_analisis = {}
    
    # 4. Evaluación de casillas (burbujas)
    for q in config["preguntas"]:
        q_id = q["id"]
        opciones = q["opciones"]
        
        opciones_valores = []
        
        for opt in opciones:
            idx = opt["indice"]
            text_opt = opt["texto"]
            cx, cy = opt["x"], opt["y"]
            radius = opt["radius"]
            
            # Crear una máscara circular de análisis de radio 4 (interno al radio 7 de la plantilla)
            # Esto evita capturar los bordes impresos del círculo en caso de desalineamiento menor
            mask = np.zeros(warped_thresh.shape, dtype=np.uint8)
            cv2.circle(mask, (cx, cy), 4, 255, -1)
            
            # Calcular métricas dentro de la burbuja
            mean_val = cv2.mean(warped_thresh, mask=mask)[0]
            fill_ratio = mean_val / 255.0
            
            mean_gray = cv2.mean(warped_gray, mask=mask)[0]
            
            opciones_valores.append({
                "indice": idx,
                "texto": text_opt,
                "x": cx,
                "y": cy,
                "fill_ratio": fill_ratio,
                "mean_gray": mean_gray
            })
            
        # Determinar cuál está marcado en base al fill_ratio y mean_gray
        # Ordenar de más oscuro a más claro (mayor fill_ratio es más marcado)
        opciones_valores.sort(key=lambda x: x["fill_ratio"], reverse=True)
        
        darkest = opciones_valores[0]
        second_darkest = opciones_valores[1] if len(opciones_valores) > 1 else None
        
        # Umbral para considerar que una casilla está definitivamente marcada
        THRESHOLD_FILL = 0.45
        THRESHOLD_GRAY = 140 # Grayscale de 0 (negro) a 255 (blanco)
        
        is_marked = darkest["fill_ratio"] > THRESHOLD_FILL or darkest["mean_gray"] < THRESHOLD_GRAY
        
        # Lógica de Confianza y Selección
        warning = None
        confidence = "Alta"
        detected_idx = None
        detected_text = ""
        
        if not is_marked:
            # Caso 1: Ninguna casilla marcada
            detected_idx = None
            detected_text = "Sin respuesta"
            confidence = "Baja"
            warning = "Sin marca"
        else:
            # Caso 2: Al menos una casilla marcada
            # Verificar si hay doble marca
            if second_darkest and (second_darkest["fill_ratio"] > THRESHOLD_FILL or second_darkest["mean_gray"] < THRESHOLD_GRAY):
                detected_idx = darkest["indice"]
                detected_text = darkest["texto"]
                confidence = "Baja"
                warning = "Doble marca"
            else:
                # Caso 3: Marca única limpia
                # Evaluar si la marca es débil
                if darkest["fill_ratio"] < 0.55 and darkest["mean_gray"] > 120:
                    confidence = "Baja"
                    warning = "Marca débil"
                
                detected_idx = darkest["indice"]
                detected_text = darkest["texto"]
                
        respuestas_detectadas[str(q_id)] = detected_text
        detalles_analisis[str(q_id)] = {
            "opciones": opciones_valores,
            "confidence": confidence,
            "warning": warning,
            "selected_idx": detected_idx
        }
        
        # 5. Anotaciones Visuales en la imagen de salida
        for opt in opciones_valores:
            cx, cy = opt["x"], opt["y"]
            idx = opt["indice"]
            
            # Dibujar marcas según detección
            if detected_idx is not None and idx == detected_idx:
                if confidence == "Alta":
                    # Marca correcta en verde
                    cv2.circle(annotated, (cx, cy), radius + 4, (0, 180, 0), 2)
                else:
                    # Advertencia (doble marca o marca débil) en amarillo/naranja
                    cv2.circle(annotated, (cx, cy), radius + 4, (0, 180, 255), 2)
            else:
                # No marcada: círculo rojo muy fino para indicar área revisada
                cv2.circle(annotated, (cx, cy), radius + 4, (0, 0, 150), 1)
                
            # Si hay doble marca, marcar el segundo también con advertencia
            if warning == "Doble marca" and second_darkest and idx == second_darkest["indice"]:
                cv2.circle(annotated, (cx, cy), radius + 4, (0, 180, 255), 2)
                
    return warped, annotated, respuestas_detectadas, detalles_analisis
