
import datetime
import locale
import logging
import os
import time
import traceback
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
import requests
from telegram.ext import ( # type: ignore
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from scripts.csv_GoogleMyMaps import generar_csv_sordos
from scripts.kml_MapsMe import generar_kml_sordos
from scripts.gpx_Osmand import generar_gpx_sordos

# Helper Function
def formatear_fecha(fecha):
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    date_object = datetime.datetime.fromisoformat(fecha)
    fecha_formateada = date_object.strftime("%d de %B del %Y")
    return fecha_formateada

def notify_exception(e: Exception) -> None:
    # Notify the admin about the exception
    error_message = f"☢️ An exception occurred in the bot:\n\n{str(e)}\n\n{traceback.format_exc()}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={CHAT_ID_ADMIN}&text={error_message}"
    requests.get(url)



# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# Constantes
PUBLICADOR, VERIFICACION, TERRITORIO, METODO_ENVIO = range(4)
load_dotenv()
CHAT_ID_ADMIN = os.environ['TELEGRAM_ADMIN_CHAT_ID']
TELEGRAM_BOT_TOKEN=os.environ['TELEGRAM_BOT_TOKEN']
BASE_URL_API = 'http://localhost:8000/api/'

# FLUJO ASIGNAR - FASE 0
# Maneja /asignar y envia Lista de Publicadores
async def asignar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    # Determinar ID de Usuario en base al ChatID de Telegram
    try:
        data = {'telegram_chatid': update.message.chat_id}
        response =  requests.post( BASE_URL_API+'publicadores/buscar_telegram_chatid/', json = data).json()
        context.user_data['user_asignador'] = response[0] # Guardar datos del Usuario en Contexto
    except Exception as e:
        notify_exception(e)
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END
    
    grupos_usuario = context.user_data['user_asignador']['user']['groups']
    
    if any(grupo.get('name') in ['administradores', 'asignadores'] for grupo in grupos_usuario):
        # Obtener Lista de Publicadores Activos de la misma Congregación
        try:
            data = {'congregacion_id': context.user_data['user_asignador']['congregacion']}
            publicadores =  requests.post(BASE_URL_API+'publicadores/activos_de_congregacion/', json = data).json()
        except Exception as e:
            notify_exception(e)
            await update.message.reply_text("Error al obtener la lista de Publicadores. Por favor contacta a un administrador.")
            return ConversationHandler.END
    

        # Generar Keyboard con boton por cada pulicador y enviar
        reply_keyboard = []
        for publicador in publicadores:
            reply_keyboard.append([str(publicador['id']) + ' - ' + publicador['nombre']])

        nombre_usuario = context.user_data['user_asignador']['nombre']
        await update.message.reply_text(
            f"🙋🏻¡Hola {nombre_usuario}! Te ayudaré a asignar un territorio. "
            "Envía /cancelar si deseas dejar de hablar conmigo.\n\n"
            "Escoge el Publicador al que deseas asignar el territorio:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="Escoge el Publicador..."
            ),
        )
        return PUBLICADOR
    
    else:
        await update.message.reply_text("No tienes permisos para asignar territorios. Por favor contacta a un administrador.")
        return ConversationHandler.END

# FLUJO ASIGNAR - FASE 1
# Guarda el Publicador, valida que no existan otras asignaciones
async def publicador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data['user_asignado_id'] = update.message.text.split(' - ')[0]
        context.user_data['user_asignado_nombre'] = update.message.text.split(' - ')[1]
    except Exception as e:
        notify_exception(e)
        await update.message.reply_text("Error al obtener el Publicador. Por favor contacta a un administrador.")
        return ConversationHandler.END

    # Verificar si el usuario tiene Asignaciones Pendientes de entregar
    try:
        data = {'congregacion_id': context.user_data['user_asignador']['congregacion']}
        asignaciones_pendientes =  requests.post(BASE_URL_API+'asignaciones/pendientes/', json = data).json()
    except Exception as e:
        notify_exception(e)
        await update.message.reply_text("Error al obtener la lista de Asignaciones. Por favor contacta a un administrador.")
        return ConversationHandler.END
    
    tiene_asignaciones_pendientes = False
    texto_asignaciones_pendientes = ""
    for asignacion in asignaciones_pendientes:
        if str(asignacion['publicador']) == str(context.user_data['user_asignado_id']):
            tiene_asignaciones_pendientes = True
            texto_asignaciones_pendientes += "*Territorio: *" + str(asignacion['territorio_numero']) + ' - ' + asignacion['territorio_nombre'] + '\n'
            texto_asignaciones_pendientes += "*Fecha de Asignación: *" + formatear_fecha(asignacion['fecha_asignacion']) + '\n\n'

    if tiene_asignaciones_pendientes:        
        await update.message.reply_text(
            "El Publicador seleccionado tiene asignaciones pendientes: \n\n" + texto_asignaciones_pendientes + "Por favor, recuérdale al herman@ e indícame si deseas hacer la nueva asignación.",
            parse_mode='markdown',
            reply_markup=ReplyKeyboardMarkup(
                [['¡Sí, hagámoslo!'], ['No, gracias']], one_time_keyboard=True, input_field_placeholder="¿Deseas asignar igual?"
            ),
        )
    else:
        await update.message.reply_text(
            "No hay asignaciones pendientes para el Publicador seleccionado. \n ¿Deseas continuar con la asignación?",
            reply_markup=ReplyKeyboardMarkup(
                [['¡Sí, hagámoslo!'], ['No, gracias']], one_time_keyboard=True, input_field_placeholder="¿Deseas asignar?"
            ),
        )
    return VERIFICACION
    
