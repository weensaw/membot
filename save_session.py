import logging
import json
from telethon import TelegramClient
from telethon.sessions import StringSession

# Replace 'your_api_id' and 'your_api_hash' with your own values
with open('config.json', 'r') as f:
    config = json.load(f)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up the Telegram client
api_id = config['api_id']
api_hash = config['api_hash']
string_session = config['string_session']

# Create a new TelegramClient without a session
with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Your string session:")
    print(client.session.save())
