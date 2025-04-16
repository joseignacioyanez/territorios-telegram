import locale
import datetime
import requests
import traceback
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_TECH_ADMIN_CHAT_ID

def formatear_fecha(fecha):
    meses_es = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre"
    }
    date_object = datetime.datetime.fromisoformat(fecha)
    dia = date_object.day
    mes = meses_es[date_object.month]
    año = date_object.year
    return f"{dia} de {mes} del {año}"


def notify_exception(e: Exception) -> None:
    # Notify the admin about the exception
    error_message = f"☢️ An exception occurred in the bot:\n\n{str(e)}\n\n{traceback.format_exc()}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_TECH_ADMIN_CHAT_ID}&text={error_message}"
    requests.get(url)
    