# FLUJO ASIGNAR - FASE 2
# Maneja la respuesta de Verificacion de Asignaciones Previas y Muestra Territorios Disponibles
async def verificacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    if update.message.text == 'No, gracias':
        await update.message.reply_text("Está bien. Ten un buen día.")
        return ConversationHandler.END
    
    else:
        # Obtener Lista de Territorios Disponibles
        try:
            data = {'congregacion_id': context.user_data['user_asignador']['congregacion']}
            territorios_disponibles =  requests.post(BASE_URL_API+'territorios/disponibles/', json = data).json()

            reply_keyboard = []
            if not territorios_disponibles:
                await update.message.reply_text("No hay territorios disponibles para asignar. Por favor contacta a un administrador.")
                return ConversationHandler.END
            for territorio in territorios_disponibles:
                reply_keyboard.append([str(territorio['numero']) + ' - ' + territorio['nombre']])

            # Guardar lista de Territorios en Contexto para acceder despues
            context.user_data['territorios_disponibles'] = territorios_disponibles           

            await update.message.reply_text(
                f"Escoge el Territorio que deseas asignar al Publicador:",
                reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="Escoge el Territorio..."
                ),
            )

            return TERRITORIO
        
        except Exception as e:
            await update.message.reply_text("Error al obtener la lista de Territorios. Por favor contacta a un administrador.")
            return ConversationHandler.END

# FLUJO ASIGNAR - FASE 3
# Guarda el Territorio y pregunta por el Método de Entrega
async def territorio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    try:
        territorio_numero_deseado = update.message.text.split(' - ')[0]
        territorio_nombre_deseado = update.message.text.split(' - ')[1]
    except Exception as e:
        notify_exception(e)
        await update.message.reply_text("Error al obtener el Publicador. Por favor contacta a un administrador.")
        return ConversationHandler.END

    
    for territorio in context.user_data['territorios_disponibles']:
        if str(territorio['numero']) == territorio_numero_deseado and territorio['nombre'] == territorio_nombre_deseado:
            context.user_data['territorio_asignar_id'] = territorio['id']
            context.user_data['territorio_asignar_numero_nombre'] = str(territorio['numero']) + ' - ' + territorio['nombre']
            break

    await update.message.reply_text(
f'''
¡Buena elección! Por último... \n
¿Cómo deseas que se entregue el territorio?.
''',
            parse_mode='markdown',
            reply_markup=ReplyKeyboardMarkup(
                [['Enviar al Telegram del herman@'], 
                ['Registrar asignación y Enviarme el PDF digital por aquí'], 
                ['Registrar asignación y Enviarme el PDF para Imprimir por aquí']], one_time_keyboard=True, input_field_placeholder="¿Cómo entregar?"
            ),
        )
        
    return METODO_ENVIO

