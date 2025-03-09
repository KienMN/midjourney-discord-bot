import asyncio
import os
import random
import re
import shutil
import time
import uuid

import openai
import requests
from loguru import logger
from playwright.async_api import Page, async_playwright


def random_sleep():
    """Sleep for a random amount of time between 1 and 5 seconds."""
    time.sleep(random.randint(50, 60))


async def open_isolated_browser(bot_command: str, channel_url: str, PROMPT: str):
    """
    Main function that starts the bot and interacts with the page.

    Parameters:
    - bot_command (str): The command for the bot to execute.
    - channel_url (str): The URL of the channel where the bot should operate.
    - PROMPT (str): The prompt text.

    Returns:
    - None
    """
    try:
        browser = None
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto("https://www.discord.com/login")

            # Get credentials securely
            # with open("credentials.txt", "r") as f:
            # email = f.readline()
            # password = f.readline()

            email = os.environ.get("DISCORD_EMAIL")
            password = os.environ.get("DISCORD_PASSWORD")

            if not email or not password:
                logger.error("Email or password not provided in credentials.txt.")
                raise ValueError("Email or password not provided in credentials.txt.")

            await page.fill("input[name='email']", email)
            await asyncio.sleep(random.randint(1, 5))
            await page.fill("input[name='password']", password)
            await asyncio.sleep(random.randint(1, 5))
            await page.click("button[type='submit']")
            await asyncio.sleep(random.randint(5, 10))
            await page.wait_for_url("https://discord.com/channels/@me", timeout=15000)
            logger.info("Successfully logged into Discord.")
            await asyncio.sleep(random.randint(1, 5))

            for i in range(1):
                await open_discord_channel(page, channel_url)
                logger.info(f"Iteration {i+1} completed.")
    except Exception as e:
        logger.error(f"Error occurred: {e} while executing the main function.")
        raise e
    finally:
        if browser:
            await browser.close()


async def main(bot_command: str, channel_url: str, PROMPTS: list[str]):
    """
    Main function that starts the bot and interacts with the page.

    Parameters:
    - bot_command (str): The command for the bot to execute.
    - channel_url (str): The URL of the channel where the bot should operate.
    - PROMPTS (str): List of text prompt.

    Returns:
    - None
    """
    try:
        browser = None
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            default_context = browser.contexts[0]
            page = await default_context.new_page()

            await open_discord_channel(page, channel_url)

            for i in range(len(PROMPTS)):
                prompt = PROMPTS[i]
                logger.info("Entering the specified bot command.")
                await send_bot_command(page, bot_command, prompt, sequence_number=i + 1)


                logger.info(f"Iteration {i+1} completed.")
                random_sleep()

    except Exception as e:
        logger.error(f"Error occurred: {e} while executing the main function.")
        raise e
    finally:
        if browser:
            await browser.close()


async def open_discord_channel(page, channel_url: str):
    """
    Function to open a Discord channel and send a bot command.

    Parameters:
    - page: The page object representing the current browser context.
    - channel_url (str): The URL of the channel to open.
    - bot_command (str): The bot command to send.
    - PROMPT (str): The prompt text.

    Returns:
    - None
    """
    try:
        await page.goto(f"{channel_url}")
        await asyncio.sleep(random.randint(1, 5))
        await page.wait_for_load_state("networkidle")
        logger.info("Successfully opened the appropriate channel.")

        # logger.info("Entering the specified bot command.")
        # await send_bot_command(page, bot_command, PROMPT)

    except Exception as e:
        logger.error(
            f"An error occurred while opening the channel and entering the bot command: {e}"
        )
        raise e


