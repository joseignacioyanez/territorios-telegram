from dataclasses import dataclass, field
import datetime
from collections import defaultdict
import io
from services import get_asignaciones_de_congregacion, get_territorios_de_congregacion
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime

# Define the class for Asignacion
class Asignacion:
    def __init__(self, id, publicador_nombre, territorio_numero, territorio_nombre, fecha_asignacion, fecha_fin):
        self.id = id
        self.publicador_nombre = publicador_nombre
        self.territorio_numero = territorio_numero
        self.territorio_nombre = territorio_nombre
        self.fecha_asignacion = fecha_asignacion
        self.fecha_fin = fecha_fin
        self.anio_teocratico = get_theocratic_year(self.fecha_fin) if self.fecha_fin else get_theocratic_year(self.fecha_asignacion)

    def __str__(self):
        return (f"Asignacion(ID: {self.id}, Publicador: {self.publicador_nombre}, "
                f"Territorio: {self.territorio_numero} - {self.territorio_nombre}, "
                f"Fecha Asignacion: {str(self.fecha_asignacion).split(' ')[0]}, "
                f"Fecha Fin: {str(self.fecha_fin).split(' ')[0]}, "
                f"Año Teocratico: {self.anio_teocratico} )")

@dataclass
class TerritoryData:
    number: int
    name: str
    asignaciones: list = field(default_factory=list)


# Function to determine the theocratic year
def get_theocratic_year(date):
    year = date.year
    if date.month > 9:  # Before September
        return year + 1
    return year

def generar_s_13_congregacion(congregacion_id):

    # Obtener Territorios de Django
    territorios = get_territorios_de_congregacion(congregacion_id)
    # Remove fields that are not needed
    territorios = {territorio['numero']: territorio['nombre'] for territorio in territorios if territorio['activo']}

    # Obtener asignaciones de Django
    data = get_asignaciones_de_congregacion(congregacion_id)
    # Convert data to Asignacion objects
    asignaciones = []
    for item in data:
        asignacion = Asignacion(
            item['id'], 
            item['publicador_nombre'], 
            item['territorio_numero'],
            item['territorio_nombre'], 
            datetime.fromisoformat(item['fecha_asignacion']),
            datetime.fromisoformat(item['fecha_fin']) if item['fecha_fin'] else None
        )
        asignaciones.append(asignacion)
    
    # Initialize a dictionary to hold the data per theocratic year and territory
    anio_teocratico_data = defaultdict(dict)

    # Insertar asignaciones
    for asignacion in asignaciones:
        anio = asignacion.anio_teocratico
        numero = asignacion.territorio_numero
        nombre = asignacion.territorio_nombre

        if numero not in anio_teocratico_data[anio]:
            # Crear TerritoryData si no existe
            anio_teocratico_data[anio][numero] = TerritoryData(
                number=numero,
                name=nombre,
                asignaciones=[]
            )

        # Añadir asignación
        anio_teocratico_data[anio][numero].asignaciones.append(asignacion)

    for year in anio_teocratico_data:
        for numero, nombre in territorios.items():
            if numero not in anio_teocratico_data[year]:
                anio_teocratico_data[year][numero] = TerritoryData(
                    number=numero,
                    name=nombre,
                    asignaciones=[]
                )
    # PDF
    generate_multi_page_pdf(anio_teocratico_data, output_file="S-13_S_generado.pdf")



def extraer_texto_para_pdf(anio_teocratico_data):
    textos_por_pagina = []

    for anio, territorios in sorted(anio_teocratico_data.items()):
        for numero, territorio_data in sorted(territorios.items()):
            asignaciones = territorio_data.asignaciones
            texto = f"Año: {anio} | Territorio {numero} - {territorio_data.name}"
            textos = [texto]
            for asignacion in asignaciones:
                fecha_ini = asignacion.fecha_asignacion.strftime("%d/%m/%Y")
                fecha_fin = asignacion.fecha_fin.strftime("%d/%m/%Y") if asignacion.fecha_fin else "—"
                linea = f"{asignacion.publicador_nombre}: {fecha_ini} - {fecha_fin}"
                textos.append(linea)

            # Agrupar en páginas de 5 líneas (o ajusta a tu plantilla)
            chunk_size = 5
            for i in range(0, len(textos), chunk_size):
                textos_por_pagina.append(textos[i:i+chunk_size])

    return textos_por_pagina



def fecha_hoy_formato_espanol():
    current_date = datetime.now()
    months = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    return current_date.strftime("%d de ") + months[current_date.month] + current_date.strftime(" %Y")

