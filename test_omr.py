import cv2
import numpy as np
import json
import os
import omr

def crear_imagen_prueba():
    # Cargar coordenadas
    with open("template_config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    w_tpl = config["page_width"]
    h_tpl = config["page_height"]
    
    # Crear un lienzo en blanco (papel blanco)
    page = np.ones((h_tpl, w_tpl, 3), dtype=np.uint8) * 255
    
    # 1. Dibujar marcadores de esquina negros (rectángulos de 20x20)
    # Centros definidos en el JSON: TL:[60,60], TR:[552,60], BL:[60,732], BR:[552,732]
    # En OpenCV los rectángulos se dibujan dando (x1, y1) y (x2, y2)
    # TL center: 60,60 -> rect [50, 50] a [70, 70]
    cv2.rectangle(page, (50, 50), (70, 70), (0, 0, 0), -1)
    # TR center: 552,60 -> rect [542, 50] a [562, 70]
    cv2.rectangle(page, (542, 50), (562, 70), (0, 0, 0), -1)
    # BL center: 60,732 -> rect [50, 722] a [70, 742]
    cv2.rectangle(page, (50, 722), (70, 742), (0, 0, 0), -1)
    # BR center: 552,732 -> rect [542, 722] a [562, 742]
    cv2.rectangle(page, (542, 722), (562, 742), (0, 0, 0), -1)
    
    # 2. Respuestas esperadas que simularemos
    # Q1: Sí (0), Q2: No (1), Q3: Sí (0), Q4: No (1), Q5: Sí (0)
    # Q6: No (1), Q7: De 1 a 2 años (2), Q8: Diversificado (2), Q9: Inmediatamente (0), Q10: Sí (0)
    respuestas_simuladas = {
        1: 0,
        2: 1,
        3: 0,
        4: 1,
        5: 0,
        6: 1,
        7: 2,
        8: 2,
        9: 1,  # Tipo B (Licencia)
        10: 1, # No (Trabajado CMI)
        11: 1, # No (Familiares CMI)
        12: 0, # Inmediatamente (Inicio)
        13: 0  # Sí (Autorización contactar)
    }
    
    # 3. Dibujar las burbujas
    for q in config["preguntas"]:
        q_id = q["id"]
        opciones = q["opciones"]
        target_idx = respuestas_simuladas[q_id]
        
        for opt in opciones:
            cx, cy = opt["x"], opt["y"]
            r = opt["radius"]
            idx = opt["indice"]
            
            # Dibujar contorno del círculo
            cv2.circle(page, (cx, cy), r, (0, 0, 0), 2)
            
            # Dibujar la marca rellena si coincide con nuestra respuesta simulada
            if idx == target_idx:
                # Simular marca de bolígrafo (relleno negro sólido)
                cv2.circle(page, (cx, cy), 5, (20, 20, 20), -1)
                
    # 4. Colocar la hoja en un fondo más grande y deformarla para simular una foto de teléfono
    # Lienzo de fondo (color madera/mesa gris-marrón)
    canvas_w, canvas_h = 1000, 1200
    photo = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 180
    
    # Dibujar algunas texturas de "mesa" (líneas tenues)
    for i in range(0, canvas_h, 80):
        cv2.line(photo, (0, i), (canvas_w, i), (160, 160, 160), 1)
        
    # Puntos de la hoja original
    src_pts = np.float32([
        [0, 0],
        [w_tpl, 0],
        [w_tpl, h_tpl],
        [0, h_tpl]
    ])
    
    # Puntos deformados en la foto simulada (rotación y deformación de perspectiva)
    dst_pts = np.float32([
        [150, 180],    # TL
        [820, 130],    # TR
        [880, 1050],   # BR
        [80, 1080]     # BL
    ])
    
    # Proyectar la hoja sobre la foto
    H_mat = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped_page = cv2.warpPerspective(page, H_mat, (canvas_w, canvas_h), borderValue=(180, 180, 180))
    
    # Mezclar la hoja sobre el fondo (donde warped_page no es gris de fondo)
    mask = (warped_page != 180).any(axis=2)
    photo[mask] = warped_page[mask]
    
    # Añadir un poco de ruido gaussiano para simular grano de cámara
    noise = np.random.normal(0, 3, photo.shape).astype(np.int16)
    photo = np.clip(photo.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Guardar imagen simulada
    os.makedirs("data/originales", exist_ok=True)
    simulated_path = "data/originales/test_simulado.jpg"
    cv2.imwrite(simulated_path, photo)
    print(f"Imagen simulada guardada en: {simulated_path}")
    
    return simulated_path, respuestas_simuladas

def ejecutar_test():
    try:
        sim_path, expected = crear_imagen_prueba()
        
        # Ejecutar el motor OMR
        print("Procesando hoja OMR simulada...")
        warped, annotated, respuestas, detalles = omr.process_omr_sheet(sim_path)
        
        # Guardar resultado
        cv2.imwrite("data/procesadas/test_simulado_procesado.jpg", annotated)
        print("Imagen procesada guardada en: data/procesadas/test_simulado_procesado.jpg")
        
        # Validar resultados
        print("\n--- Resultados de la validación ---")
        exito_total = True
        
        # Opciones a nombres
        for q_id, opt_idx in expected.items():
            # Obtener el texto esperado
            with open("template_config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            q_conf = [q for q in config["preguntas"] if q["id"] == q_id][0]
            texto_esperado = q_conf["opciones"][opt_idx]["texto"]
            
            detectado = respuestas.get(str(q_id))
            conf = detalles.get(str(q_id), {}).get("confidence", "N/A")
            
            status = "✅ OK" if detectado == texto_esperado else "❌ ERROR"
            if detectado != texto_esperado:
                exito_total = False
                
            print(f"Pregunta {q_id}: Esperado: '{texto_esperado}' | Detectado: '{detectado}' | Confianza: {conf} | {status}")
            
        if exito_total:
            print("\n🎉 ¡TODAS LAS RESPUESTAS FUERON DETECTADAS CORRECTAMENTE CON ÉXITO!")
        else:
            print("\n❌ Hubo errores en la detección.")
            
    except Exception as e:
        print(f"Ocurrió un error en el test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    ejecutar_test()
