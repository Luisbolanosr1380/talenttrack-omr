import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER

def generar():
    archivo_pdf = "plantilla_omr.pdf"
    archivo_json = "template_config.json"
    
    # Configuración de página (Carta: 612x792 puntos)
    w, h = LETTER
    c = canvas.Canvas(archivo_pdf, pagesize=LETTER)
    
    config = {"preguntas": []}
    
    # Dibujar marcadores de esquina (cuadrados negros)
    margin = 50
    size = 20
    c.setFillColorRGB(0, 0, 0)
    c.rect(margin, h-margin-size, size, size, fill=1) # Top Left
    c.rect(w-margin-size, h-margin-size, size, size, fill=1) # Top Right
    c.rect(margin, margin, size, size, fill=1) # Bottom Left
    c.rect(w-margin-size, margin, size, fill=1, fill=1) # Bottom Right
    
    # Generar 10 preguntas con 4 opciones (A, B, C, D)
    start_y = h - 150
    for i in range(10):
        y = start_y - (i * 40)
        config["preguntas"].append({"id": i + 1, "opciones": []})
        c.drawString(100, y, f"Pregunta {i+1}")
        
        for j in range(4):
            x = 200 + (j * 50)
            c.circle(x, y, 10, stroke=1, fill=0)
            config["preguntas"][i]["opciones"].append({"letra": chr(65+j), "x": x, "y": y})
            
    c.save()
    with open(archivo_json, 'w') as f:
        json.dump(config, f, indent=4)
    print("Plantilla y JSON generados correctamente.")

if __name__ == "__main__":
    generar()