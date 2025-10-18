from dataclasses import dataclass, field
import datetime
from collections import defaultdict
import io
from services import get_asignaciones_de_congregacion, get_territorios_de_congregacion
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime

# Clases
class Asignacion:
    def __init__(self, id, publicador_nombre, territorio_numero, territorio_nombre, fecha_asignacion, fecha_fin):
        self.id = id
        self.publicador_nombre = publicador_nombre
        # Usar los campos de texto en lugar de los campos de relación
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

# Determinar el Año Teocrático
# El año teocrático comienza en septiembre y termina en agosto del año siguiente
def get_theocratic_year(date):
    if date is None:
        return datetime.now().year
    year = date.year
    if date.month > 9:
        return year + 1
    return year

def fecha_hoy_formato_espanol():
    current_date = datetime.now()
    months = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    return current_date.strftime("%d de ") + months[current_date.month] + current_date.strftime(" %Y")

def generar_s_13_pdf_bytes(congregacion_id, template_path="scripts/S-13_S.pdf"):
    """
    Genera el formulario S-13 para una congregación específica y devuelve los bytes del PDF.
    """
    from datetime import datetime
    from collections import defaultdict

    # Obtener Territorios de Django (para los que no tienen asignaciones)
    territorios = get_territorios_de_congregacion(congregacion_id)
    territorios = {territorio['numero']: territorio['nombre'] for territorio in territorios if territorio['activo']}

    # Obtener asignaciones de Django
    data = get_asignaciones_de_congregacion(congregacion_id)

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

    anio_teocratico_data = defaultdict(dict)

    # 💡 Determina los años teocráticos a cubrir
    anios_teocraticos = sorted({a.anio_teocratico for a in asignaciones})
    anio_actual = datetime.now().year

    if anio_actual not in anios_teocraticos:
        anios_teocraticos.append(anio_actual)

    anios_teocraticos = sorted(anios_teocraticos)

    # Primero, crear un diccionario que registre los nombres de territorios por año
    nombres_historicos = defaultdict(dict)  # {año: {numero: nombre}}
    
    # Registrar nombres históricos de las asignaciones
    for asignacion in asignaciones:
        anio = asignacion.anio_teocratico
        numero = asignacion.territorio_numero
        nombre = asignacion.territorio_nombre
        if numero not in nombres_historicos[anio]:
            nombres_historicos[anio][numero] = nombre

    # 💡 Crear estructura base con territorios para cada año
    for anio in anios_teocraticos:
        # Primero, añadir territorios que tienen asignaciones en este año
        for asignacion in [a for a in asignaciones if a.anio_teocratico == anio]:
            numero = asignacion.territorio_numero
            nombre = asignacion.territorio_nombre
            if numero not in anio_teocratico_data[anio]:
                anio_teocratico_data[anio][numero] = TerritoryData(
                    number=numero,
                    name=nombre,
                    asignaciones=[]
                )
        
        # Luego, añadir todos los territorios activos que no tienen asignaciones
        for numero, nombre_actual in territorios.items():
            if numero not in anio_teocratico_data[anio]:
                # Buscar si hay nombre histórico para este año
                nombre = nombres_historicos[anio].get(numero, nombre_actual)
                # Si no hay nombre histórico para este año, buscar en años anteriores
                if nombre == nombre_actual:
                    for año_anterior in sorted([a for a in anios_teocraticos if a < anio], reverse=True):
                        if numero in nombres_historicos[año_anterior]:
                            nombre = nombres_historicos[año_anterior][numero]
                            break
                
                anio_teocratico_data[anio][numero] = TerritoryData(
                    number=numero,
                    name=nombre,
                    asignaciones=[]
                )

    # Insertar asignaciones reales
    for asignacion in asignaciones:
        anio = asignacion.anio_teocratico
        numero = asignacion.territorio_numero
        anio_teocratico_data[anio][numero].asignaciones.append(asignacion)

    # Añadir mensaje de "-" a los que no tengan asignaciones
    for year in anio_teocratico_data:
        for numero, territory_data in anio_teocratico_data[year].items():
            if not territory_data.asignaciones:
                territory_data.asignaciones.append(Asignacion(
                    id=None,
                    publicador_nombre="-",
                    territorio_numero=numero,
                    territorio_nombre=territory_data.name,
                    fecha_asignacion=None,
                    fecha_fin=None
                ))

    # Generar el PDF en memoria
    pdf_bytes = generate_multi_page_pdf_bytes(anio_teocratico_data, template_path)
    return pdf_bytes


