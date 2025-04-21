import csv
from io import BytesIO, StringIO
from services import get_sordos_para_exportar_de_congregacion, get_territorios_de_congregacion

def generar_csv_sordos(congregacion_id):
    # Usamos StringIO para manipular el texto del CSV
    csv_output = StringIO()
    
    writer = csv.writer(csv_output, lineterminator='\n', quoting=csv.QUOTE_NONE, quotechar=None, delimiter=',', escapechar='\\')
    
    field = ['WKT', 'nombre', 'descripción', 'detalles_direccion', 'estudio']
    writer.writerow(field)

    sordos = get_sordos_para_exportar_de_congregacion(congregacion_id)

    for sordo in sordos:
        WKT = f"\"POINT ({sordo['gps_longitud']} {sordo['gps_latitud']})\""
        if sordo['territorio_nombre'] == "Estudios":
            estudio = "Estudio"
        else:
            estudio = "No Estudio"

        nombre = f"{sordo['codigo']} - {sordo['nombre']} - {sordo['anio_nacimiento']}".replace(',', ';')
        direccion = f"{sordo['direccion']}".replace(',', ';')
        detalles_direccion = f"{sordo['detalles_direccion']}".replace(',', ';')

        writer.writerow([WKT, nombre, direccion, detalles_direccion, estudio])

    territorios = get_territorios_de_congregacion(congregacion_id)

    for territorio in territorios:
        if territorio['numero'] == 0:
            continue

        nombre = f"{territorio['numero']} - {territorio['nombre']}"
        poligono = "\"POLYGON (("

        ya_primero = False
        primero = ""

        for sordo in sordos:
            if sordo['territorio_numero'] == territorio['numero']:
                poligono += f"{sordo['gps_longitud']} {sordo['gps_latitud']},"
                if not ya_primero:
                    primero = f"{sordo['gps_longitud']} {sordo['gps_latitud']}"
                    ya_primero = True
        
        poligono = poligono + primero + "))\""

        writer.writerow([poligono, nombre, '', '', 'Territorio'])

    # Reemplazar \, con , en las líneas que comienzan con "POLYGON"
    csv_content = csv_output.getvalue()
    lines = csv_content.split('\n')
    for i in range(len(lines)):
        if lines[i].startswith("\"POLYGON"):
            lines[i] = lines[i].replace("\\,", ", ")
    
    # Reconstruir el contenido CSV
    modified_content = '\n'.join(lines)
    
    # Convertir a BytesIO para enviar como documento
    byte_output = BytesIO(modified_content.encode('utf-8'))
    return byte_output

if __name__ == '__main__':
    generar_csv_sordos()