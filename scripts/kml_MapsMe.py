from datetime import datetime
import locale
import xml.etree.ElementTree as ET
from io import BytesIO

import requests
import defusedxml.ElementTree


def obtener_fecha_titulo():
    fecha = datetime.now().date()
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    fecha_formateada = fecha.strftime("%d de %B del %Y")
    return fecha_formateada

def generar_kml_sordos():

    NOMBRE_KML = f"Sordos Sangolqui - {obtener_fecha_titulo()}"
    DESCRIPCION = "Territorios de Señas Sangolquí"

    root = ET.Element("kml")
    root.set("xmlns", "http://www.opengis.net/kml/2.2")

    document = ET.SubElement(root, "Document")

    estilos = b'''\
    <Styles>
    <Style id="placemark-red">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-red.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-blue">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-blue.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-purple">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-purple.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-yellow">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-yellow.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-pink">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-pink.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-brown">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-brown.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-green">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-green.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-orange">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-orange.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-deeppurple">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-deeppurple.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-lightblue">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-lightblue.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-cyan">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-cyan.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-teal">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-teal.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-lime">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-lime.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-deeporange">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-deeporange.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-gray">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-gray.png</href>
        </Icon>
        </IconStyle>
    </Style>
    <Style id="placemark-bluegray">
        <IconStyle>
        <Icon>
            <href>http://maps.me/placemarks/placemark-bluegray.png</href>
        </Icon>
        </IconStyle>
    </Style>
    </Styles>\
    '''

    estilos = defusedxml.ElementTree.parse(BytesIO(estilos))
    estilos_root = estilos.getroot()

    for estilo in estilos_root.iter('Style'):
        document.append(estilo)

    name = ET.SubElement(document, "name")
    name.text = NOMBRE_KML

    description = ET.SubElement(document, "description")
    description.text = DESCRIPCION

    visibility = ET.SubElement(document, "visibility")
    visibility.text = "1"

    # Extended Data
    extended_data = ET.SubElement(document, "ExtendedData")
    extended_data.set("xmlns:mwm", "http://maps.me/")
    mwm_name = ET.SubElement(extended_data, "mwm:name")
    mwm_lang = ET.SubElement(mwm_name, "mwm:lang")
    mwm_lang.set("code", "default")
    mwm_lang.text = NOMBRE_KML
    mwm_annotation = ET.SubElement(extended_data, "mwm:annotation")
    mwm_description = ET.SubElement(extended_data, "mwm:description")
    mwmw_lang_2 = ET.SubElement(mwm_description, "mwm:lang")
    mwmw_lang_2.set("code", "default")
    mwmw_lang_2.text = DESCRIPCION
    mwm_last_modified = ET.SubElement(extended_data, "mwm:lastModified")
    mwm_last_modified.text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    mwm_access_Rules = ET.SubElement(extended_data, "mwm:accessRules")
    mwm_access_Rules.text = "Local"


    data = {'congregacion_id': 1}
    sordos =  requests.post('http://territorios-django:8000/api/sordos/para_kml_y_gpx/', json = data).json()

    for sordo in sordos:
        placemark = ET.SubElement(document, "Placemark")
        
        name = ET.SubElement(placemark, "name")
        name.text = sordo['codigo'] + ' - ' + sordo['nombre'] + ' - ' + str(sordo['anio_nacimiento'])
        
        description = ET.SubElement(placemark, "description")
        description.text = f"{sordo['direccion']} -- {sordo['detalles_direccion']}"
        
        styleUrl = ET.SubElement(placemark, "styleUrl")
        if sordo['publicador_estudio']:
            styleUrl.text = "#placemark-lime"
        else:
            styleUrl.text = "#placemark-red"
        
        point = ET.SubElement(placemark, "Point")
        coordinates = ET.SubElement(point, "coordinates")
        coordinates.text = f"{sordo['gps_longitud']},{sordo['gps_latitud']}"
        
        #extended_data = ET.SubElement(placemark, "ExtendedData")
        #data = ET.SubElement(extended_data, "Data")
        #data.set("name", "Territorio")
        #value = ET.SubElement(data, "value")
        #value.text = f"{sordo['territorio_numero']} - {sordo['territorio_nombre']}"

    data = {'congregacion_id': 1}
    territorios =  requests.post('http://territorios-django:8000/api/territorios/congregacion/', json = data).json()

    for territorio in territorios:

        if territorio['numero'] == 0:
                continue
        
        placemark = ET.SubElement(document, "Placemark")
        name = ET.SubElement(placemark, "name")
        name.text = f"{territorio['numero']} - {territorio['nombre']}"
        line_string = ET.SubElement(placemark, "LineString")
        tessellate = ET.SubElement(line_string, "tessellate")
        tessellate.text = "1"
        coordinates = ET.SubElement(line_string, "coordinates")

        coordinates_text = "\n"
        ya_primero = False
        primero = ""

        for sordo in sordos:
            if sordo['territorio_numero'] == territorio['numero']:
                coordinates_text += f"{sordo['gps_longitud']},{sordo['gps_latitud']},0\n"
                if not ya_primero:
                    primero = f"{sordo['gps_longitud']},{sordo['gps_latitud']},0\n"
                    ya_primero = True
        
        coordinates_text += primero
        coordinates.text = coordinates_text

    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    tree.write("territorios.kml", xml_declaration=True,encoding='utf-8', method="xml")

    return "territorios.kml"

if __name__ == '__main__':
    generar_kml_sordos()
