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

if __name__ == "__main__":
    # Read prompts from a file
    PROMPTS = []

    with open("prompts.txt", "r") as f:
        line = f.readline()
        while line:
            PROMPTS.append(line.strip())
            line = f.readline()

    print(PROMPTS)

    asyncio.run(main(bot_command, channel_url, PROMPTS))
