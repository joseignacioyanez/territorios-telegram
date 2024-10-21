# Standard Library Imports
import os
import time
import datetime
import requests

# Telegram Imports
from telegram import (  # type: ignore
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup  
) 
from telegram.ext import (  # type: ignore
    ContextTypes,
    ConversationHandler,
)

# Custom Utility Imports
from utils import notify_exception, formatear_fecha
from config import (
    PUBLICADOR, 
    VERIFICACION, 
    TERRITORIO, 
    METODO_ENVIO, 
    CHAT_ID_ADMIN, 
    BASE_URL_API, 
    logger
)

# Services Imports
from services import (
    delete_asignacion, 
    entregar_asignacion, 
    get_asignacion, 
    get_publicador, 
    get_user_by_telegram_chatid, 
    get_publicadores_activos_de_congregacion, 
    get_asignaciones_pendiente_de_congregacion, 
    get_territorios_disponibles_de_congregacion, 
    registrar_asignacion_y_generar_documento, 
    get_asignaciones_entregadas_de_congregacion, 
    get_territorios_de_congregacion
)

# Custom Import for File Generation
from kml_MapsMe import generar_kml_sordos
from gpx_Osmand import generar_gpx_sordos
from csv_GoogleMyMaps import generar_csv_sordos


# FLUJO ASIGNAR - FASE 0
# Maneja /asignar y envia Lista de Publicadores
async def asignar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    # Determinar ID de Usuario en base al ChatID de Telegram
    try:
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        context.user_data['user_asignador'] = user
    except Exception as e:
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END
        
    # Verificar Permisos en base a Grupos de Usuarios
    user_groups = context.user_data['user_asignador']['user']['groups']
    groups_pueden_asignar = ['administradores', 'asignadores']
    if any(group.get('name') in groups_pueden_asignar for group in user_groups):
        
        # Obtener Lista de Publicadores Activos de la misma Congregación
        try:
            id_congregacion = context.user_data['user_asignador']['congregacion']
            publicadores = get_publicadores_activos_de_congregacion(id_congregacion)
        except Exception as e:
            await update.message.reply_text("Error al obtener la lista de Publicadores. Por favor contacta a un administrador.")
            return ConversationHandler.END

        # Generar Keyboard con boton por cada publicador y enviar
        reply_keyboard = []
        for publicador in publicadores:
            reply_keyboard.append([str(publicador['id']) + ' - ' + publicador['nombre']])

        # Enviar botones para que escoja publicador
        nombre_usuario = context.user_data['user_asignador']['nombre']
        await update.message.reply_text(
            f"🙋🏻¡Hola {nombre_usuario}! Te ayudaré a asignar un territorio. "
            "Envía o topa /cancelar si deseas dejar de hablar conmigo.\n\n"
            "Escoge el Publicador al que deseas asignar el territorio:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="Escoge el Publicador..."
            ),
        )
        # Envia Flag terminando Fase del Flujo
        return PUBLICADOR
    
    # Si el usuario asignador no pertenece a grupos por permisos
    else:
        await update.message.reply_text("No tienes permisos para asignar territorios. Por favor contacta a un administrador.")
        return ConversationHandler.END

