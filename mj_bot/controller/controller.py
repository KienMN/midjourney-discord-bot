import asyncio
import random
import re
import shutil

import requests
from loguru import logger
from playwright.async_api import Page
import uuid

from mj_bot.controller.registry import Registry
from mj_bot.controller.view import (
    DiscordBotCommandAction,
    DiscordChannelAction,
    DiscordMidjourneyImageOutput,
    DiscordMidjourneyPromptAction,
    NoParamsAction,
    WaitAction
)


class Controller:
    def __init__(self):
        self.registry = Registry()

        @self.registry.action(
            "Go to a discord channel", param_model=DiscordChannelAction
        )
        async def open_discord_channel(params: DiscordChannelAction, page: Page):
            try:
                await page.goto(f"{params.channel_url}")
                await asyncio.sleep(random.randint(1, 5))
                await page.wait_for_load_state("networkidle")
                logger.info("Successfully opened the appropriate channel.")

            except Exception as e:
                logger.error(
                    f"An error occurred while opening the channel and entering the bot command: {e}"
                )
                raise e

        @self.registry.action(
            "Select a command for the bot in the chat bar.",
            param_model=DiscordBotCommandAction,
        )
        async def send_bot_command(params: DiscordBotCommandAction, page: Page):
            try:
                logger.info("Clicking on chat bar.")
                chat_bar = page.get_by_role(
                    "textbox", name=params.chat_message_placeholder
                )
                await asyncio.sleep(random.randint(1, 3))

                logger.info("Typing in bot command")
                await chat_bar.fill(params.command)

                logger.info("Selecting the prompt option in the suggestions menu")
                prompt_option_selector = "#autocomplete-0 > .base__13533"
                await page.wait_for_selector(
                    prompt_option_selector, state="visible", timeout=10000
                )
                prompt_option = page.locator(prompt_option_selector)
                await asyncio.sleep(random.randint(1, 3))
                await prompt_option.click()

            except Exception as e:
                logger.exception(
                    f"An error occurred while sending the bot command: {e}"
                )
                raise e

        @self.registry.action(
            "Filling prompt and submit to Midjourney bot",
            param_model=DiscordMidjourneyPromptAction,
        )
        async def submit_midjourney_prompt(
            params: DiscordMidjourneyPromptAction, page: Page
        ):
            try:
                prompt_text = params.prompt
                # await asyncio.sleep(random.randint(1, 5))
                pill_value_locator = "span.optionPillValue__1464f"
                await page.fill(pill_value_locator, prompt_text)
                await asyncio.sleep(random.randint(3, 5))
                await page.keyboard.press("Enter")
                logger.info(f"Successfully submitted prompt: {prompt_text}")
            except Exception as e:
                logger.error(f"An error occurred while submitting the prompt: {e}")
                raise e

        @self.registry.action(
            "Wait for and select upscale options.", param_model=NoParamsAction
        )
        async def wait_and_select_upscale_options(params: NoParamsAction, page: Page):
            number_of_images: int = 1
            timeout = 120  # int(os.environ.get("WAIT_FOR_UPSCALE_TIMEOUT", 120))
            try:
                while True:
                    last_message = await get_last_message(page)

                    # Check for 'U1' in the last message
                    if "U1" in last_message:
                        logger.info(
                            "Found upscale options. Attempting to upscale all generated images."
                        )

                        random_selection = random.sample(
                            ["U1", "U2", "U3", "U4"], number_of_images
                        )

                        try:
                            for selection in random_selection:
                                await select_upscale_option(page, selection)
                                await asyncio.sleep(random.randint(5, 10))
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

                        break  # Exit the loop when upscale options have been found and selected

                    else:
                        if timeout % 30 == 0:
                            logger.info(
                                "Upscale options not yet available, waiting... Timeout after %s",
                                timeout,
                            )
                        await asyncio.sleep(10)
                        timeout -= 10
                        if timeout <= 0:
                            raise TimeoutError(
                                "Timeout while waiting for upscale options."
                            )
            except Exception as e:
                logger.error(f"An error occurred while finding the last message: {e}")
                raise e

        @self.registry.action(
            "Wait for the Upscale option to be available and select that option.",
            param_model=NoParamsAction,
        )
        async def wait_and_select_super_upscale_options(
            params: NoParamsAction, page: Page
        ):
            number_of_images: int = 1
            timeout = 120  # int(os.environ.get("WAIT_FOR_UPSCALE_TIMEOUT", 120))

            try:
                # Repeat until upscale options are found
                while True:
                    last_message = await get_last_message(page)

                    # Check for 'Upscale' in the last message
                    if "Upscale (Subtle)" in last_message:
                        logger.info(
                            "Found upscale options. Attempting to upscale generated images."
                        )

                        random_selection = random.sample(
                            ["Upscale (Subtle)"], number_of_images
                        )

                        try:
                            for selection in random_selection:
                                await select_upscale_option(page, selection)
                                await asyncio.sleep(random.randint(5, 10))
                        except Exception as e:
                            logger.error(
                                f"An error occurred while selecting upscale options: {e}"
                            )
                            raise e

                        break  # Exit the loop when upscale options have been found and selected

                    else:
                        if timeout % 30 == 0:
                            logger.info(
                                "Upscale options not yet available, waiting... Timeout after %s",
                                timeout,
                            )
                        await asyncio.sleep(10)
                        timeout -= 10
                        if timeout <= 0:
                            raise TimeoutError(
                                "Timeout while waiting for upscale options."
                            )

            except Exception as e:
                logger.error(f"An error occurred while finding the last message: {e}")
                raise e

        @self.registry.action(
            "Download upscaled images", param_model=DiscordMidjourneyImageOutput
        )
        async def download_upscaled_images(
            params: DiscordMidjourneyImageOutput,
            page: Page,
        ):
            prompt_text = params.prompt
            number_of_images = 1
            sequence_number = params.sequence_number
            output_dir = params.output_dir
            timeout: int = 600
            try:
                while True:
                    messages = await page.query_selector_all(".messageListItem__5126c")
                    last_k_messages = messages[-number_of_images:]

                    for message in last_k_messages:
                        message_text = await message.evaluate_handle(
                            "(node) => node.innerText"
                        )
                        message_text = str(message_text)

                    # Comment for cleaner logs
                    # logger.info("Message text: {}", message_text)

                    if "Vary (Strong)" in message_text and "Web" in message_text:
                        try:
                            image_elements = await page.query_selector_all(
                                ".originalLink_af017a"
                            )
                            last_k_images = image_elements[-number_of_images:]

                            for i, image in enumerate(last_k_images):
                                src = await image.get_attribute("href")
                                url = src
                                if not sequence_number:
                                    response = re.sub(
                                        r"[^a-zA-Z0-9\s]", "", prompt_text
                                    )
                                    response = response.replace(" ", "_").replace(
                                        ",", "_"
                                    )
                                    response = re.sub(r'[\<>:"/|?*]', "", response)
                                    response = response.replace("\n\n", "_")
                                    response = response[:50].rstrip(". ") + str(
                                        uuid.uuid1()
                                    )
                                elif number_of_images > 1:
                                    response = f"pic_{sequence_number}_{i + 1}_of_{number_of_images}"
                                else:
                                    response = f"pic_{sequence_number}"

                                download_response = requests.get(url, stream=True)

                                with open(
                                    f"{output_dir or "."}/{str(response)}.png", "wb"
                                ) as out_file:
                                    shutil.copyfileobj(download_response.raw, out_file)
                                del download_response

                        except Exception as e:
                            logger.info(
                                f"An error occurred while downloading the images: {e}"
                            )
                        finally:
                            break

                    else:
                        if timeout <= 0:
                            raise TimeoutError(
                                "Timeout while waiting for images to be available."
                            )
                        if timeout % 60 == 0:
                            logger.info(
                                f"Images not yet available, waiting... Timeout after {timeout}"
                            )

                        await asyncio.sleep(10)
                        timeout -= 10

            except Exception as e:
                logger.info(f"An error occurred while finding the last message: {e}")

        @self.registry.action(
            "Wait", param_model=WaitAction
        )
        async def wait(params: WaitAction):
            await asyncio.sleep(random.randint(params.seconds - params.range_, params.seconds))

        async def get_last_message(page: Page) -> str:
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
                last_message_text = await last_message.evaluate(
                    "(node) => node.innerText"
                )

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

        async def select_upscale_option(page: Page, option_text: str):
            """
            Function to select an upscale option based on the provided text.

            Parameters:
            - page: The page object representing the current browser context.
            - option_text (str): The text of the upscale option to select.

            Returns:
            - None
            """
            try:
                upscale_option = page.locator(
                    f"button:has-text('{option_text}')"
                ).locator("nth=-1")
                if not upscale_option:
                    logger.error(f"No upscale option found with text: {option_text}.")
                    raise ValueError(
                        f"No upscale option found with text: {option_text}."
                    )

                await upscale_option.click()
                logger.info(f"Successfully clicked {option_text} upscale option.")

            except Exception as e:
                logger.error(
                    f"An error occurred while selecting the upscale option: {e}"
                )
                raise e
