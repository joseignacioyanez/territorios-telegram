from datetime import datetime
from io import BytesIO
import locale
import xml.etree.ElementTree as ET
from services import get_sordos_para_exportar_de_congregacion, get_territorios_de_congregacion

import requests

def obtener_fecha_titulo():
    fecha = datetime.now().date()
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    fecha_formateada = fecha.strftime("%d de %B del %Y")
    return fecha_formateada

def generar_gpx_sordos(congregacion_id):

    NOMBRE_GPX = f"Sordos - {obtener_fecha_titulo()}"

    root = ET.Element("gpx")
    root.set("version", "1.1")
    root.set("creator", "OsmAnd Maps 4.7.3 (4.7.3.10)")
    root.set("xmlns", "http://www.topografix.com/GPX/1/1")
    root.set("xmlns:osmand", "https://osmand.net")
    root.set("xmlns:gpxtpx", "http://www.garmin.com/xmlschemas/TrackPointExtension/v1")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("xsi:schemaLocation", "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd")

    metadata = ET.SubElement(root, "metadata")

    name = ET.SubElement(metadata, "name")
    name.text = NOMBRE_GPX

    time = ET.SubElement(metadata, "time")
    time.text = str(datetime.now().date())
                    
    # Puntos
    sordos = get_sordos_para_exportar_de_congregacion(congregacion_id)

    for sordo in sordos:
        wpt = ET.SubElement(root, "wpt")
        wpt.set("lat", str(sordo['gps_latitud']))
        wpt.set("lon", str(sordo['gps_longitud']))

        ele = ET.SubElement(wpt, "ele")
        name_gpx = ET.SubElement(wpt, "name")
        name_gpx.text = f"{sordo['codigo']} - {sordo['nombre']} - {sordo['anio_nacimiento']}"
        desc = ET.SubElement(wpt, "desc")
        desc.text = f"{sordo['direccion']} -- {sordo['detalles_direccion']}"
        type = ET.SubElement(wpt, "type")
        type.text = "Sordos"
        extensions = ET.SubElement(wpt, "extensions")
        osmand_icon = ET.SubElement(extensions, "osmand:osm")
        osmand_icon.text = "special_marker"
        osmand_background = ET.SubElement(extensions, "osmand:background")
        osmand_background.text = "circle"
        osmand_color = ET.SubElement(extensions, "osmand:color")
        try:
            if sordo['territorio_nombre'] == "Estudios":
                osmand_color.text = "#ff86b953"
            else:
                osmand_color.text = "#ffff0000"
        except KeyError:
            osmand_color.text = "#ffff0000"
        osmand_ammenity_subtype = ET.SubElement(extensions, "osmand:amenity_subtype")
        osmand_ammenity_subtype.text = "user_defined_other_postcode"
        osmand_ammenity_type = ET.SubElement(extensions, "osmand:amenity_type")
        osmand_ammenity_type.text = "user_defined_other"

    territorios =  get_territorios_de_congregacion(congregacion_id)
    
    for territorio in territorios:

        if territorio['numero'] == 0:
                continue

        trk = ET.SubElement(root, "trk")

        name = f"{territorio['numero']} - {territorio['nombre']}"
        name_gpx = ET.SubElement(trk, "name")
        name_gpx.text = name

        trkseg = ET.SubElement(trk, "trkseg")

        ya_primero = False
        primero = {}

        for sordo in sordos:
            if sordo.get('territorio_numero') == territorio['numero']:
                trkpt = ET.SubElement(trkseg, "trkpt")
                trkpt.set("lat", str(sordo['gps_latitud']))
                trkpt.set("lon", str(sordo['gps_longitud']))
                ele = ET.SubElement(trkpt, "ele")
                ele.text = "0.0"

                if not ya_primero:
                    primero = {"longitud":sordo['gps_longitud'], "latitud":sordo['gps_latitud']}
                    ya_primero = True

        last_trkpt = ET.SubElement(trkseg, "trkpt")
        last_trkpt.set("lat", str(primero.get('latitud')))
        last_trkpt.set("lon", str(primero.get('longitud')))
        ele = ET.SubElement(last_trkpt, "ele")
        ele.text = "0.0"


    # extensions = b'''\
    # <ext>
    # <extensions>
    #         <osmand:show_arrows>false</osmand:show_arrows>
    #         <osmand:show_start_finish>true</osmand:show_start_finish>
    #         <osmand:vertical_exaggeration_scale>1.000000</osmand:vertical_exaggeration_scale>
    #         <osmand:line_3d_visualization_by_type>none</osmand:line_3d_visualization_by_type>
    #         <osmand:line_3d_visualization_wall_color_type>upward_gradient</osmand:line_3d_visualization_wall_color_type>
    #         <osmand:line_3d_visualization_position_type>top</osmand:line_3d_visualization_position_type>
    #         <osmand:split_interval>0</osmand:split_interval>
    #         <osmand:split_type>no_split</osmand:split_type>
    #         <osmand:points_groups>
    #             <osmand:group color="#ffffffff" background="" name="" icon=""/>
    #         </osmand:points_groups>
    #     </extensions>
    #     <extensions>
    #     </extensions>
    # </ext>\
    # '''
    # extensions = ET.parse(BytesIO(extensions))
    # extensions_root = extensions.getroot()
    # for extension in extensions_root.iter('extensions'):
    #     root.append(extension)


    # Hola

    extensions = ET.SubElement(root, "extensions")
    osmand_show_arrows = ET.SubElement(extensions, "osmand:show_arrows")
    osmand_show_arrows.text = "false"   
    osmand_show_start_finish = ET.SubElement(extensions, "osmand:show_start_finish")
    osmand_show_start_finish.text = "false"
    osmand_vertical_exaggeration_scale = ET.SubElement(extensions, "osmand:vertical_exaggeration_scale")
    osmand_vertical_exaggeration_scale.text = "1.000000"
    osmand_line_3d_visualization_by_type = ET.SubElement(extensions, "osmand:line_3d_visualization_by_type")
    osmand_line_3d_visualization_by_type.text = "none"
    osmand_line_3d_visualization_wall_color_type = ET.SubElement(extensions, "osmand:line_3d_visualization_wall_color_type")
    osmand_line_3d_visualization_wall_color_type.text = "upward_gradient"
    osmand_line_3d_visualization_position_type = ET.SubElement(extensions, "osmand:line_3d_visualization_position_type")
    osmand_line_3d_visualization_position_type.text = "top"
    osmand_split_interval = ET.SubElement(extensions, "osmand:split_interval")
    osmand_split_interval.text = "0"
    osmand_split_type = ET.SubElement(extensions, "osmand:split_type")
    osmand_split_type.text = "no_split"
    osmand_color = ET.SubElement(extensions, "osmand:color")    
    osmand_color.text = "#aa4e4eff"
    osmand_width = ET.SubElement(extensions, "osmand:width")
    osmand_width.text = "9"
    points_groups = ET.SubElement(extensions, "osmand:points_groups")
    group = ET.SubElement(points_groups, "osmand:group")
    group.set("background", "circle")
    group.set("name", NOMBRE_GPX)
    group.set("color", "#ffff0000")
    group.set("icon", "special_marker")
    
    
    # En lugar de escribir a un archivo, escribimos a un BytesIO
    output_buffer = BytesIO()
    tree = ET.ElementTree(root)
    ET.indent(tree, space="\t", level=0)
    
    # Escribir el XML al buffer en memoria
    tree.write(output_buffer, xml_declaration=True, encoding='utf-8', method="xml")
    
    # Volver al inicio del buffer
    output_buffer.seek(0)
    
    # Devolver el buffer en lugar del nombre del archivo
    return output_buffer

if __name__ == '__main__':
    generar_gpx_sordos()