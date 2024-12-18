import os
import traceback
import requests
from telegram import Update # type: ignore
from telegram.ext import ( # type: ignore
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from config import (
    PUBLICADOR, 
    VERIFICACION, 
    TERRITORIO, 
    METODO_ENVIO, 
    CHAT_ID_ADMIN, 
    TELEGRAM_BOT_TOKEN
)

from handlers import (
    asignar, 
    cancelar, 
    reporte_asignaciones, 
    reporte_entregas,
    reporte_territorios, 
    menu_administrador, 
    exportar_sordos,
    inline_button_asignaciones,
    publicador,
    verificacion,
    territorio,
    metodo_envio,
    start,
    echo
)

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