from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.getcwd(), '.env'))

os.environ.setdefault('SIMPLE_SETTINGS', 'stare.settings.base')
from simple_settings import settings

__all__ = ['settings']
