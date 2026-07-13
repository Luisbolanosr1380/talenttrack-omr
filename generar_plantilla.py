import json
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

def generar():
    archivo_pdf = "plantilla_omr.pdf"
    archivo_json = "template_config.json"
    
    # Dimensiones Carta (612 x 792 puntos)
    w, h = LETTER
    
    c = canvas.Canvas(archivo_pdf, pagesize=LETTER)
    
    # 1. Dibujar marcadores de esquina (cuadrados negros de 20x20)
    margin = 50
    size = 20
    
    c.setFillColorRGB(0, 0, 0)
    # Esquina Superior Izquierda (TL)
    c.rect(margin, h - margin - size, size, size, fill=1)
    # Esquina Superior Derecha (TR)
    c.rect(w - margin - size, h - margin - size, size, size, fill=1)
    # Esquina Inferior Izquierda (BL)
    c.rect(margin, margin, size, size, fill=1)
    # Esquina Inferior Derecha (BR)
    c.rect(w - margin - size, margin, size, size, fill=1)
    
    # 2. Dibujar Encabezado e Instrucciones
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 80, "TALENTTRACK OMR - REGISTRO DE CANDIDATO")
    
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 100, "Instrucciones: Rellene firmemente con bolígrafo negro o azul oscuro dentro de las casillas correspondientes.")
    c.drawCentredString(w / 2, h - 112, "Evite tachaduras y no doble la hoja para garantizar una correcta lectura digital.")
    
    # 3. Campos de información del Candidato (Visual)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(70, h - 135, "No. Formulario: _________________")
    c.drawString(240, h - 135, "Nombre: _____________________________________")
    c.drawString(450, h - 135, "Teléfono: _______________")
    
    # Dibujar línea divisoria sutil
    c.setStrokeColorRGB(0.8, 0.8, 0.8)
    c.setLineWidth(1)
    c.line(70, h - 145, w - 70, h - 145)
    
    # Restaurar color de texto negro
    c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    
    # Definición de las 13 preguntas
    preguntas_data = [
        {
            "id": 1,
            "text": "¿Vive en Amatitlán o en un municipio cercano?",
            "options": ["Sí", "No"]
        },
        {
            "id": 2,
            "text": "¿Tiene disponibilidad para trabajar en Amatitlán?",
            "options": ["Sí", "No"]
        },
        {
            "id": 3,
            "text": "¿Tiene disponibilidad para trabajar en turnos rotativos?",
            "options": ["Sí", "No"]
        },
        {
            "id": 4,
            "text": "¿Puede trabajar en horario nocturno?",
            "options": ["Sí", "No"]
        },
        {
            "id": 5,
            "text": "¿Cuenta con transporte propio o una forma segura de movilizarse?",
            "options": ["Sí", "No"]
        },
        {
            "id": 6,
            "text": "¿Tiene experiencia en producción, bodega, despacho o planta?",
            "options": ["Sí", "No"]
        },
        {
            "id": 7,
            "text": "¿Cuánto tiempo de experiencia tiene?",
            "options": ["Sin experiencia", "Menos de 1 año", "De 1 a 2 años", "Más de 2 años"]
        },
        {
            "id": 8,
            "text": "¿Cuál es su nivel educativo?",
            "options": ["Primaria", "Básicos", "Diversificado", "Universidad"]
        },
        {
            "id": 9,
            "text": "¿Cuenta con licencia de conducir?",
            "options": ["No", "Tipo B", "Tipo A"]
        },
        {
            "id": 10,
            "text": "¿Ha trabajado anteriormente en CMI?",
            "options": ["Sí", "No"]
        },
        {
            "id": 11,
            "text": "¿Tiene familiares trabajando actualmente en CMI?",
            "options": ["Sí", "No"]
        },
        {
            "id": 12,
            "text": "¿Cuándo podría iniciar?",
            "options": ["Inmediatamente", "En 1 semana", "En 15 días", "Más de 15 días"]
        },
        {
            "id": 13,
            "text": "¿Autoriza que TalentTrack le contacte para otras plazas?",
            "options": ["Sí", "No"]
        }
    ]
    
    config = {
        "page_width": int(w),
        "page_height": int(h),
        "corners": {
            "TL": [margin + (size / 2), margin + (size / 2)],             # OpenCV coordinates are calculated below
            "TR": [w - margin - (size / 2), margin + (size / 2)],
            "BL": [margin + (size / 2), h - margin - (size / 2)],
            "BR": [w - margin - (size / 2), h - margin - (size / 2)]
        },
        "preguntas": []
    }
    
    # Posicionar preguntas
    start_y = 610  # y en ReportLab
    step_y = 35
    radius = 7
    
    for i, q in enumerate(preguntas_data):
        y_text = start_y - (i * step_y)
        y_options = y_text - 14
        
        # Dibujar pregunta
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(70, y_text, f"{q['id']}. {q['text']}")
        
        q_config = {
            "id": q["id"],
            "text": q["text"],
            "opciones": []
        }
        
        # Posicionar opciones horizontalmente
        c.setFont("Helvetica", 9)
        num_opts = len(q["options"])
        
        if num_opts == 2:
            xs = [90, 190]
        elif num_opts == 3:
            xs = [90, 190, 290]
        else:
            xs = [90, 210, 330, 450]
            
        for idx, opt_text in enumerate(q["options"]):
            x_circle = xs[idx]
            
            # Dibujar burbuja OMR (Círculo)
            c.setLineWidth(1.5)
            c.circle(x_circle, y_options, radius, stroke=1, fill=0)
            
            # Dibujar etiqueta de la opción
            c.drawString(x_circle + 15, y_options - 3, opt_text)
            
            # Guardar coordenadas de la burbuja en espacio OpenCV
            # ReportLab y=0 es abajo. OpenCV y=0 es arriba.
            x_cv = x_circle
            y_cv = h - y_options
            
            q_config["opciones"].append({
                "indice": idx,
                "texto": opt_text,
                "x": int(x_cv),
                "y": int(y_cv),
                "radius": radius
            })
            
        config["preguntas"].append(q_config)
        
    c.save()
    
    # Escribir archivo de configuración JSON
    with open(archivo_json, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        
    print(f"Éxito: Se generó '{archivo_pdf}' y '{archivo_json}'.")

if __name__ == "__main__":
    generar()