async def send_bot_command(
    page, command: str, PROMPT: str, sequence_number: int = None
):
    """
    Function to send a command to the bot in the chat bar.

    Parameters:
    - page: The page object representing the current browser context.
    - command (str): The command to send to the bot.
    - PROMPT (str): The prompt for the command.

    Returns:
    - None
    """
    try:
        logger.info("Clicking on chat bar.")
        # chat_bar = page.get_by_role("textbox", name="Message #test-text-channel")
        chat_bar = page.get_by_role("textbox", name="Nhắn #việt-hưng")
        await asyncio.sleep(random.randint(1, 5))

        logger.info("Typing in bot command")
        await chat_bar.fill(command)
        await asyncio.sleep(random.randint(1, 5))

        logger.info("Selecting the prompt option in the suggestions menu")
        prompt_option_selector = "#autocomplete-0 > .base__13533"
        await page.wait_for_selector(
            prompt_option_selector, state="visible", timeout=10000
        )
        prompt_option = page.locator(prompt_option_selector)
        await asyncio.sleep(random.randint(1, 5))
        await prompt_option.click()

        logger.info("Generating prompt using OpenAI's API.")
        await generate_prompt_and_submit_command(page, PROMPT, sequence_number)

    except Exception as e:
        logger.exception(f"An error occurred while sending the bot command: {e}")
        raise e


async def generate_prompt_and_submit_command(
    page, prompt: str, sequence_number: int = None
):
    try:
        # prompt_text = gpt3_midjourney_prompt(prompt)
        prompt_text = prompt
        await asyncio.sleep(random.randint(1, 5))
        pill_value_locator = "span.optionPillValue__1464f"
        await page.fill(pill_value_locator, prompt_text)
        await asyncio.sleep(random.randint(1, 5))
        await page.keyboard.press("Enter")
        logger.info(f"Successfully submitted prompt: {prompt_text}")
        await wait_and_select_upscale_options(page, prompt_text, sequence_number)
    except Exception as e:
        logger.error(f"An error occurred while submitting the prompt: {e}")
        raise e


def gpt3_midjourney_prompt(
    prompt: str,
    engine="text-davinci-003",
    temp=0.7,
    top_p=1.0,
    tokens=400,
    freq_pen=0.0,
    pres_pen=0.0,
) -> str:
    """
    Function to generate a prompt using the OpenAI GPT-3 model.

    Parameters:
    - prompt (str): The initial text to base the generation on.
    - engine (str): The id of the engine to use for completion.
    - temp (float): Controls randomness. Lower value means less random.
    - top_p (float): Nucleus sampling. Higher value means more random.
    - tokens (int): The maximum number of tokens to generate.
    - freq_pen (float): Alters the likelihood of choosing tokens based on their frequency.
    - pres_pen (float): Alters the likelihood of choosing tokens based on their presence in the prompt.

    Returns:
    - str: The generated text.
    """
    if not prompt:
        logger.error("Prompt cannot be empty.")
        raise ValueError("Prompt cannot be empty.")

    prompt = prompt.encode(encoding="ASCII", errors="ignore").decode()

    try:
        response = openai.Completion.create(
            engine=engine,
            prompt=prompt,
            temperature=temp,
            max_tokens=tokens,
            top_p=top_p,
            frequency_penalty=freq_pen,
            presence_penalty=pres_pen,
        )

        if not response.choices:
            logger.error("No response from OpenAI API.")
            raise ValueError("No response from OpenAI API.")

        text = response.choices[0].text.strip()

        if not text:
            logger.error("Response text cannot be empty.")
            raise ValueError("Response text cannot be empty.")

        return text

    except Exception as e:
        logger.error(f"Error occurred: {e} while generating prompt.")
        raise e


