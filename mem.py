import json
import logging
import asyncio
import time
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto, DialogFilter, InputPeerChannel, ReactionEmoji
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.errors import FloodWaitError

# Загрузка конфигурации из config.json
with open('config.json', 'r') as f:
    config = json.load(f)

api_id = config['api_id']
api_hash = config['api_hash']
check_period = config['check_period']
string_session = config['string_session']
target_channel = config['target_channel']
funny_coefficient = config['funny_coefficient']
negative_reactions = config['negative_reactions']
positive_reactions = config['positive_reactions']
spreading_coefficient = config['spreading_coefficient']
involvement_coefficient = config['involvement_coefficient']
meme_age_threshold = config['meme_age_threshold']
max_messages_to_send = config['max_messages_to_send']
send_interval = config['send_interval']

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = TelegramClient(StringSession(string_session), api_id, api_hash)

processed_messages_file = 'processed_messages.json'

# Загрузка ID последних обработанных сообщений
try:
    with open(processed_messages_file, 'r') as f:
        processed_messages = json.load(f)
    if isinstance(processed_messages, list):
        processed_messages = {}
except (FileNotFoundError, json.JSONDecodeError):
    processed_messages = {}

# Переменные для отслеживания лимитов
messages_sent = 0
last_sent_time = time.time()

async def get_channels_from_folder(folder_name):
    dialog_filters = await client(GetDialogFiltersRequest())
    logger.info(f"Dialog filters: {dialog_filters}")

    channels = []
    for dialog_filter in dialog_filters.filters:
        if isinstance(dialog_filter, DialogFilter) and dialog_filter.title == folder_name:
            for peer in dialog_filter.include_peers:
                if isinstance(peer, InputPeerChannel):
                    channels.append(peer)
    return channels

async def get_channel_info(channel_id):
    try:
        full_channel = await client(GetFullChannelRequest(channel_id))
        return full_channel
    except FloodWaitError as e:
        logger.warning(f"Rate limit exceeded. Sleeping for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
        return await get_channel_info(channel_id)  # Retry after sleeping

async def calculate_involvement_score(channel_info):
    subscribers_count = channel_info.full_chat.participants_count
    involvement_score = subscribers_count * involvement_coefficient
    return involvement_score


async def analyze_and_forward_messages():
    global messages_sent, last_sent_time

    # Обрабатываем каналы из обеих папок
    folders = ['memes', 'cat']
    for folder in folders:
        source_channels = await get_channels_from_folder(folder)
        logger.info(f"Found channels in '{folder}' folder: {len(source_channels)} channel(s).")

        for source_channel in source_channels:
            channel_id = str(source_channel.channel_id)
            last_processed_id = processed_messages.get(channel_id, 0)

            # Получаем информацию о канале
            channel_info = await get_channel_info(source_channel)

            # Вычисляем уровень вовлечённости
            involvement_score = await calculate_involvement_score(channel_info)

            # Проверка мемов на "настоявшиеся"
            async for message in client.iter_messages(source_channel, reverse=True):
                logger.info(f"Processing message {message.id} in channel {channel_id}.")
                if isinstance(message.media, MessageMediaPhoto) and message.id > last_processed_id:
                    logger.info(f"Found photo message {message.id} that has not been processed yet.")

                    # Проверяем, настоился ли мем
                    elapsed_time = time.time() - message.date.timestamp()
                    logger.info(f"Elapsed time for message {message.id}: {elapsed_time} seconds.")
                    if elapsed_time >= meme_age_threshold:
                        logger.info(f"Found aged meme {message.id} in channel {channel_id}.")

                        if hasattr(message, 'reactions') and message.reactions:
                            reactions = message.reactions
                            logger.info(f"Message {message.id} has reactions: {reactions}")

                            positive_count = sum(
                                reaction.count for reaction in reactions.results
                                if isinstance(reaction.reaction, ReactionEmoji) and
                                reaction.reaction.emoticon in positive_reactions
                            )
                            negative_count = sum(
                                reaction.count for reaction in reactions.results
                                if isinstance(reaction.reaction, ReactionEmoji) and
                                reaction.reaction.emoticon in negative_reactions
                            )
                            total_count = positive_count + negative_count

                            logger.info(f"Positive count: {positive_count}, Negative count: {negative_count}, Total count: {total_count}")

                            if total_count > 0:
                                funny_score = positive_count / total_count
                                logger.info(f"Funny score for message {message.id}: {funny_score}")

                                # Добавим логи
                                logger.info(f"Checking conditions for reposting: funny_score >= {funny_coefficient} and involvement_score >= {spreading_coefficient}.")
                                if funny_score >= funny_coefficient and involvement_score >= spreading_coefficient:
                                    # Проверяем лимит отправки сообщений
                                    current_time = time.time()
                                    if messages_sent < max_messages_to_send and current_time - last_sent_time >= send_interval:
                                        try:
                                            await client.send_file(target_channel, message.media, caption="")
                                            messages_sent += 1
                                            logger.info(f"Reposted photo message {message.id} from {channel_id} to {target_channel}")

                                            # Обновляем ID последнего обработанного сообщения
                                            processed_messages[channel_id] = message.id
                                            with open(processed_messages_file, 'w') as f:
                                                json.dump(processed_messages, f)
                                            logger.info(f"Updated last processed message ID for {channel_id} to {message.id}")
                                        except FloodWaitError as e:
                                            logger.warning(f"Rate limit exceeded while sending message. Sleeping for {e.seconds} seconds.")
                                            await asyncio.sleep(e.seconds)  # Ждём до конца лимита

                                    if messages_sent >= max_messages_to_send:
                                        last_sent_time = current_time  # Обновляем время последней отправки
                                        messages_sent = 0  # Сбрасываем счётчик сообщений
                    else:
                        logger.info(f"Message {message.id} has not aged enough.")


async def main():
    await client.start()  # запускаем клиент
    logger.info("Client is connected")

    while True:
        await analyze_and_forward_messages()
        await asyncio.sleep(check_period * 60)  # Пауза между проверками

if __name__ == "__main__":
    client.loop.run_until_complete(main())
