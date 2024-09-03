import csv

import requests

def generar_csv_sordos():

    with open('territorios.csv', 'w', newline='') as file:
        writer = csv.writer(file, lineterminator='\n', quoting=csv.QUOTE_NONE, quotechar=None, delimiter=',', escapechar='\\')
        field = ['WKT', 'nombre', 'descripción', 'detalles_direccion', 'estudio']

        writer.writerow(field)

        data = {'congregacion_id': 1}
        sordos =  requests.post('http://territorios-django:8000/api/sordos/para_kml_y_gpx/', json = data, timeout=60).json()

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

        data = {'congregacion_id': 1}
        territorios =  requests.post('http://territorios-django:8000/api/territorios/congregacion/', json = data, timeout=60).json()

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

    # After everythin, open the file and if the row starts with "POLYGON" then it is a territory, replace \ with nothing
    with open('territorios.csv', 'r') as file:
        lines = file.readlines()
        for i in range(len(lines)):
            if lines[i].startswith("\"POLYGON"):
                lines[i] = lines[i].replace("\\,", ", ")
        
    with open('territorios.csv', 'w') as file:
        file.writelines(lines)
    
    return "territorios.csv"

if __name__ == '__main__':
    generar_csv_sordos()