async def wait_and_select_upscale_options(
    page, prompt_text: str, sequence_number: int = None
):
    """
    Function to wait for and select upscale options.

    Parameters:
    - page: The page to operate on.
    - prompt_text (str): The text of the prompt.

    Returns:
    - None
    """
    try:
        prompt_text = prompt_text.lower()

        # Repeat until upscale options are found
        while True:
            last_message = await get_last_message(page)

            # Check for 'U1' in the last message
            if "U1" in last_message:
                logger.info(
                    "Found upscale options. Attempting to upscale all generated images."
                )
                random_selection = random.choice(["U1", "U2", "U3", "U4"])
                try:
                    await select_upscale_option(page, random_selection)
                    time.sleep(random.randint(10, 20))
                    # await select_upscale_option(page, "U2")
                    # time.sleep(random.randint(3, 5))
                    # await select_upscale_option(page, "U3")
                    # time.sleep(random.randint(3, 5))
                    # await select_upscale_option(page, "U4")
                    # time.sleep(random.randint(3, 5))
                except Exception as e:
                    logger.error(
                        f"An error occurred while selecting upscale options: {e}"
                    )
                    raise e

                await download_upscaled_images(page, prompt_text, sequence_number=sequence_number)
                break  # Exit the loop when upscale options have been found and selected

            else:
                logger.info("Upscale options not yet available, waiting...")
                await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"An error occurred while finding the last message: {e}")
        raise e


async def get_last_message(page) -> str:
    """
    Function to get the last message from the provided page.

    Parameters:
    - page: The page from which to fetch the last message.

    Returns:
    - str: The text of the last message.
    """
    try:
        messages = await page.query_selector_all(".messageListItem__5126c")
        if not messages:
            logger.error("No messages found on the page.")
            raise ValueError("No messages found on the page.")

        last_message = messages[-1]
        last_message_text = await last_message.evaluate("(node) => node.innerText")

        if not last_message_text:
            logger.error("Last message text cannot be empty.")
            raise ValueError("Last message text cannot be empty.")

        last_message_text = str(last_message_text)
        # Commented out for now, as it's not needed.
        # logger.info(f"Last message: {last_message_text}")
        return last_message_text

    except Exception as e:
        logger.error(f"Error occurred: {e} while getting the last message.")
        raise e


async def select_upscale_option(page, option_text: str):
    """
    Function to select an upscale option based on the provided text.

    Parameters:
    - page: The page object representing the current browser context.
    - option_text (str): The text of the upscale option to select.

    Returns:
    - None
    """
    try:
        upscale_option = page.locator(f"button:has-text('{option_text}')").locator(
            "nth=-1"
        )
        if not upscale_option:
            logger.error(f"No upscale option found with text: {option_text}.")
            raise ValueError(f"No upscale option found with text: {option_text}.")

        await upscale_option.click()
        logger.info(f"Successfully clicked {option_text} upscale option.")

    except Exception as e:
        logger.error(f"An error occurred while selecting the upscale option: {e}")
        raise e


async def download_upscaled_images(
    page, prompt_text: str, number_of_images=1, sequence_number: int = None
):
    try:
        messages = await page.query_selector_all(".messageListItem__5126c")
        last_four_messages = messages[-number_of_images:]

        for message in last_four_messages:
            message_text = await message.evaluate_handle("(node) => node.innerText")
            message_text = str(message_text)

        # Comment for cleaner logs
        # logger.info("Message text: {}", message_text)

        if "Vary (Strong)" in message_text and "Web" in message_text:
            try:
                image_elements = await page.query_selector_all(".originalLink_af017a")
                last_four_images = image_elements[-number_of_images:]

                for image in last_four_images:
                    src = await image.get_attribute("href")
                    url = src
                    if not sequence_number:
                        response = re.sub(r"[^a-zA-Z0-9\s]", "", prompt_text)
                        response = response.replace(" ", "_").replace(",", "_")
                        response = re.sub(r'[\<>:"/|?*]', "", response)
                        response = response.replace("\n\n", "_")
                        response = response[:50].rstrip(". ") + str(uuid.uuid1())
                    else:
                        response = f"pic_{sequence_number}"

                    download_response = requests.get(url, stream=True)

                    with open(f"{str(response)}.png", "wb") as out_file:
                        shutil.copyfileobj(download_response.raw, out_file)
                    del download_response

            except Exception as e:
                logger.info(f"An error occurred while downloading the images: {e}")

        else:
            await download_upscaled_images(page, prompt_text)

    except Exception as e:
        logger.info(f"An error occurred while finding the last message: {e}")
