import json
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.types import MessageMediaPhoto, DialogFilter, InputPeerChannel, ReactionEmoji
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetDialogFiltersRequest

# Load configuration from config.json
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the client
client = TelegramClient(StringSession(string_session), api_id, api_hash)

# Filename to store the last processed message ID for each channel
processed_messages_file = 'processed_messages.json'

# Load the last processed message ID for each channel from the file
try:
    with open(processed_messages_file, 'r') as f:
        processed_messages = json.load(f)
    if isinstance(processed_messages, list):
        processed_messages = {}
except (FileNotFoundError, json.JSONDecodeError):
    processed_messages = {}

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
    full_channel = await client(GetFullChannelRequest(channel_id))
    return full_channel

async def calculate_involvement_score(channel_info):
    # Example: Calculate involvement score based on subscribers count and other metrics
    subscribers_count = channel_info.full_chat.participants_count
    involvement_score = subscribers_count * involvement_coefficient
    return involvement_score

async def analyze_and_forward_messages():
    source_channels = await get_channels_from_folder('memes')
    logger.info(f"Found channels in 'memes' folder: {source_channels}")

    for source_channel in source_channels:
        channel_id = str(source_channel.channel_id)
        last_processed_id = processed_messages.get(channel_id, 0)
        
        # Get channel information
        channel_info = await get_channel_info(source_channel)
        
        # Calculate involvement score
        involvement_score = await calculate_involvement_score(channel_info)
        
        async for message in client.iter_messages(source_channel):
            if isinstance(message.media, MessageMediaPhoto) and message.id > last_processed_id:
                logger.info(f"Message {message.id}: {message.views}")

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

                    if total_count > 0:
                        funny_score = positive_count / total_count

                        if funny_score >= funny_coefficient and involvement_score >= spreading_coefficient:
                            try:
                                await client.send_message(target_channel, message)
                                logger.info(
                                    f"Reposted photo message {message.id} "
                                    f"from {channel_id} to {target_channel}"
                                )
                                processed_messages[channel_id] = message.id
                                with open(processed_messages_file, 'w') as f:
                                    json.dump(processed_messages, f)
                                logger.info(f"Updated last processed message ID for {channel_id} to {message.id}")
                                
                                # Задержка перед отправкой следующего сообщения
                                await asyncio.sleep(10)  # Установи задержку в секундах между сообщениями
                            except FloodWaitError as e:
                                logger.warning(f"FloodWaitError: Подождем {e.seconds} секунд перед повтором.")
                                await asyncio.sleep(e.seconds)  # Ожидание на основе FloodWaitError

                else:
                    logger.info(f"Message {message.id} has no reactions")

async def main():
    await client.start()  # start the client
    logger.info("Client is connected")

    while True:
        await analyze_and_forward_messages()
        await asyncio.sleep(check_period * 60)  # in minutes

if __name__ == "__main__":
    client.loop.run_until_complete(main())