def generate_multi_page_pdf(anio_teocratico_data, output_file="final_output.pdf"):
    # Create a PDF writer object
    pdf_writer = PyPDF2.PdfWriter()
    
    # Track last completion dates across years
    ultima_fecha_anio_anterior = []
    
    # Process data for each year
    for anio, territorios in sorted(anio_teocratico_data.items()):
        # Prepare data for this year
        territorio_items = sorted(territorios.items())
        nombres_territorios = []
        fecha_ultimo_completado_territorios = []
        asignaciones_territorios = []
        
        # Process each territory
        for numero, territorio_data in territorio_items:
            asignaciones = territorio_data.asignaciones
            
            # Calculate number of lines needed for this territory
            if len(asignaciones) > 4:
                cantidad_lineas_territorio = (len(asignaciones) + 3) // 4
            else:
                cantidad_lineas_territorio = 1
            
            # Process each line for this territory
            for i in range(cantidad_lineas_territorio):
                # Add territory name
                nombre = territorio_data.name
                if i > 0:
                    nombre = nombre + " (cont.)"
                nombres_territorios.append({
                    "territorio_numero": numero,
                    "territorio_nombre": nombre,
                    "anio_teocratico": anio
                })
                
                # Add last completion date if available
                for territorio in ultima_fecha_anio_anterior:
                    if territorio["territorio_numero"] == numero:
                        fecha_ultimo_completado_territorios.append({
                            "territorio_numero": numero,
                            "fecha_fin": territorio["fecha_fin"],
                        })
                        break
                else:
                    # Add an empty entry if no previous completion date
                    fecha_ultimo_completado_territorios.append({
                        "territorio_numero": numero,
                        "fecha_fin": "",
                    })
            
            # Add assignments to the list
            if asignaciones:
                for i in range(0, len(asignaciones), 4):
                    chunk = asignaciones[i:i+4]
                    asignaciones_territorios.append(chunk)
            else:
                asignaciones_territorios.append([])
            
            # Record the last assignment date for next year
            if asignaciones:
                ultima_fecha_anio_anterior.append({
                    "territorio_numero": numero,
                    "territorio_nombre": territorio_data.name,
                    "fecha_fin": asignaciones[-1].fecha_fin
                })
            else:
                ultima_fecha_anio_anterior.append({
                    "territorio_numero": numero,
                    "territorio_nombre": territorio_data.name,
                    "fecha_fin": ""
                })
        
        # Generate pages for this year (max 20 territories per page)
        for page_idx in range(0, len(nombres_territorios), 20):
            # Get items for this page
            page_nombres = nombres_territorios[page_idx:page_idx+20]
            page_fechas = fecha_ultimo_completado_territorios[page_idx:page_idx+20]
            page_asignaciones = asignaciones_territorios[page_idx:page_idx+20]
            
            # Create a complete page from scratch
            create_complete_page(pdf_writer, page_nombres, page_fechas, page_asignaciones, anio)
    
    # Write the PDF to file
    with open(output_file, 'wb') as f:
        pdf_writer.write(f)

def create_complete_page(pdf_writer, nombres_territorios, fechas_completado, asignaciones, anio_titulo, template="scripts/S-13_S.pdf"):
    # Open the template file and keep it open until we're done with it
    template_file = open(template, 'rb')
    template_reader = PyPDF2.PdfReader(template_file)
    template_page = template_reader.pages[0]
    width = template_page.mediabox.width
    height = template_page.mediabox.height
    
    # Create the overlay canvas
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(width, height))
    
    # Añadir título con tamaño explícito
    c.setFont("Helvetica-Bold", 11)
    c.drawString(150, 748, f"Año Teocrático {anio_titulo}")
    
    # Añadir fecha de generación con tamaño explícito
    c.setFont("Helvetica", 8)
    c.drawString(450, 40, f"Generado el {fecha_hoy_formato_espanol()}")
    
    # Posiciones para los elementos
    POSICIONES = [686 - (i * 31.25) for i in range(30)]
    
    # Añadir nombres de territorios - siempre usar tamaño 7
    for i, text in enumerate(nombres_territorios):
        # Establecer fuente explícitamente antes de cada uso
        c.setFont("Helvetica", 7)
        y = POSICIONES[i]
        territorio_nombre = text['territorio_nombre']
        if len(territorio_nombre) > 16:
            if territorio_nombre[-7:] == "(cont.)":
                territorio_nombre = territorio_nombre[:11] + "..." + territorio_nombre[-7:]
            else:
                territorio_nombre = territorio_nombre[:16] + "..."
        c.drawString(73, y, f"{territorio_nombre}")
        
        # Número de territorio - siempre usar tamaño 18
        c.setFont("Helvetica-Bold", 18)
        c.drawString(44, y - 11, f'{text["territorio_numero"]}')
    
    # Añadir fechas de último completado - siempre usar tamaño 9
    for i, text in enumerate(fechas_completado):
        if text["fecha_fin"]:
            y = POSICIONES[i] - 14
            c.setFont("Helvetica", 9)
            c.drawString(74, y, f'{str(text["fecha_fin"]).split(" ")[0]}')
    
    # Añadir asignaciones - siempre usar tamaño 7
    for i, assignments in enumerate(asignaciones):
        y = POSICIONES[i]
        
        for j, asignacion in enumerate(assignments):
            if asignacion is None:
                continue
                
            x = 145 + j * 107
            
            # Nombre del publicador
            nombre = asignacion.publicador_nombre
            if len(nombre) > 25:
                nombre = nombre[:25] + "..."
            # Restablecer fuente explícitamente
            c.setFont("Helvetica", 7)
            c.setFillGray(0.2)
            c.drawString(x, y, f"{nombre}")
            
            # Fecha de asignación
            c.setFont("Helvetica", 7)  # Restablecer explícitamente
            fecha_asignacion = asignacion.fecha_asignacion.strftime("%d/%m/%Y")
            c.drawString(x, y - 15, f"{fecha_asignacion}")
            
            # Fecha de fin
            c.setFont("Helvetica", 7)  # Restablecer explícitamente
            fecha_fin = asignacion.fecha_fin.strftime("%d/%m/%Y") if asignacion.fecha_fin else "        —"
            c.drawString(x+50, y - 15, f"{fecha_fin}")
    
    # Guardar y cerrar el canvas
    c.save()
    packet.seek(0)
    
    # Crear un nuevo PDF de superposición
    overlay = PyPDF2.PdfReader(packet)
    
    # Fusionar la plantilla con la superposición
    template_page.merge_page(overlay.pages[0])
    
    # Añadir la página completa al PDF de salida
    pdf_writer.add_page(template_page)
    
    # Cerrar el archivo de plantilla cuando terminemos
    template_file.close()

if __name__ == '__main__':
    generar_s_13_congregacion(1)