# FLUJO ASIGNAR - FASE 4
# Guarda el Método de Entrega y finaliza la asignación
async def metodo_envio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    if update.message.text == 'Enviar al Telegram del herman@':
        context.user_data['metodo_entrega'] = 'digital_publicador'
    elif update.message.text == 'Registrar asignación y Enviarme el PDF digital por aquí':
        context.user_data['metodo_entrega'] = 'digital_asignador'
    elif update.message.text == 'Registrar asignación y Enviarme el PDF para Imprimir por aquí':
        context.user_data['metodo_entrega'] = 'impreso_asignador'
    else:
        await update.message.reply_text("Error al obtener el Publicador. Por favor contacta a un administrador.")
        return ConversationHandler.END


    data = {
            'publicador_id': context.user_data['user_asignado_id'],
            'territorio_id': context.user_data['territorio_asignar_id'],
            'metodo_entrega': context.user_data['metodo_entrega'],
            'solo_pdf': False
        }
    response_raw =  requests.post('http://localhost:8000/webTerritorios/asignar_territorio/', json = data)
    response = response_raw.json()

    if response_raw.status_code == 200:
        
        user_asignador_nombre = context.user_data['user_asignador']['nombre']

        if context.user_data['metodo_entrega'] == 'digital_publicador':
                
            file = response.get('file_path')
            with open(file, 'rb') as document_file:
                if response.get('chat_id'):
                    await context.bot.send_document(chat_id=response.get('chat_id'), document=document_file, caption=f"¡Hola {context.user_data['user_asignado_nombre']}! Se te ha asignado el territorio *{response.get('territorio')}*. \n Por favor visita las direcciones, predica a cualquier persona que salga e intenta empezar estudios. Anota si no encuentras a nadie y regresa en diferentes horarios. Puedes avisarnos si cualquier detalle es incorrecto. \n ¡Muchas gracias por tu trabajo! 🎒🤟🏼", parse_mode='markdown')
                else:
                    await update.message.reply_document(document=document_file, caption='*Por favor hazle llegar el territorio al publicador porque no se registra su Telegram en el Sistema*. Gracias', parse_mode='markdown')
                # Notificar al Administrador
                await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"ℹ️ El territorio {response.get('territorio')} ha sido asignado a {context.user_data['user_asignado_nombre']} por {user_asignador_nombre} correctamente. Se ha enviado al Telegram del publicador")

        elif context.user_data['metodo_entrega'] == 'digital_asignador':
            
            file = response.get('file_path')
            with open(file, 'rb') as document_file:
                await update.message.reply_document(document=document_file, caption='*Por favor hazle llegar el territorio al publicador*. Gracias', parse_mode='markdown')
                # Notificar al Administrador
                await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"ℹ️ El territorio {response.get('territorio')} ha sido asignado a {context.user_data['user_asignado_nombre']} por {user_asignador_nombre} correctamente. Se ha descargado el PDF digital para el asignador")

        elif context.user_data['metodo_entrega'] == 'impreso_asignador':
            
            file = response.get('file_path')
            with open(file, 'rb') as document_file:
                await update.message.reply_document(document=document_file, caption='*Por favor hazle llegar el territorio al publicador*. Gracias', parse_mode='markdown')
                # Notificar al Administrador
                await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"ℹ️ El territorio {response.get('territorio')} ha sido asignado a {context.user_data['user_asignado_nombre']} por {user_asignador_nombre} correctamente. Se ha descargado el PDF para imprimir para el asignador")
        
        else:
            await update.message.reply_text("No se reconoce el método de entrega. Por favor contacta a un administrador.")
            return ConversationHandler.END
    else:
        await update.message.reply_text(f"Error al asignar el territorio. Por favor contacta a un administrador. {response.get('error')}")
        return ConversationHandler.END

    # Cleanup
    os.remove(file)
    
    await update.message.reply_text(
        f"¡Excelente! \n {context.user_data['territorio_asignar_numero_nombre']} se asignó a {context.user_data['user_asignado_nombre']}. \n ¡Gracias por tu ayuda! \n", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# FLUJO ASIGNAR - FALLBACK CANCELAR
# Cancela la conversación
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text("Adiós! Espero volvamos a conversar.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Flujo Reporte de Asignaciones Pendientes para Administradores
async def reporte_asignaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    try:
        # Determinar ID de Usuario en base al ChatID de Telegram
        data = {'telegram_chatid': update.message.chat_id}
        usuario =  requests.post(BASE_URL_API+'publicadores/buscar_telegram_chatid/', json = data).json()[0]
        context.user_data['user_data'] = usuario
        grupos_usuario = usuario['user']['groups']
        
        if any(grupo.get('name') == 'administradores' for grupo in grupos_usuario):
            # Obtener Lista de Asignaciones Pendientes
            data = {'congregacion_id': usuario['congregacion']}
            asignaciones_pendientes =  requests.post(BASE_URL_API+'asignaciones/pendientes/', json = data).json()

            # Generar Keyboard con boton por cada asignacion
            encabezado = "📋 *Asignaciones Pendientes* \n\n"
            keyboard = []
            for asignacion in asignaciones_pendientes:
                territorio = str(asignacion['territorio_numero']) + '-' + asignacion['territorio_nombre']
                publicador = asignacion['publicador_nombre']

                current_date = datetime.datetime.now().date()
                given_date = datetime.datetime.fromisoformat(asignacion['fecha_asignacion']).date()
                days_since_date = (current_date - given_date).days
                
                boton_asignacion = ""

                if days_since_date < 14:
                    boton_asignacion += f"🟢"
                elif days_since_date < 21:
                    boton_asignacion += f"🟡"
                else:
                    boton_asignacion += f"🔴"
                
                boton_asignacion += f" {days_since_date} días | {territorio} -> {publicador}"

                # Callback Data
                callback_data = ""
                # 1. Timestamp epoch
                callback_data += str(int(time.time()))
                # 2. Flag Proceso
                callback_data += ";reporte_asignacion;"
                # 3. ID Asignacion
                callback_data += f"{asignacion['id']}"


                keyboard.append([InlineKeyboardButton(boton_asignacion, callback_data=callback_data)])       

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                encabezado,
                reply_markup=reply_markup,
                parse_mode='markdown'
            )
        else:
            await update.message.reply_text("No tienes permisos para ver este reporte. Por favor contacta a un administrador.")
            return ConversationHandler.END

    except Exception as e:
        print(e)
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END

#Flujo de Reporte de Entregas Recientes para Administradores
async def reporte_entregas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        # Determinar ID de Usuario en base al ChatID de Telegram
        data = {'telegram_chatid': update.message.chat_id}
        usuario =  requests.post(BASE_URL_API+'publicadores/buscar_telegram_chatid/', json = data).json()[0]
        context.user_data['user_data'] = usuario
        grupos_usuario = usuario['user']['groups']
        
        if any(grupo.get('name') == 'administradores' for grupo in grupos_usuario):
            # Obtener Lista de Entregas Recientes
            data = {'congregacion_id': usuario['congregacion']}
            asignaciones_entregadas =  requests.post(BASE_URL_API+'asignaciones/entregadas/', json = data).json()

            # Generar Keyboard con boton por cada asignacion
            encabezado = "📋 *Asignaciones Entregadas Recientemente* \n\n"
            keyboard = []
            for asignacion in asignaciones_entregadas:
                territorio = str(asignacion['territorio_numero']) + '-' + asignacion['territorio_nombre']
                publicador = asignacion['publicador_nombre']

                current_date = datetime.datetime.now().date()
                given_date = datetime.datetime.fromisoformat(asignacion['fecha_asignacion']).date()
                days_since_date = (current_date - given_date).days
                
                boton_asignacion = "✅ "
                
                boton_asignacion += f" {days_since_date} días | {territorio} -> {publicador}"

                # Callback Data
                callback_data = ""
                # 1. Timestamp epoch
                callback_data += str(int(time.time()))
                # 2. Flag Proceso
                callback_data += ";detalle_asignacion;"
                # 3. ID Asignacion
                callback_data += f"{asignacion['id']}"


                keyboard.append([InlineKeyboardButton(boton_asignacion, callback_data=callback_data)])       

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                encabezado,
                reply_markup=reply_markup,
                parse_mode='markdown'
            )
        else:
            await update.message.reply_text("No tienes permisos para ver este reporte. Por favor contacta a un administrador.")
            return ConversationHandler.END

    except Exception as e:
        print(e)
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END