# FLUJO ASIGNAR - FASE 1
# Guarda el Publicador, valida que no existan otras asignaciones
async def publicador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Parse Boton de Publicador escogido
    try:
        publicador_escogido = update.message.text
        context.user_data['user_asignado_id'] = publicador_escogido.split(' - ')[0]
        context.user_data['user_asignado_nombre'] = publicador_escogido.split(' - ')[1]
    except Exception as e:
        notify_exception(e)
        await update.message.reply_text("Error al obtener el Publicador. Por favor contacta a un administrador.")
        return ConversationHandler.END

    # Verificar si el usuario tiene Asignaciones Pendientes de entregar
    try:
        congregacion_id = context.user_data['user_asignador']['congregacion']
        asignaciones_pendientes =  get_asignaciones_pendiente_de_congregacion(congregacion_id)
    except Exception as e:
        await update.message.reply_text("Error al obtener la lista de Asignaciones Pendientes. Por favor contacta a un administrador.")
        return ConversationHandler.END
    
    # Recorrer asignaciones pendientes para buscar coincidencias y avisar al Asignador
    tiene_asignaciones_pendientes = False
    texto_asignaciones_pendientes = ""
    for asignacion in asignaciones_pendientes:
        if str(asignacion['publicador']) == str(context.user_data['user_asignado_id']):
            tiene_asignaciones_pendientes = True
            texto_asignaciones_pendientes += "*Territorio: *" + str(asignacion['territorio_numero']) + ' - ' + asignacion['territorio_nombre'] + '\n'
            texto_asignaciones_pendientes += "*Fecha de Asignación: *" + formatear_fecha(asignacion['fecha_asignacion']) + '\n\n'

    botones_pregunta_continuar_asignacion = ReplyKeyboardMarkup( [['¡Sí, hagámoslo!'], ['No, gracias']], one_time_keyboard=True, input_field_placeholder="¿Deseas asignar?")
    if tiene_asignaciones_pendientes:        
        await update.message.reply_text(
            "El Publicador seleccionado tiene asignaciones pendientes: \n\n" + texto_asignaciones_pendientes + "Por favor, recuérdale al herman@ e indícame si deseas hacer la nueva asignación.",
            parse_mode='markdown',
            reply_markup=botones_pregunta_continuar_asignacion,
        )
    else:
        await update.message.reply_text(
            "No hay asignaciones pendientes para el Publicador seleccionado. \n ¿Deseas continuar con la asignación?",
            reply_markup=botones_pregunta_continuar_asignacion,
        )
    # Envia Flag terminando Fase del Flujo
    return VERIFICACION
    
# FLUJO ASIGNAR - FASE 2
# Maneja la respuesta de Verificacion de Asignaciones Previas y Muestra Territorios Disponibles
async def verificacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    
    if update.message.text == 'No, gracias':
        await update.message.reply_text("Está bien. Ten un buen día.")
        return ConversationHandler.END
    
    # Por defecto, continuar con el proceso
    else:

        # Obtener Lista de Territorios Disponibles
        try:
            congregacion_id = context.user_data['user_asignador']['congregacion']
            territorios_disponibles = get_territorios_disponibles_de_congregacion(congregacion_id)
            context.user_data['territorios_disponibles'] = territorios_disponibles

            # Crear botones con los territorios disponibles
            reply_keyboard = []
            if not territorios_disponibles:
                await update.message.reply_text("No hay territorios disponibles para asignar. Por favor contacta a un administrador.")
                return ConversationHandler.END
            for territorio in territorios_disponibles:
                reply_keyboard.append([str(territorio['numero']) + ' - ' + territorio['nombre']])

            await update.message.reply_text(
                f"Escoge el Territorio que deseas asignar al Publicador:",
                reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, input_field_placeholder="Escoge el Territorio..."
                ),
            )
            # Envia Flag terminando Fase del Flujo
            return TERRITORIO
        
        except Exception as e:
            await update.message.reply_text("Error al obtener la lista de Territorios. Por favor contacta a un administrador.")
            return ConversationHandler.END

# FLUJO ASIGNAR - FASE 3
# Guarda el Territorio y pregunta por el Método de Entrega
async def territorio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    # Parse Boton escogido de Territorio
    try:
        territorio_deseado = update.message.text
        territorio_numero_deseado = territorio_deseado.split(' - ')[0]
        territorio_nombre_deseado = territorio_deseado.split(' - ')[1]
    except Exception as e:
        notify_exception(e)
        await update.message.reply_text("Error al obtener el Publicador. Por favor contacta a un administrador.")
        return ConversationHandler.END

    # Comprobar que el territorio escogido estaba en la lista de disponibles
    for territorio in context.user_data['territorios_disponibles']:
        if str(territorio['numero']) == territorio_numero_deseado and territorio['nombre'] == territorio_nombre_deseado:
            context.user_data['territorio_asignar_id'] = territorio['id']
            context.user_data['territorio_asignar_numero_nombre'] = str(territorio['numero']) + ' - ' + territorio['nombre']
            break

    # Enviar botones sobre el metodo de Envio
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
    
    # Enviar flag del final de la fase del Flujo
    return METODO_ENVIO

