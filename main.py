import asyncio
import os

from dotenv import load_dotenv

from utils import main

load_dotenv()

art_type = ""
bot_command = "/imagine"
topic = ""
descriptors = ""

channel_url = os.environ.get("DISCORD_CHANNEL_URL")
# PROMPT = f"Generate a Midjourney prompt to result in an {art_type} image about {topic} include {descriptors}"

PROMPTS = [
    "Generate a picture of a whale in a sunny day",
    "Generate a picture of a lion wearing a suit in the office",
]

asyncio.run(main(bot_command, channel_url, PROMPTS))
