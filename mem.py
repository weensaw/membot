import json
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto

# Загрузка конфигурации из config.json
with open('config.json', 'r') as f:
    config = json.load(f)

api_id = config['api_id']
api_hash = config['api_hash']
string_session = config['string_session']
source_channel = config['source_channel']
target_channel = config['target_channel']
check_period = config['check_period']
negative_reactions = config['negative_reactions']
positive_reactions = config['positive_reactions']
funny_coefficient = config['funny_coefficient']
spreading_coefficient = config['spreading_coefficient']
involvement_coefficient = config['involvement_coefficient']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация клиента
client = TelegramClient(StringSession(string_session), api_id, api_hash)

# Имя файла для хранения идентификаторов пересланных сообщений
processed_messages_file = 'processed_messages.json'

# Загрузка идентификаторов пересланных сообщений из файла
try:
    with open(processed_messages_file, 'r') as f:
        processed_messages = set(json.load(f))
except (FileNotFoundError, json.JSONDecodeError):
    processed_messages = set()

async def analyze_and_forward_messages():
    async for message in client.iter_messages(source_channel, limit=10):
        if isinstance(message.media, MessageMediaPhoto):  # Проверяем, является ли сообщение фотографией
            if message.id not in processed_messages:
                reactions = message.reactions
                if reactions:
                    positive_count = sum(reaction.count for reaction in reactions.results if reaction.reaction.emoticon in positive_reactions)
                    negative_count = sum(reaction.count for reaction in reactions.results if reaction.reaction.emoticon in negative_reactions)
                    total_count = positive_count + negative_count

                    if total_count > 0:
                        funny_score = positive_count / total_count
                        if funny_score >= funny_coefficient:
                            await client.send_message(target_channel, message)
                            logger.info(f"Reposted photo message {message.id} from {source_channel} to {target_channel}")
                            processed_messages.add(message.id)
                            with open(processed_messages_file, 'w') as f:
                                json.dump(list(processed_messages), f)

async def main():
    await client.start()  # Явно стартуем клиента
    logger.info("Client is connected")
    
    while True:
        await analyze_and_forward_messages()
        await asyncio.sleep(check_period * 60)  # check_period в минутах

if __name__ == "__main__":
    client.loop.run_until_complete(main())