# FLUJO ASIGNAR - FASE 4
# Guarda el Método de Entrega y finaliza la asignación
async def metodo_envio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    # Parse boton d eMetodo de envio y guardar en contexto
    if update.message.text == 'Enviar al Telegram del herman@':
        context.user_data['metodo_entrega'] = 'digital_publicador'
    elif update.message.text == 'Registrar asignación y Enviarme el PDF digital por aquí':
        context.user_data['metodo_entrega'] = 'digital_asignador'
    elif update.message.text == 'Registrar asignación y Enviarme el PDF para Imprimir por aquí':
        context.user_data['metodo_entrega'] = 'impreso_asignador'
    else:
        await update.message.reply_text("Error al obtener el Publicador. Por favor contacta a un administrador.")
        return ConversationHandler.END

    publicador = context.user_data['user_asignado_id']
    territorio = context.user_data['territorio_asignar_id']
    metodo_entrega = context.user_data['metodo_entrega']
    solo_generar = False
    registro_exitoso, response = registrar_asignacion_y_generar_documento(publicador, territorio, metodo_entrega, solo_generar)

    if registro_exitoso:
        
        user_asignador_nombre = context.user_data['user_asignador']['nombre']
        user_asignado_nombre = context.user_data['user_asignado_nombre']
        territorio_nombre = response.get('territorio')

        file = response.get('file_path')

        if metodo_entrega == 'digital_publicador':
            with open(file, 'rb') as document_file:
                # Si el usuario tiene Telegram registrado
                if response.get('chat_id'):
                    publicador_chat_id = response.get('chat_id')
                    await context.bot.send_document(chat_id= publicador_chat_id, 
                                                    document= document_file, 
                                                    caption=f"¡Hola {user_asignado_nombre}! Se te ha asignado el territorio *{territorio_nombre}*. \n Por favor visita las direcciones, predica a cualquier persona que salga e intenta empezar estudios. Anota si no encuentras a nadie y regresa en diferentes horarios. Puedes avisarnos si cualquier detalle es incorrecto. \n ¡Muchas gracias por tu trabajo! 🎒🤟🏼", 
                                                    parse_mode= 'markdown')
                # Si el usuario no tiene Telegram registrado, enviar al Asignador para reenvio
                else:
                    await update.message.reply_document(document=document_file, 
                                                        caption='*Por favor hazle llegar el territorio al publicador porque no se registra su Telegram en el Sistema. Y enviale el siguiente mensaje. Gracias*', 
                                                        parse_mode='markdown')
                    await update.message.reply_text(f"¡Hola {user_asignado_nombre}! Se te ha asignado el territorio *{territorio_nombre}*. \n Por favor visita las direcciones, predica a cualquier persona que salga e intenta empezar estudios. Anota si no encuentras a nadie y regresa en diferentes horarios. Puedes avisarnos si cualquier detalle es incorrecto. \n ¡Muchas gracias por tu trabajo! 🎒🤟🏼", 
                                                    parse_mode= 'markdown')
                # Notificar al Administrador
                await context.bot.send_message(chat_id=CHAT_ID_ADMIN, 
                                                text=f"ℹ️ El territorio {territorio_nombre} ha sido asignado a {user_asignado_nombre} por {user_asignador_nombre} correctamente. Se ha enviado al Telegram del publicador")

        elif metodo_entrega == 'digital_asignador':
            with open(file, 'rb') as document_file:
                await update.message.reply_document(document=document_file,
                                                    caption='*Por favor hazle llegar el territorio al publicador porque no se registra su Telegram en el Sistema. Y enviale el siguiente mensaje. Gracias*', 
                                                    parse_mode='markdown')
                await update.message.reply_text(f"¡Hola {user_asignado_nombre}! Se te ha asignado el territorio *{territorio_nombre}*. \n Por favor visita las direcciones, predica a cualquier persona que salga e intenta empezar estudios. Anota si no encuentras a nadie y regresa en diferentes horarios. Puedes avisarnos si cualquier detalle es incorrecto. \n ¡Muchas gracias por tu trabajo! 🎒🤟🏼", 
                                                    parse_mode= 'markdown')
                # Notificar al Administrador
                await context.bot.send_message(chat_id=CHAT_ID_ADMIN, 
                                                text=f"ℹ️ El territorio {territorio_nombre} ha sido asignado a {user_asignado_nombre} por {user_asignador_nombre} correctamente. Se ha descargado el PDF digital para el asignador")

        elif metodo_entrega == 'impreso_asignador':
            with open(file, 'rb') as document_file:
                await update.message.reply_document(document=document_file, 
                                                    caption='*Por favor hazle llegar el territorio al publicador*. Gracias', 
                                                    parse_mode='markdown')
                # Notificar al Administrador
                await context.bot.send_message(chat_id=CHAT_ID_ADMIN, 
                                                text=f"ℹ️ El territorio {territorio_nombre} ha sido asignado a {user_asignado_nombre} por {user_asignador_nombre} correctamente. Se ha descargado el PDF para imprimir para el asignador")
        
        else:
            await update.message.reply_text("No se reconoce el método de entrega. Por favor contacta a un administrador.")
            return ConversationHandler.END
    
    else:
        notify_exception(response.get('error'))
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
    await update.message.reply_text("Adiós! Espero volvamos a conversar.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# Flujo Reporte de Asignaciones Pendientes para Administradores
async def reporte_asignaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Determinar ID de Usuario en base al ChatID de Telegram
    try:
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        context.user_data['user_data'] = user
    
        # Verificar Permisos en base a Grupos de Usuarios
        user_groups = context.user_data['user_data']['user']['groups']
        groups_pueden_administrar = ['administradores']
        if any(group.get('name') in groups_pueden_administrar for group in user_groups):

            # Obtener Lista de Asignaciones Pendientes
            congregacion_id = user['congregacion']
            asignaciones_pendientes = get_asignaciones_pendiente_de_congregacion(congregacion_id)


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
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END

#Flujo de Reporte de Entregas Recientes para Administradores
async def reporte_entregas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Determinar ID de Usuario en base al ChatID de Telegram
    try:
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        context.user_data['user_data'] = user
    
        # Verificar Permisos en base a Grupos de Usuarios
        user_groups = context.user_data['user_data']['user']['groups']
        groups_pueden_administrar = ['administradores']
        if any(group.get('name') in groups_pueden_administrar for group in user_groups):

            # Obtener Lista de Entregas Recientes
            congregacion_id = user['congregacion']
            asignaciones_entregadas =  get_asignaciones_entregadas_de_congregacion(congregacion_id)

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
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END

#Flujo de Reporte de Territorios y cantidad de Sordos para Administradores
async def reporte_territorios(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Determinar ID de Usuario en base al ChatID de Telegram
    try:
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        context.user_data['user_data'] = user
    
        # Verificar Permisos en base a Grupos de Usuarios
        user_groups = context.user_data['user_data']['user']['groups']
        groups_pueden_administrar = ['administradores']
        if any(group.get('name') in groups_pueden_administrar for group in user_groups):

            # Obtener Lista de Territorios
            congregacion_id = user['congregacion']
            territorios =  get_territorios_de_congregacion(congregacion_id)

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
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END

async def exportar_sordos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    # Determinar ID de Usuario en base al ChatID de Telegram
    try:
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        context.user_data['user_data'] = user
    
        # Verificar Permisos en base a Grupos de Usuarios
        user_groups = context.user_data['user_data']['user']['groups']
        groups_pueden_administrar = ['administradores']
        if any(group.get('name') in groups_pueden_administrar for group in user_groups):

            # Obtener Lista de Territorios
            congregacion_id = user['congregacion']

            csv = generar_csv_sordos(congregacion_id)
            with open(csv, 'rb') as document_file:                    
                await context.bot.send_document(chat_id=update.effective_chat.id, document=document_file, caption=f"*CSV* - Google My Maps", parse_mode='markdown')
                
            kml = generar_kml_sordos(congregacion_id)
            with open(kml, 'rb') as document_file:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=document_file, caption=f"*KML* - Maps.Me", parse_mode='markdown')

            gpx = generar_gpx_sordos(congregacion_id)
            with open(gpx, 'rb') as document_file:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=document_file, caption=f"*GPX* - Osmand", parse_mode='markdown')

            # Cleanup
            os.remove(csv)
            os.remove(kml)
            os.remove(gpx)

    except Exception as e:
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")
        return ConversationHandler.END


