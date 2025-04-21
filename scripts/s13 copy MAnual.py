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

def add_page(output_writer, text_data, template="scripts/S-13_S.pdf", page_number=0, titulo=None):
    template_reader = PyPDF2.PdfReader(open(template, 'rb'))
    page_index = page_number if page_number < len(template_reader.pages) else 0
    template_page = template_reader.pages[page_index]

    c = canvas.Canvas("overlay.pdf", pagesize=[template_page.mediabox.width, template_page.mediabox.height])
    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)

    # Posiciones verticales según el número de líneas (ajusta si necesario)
    POSICIONES = [680 - (i * 30) for i in range(10)]  # 10 líneas separadas 30 pts
    for i, text in enumerate(text_data):
        x = 40 if page_number == 0 else 320  # Diferentes columnas si quieres
        y = POSICIONES[i]
        c.drawString(x, y, text)

    if titulo:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, 770, titulo)

    c.setFont("Helvetica", 8)
    c.drawString(450, 20, f"Generado el {fecha_hoy_formato_espanol()}")

    c.save()

    overlay_reader = PyPDF2.PdfReader(open("overlay.pdf", 'rb'))
    overlay_page = overlay_reader.pages[0]
    template_page.merge_page(overlay_page)

def insertar_nombres_de_territorios(output_writer, text_data, fechas_completado, template="scripts/S-13_S.pdf", page_number=0, titulo=None):
    template_reader = PyPDF2.PdfReader(open(template, 'rb'))
    page_index = page_number if page_number < len(template_reader.pages) else 0
    template_page = template_reader.pages[page_index]

    c = canvas.Canvas("overlay.pdf", pagesize=[template_page.mediabox.width, template_page.mediabox.height])
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.black)

    # Posiciones verticales según el número de líneas (ajusta si necesario)
    POSICIONES = [686 - (i * 31.25) for i in range(30)]  # 10 líneas separadas 30 pts
    for i, text in enumerate(text_data):
        x = 73
        y = POSICIONES[i]
        # Ajustar el texto para que no se salga del área
        if len(text['territorio_nombre']) > 16:
            # Si el texto termina en (cont.) recortar el exceso y poner ... antes de los parentesis
            if text['territorio_nombre'][-7:] == "(cont.)":
                text['territorio_nombre'] = text['territorio_nombre'][:11] + "..." + text['territorio_nombre'][-7:]
            else:
                # Si no termina en (cont.) recortar el exceso y poner ...
                text['territorio_nombre'] = text['territorio_nombre'][:16] + "..."
        c.drawString(x, y, f"{text['territorio_nombre']}")
        
    for i, text in enumerate(text_data):
        x = 44 # if page_number == 0 else 320
        y = POSICIONES[i] - 11
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x,y, f'{text["territorio_numero"]}')

    # Insertar fechas de ultima vez completad)
    for i, text in enumerate(fechas_completado):
        x = 74  
        y = POSICIONES[i] - 14
        c.setFont("Helvetica", 9)
        c.drawString(x,y, f'{str(text["fecha_fin"]).split(" ")[0]}')

    if titulo:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(150, 748, titulo)

    c.setFont("Helvetica",8)
    c.drawString(450, 40, f"Generado el {fecha_hoy_formato_espanol()}")

    c.save()

    overlay_reader = PyPDF2.PdfReader(open("overlay.pdf", 'rb'))
    overlay_page = overlay_reader.pages[0]
    template_page.merge_page(overlay_page)

    output_writer.add_page(template_page)

def insertar_asignaciones(output_writer, asignaciones, template="overlay.pdf", page_number=0):
    # Obtener la página existente del output_writer
    page = output_writer.pages[page_number]

    # Crear canvas sobre una página con el mismo tamaño
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=[page.mediabox.width, page.mediabox.height])
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.black)

    # Posiciones verticales según el número de líneas (ajusta si necesario)
    POSICIONES = [686 - (i * 31.25) for i in range(20)]  # 10 líneas separadas 30 pts

    for i, linea_asignaciones in enumerate(asignaciones):
        linea_actual = 0
        if not isinstance(linea_asignaciones, list):
                linea_asignaciones = [linea_asignaciones]
        
        y = POSICIONES[i] - (linea_actual * 11)

        for columna, asignacion in enumerate(linea_asignaciones):
        
            x = 145 + columna * 107

            # Nombre Publicador
            nombre = asignacion.publicador_nombre
            if len(nombre) > 25:
                nombre = nombre[:25] + "..."
            c.setFont("Helvetica", 7)
            c.setFillGray(0.2)
            c.drawString(x, y, f"{nombre}")

            # Fecha Asignacion
            fecha_asignacion = asignacion.fecha_asignacion.strftime("%d/%m/%Y")
            c.setFont("Helvetica", 7)
            c.drawString(x, y - 15, f"{fecha_asignacion}")
            
            # Fecha Fin
            fecha_fin = asignacion.fecha_fin.strftime("%d/%m/%Y") if asignacion.fecha_fin else "        —"
            c.setFont("Helvetica", 7)
            c.drawString(x+50, y - 15, f"{fecha_fin}")

        linea_actual += 1

    c.save()
    # Regresar al principio del canvas
    packet.seek(0)
    overlay_pdf = PyPDF2.PdfReader(packet)
    overlay_page = overlay_pdf.pages[0]
    # Fusionar con la página original
    page.merge_page(overlay_page)