def generate_multi_page_pdf_bytes(anio_teocratico_data, template_path):
    """
    Genera un PDF multi-página en memoria y lo devuelve como bytes.
    
    Args:
        anio_teocratico_data: Datos organizados por año teocrático
        template_path: Ruta al archivo de plantilla
        
    Returns:
        bytes: El PDF generado como bytes
    """
    # Create a PDF writer object
    pdf_writer = PyPDF2.PdfWriter()
    
    # Track last completion dates across years
    ultima_fecha_por_territorio = {}
    
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

            if numero == 0:
                # Skip territory number 0 (usually reserved for special cases)
                continue
            
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
                # lookup en el dict (o "" si no existe)
                fecha = ultima_fecha_por_territorio.get(numero, "")
                fecha_ultimo_completado_territorios.append({
                    "territorio_numero": numero,
                    "fecha_fin": fecha,
                })

            
            # Add assignments to the list
            if asignaciones:
                for i in range(0, len(asignaciones), 4):
                    chunk = asignaciones[i:i+4]
                    asignaciones_territorios.append(chunk)
            else:
                asignaciones_territorios.append([])
            
            # Record the last assignment date for next year
            # → Nuevo: solo actualizar si hubo asignaciones completadas
            completed_dates = [a.fecha_fin for a in asignaciones if a.fecha_fin]
            if completed_dates:
                # toma la más reciente de todas las completadas este año
                ultima_fecha_por_territorio[numero] = max(completed_dates)
            # si completed_dates está vacío, 
            # dejamos la que ya existía del año anterior intacta
        
        # Generate pages for this year (max 20 territories per page)
        for page_idx in range(0, len(nombres_territorios), 20):
            # Get items for this page
            page_nombres = nombres_territorios[page_idx:page_idx+20]
            page_fechas = fecha_ultimo_completado_territorios[page_idx:page_idx+20]
            page_asignaciones = asignaciones_territorios[page_idx:page_idx+20]
            # Create a complete page from scratch
            create_complete_page(pdf_writer, page_nombres, page_fechas, page_asignaciones, anio, template_path)
    
    # Write the PDF to memory buffer
    output_buffer = io.BytesIO()
    pdf_writer.write(output_buffer)
    output_buffer.seek(0)
    
    # Return the bytes
    return output_buffer.getvalue()

def create_complete_page(pdf_writer, nombres_territorios, fechas_completado, asignaciones, anio_titulo, template_path):
    # Open the template file and keep it open until we're done with it
    with open(template_path, 'rb') as template_file:
        template_reader = PyPDF2.PdfReader(template_file)
        template_page = template_reader.pages[0]
        width = template_page.mediabox.width
        height = template_page.mediabox.height
        
        # Create the overlay canvas
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(width, height))
        
        # Añadir título con tamaño explícito
        c.setFont("Helvetica-Bold", 11)
        c.drawString(150, 748, f"{anio_titulo}")
        
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
                c.drawString(74, y, f'{str(text["fecha_fin"].strftime("%d/%m/%Y"))}')
        
        # Añadir asignaciones - siempre usar tamaño 7
        for i, assignments in enumerate(asignaciones):
            y = POSICIONES[i]

            # TEST
            if len(assignments) == 0:  # Cuando no haya asignaciones
                # Añadir un mensaje de "-" en lugar de espacios vacíos
                c.setFont("Helvetica", 7)
                c.setFillGray(0.2)
                c.drawString(145, y, "-")
            else:
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
                    if asignacion.fecha_asignacion:
                        fecha_asignacion = asignacion.fecha_asignacion.strftime("%d/%m/%Y")
                        c.drawString(x, y - 15, f"{fecha_asignacion}")
                    
                    # Fecha de fin
                    c.setFont("Helvetica", 7)  # Restablecer explícitamente
                    if asignacion.fecha_fin:
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

if __name__ == '__main__':
    pdf_bytes = generar_s_13_pdf_bytes(1)
    with open("S-13_Generado.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("PDF generado y guardado como output.pdf")
