#from services import get_asignaciones_de_congregacion, get_territorios_de_congregacion

import datetime
from collections import defaultdict
import json


# Define the class for Asignacion
class Asignacion:
    def __init__(self, id, publicador_nombre, territorio_numero, territorio_nombre, fecha_asignacion, fecha_fin):
        self.id = id
        self.publicador_nombre = publicador_nombre
        self.territorio_numero = territorio_numero
        self.territorio_nombre = territorio_nombre
        self.fecha_asignacion = fecha_asignacion
        self.fecha_fin = fecha_fin



# Function to determine the theocratic year
def get_theocratic_year(date):
    year = date.year
    if date.month < 9:  # Before September
        return year - 1
    return year


def generar_s_13_congregacion(congregacion_id):

    #asignaciones = get_asignaciones_de_congregacion(congregacion_id)
    #territorios = get_territorios_de_congregacion(congregacion_id)

    json_data = '''
[
    {
        "id": 20,
        "publicador_nombre": "Bryan Ortiz",
        "territorio_numero": 13,
        "territorio_nombre": "Conocoto A",
        "fecha_asignacion": "2024-08-10T19:11:33.829000-05:00",
        "fecha_fin": "2024-08-16T14:11:20.778200-05:00",
        "publicador": 21,
        "territorio": 13
    },
    {
        "id": 42,
        "publicador_nombre": "Mauricio Guamán",
        "territorio_numero": 14,
        "territorio_nombre": "Conocoto B",
        "fecha_asignacion": "2024-09-12T16:17:13.973513-05:00",
        "fecha_fin": null,
        "publicador": 7,
        "territorio": 14
    },
    {
        "id": 17,
        "publicador_nombre": "José Ignacio Yánez",
        "territorio_numero": 9,
        "territorio_nombre": "San Pedro A",
        "fecha_asignacion": "2024-08-01T18:49:25.759000-05:00",
        "fecha_fin": "2024-08-05T18:40:54-05:00",
        "publicador": 4,
        "territorio": 9
    },
    {
        "id": 18,
        "publicador_nombre": "Mauricio Guamán",
        "territorio_numero": 10,
        "territorio_nombre": "San Pedro B",
        "fecha_asignacion": "2024-08-01T18:50:05.572000-05:00",
        "fecha_fin": "2024-08-01T18:42:14-05:00",
        "publicador": 7,
        "territorio": 10
    },
    {
        "id": 26,
        "publicador_nombre": "José Alberto Yánez",
        "territorio_numero": 7,
        "territorio_nombre": "Santa Rosa",
        "fecha_asignacion": "2024-08-14T09:21:16.322726-05:00",
        "fecha_fin": "2024-08-14T13:43:08-05:00",
        "publicador": 1,
        "territorio": 7
    },
    {
        "id": 29,
        "publicador_nombre": "Ronald Mendoza",
        "territorio_numero": 23,
        "territorio_nombre": "Pintag",
        "fecha_asignacion": "2024-08-14T10:55:28.942087-05:00",
        "fecha_fin": "2024-08-14T18:43:56-05:00",
        "publicador": 24,
        "territorio": 23
    },
    {
        "id": 43,
        "publicador_nombre": "Mariclau de Rivera",
        "territorio_numero": 23,
        "territorio_nombre": "Pintag",
        "fecha_asignacion": "2024-08-21T13:44:33.485000-05:00",
        "fecha_fin": "2024-08-21T18:44:57.071000-05:00",
        "publicador": 12,
        "territorio": 23
    },
    {
        "id": 30,
        "publicador_nombre": "José Alberto Yánez",
        "territorio_numero": 5,
        "territorio_nombre": "Turucocha & Cotogchoa",
        "fecha_asignacion": "2024-08-15T09:23:39.404777-05:00",
        "fecha_fin": "2024-08-15T18:47:59-05:00",
        "publicador": 1,
        "territorio": 5
    },
    {
        "id": 32,
        "publicador_nombre": "José Ignacio Yánez",
        "territorio_numero": 6,
        "territorio_nombre": "Selva Alegre & San Fernando",
        "fecha_asignacion": "2024-08-15T10:37:48.750296-05:00",
        "fecha_fin": "2024-08-16T18:50:01-05:00",
        "publicador": 4,
        "territorio": 6
    },
    {
        "id": 35,
        "publicador_nombre": "Bryan Ortiz",
        "territorio_numero": 21,
        "territorio_nombre": "Peaje",
        "fecha_asignacion": "2024-08-16T09:12:01.751986-05:00",
        "fecha_fin": "2024-08-16T18:50:24-05:00",
        "publicador": 21,
        "territorio": 21
    },
    {
        "id": 36,
        "publicador_nombre": "José Ignacio Yánez",
        "territorio_numero": 15,
        "territorio_nombre": "Monserrat",
        "fecha_asignacion": "2024-08-16T09:25:58.689882-05:00",
        "fecha_fin": "2024-08-29T18:52:09-05:00",
        "publicador": 4,
        "territorio": 15
    },
    {
        "id": 44,
        "publicador_nombre": "Bryan Ortiz",
        "territorio_numero": 15,
        "territorio_nombre": "Monserrat",
        "fecha_asignacion": "2024-08-29T13:52:55.835000-05:00",
        "fecha_fin": "2024-08-29T18:53:11.133000-05:00",
        "publicador": 21,
        "territorio": 15
    },
    {
        "id": 37,
        "publicador_nombre": "David Rivera",
        "territorio_numero": 1,
        "territorio_nombre": "Amaguaña",
        "fecha_asignacion": "2024-08-17T09:21:41.621967-05:00",
        "fecha_fin": "2024-08-17T18:54:10-05:00",
        "publicador": 11,
        "territorio": 1
    },
    {
        "id": 38,
        "publicador_nombre": "Bryan Ortiz",
        "territorio_numero": 19,
        "territorio_nombre": "Guangopolo",
        "fecha_asignacion": "2024-08-17T09:23:23.795278-05:00",
        "fecha_fin": "2024-08-17T18:54:44-05:00",
        "publicador": 21,
        "territorio": 19
    },
    {
        "id": 39,
        "publicador_nombre": "José Ignacio Yánez",
        "territorio_numero": 17,
        "territorio_nombre": "Armenia A",
        "fecha_asignacion": "2024-08-17T09:30:17.606614-05:00",
        "fecha_fin": "2024-08-17T18:57:04-05:00",
        "publicador": 4,
        "territorio": 17
    },
    {
        "id": 40,
        "publicador_nombre": "Bryan Ortiz",
        "territorio_numero": 22,
        "territorio_nombre": "Alangasí",
        "fecha_asignacion": "2024-08-17T16:37:25.781262-05:00",
        "fecha_fin": "2024-08-17T18:57:34-05:00",
        "publicador": 21,
        "territorio": 22
    },
    {
        "id": 46,
        "publicador_nombre": "Camila Ortiz",
        "territorio_numero": 12,
        "territorio_nombre": "La Salle",
        "fecha_asignacion": "2024-09-26T09:15:20.698242-05:00",
        "fecha_fin": null,
        "publicador": 22,
        "territorio": 12
    },
    {
        "id": 47,
        "publicador_nombre": "Romina Yánez",
        "territorio_numero": 8,
        "territorio_nombre": "Sangolquí",
        "fecha_asignacion": "2024-09-26T09:16:19.174589-05:00",
        "fecha_fin": null,
        "publicador": 2,
        "territorio": 8
    },
    {
        "id": 48,
        "publicador_nombre": "José Alberto Yánez",
        "territorio_numero": 3,
        "territorio_nombre": "Chaupitena",
        "fecha_asignacion": "2024-09-26T09:17:39.395310-05:00",
        "fecha_fin": null,
        "publicador": 1,
        "territorio": 3
    },
    {
        "id": 49,
        "publicador_nombre": "José Alberto Yánez",
        "territorio_numero": 11,
        "territorio_nombre": "6 de Junio",
        "fecha_asignacion": "2024-10-03T09:18:01.955470-05:00",
        "fecha_fin": null,
        "publicador": 1,
        "territorio": 11
    },
    {
        "id": 50,
        "publicador_nombre": "José Alberto Yánez",
        "territorio_numero": 9,
        "territorio_nombre": "San Pedro A",
        "fecha_asignacion": "2024-10-03T10:39:06.812156-05:00",
        "fecha_fin": null,
        "publicador": 1,
        "territorio": 9
    },
    {
        "id": 51,
        "publicador_nombre": "Gaby de Guamán",
        "territorio_numero": 13,
        "territorio_nombre": "Conocoto A",
        "fecha_asignacion": "2024-10-03T16:40:18.674220-05:00",
        "fecha_fin": null,
        "publicador": 8,
        "territorio": 13
    },
    {
        "id": 52,
        "publicador_nombre": "Maritza de Guevara",
        "territorio_numero": 10,
        "territorio_nombre": "San Pedro B",
        "fecha_asignacion": "2024-10-04T09:13:50.673698-05:00",
        "fecha_fin": null,
        "publicador": 14,
        "territorio": 10
    }
]
'''

    # Load the JSON data into Python objects
    data = json.loads(json_data)

    # Initialize a dictionary to hold the data per theocratic year and territory
    theocratic_year_data = defaultdict(lambda: defaultdict(list))

    # Convert data to Asignacion objects
    asignaciones = []
    for item in data:
        asignacion = Asignacion(
            item['id'], 
            item['publicador_nombre'], 
            item['territorio_numero'],
            item['territorio_nombre'], 
            datetime.datetime.fromisoformat(item['fecha_asignacion']),
            datetime.datetime.fromisoformat(item['fecha_fin']) if item['fecha_fin'] else None
        )
        asignaciones.append(asignacion)

    # Populate theocratic year matrix
    for asignacion in asignaciones:
        theocratic_year = get_theocratic_year(asignacion.fecha_asignacion)
        theocratic_year_data[theocratic_year][asignacion.territorio_numero].append(asignacion)

    print(theocratic_year_data.get(2024).get(13))
    for asignacion in theocratic_year_data.get(2024).get(13):
        print(asignacion.publicador_nombre)

    # Access the data per theocratic year and territory
    for year, territories in theocratic_year_data.items():
        print(f"\nTheocratic Year: {year}")
        
        # Sort the territories by the territory number (the keys of the dictionary)
        for territory, assignments in sorted(territories.items()):
            if assignments:
                # Get the territorio_nombre from the first assignment
                territorio_nombre = assignments[0].territorio_nombre
                print(f"  Territory {territory} ({territorio_nombre}):")
                
                # Sort the assignments by the fecha_asignacion (start date)
                sorted_assignments = sorted(assignments, key=lambda x: x.fecha_asignacion)
                
                # Print the sorted assignments
                for asignacion in sorted_assignments:
                    print(f"    Assigned to {asignacion.publicador_nombre} from {asignacion.fecha_asignacion} to {asignacion.fecha_fin}")


if __name__ == '__main__':
    generar_s_13_congregacion(1)