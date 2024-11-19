import locale
import datetime
import traceback
from config import TELEGRAM_BOT_TOKEN, CHAT_ID_ADMIN
from security import safe_requests

def formatear_fecha(fecha):
    try:
        locale.setlocale(locale.LC_TIME, 'C.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_TIME, '')
    date_object = datetime.datetime.fromisoformat(fecha)
    fecha_formateada = date_object.strftime("%d de %B del %Y")
    return fecha_formateada


def notify_exception(e: Exception) -> None:
    # Notify the admin about the exception
    error_message = f"☢️ An exception occurred in the bot:\n\n{str(e)}\n\n{traceback.format_exc()}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={CHAT_ID_ADMIN}&text={error_message}"
    safe_requests.get(url)
