import datetime
import requests
from config import BASE_URL_API, BASE_URL_WEB
from utils import notify_exception
from security import safe_requests

def get_user_by_telegram_chatid(telegram_chatid):
    try:
        data = {'telegram_chatid': telegram_chatid}
        return requests.post(BASE_URL_API + 'publicadores/buscar_telegram_chatid/', json=data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_publicadores_activos_de_congregacion(congregacion_id):
    try:
        data = {'congregacion_id': congregacion_id}
        return requests.post(BASE_URL_API+'publicadores/activos_de_congregacion/', json = data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_asignaciones_pendiente_de_congregacion(congregacion_id):
    try:
        data = {'congregacion_id': congregacion_id}
        return requests.post(BASE_URL_API+'asignaciones/pendientes/', json = data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_territorios_disponibles_de_congregacion(congregacion_id):
    try:
        data = {'congregacion_id': congregacion_id}
        return requests.post(BASE_URL_API+'territorios/disponibles/', json = data).json()
    except Exception as e:
        notify_exception(e)
        raise

def registrar_asignacion_y_generar_documento(publicador, territorio, metodo_entrega, solo_generar):
    try:
        data = {
            'publicador_id': publicador,
            'territorio_id': territorio,
            'metodo_entrega': metodo_entrega,
            'solo_pdf': solo_generar
        }

        response_raw = requests.post(BASE_URL_WEB+'webTerritorios/asignar_territorio/', json = data)
        registro_exitoso = False
        if response_raw.status_code == 200:
            registro_exitoso = True
        response = response_raw.json()

        return registro_exitoso, response

    except Exception as e:
        notify_exception(e)
        raise


def get_asignaciones_entregadas_de_congregacion(congregacion_id):
    try:
        data = {'congregacion_id': congregacion_id}
        return requests.post(BASE_URL_API+'asignaciones/entregadas/', json = data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_territorios_de_congregacion(congregacion_id):
    try:
        data = {'congregacion_id': congregacion_id}
        return requests.post(BASE_URL_API+'territorios/congregacion/', json = data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_sordos_para_exportar_de_congregacion(congregacion_id):
    try:
        data = {'congregacion_id': congregacion_id}
        return requests.post(BASE_URL_API+'sordos/para_kml_y_gpx/', json = data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_asignacion(asignacion_id):
    try:
        return  safe_requests.get(BASE_URL_API + 'asignaciones/' + asignacion_id).json()
    except Exception as e:
        notify_exception(e)
        raise

def delete_asignacion(asignacion_id):
    try:
        return requests.delete(BASE_URL_API + f'asignaciones/{asignacion_id}/')
    except Exception as e:
        notify_exception(e)
        raise

def entregar_asignacion(asignacion_id):
    try:
        asignacion =  get_asignacion(asignacion_id)
        # Fecha formato ISO pero sin el tiempo, split
        asignacion['fecha_fin'] = datetime.datetime.now().isoformat().split('T')[0]
        return requests.put(BASE_URL_API + f'asignaciones/{asignacion_id}/', json=asignacion)
    except Exception as e:
        notify_exception(e)
        raise

def get_publicador(publicador_id):
    try:
        return safe_requests.get(BASE_URL_API + f'publicadores/{publicador_id}').json()
    except Exception as e:
        notify_exception(e)
        raise

def get_asignaciones_de_congregacion(congregacion_id):
    try:
        data = {'congregacion_id': congregacion_id}
        return requests.post(BASE_URL_API + 'asignaciones/reporte_congregacion/', json=data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_superadmin_from_publicador(publicador_id):
    try:
        data = {'publicador_id': publicador_id}
        return requests.post(BASE_URL_API + f'publicadores/superadmin_congregacion/', json=data).json()
    except Exception as e:
        notify_exception(e)
        raise

def get_todos_superadmin():
    try:
        return safe_requests.get(BASE_URL_API + 'publicadores/superadmin/').json()
    except Exception as e:
        notify_exception(e)
        raise