#Flujo de Reporte de Territorios y cantidad de Sordos para Administradores
async def reporte_territorios(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        # Determinar ID de Usuario en base al ChatID de Telegram
        data = {'telegram_chatid': update.message.chat_id}
        usuario =  requests.post(BASE_URL_API+'publicadores/buscar_telegram_chatid/', json = data).json()[0]
        context.user_data['user_data'] = usuario
        grupos_usuario = usuario['user']['groups']
        
        if any(grupo.get('name') == 'administradores' for grupo in grupos_usuario):
            # Obtener Lista de Entregas Recientes
            data = {'congregacion_id': usuario['congregacion']}
            territorios =  requests.post(BASE_URL_API+'territorios/congregacion/', json = data).json()

            # Generar Keyboard con boton por cada asignacion
            encabezado = "🗺️ *Reporte de Territorios* \n\n"
            texto = encabezado
            total = 0
            for territorio in territorios:
                total += territorio['cantidad_sordos']

                emoji_asignado = ""
                if territorio['asignado']:
                    emoji_asignado = "🔒"
                else:
                    emoji_asignado = "🆓"

                # Terirtorios Reservados
                if territorio['numero'] == 0:
                    emoji_asignado = "🚫"

                territorio_texto = f"{emoji_asignado} *Territorio:* {territorio['numero']} - {territorio['nombre']}\n"
                territorio_texto += f"👥 *Sordos:* {territorio['cantidad_sordos']}\n\n"
                texto += territorio_texto

            texto += f"👥 *Total de Sordos:* {total}\n\n"

            await update.message.reply_text(
                texto,
                parse_mode='markdown'
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text("No tienes permisos para ver este reporte. Por favor contacta a un administrador.")
            return ConversationHandler.END

    except Exception as e:
        print(e)
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END

async def exportar_sordos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    csv = generar_csv_sordos()
    with open(csv, 'rb') as document_file:                    
        await context.bot.send_document(chat_id=update.effective_chat.id, document=document_file, caption=f"*CSV* - Google My Maps", parse_mode='markdown')
        
    
    kml = generar_kml_sordos()
    with open(kml, 'rb') as document_file:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=document_file, caption=f"*KML* - Maps.Me", parse_mode='markdown')

    gpx = generar_gpx_sordos()
    with open(gpx, 'rb') as document_file:
        await context.bot.send_document(chat_id=update.effective_chat.id, document=document_file, caption=f"*GPX* - Osmand", parse_mode='markdown')

    # Cleanup
    os.remove(csv)
    os.remove(kml)
    os.remove(gpx)



async def menu_administrador(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        # Determinar ID de Usuario en base al ChatID de Telegram
        data = {'telegram_chatid': update.message.chat_id}
        usuario =  requests.post(BASE_URL_API+'publicadores/buscar_telegram_chatid/', json = data).json()[0]
        context.user_data['user_data'] = usuario
        grupos_usuario = usuario['user']['groups']
        
        if any(grupo.get('name') == 'administradores' for grupo in grupos_usuario):

            keyboard = [
                ['/reporteAsignaciones \n 📋 Reporte de Asignaciones Pendientes'],
                ['/reporteEntregas \n 📋 Reporte de Entregas Recientes'],
                ['/reporteTerritorios \n 🗺️ Reporte de Territorios'],
                ['/exportarSordos \n 📍 Exportar a Apps de Mapas'],
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, input_field_placeholder="Escoge una opción...")
            await update.message.reply_text("👨🏻‍💼 *Menú de Administrador* \n\n ¿Qué deseas hacer?", reply_markup=reply_markup, parse_mode='markdown')

        else:
            await update.message.reply_text("No tienes permisos para ver este menú. Por favor contacta a un administrador.")
    except Exception as e:
        notify_exception(e)
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")

# Manejar Callbacks de Botones Inline
async def inline_button_asignaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        timestamp = query.data.split(';')[0]
        flag_proceso = query.data.split(';')[1]
        dato = query.data.split(';')[2]
        dato2 = query.data.split(';')[3]
    except Exception as e:
        pass

    # Ignorar Queries de mas de 5 minutos
    if int(time.time()) - int(timestamp) > 300:
        pass
    else:
        try:
            # DETALLE DE ASIGNACION no entregada con botones para administrar
            if flag_proceso == "reporte_asignacion":
                # Obtener detalles de asignacion
                asignacion_detalles =  requests.get(BASE_URL_API + 'asignaciones/' + dato).json()

                # Devolver botones para Borrar y Entregar Asignacion
                timestamp_now = str(int(time.time()))
                keyboard = [
                    [InlineKeyboardButton("🗑️ Borrar", callback_data=f"{timestamp_now};borrar_asignacion;{dato}"),
                    InlineKeyboardButton("✅ Entregar", callback_data=f"{timestamp_now};entregar_asignacion;{dato}")],
                    [InlineKeyboardButton("📄 Regenerar PDF", callback_data=f"{timestamp_now};regenerar_pdf;{dato}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Descripcion de la Asignacion
                descripcion = f'''
    📋 *Asignacion* \n
    *id:* {asignacion_detalles['id']}
    *Territorio:* {asignacion_detalles['territorio_numero']} - {asignacion_detalles['territorio_nombre']}
    *Publicador:* {asignacion_detalles['publicador_nombre']}
    *Fecha de Asignacion:* {formatear_fecha(asignacion_detalles['fecha_asignacion'])}
    '''             
                await query.message.reply_text(text=descripcion, reply_markup=reply_markup, parse_mode='markdown')
            
            # DETALLE DE ASIGNACION entregada
            elif flag_proceso == "detalle_asignacion":
                # Obtener detalles de asignacion
                asignacion_detalles =  requests.get(BASE_URL_API + 'asignaciones/' + dato).json()
                # Descripcion de la Asignacion
                descripcion = f'''
    📋 *Asignacion* \n
    *id:* {asignacion_detalles['id']}
    *Territorio:* {asignacion_detalles['territorio_numero']} - {asignacion_detalles['territorio_nombre']}
    *Publicador:* {asignacion_detalles['publicador_nombre']}
    *Fecha de Asignacion:* {formatear_fecha(asignacion_detalles['fecha_asignacion'])}
    *Fecha de Entrega:* {formatear_fecha(asignacion_detalles['fecha_fin'])}
    '''             
                await query.message.reply_text(text=descripcion, parse_mode='markdown')

            # BORRAR ASIGNACION
            elif flag_proceso == "borrar_asignacion":
                response = requests.delete(BASE_URL_API + f'asignaciones/{dato}/')
                if response.status_code == 204:
                    response = "Asignacion Borrada Exitosamente. 🚮"
                else:
                    response = f"Error al Borrar Asignacion. Status Code: {response.status_code}."
                await query.message.reply_text(text=response)
                await query.message.delete()
            
            # ENTREGAR ASIGNACION
            elif flag_proceso == "entregar_asignacion":
                asignacion = requests.get(BASE_URL_API + f'asignaciones/{dato}').json()
                asignacion['fecha_fin'] = datetime.datetime.now().isoformat()
                response = requests.put(BASE_URL_API + f'asignaciones/{dato}/', json=asignacion)
                if response.status_code == 200:
                    response = "Asignacion Entregada Exitosamente. 🥳"
                else:
                    response = f"Error al Entregar Asignacion. Status Code: {response.status_code}."
                await query.message.reply_text(text=response)

            # REGENERAR PDF DE ASIGNACION
            elif flag_proceso == "regenerar_pdf":
                # DATO = ID ASIGNACION
                asignacion = requests.get(BASE_URL_API + f'asignaciones/{dato}').json()
                publicador = requests.get(BASE_URL_API + f'publicadores/{asignacion["publicador"]}').json()
                telegram_chatid = publicador['telegram_chatid']
                dato2_publicador = telegram_chatid
                
                # DATO2 = TELEGRAM_CHAT_ID
                dato2_solicitante = update.effective_chat.id # Solicitante
                # Devolver botones para escoger Metodo de Entrega
                timestamp_now = str(int(time.time()))
                keyboard = [
                    [InlineKeyboardButton("📦 Enviar a Hermano Telegram", callback_data=f"{timestamp_now};regenerar_pdf_digital_al_asignado;{dato};{dato2_publicador}")],
                    [InlineKeyboardButton("👇🏼📱 Por aqui, digital", callback_data=f"{timestamp_now};regenerar_pdf_digital_al_solicitante;{dato};{dato2_solicitante}")],
                    [InlineKeyboardButton("👇🏼📄 Por aqui, impreso", callback_data=f"{timestamp_now};regenerar_pdf_impreso_al_solicitante;{dato};{dato2_solicitante}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)        
                await query.message.reply_text(text="Escoge como enviar el PDF:", reply_markup=reply_markup)

            # 1. REGENERAR PDF DIGITAL AL ASIGNADO
            elif flag_proceso == "regenerar_pdf_digital_al_asignado":
                asignacion = requests.get(BASE_URL_API + f'asignaciones/{dato}').json()
                data = {
                'publicador_id': asignacion['publicador'],
                'territorio_id': asignacion['territorio'],
                'metodo_entrega': 'digital_publicador',
                'solo_pdf': True
                }
                response_raw =  requests.post('http://localhost:8000/webTerritorios/asignar_territorio/', json = data)
                response = response_raw.json()
                if response_raw.status_code == 200:                        
                    file = response.get('file_path')
                    with open(file, 'rb') as document_file:
                        
                        await context.bot.send_document(chat_id=dato2, document=document_file, caption=f"¡Hola {asignacion['publicador_nombre']}! Se te ha asignado el territorio *{str(asignacion['territorio_numero']) + ' - ' + asignacion['territorio_nombre']}*. \n Por favor visita las direcciones, predica a cualquier persona que salga e intenta empezar estudios. Anota si no encuentras a nadie y regresa en diferentes horarios. Puedes avisarnos si cualquier detalle es incorrecto. \n ¡Muchas gracias por tu trabajo! 🎒🤟🏼", parse_mode='markdown')
                
                # Cleanup
                os.remove(file)
                await query.message.reply_text("PDF enviado al Telegram del Publicador.")

            # 2. REGENERAR PDF DIGITAL AL SOLICITANTE
            elif flag_proceso == "regenerar_pdf_digital_al_solicitante":
                asignacion = requests.get(BASE_URL_API + f'asignaciones/{dato}').json()
                data = {
                'publicador_id': asignacion['publicador'],
                'territorio_id': asignacion['territorio'],
                'metodo_entrega': 'digital_asignador',
                'solo_pdf': True
                }
                response_raw =  requests.post('http://localhost:8000/webTerritorios/asignar_territorio/', json = data)
                response = response_raw.json()
                if response_raw.status_code == 200:                        
                    file = response.get('file_path')
                    with open(file, 'rb') as document_file:
                        await context.bot.send_document(chat_id=dato2, document=document_file, caption=f"He aquí el documento!!!", parse_mode='markdown')
                
                # Cleanup
                os.remove(file)


            # 3. REGENERAR PDF IMPRESO AL SOLICITANTE
            elif flag_proceso == "regenerar_pdf_impreso_al_solicitante":
                asignacion = requests.get(BASE_URL_API + f'asignaciones/{dato}').json()
                data = {
                'publicador_id': asignacion['publicador'],
                'territorio_id': asignacion['territorio'],
                'metodo_entrega': 'impreso_asignador',
                'solo_pdf': True
                }
                response_raw =  requests.post('http://localhost:8000/webTerritorios/asignar_territorio/', json = data)
                response = response_raw.json()
                if response_raw.status_code == 200:                        
                    file = response.get('file_path')
                    with open(file, 'rb') as document_file:
                        await context.bot.send_document(chat_id=dato2, document=document_file, caption=f"He aquí el documento!!!", parse_mode='markdown')
                
                # Cleanup
                os.remove(file)
        except Exception as e:
            notify_exception(e)
            await query.message.reply_text("Error al procesar la solicitud. Por favor contacta a un administrador.")



# COMANDO START
# Usado en las urls de los botones de los territorios
async def start (update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Usar API para obtener nombre del ChatID, en su defecto usar su username
    try:
        data = {'telegram_chatid': update.effective_chat.id}
        response =  requests.post(BASE_URL_API+'publicadores/buscar_telegram_chatid/', json = data).json()
        nombre_usuario = response[0]['nombre']
    except:
        nombre_usuario = update.effective_user.username


    # Comando /start sin argumentos - Ignorar
    if not context.args:
        pass
    # Comando /start con argumento incompleto - Ignorar
    elif context.args[0] == "reportar":
        pass
    # Comando /start con argumento completo
    elif context.args[0].startswith("reportar"):
        codigo_sordo = context.args[0].split('_')[1]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Por favor indícame lo que hace falta corregir con el sordo {codigo_sordo}. Gracias!")
        await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"⚠️ Reporte - {codigo_sordo} --- {nombre_usuario} - {update.effective_chat.id}")
    elif context.args[0].startswith("entregar"):
        id_asignacion = context.args[0].split('_')[1]

        # Llamar a Funcion de Entrega
        try:
            asignacion = requests.get(BASE_URL_API + f'asignaciones/{id_asignacion}').json()
            asignacion['fecha_fin'] = datetime.datetime.now().isoformat()
            response = requests.put(BASE_URL_API + f'asignaciones/{id_asignacion}/', json=asignacion)
            if response.status_code == 200:
                response = "Asignacion Entregada Exitosamente. 🥳"
            else:
                response = f"Error al Entregar Asignacion. Status Code: {response.status_code}."
            await update.message.reply_text(text=response)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Gracias por entregar el territorio {str(asignacion['territorio_numero'])} - {asignacion['territorio_nombre']} !")
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"🥳 Entrega - {id_asignacion} --- {nombre_usuario} - {update.effective_chat.id}")
        except Exception as e:
            notify_exception(e)
            await update.message.reply_text("Error al entregar el territorio. Por favor contacta a un administrador.")

# RESTO DE MENSAJES - REENVIO A ADMIN
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    # Usar API para obtener nombre del ChatID, en su defecto usar su username
    try:
        data = {'telegram_chatid': update.effective_chat.id}
        response =  requests.post(BASE_URL_API+'publicadores/buscar_telegram_chatid/', json = data).json()
        nombre_usuario = response[0]['nombre']
    except:
        nombre_usuario = update.effective_user.username
    
    # Ignorar mensajes del Administrador    
    if str(update.effective_chat.id) == str(CHAT_ID_ADMIN):
        pass
    else:
        # Verificar Tipos de Mensajes
        if update.message.location:
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 📍 Ubicación")
            await context.bot.send_location(chat_id=CHAT_ID_ADMIN, latitude=update.message.location.latitude, longitude=update.message.location.longitude)
        elif update.message.photo:
            file_id = update.message.photo[0].file_id
            caption = update.message.caption
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 📸 Foto")
            await context.bot.send_photo(chat_id=CHAT_ID_ADMIN, photo=file_id, caption=caption)
        elif update.message.voice:
            file_id = update.message.voice.file_id
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 🎤 Audio")
            await context.bot.send_voice(chat_id=CHAT_ID_ADMIN, voice=file_id)
        elif update.message.audio:
            file_id = update.message.audio.file_id
            caption = update.message.caption
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 🎵 Audio")
            await context.bot.send_audio(chat_id=CHAT_ID_ADMIN, audio=file_id, caption=caption)
        elif update.message.document:
            file_id = update.message.document.file_id
            caption = update.message.caption
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 📄 Documento")
            await context.bot.send_document(chat_id=CHAT_ID_ADMIN, document=file_id, caption=caption)
        elif update.message.video:
            file_id = update.message.video.file_id
            caption = update.message.caption
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 🎥 Video")
            await context.bot.send_video(chat_id=CHAT_ID_ADMIN, video=file_id, caption=caption)
        elif update.message.video_note:
            file_id = update.message.video_note.file_id
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 🎥 Video Note")
            await context.bot.send_video_note(chat_id=CHAT_ID_ADMIN, video_note=file_id)
        elif update.message.sticker:
            file_id = update.message.sticker.file_id
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 🎨 Sticker")
            await context.bot.send_sticker(chat_id=CHAT_ID_ADMIN, sticker=file_id)
        elif update.message.contact:
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 👤 Contacto")
            await context.bot.send_contact(chat_id=CHAT_ID_ADMIN, phone_number=update.message.contact.phone_number, first_name=update.message.contact.first_name)
        elif update.message.text:
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 📝 Texto")
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=update.message.text)
        else:
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=f"💬 {nombre_usuario} - {update.effective_chat.id} - 🤷‍♂️ No se pudo identificar el tipo de mensaje")
            await context.bot.send_message(chat_id=CHAT_ID_ADMIN, text=update)

def main() -> None:
    """Run the bot."""
    # Crear Aplicacion con Token
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("asignar", asignar)],
        states={
            PUBLICADOR: [MessageHandler(filters.Regex("^(?!\/cancelar$).*"), publicador), CommandHandler("cancelar", cancelar)],
            VERIFICACION: [MessageHandler(filters.Regex("^(?!\/cancelar$).*"), verificacion), CommandHandler("cancelar", cancelar)],
            TERRITORIO: [MessageHandler(filters.Regex("^(?!\/cancelar$).*"), territorio), CommandHandler("cancelar", cancelar)],
            METODO_ENVIO: [MessageHandler(filters.Regex("^(?!\/cancelar$).*"), metodo_envio), CommandHandler("cancelar", cancelar)]
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler("reporteAsignaciones",reporte_asignaciones))
    application.add_handler(CommandHandler("reporteEntregas",reporte_entregas))
    application.add_handler(CommandHandler("reporteTerritorios",reporte_territorios))
    application.add_handler(CommandHandler("exportarSordos", exportar_sordos))
    application.add_handler(CommandHandler("admin", menu_administrador))
    application.add_handler(CallbackQueryHandler(inline_button_asignaciones))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler( filters.ALL, echo))
    try:
        # Correr hasta Ctrl + C
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        # Notify the admin about the exception
        print(f"An exception occurred in the bot:\n\n{str(e)}\n\n{traceback.format_exc()}")
        error_message = f"An exception occurred in the bot:\n\n{str(e)}\n\n{traceback.format_exc()}"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={CHAT_ID_ADMIN}&text={error_message}"
        requests.get(url)

if __name__ == "__main__":
    main()