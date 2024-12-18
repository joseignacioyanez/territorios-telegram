import os
from dotenv import load_dotenv
import logging

# Constantes
PUBLICADOR, VERIFICACION, TERRITORIO, METODO_ENVIO = range(4)
load_dotenv()
CHAT_ID_ADMIN = os.environ['TELEGRAM_ADMIN_CHAT_ID']
TELEGRAM_BOT_TOKEN=os.environ['TELEGRAM_BOT_TOKEN']
# Producción
BASE_URL_API = 'http://territorios-django:8000/api/'
BASE_URL_WEB = 'http://territorios-django:8000/'
#Desarrollo
#BASE_URL_API = 'http://localhost:8000/api/'
#BASE_URL_WEB = 'http://localhost:8000/'

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)