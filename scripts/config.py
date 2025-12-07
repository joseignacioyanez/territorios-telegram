import os
from dotenv import load_dotenv
import logging

# Constantes
PUBLICADOR, VERIFICACION, TERRITORIO, METODO_ENVIO = range(4)
load_dotenv()

# Tech Admin
TELEGRAM_TECH_ADMIN_CHAT_ID = os.environ['TELEGRAM_TECH_ADMIN_CHAT_ID']

TELEGRAM_BOT_TOKEN=os.environ['TELEGRAM_BOT_TOKEN']
env=os.environ['TELEGRAM_BOT_TOKEN']
base_url=os.environ['BASE_URL']
# Producción
#BASE_URL_API = 'http://territorios-django:8000/api/'
#BASE_URL_WEB = 'http://territorios-django:8000/'
#Desarrollo
BASE_URL_API = f'http://{base_url}/api/'
BASE_URL_WEB = f'http://{base_url}/'

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)