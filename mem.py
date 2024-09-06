import json
import logging
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto, DialogFilter, InputPeerChannel
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetDialogFiltersRequest

# Load configuration from config.json
with open('config.json', 'r') as f:
    config = json.load(f)

# Extract configuration values
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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the Telegram client
client = TelegramClient(StringSession(string_session), api_id, api_hash)

# Filename to store the last processed message ID for each channel
processed_messages_file = 'processed_messages.json'

# Load the last processed message ID for each channel from the file
try:
    with open(processed_messages_file, 'r') as f:
        processed_messages = json.load(f)
    if isinstance(processed_messages, list):
        # If the data is a list, reinitialize as an empty dictionary
        processed_messages = {}
except (FileNotFoundError, json.JSONDecodeError):
    processed_messages = {}


async def get_channels_from_folder(folder_name):
    """ Retrieve channels from a specified Telegram folder. """
    dialog_filters = await client(GetDialogFiltersRequest())
    logger.info(f"Dialog filters: {dialog_filters}")

    # Ensure dialog_filters is a single DialogFilter object
    if isinstance(dialog_filters, list):
        dialog_filters = dialog_filters[0]

    # Extract InputPeerChannel objects from the specified folder
    for dialog_filter in dialog_filters.filters:
        if isinstance(dialog_filter, DialogFilter) and dialog_filter.title == folder_name:
            return [
                peer
                for peer in dialog_filter.include_peers
                if isinstance(peer, InputPeerChannel)]
    return []


async def get_channel_info(channel_id):
    """ Retrieve full information about a Telegram channel. """
    full_channel = await client(GetFullChannelRequest(channel_id))
    return full_channel


async def calculate_involvement_score(channel_info):
    """ Calculate involvement score based on channel's subscribers count. """
    subscribers_count = channel_info.full_chat.participants_count
    involvement_score = subscribers_count * involvement_coefficient
    return involvement_score


async def analyze_and_forward_messages(source_channels):
    """ Analyze and forward messages from specified Telegram channels. """
    for source_channel in source_channels:
        channel_id = str(source_channel.channel_id)
        logger.info(f"Analyzing channel {channel_id}")
        last_processed_id = processed_messages.get(channel_id, 0)

        channel_info = await get_channel_info(source_channel)
        involvement_score = await calculate_involvement_score(channel_info)

        # Iterate over messages in the channel
        async for message in client.iter_messages(source_channel):
            if isinstance(message.media, MessageMediaPhoto) and message.id > last_processed_id:
                logger.info(f"Message {message.id}: {message.views} views")

                # Check if the message has reactions
                if hasattr(message, 'reactions') and message.reactions:
                    reactions = message.reactions
                    logger.info(f"Message {message.id} has reactions: {reactions}")

                    # Calculate positive and negative reactions counts
                    positive_count = sum(
                        reaction.count for reaction in reactions.results
                        if reaction.reaction.emoticon in positive_reactions
                    )
                    negative_count = sum(
                        reaction.count for reaction in reactions.results
                        if reaction.reaction.emoticon in negative_reactions
                    )
                    total_count = positive_count + negative_count

                    # Calculate funny score and decide whether to forward the message
                    if total_count > 0:
                        funny_score = positive_count / total_count

                        if funny_score >= funny_coefficient and involvement_score >= spreading_coefficient:
                            await client.send_message(target_channel, message)
                            logger.info(
                                f"Reposted photo message {message.id} "
                                f"from {channel_id} to {target_channel}"
                            )
                            processed_messages[channel_id] = message.id
                            with open(processed_messages_file, 'w') as f:
                                json.dump(processed_messages, f)
                            logger.info(f"Updated last processed message ID for {channel_id} to {message.id}")
                else:
                    logger.info(f"Message {message.id} has no reactions")


async def main():
    """
    Main function to start the Telegram client, retrieve channels, and begin message analysis.
    """
    await client.start()
    logger.info("Client is connected")

    # Retrieve channels from both 'cats' and 'memes' folders
    cats_channels = await get_channels_from_folder('cats')
    memes_channels = await get_channels_from_folder('memes')

    # Combine the channels from both folders into one list
    source_channels = cats_channels + memes_channels

    logger.info(f"Found channels in 'cats' folder: {cats_channels}")
    logger.info(f"Found channels in 'memes' folder: {memes_channels}")

    while True:
        await analyze_and_forward_messages(source_channels)
        await asyncio.sleep(check_period * 60)

if __name__ == "__main__":
    # Run the main coroutine
    client.loop.run_until_complete(main())