async def menu_administrador(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Determinar ID de Usuario en base al ChatID de Telegram
    try:
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        context.user_data['user_data'] = user
    
        # Verificar Permisos en base a Grupos de Usuarios
        user_groups = context.user_data['user_data']['user']['groups']
        groups_pueden_administrar = ['administradores']
        if any(group.get('name') in groups_pueden_administrar for group in user_groups):

            keyboard = [
                ['/reporteAsignaciones \n 📋 Reporte de Asignaciones Pendientes'],
                ['/reporteEntregas \n 📋 Reporte de Entregas Recientes'],
                ['/reporteTerritorios \n 🗺️ Reporte de Territorios'],
                ['/exportarSordos \n 📍 Exportar a Apps de Mapas'],
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, 
                                                one_time_keyboard=True, 
                                                input_field_placeholder="Escoge una opción...")
            await update.message.reply_text("👨🏻‍💼 *Menú de Administrador* \n\n ¿Qué deseas hacer?", 
                                            reply_markup=reply_markup, 
                                            parse_mode='markdown')

        else:
            await update.message.reply_text("No tienes permisos para ver este menú. Por favor contacta a un administrador.")
    except Exception as e:
        await update.message.reply_text("No se reconoce este usuario. Por favor contacta a un administrador.")

# Manejar Callbacks de Botones Inline
async def inline_button_asignaciones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    query = update.callback_query
    await query.answer()

    # Parse Callback Data
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
            # 1. DETALLE DE ASIGNACION no entregada con botones para administrar
            if flag_proceso == "reporte_asignacion":
                # Obtener detalles de asignacion
                asignacion =  get_asignacion(dato)

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
    *id:* {asignacion['id']}
    *Territorio:* {asignacion['territorio_numero']} - {asignacion['territorio_nombre']}
    *Publicador:* {asignacion['publicador_nombre']}
    *Fecha de Asignacion:* {formatear_fecha(asignacion['fecha_asignacion'])}
    '''             
                await query.message.reply_text(text=descripcion, reply_markup=reply_markup, parse_mode='markdown')
            
            # 2. DETALLE DE ASIGNACION entregada
            elif flag_proceso == "detalle_asignacion":
                # Obtener detalles de asignacion
                asignacion =  get_asignacion(dato)
                # Descripcion de la Asignacion
                descripcion = f'''
    📋 *Asignacion* \n
    *id:* {asignacion['id']}
    *Territorio:* {asignacion['territorio_numero']} - {asignacion['territorio_nombre']}
    *Publicador:* {asignacion['publicador_nombre']}
    *Fecha de Asignacion:* {formatear_fecha(asignacion['fecha_asignacion'])}
    *Fecha de Entrega:* {formatear_fecha(asignacion['fecha_fin'])}
    '''             
                await query.message.reply_text(text=descripcion, parse_mode='markdown')

            # 3. BORRAR ASIGNACION
            elif flag_proceso == "borrar_asignacion":
                response = delete_asignacion(dato)
                if response.status_code == 204:
                    response = "Asignacion Borrada Exitosamente. 🚮"
                else:
                    response = f"Error al Borrar Asignacion. Status Code: {response.status_code}."
                    notify_exception(response)
                await query.message.reply_text(text=response)
                await query.message.delete()
            
            # 4. ENTREGAR ASIGNACION
            elif flag_proceso == "entregar_asignacion":
                response = entregar_asignacion(dato)
                if response.status_code == 200:
                    response = "Asignacion Entregada Exitosamente. 🥳"
                else:
                    response = f"Error al Entregar Asignacion. Status Code: {response.status_code}."
                    notify_exception(response)
                await query.message.reply_text(text=response)

            # 5. REGENERAR PDF DE ASIGNACION
            elif flag_proceso == "regenerar_pdf":
                # DATO = ID ASIGNACION
                asignacion = get_asignacion(dato)
                publicador = get_publicador(asignacion["publicador"])
                
                # DATO2 = TELEGRAM_CHAT_ID
                telegram_chatid = publicador['telegram_chatid']
                dato2_publicador = telegram_chatid
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

            # 5.1. REGENERAR PDF DIGITAL AL ASIGNADO
            elif flag_proceso == "regenerar_pdf_digital_al_asignado":
                asignacion = get_asignacion(dato)
                registro_exitoso, response = registrar_asignacion_y_generar_documento(
                        asignacion['publicador'], 
                        asignacion['territorio'], 
                        'digital_publicador', 
                        True
                    )
                
                if registro_exitoso:
                    file = response.get('file_path')
                    with open(file, 'rb') as document_file:
                        publicador_nombre = asignacion['publicador_nombre']
                        territorio_info = f"{asignacion['territorio_numero']} - {asignacion['territorio_nombre']}"

                        mensaje = (
                            f"¡Hola {publicador_nombre}! "
                            f"Se te ha asignado el territorio *{territorio_info}*.\n"
                            "Por favor visita las direcciones, predica a cualquier persona que salga e intenta empezar estudios. "
                            "Anota si no encuentras a nadie y regresa en diferentes horarios. "
                            "Puedes avisarnos si cualquier detalle es incorrecto.\n"
                            "¡Muchas gracias por tu trabajo! 🎒🤟🏼"
                        )

                        await context.bot.send_document(
                            chat_id=dato2, 
                            document=document_file, 
                            caption=mensaje, 
                            parse_mode='markdown'
                        )
                # Cleanup
                os.remove(file)
                await query.message.reply_text("PDF enviado al Telegram del Publicador.")

            # 5.2. REGENERAR PDF DIGITAL AL SOLICITANTE
            elif flag_proceso == "regenerar_pdf_digital_al_solicitante":
                asignacion = get_asignacion(dato)
                registro_exitoso, response = registrar_asignacion_y_generar_documento(
                        asignacion['publicador'], 
                        asignacion['territorio'], 
                        'digital_asignador', 
                        True
                    )
                
                if registro_exitoso:                   
                    file = response.get('file_path')
                    with open(file, 'rb') as document_file:
                        await context.bot.send_document(
                                        chat_id=dato2, 
                                        document=document_file, 
                                        caption="He aquí el documento!!!", 
                                        parse_mode='markdown'
                                    )                
                # Cleanup
                os.remove(file)


            # 5.3. REGENERAR PDF IMPRESO AL SOLICITANTE
            elif flag_proceso == "regenerar_pdf_impreso_al_solicitante":
                asignacion = get_asignacion(dato)
                registro_exitoso, response = registrar_asignacion_y_generar_documento(
                        asignacion['publicador'], 
                        asignacion['territorio'], 
                        'impreso_asignador', 
                        True
                    )
                
                if registro_exitoso:   
                    file = response.get('file_path')
                    with open(file, 'rb') as document_file:
                        await context.bot.send_document(
                                        chat_id=dato2, 
                                        document=document_file, 
                                        caption=f"He aquí el documento!!!", 
                                        parse_mode='markdown'
                                        )
                
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
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        nombre_usuario = user['nombre']
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
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"Por favor indícame lo que hace falta corregir con el sordo {codigo_sordo}. Gracias!"
            )
        await context.bot.send_message(
            chat_id=CHAT_ID_ADMIN, 
            text=f"⚠️ Reporte - {codigo_sordo} --- {nombre_usuario} - {update.effective_chat.id}"
            )
    
    elif context.args[0].startswith("entregar"):
        id_asignacion = context.args[0].split('_')[1]

        # Llamar a Funcion de Entrega
        try:
            response = entregar_asignacion(id_asignacion)
            asignacion = get_asignacion(id_asignacion)

            if response.status_code == 200:
                response = "Asignacion Entregada Exitosamente. 🥳"
            else:
                response = f"Error al Entregar Asignacion. Status Code: {response.status_code}."
                notify_exception(response)

            await update.message.reply_text(text=response)
            await context.bot.send_message(
                chat_id=update.effective_chat.id, 
                text=f"Gracias por entregar el territorio {str(asignacion['territorio_numero'])} - {asignacion['territorio_nombre']} !"
                )
            await context.bot.send_message(
                chat_id=CHAT_ID_ADMIN, 
                text=f"🥳 Entrega - {id_asignacion} --- {nombre_usuario} - {update.effective_chat.id}"
                )
        except Exception as e:
            notify_exception(e)
            await update.message.reply_text("Error al entregar el territorio. Por favor contacta a un administrador.")

# RESTO DE MENSAJES - REENVIO A ADMIN
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    # Usar API para obtener nombre del ChatID, en su defecto usar su username
    try:
        user = get_user_by_telegram_chatid(update.message.chat_id)[0]
        nombre_usuario = user['nombre']
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