def imprimir_anio_teocratico(output_writer, nombres_territorios, fechas_ultimo_completo, asignaciones, page_number=0):
    #  si nombres_territorios tieen mas de 20 elementos, debo hacer una nueva pagina para la linea 21, en adelante
    paginas_restantes = len(nombres_territorios)
    indice = 0
    while paginas_restantes > 0:
        # Insertar Contenidos 20 por 20
        insertar_nombres_de_territorios(output_writer, nombres_territorios[indice:indice+20], fechas_ultimo_completo[indice:indice+20], page_number=page_number, titulo=f"{nombres_territorios[indice]['anio_teocratico']}")
        insertar_asignaciones(output_writer, asignaciones[indice:indice+20], page_number=page_number)
        # Actualizar el número de páginas restantes
        paginas_restantes -= 20
        indice += 20
        page_number += 1

def generate_multi_page_pdf(anio_teocratico_data, output_file="final_output.pdf"):
    output_writer = PyPDF2.PdfWriter()

    # Para columna "Ultima vez finalizado"
    ultima_fecha_anio_anterior = []

    cantidad_de_anios = len(anio_teocratico_data)

    for anio, territorios in sorted(anio_teocratico_data.items()):
        # Ordenamos los territorios por número
        territorio_items = sorted(territorios.items())

        # Necesito estos arreglos de datos
        nombres_territorios = [] #{"territorio_numero": "", "territorio_nombre": ""}
        fecha_ultimo_completado_territorios = [] #{"territorio_numero": "", "fecha_fin": ""}
        asignaciones_territorios = []

        for numero, territorio_data in territorio_items:
            asignaciones = territorio_data.asignaciones

            # Entran 4 asignaciones por linea, determinar cuantas lineas de este territorio
            if len(asignaciones) > 4:
                cantidad_lineas_territorio = len(asignaciones) // 4
                # Si sobran asignaciones, añadir una pagina mas
                if len(asignaciones) % 4 > 0:
                    cantidad_lineas_territorio += 1
            else:
                cantidad_lineas_territorio = 1

            for i in range(cantidad_lineas_territorio):
                # Guardar el nombre del territorio y si hay mas de 4, en la siguiente linea
                nombre = territorio_data.name
                if i > 0:
                    nombre = nombre + " (cont.)"
                nombres_territorios.append({
                    "territorio_numero": numero,
                    "territorio_nombre": nombre,
                    "anio_teocratico": anio
                })
                # Insertar fecha de ultima vez completado s es que en el areglo ultima_fecha_anio_anterior hay info de este territorio
                for territorio in ultima_fecha_anio_anterior:
                    if territorio["territorio_numero"] == numero:
                        fecha_ultimo_completado_territorios.append({
                            "territorio_numero": numero,
                            "fecha_fin": territorio["fecha_fin"],
                        })
                        break

            if asignaciones:
                for i in range(0, len(asignaciones), 4):
                    asignaciones_territorios.append(asignaciones[i:i+4])
            else:
                asignaciones_territorios.append([])


            # Regresar a la ultima fecha de asignacion y registrarla
            if len(asignaciones) > 0:
                ultima_fecha_anio_anterior.append({
                    "territorio_numero": numero,
                    "territorio_nombre": nombre,
                    "fecha_fin": asignaciones[-1].fecha_fin
                })
            else:
                ultima_fecha_anio_anterior.append({
                    "territorio_numero": numero,
                    "territorio_nombre": nombre,
                    "fecha_fin": ""
                })

        # Mandar a imprimir
        # Esta funcion maneja la division por paginas
        imprimir_anio_teocratico(output_writer, nombres_territorios,  fecha_ultimo_completado_territorios, asignaciones_territorios, page_number=len(output_writer.pages))

    with open(output_file, 'wb') as f:
        output_writer.write(f)





if __name__ == '__main__':
    generar_s_13_congregacion(1)