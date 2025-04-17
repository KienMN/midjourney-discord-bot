import asyncio
import os
import random
import sys
from datetime import datetime

from dotenv import load_dotenv, set_key
from loguru import logger
from playwright.async_api import async_playwright
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils import (
    download_upscaled_images,
    generate_prompt_and_submit_command,
    open_discord_channel,
    random_sleep,
    send_bot_command,
    wait_and_select_upscale_options,
    wait_and_select_super_upscale_options,
)

load_dotenv()


def configure_logging():
    """Configure logging with a unique filename for each run."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/midjourney_bot_{timestamp}.log"
    
    # Remove default handler and add file handler with proper formatting
    logger.remove()
    logger.add(
        log_file,
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        backtrace=True,
        diagnose=True
    )
    logger.add(
        lambda msg: print(msg),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        backtrace=True,
        diagnose=True
    )
    
    logger.info(f"Logging configured. Log file: {log_file}")


class FileProcessor(QThread):
    progress = pyqtSignal(int)
    completed = pyqtSignal(str, str)  # Changed to include status (title, message)

    def __init__(self, input_file, output_dir, upscale):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.upscale = upscale  # Upscale option
        self.bot_command = "/imagine"
        self.channel_url = os.environ.get("DISCORD_CHANNEL_URL")
        self.PROMPTS = []

    def run(self):
        try:
            with open(self.input_file, "r") as f:
                line = f.readline()
                while line:
                    if line.strip():
                        self.PROMPTS.append(line.strip())
                    line = f.readline()
            logger.info(f"Channel URL: {self.channel_url}")
            if len(self.PROMPTS) != 0:
                asyncio.run(
                    self.process_file_async()
                )  # Run the async function inside the thread
                self.completed.emit("✅ Success", "All images have been processed successfully!")
            else:
                logger.error("No prompts found in the input file.")
                self.completed.emit("⚠️ Error", "No prompts found in the input file.")
        except Exception as e:
            logger.exception("Error in FileProcessor.run()")  # This will log the full traceback
            self.completed.emit("❌ Error", f"An error occurred: {str(e)}")

    async def process_file_async(self):
        try:
            total_prompts = len(self.PROMPTS)
            page = None
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                try:
                    default_context = browser.contexts[0]
                    page = await default_context.new_page()

                    await open_discord_channel(page, self.channel_url)

                    for i in range(total_prompts):
                        prompt = self.PROMPTS[i]
                        logger.info("Entering the specified bot command.")
                        await send_bot_command(page, self.bot_command)
                        await asyncio.sleep(random.randint(1, 5))

                        logger.info("Submit command.")
                        await generate_prompt_and_submit_command(page, prompt)
                        await asyncio.sleep(random.randint(1, 5))

                        logger.info("Wait and select upscale options.")
                        await wait_and_select_upscale_options(
                            page,
                            number_of_images=int(
                                os.environ.get("NUMBER_OF_UPSCALED_IMAGES")
                            ),
                        )
                        await asyncio.sleep(random.randint(1, 5))

                        if self.upscale:
                            await wait_and_select_super_upscale_options(
                                page, number_of_images=1
                            )

                        logger.info("Download upscaled images.")
                        await download_upscaled_images(
                            page,
                            prompt,
                            number_of_images=int(
                                os.environ.get("NUMBER_OF_UPSCALED_IMAGES")
                            ),
                            sequence_number=i + 1,
                            output_dir=self.output_dir,
                            timeout=int(os.environ.get("WAIT_FOR_DOWNLOAD_TIMEOUT", 600))
                        )

                        logger.info(f"Iteration {i+1} completed.")
                        self.progress.emit((i + 1) * 100 // total_prompts)
                        
                        if i + 1 == total_prompts:
                            break
                        random_sleep()

                except Exception as e:
                    # logger.error(f"Error occurred: {e} while executing the main function.")
                    # self.completed.emit("❌ Error", f"An error occurred while processing: {str(e)}")
                    raise e
                finally:
                    if page:
                        try:
                            await page.close()
                            logger.info("Page closed successfully.")
                        except Exception as e:
                            logger.error(f"Error closing page: {e}")
                    try:
                        await browser.close()
                        logger.info("Browser closed successfully.")
                    except Exception as e:
                        logger.error(f"Error closing browser: {e}")

        except Exception as e:
            # logger.error(f"Error in process_file_async: {e}")
            # self.completed.emit("❌ Error", f"An error occurred: {str(e)}")
            raise e

    async def write_to_file(self, filename, content):
        """Asynchronously writes content to a file."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_write, filename, content)

    def _sync_write(self, filename, content):
        """Synchronous write function to be used with asyncio's executor."""
        with open(filename, "w", encoding="utf-8") as out_file:
            out_file.write(content)


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.env_file = '.env'
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Discord Channel URL
        url_group = QWidget()
        url_layout = QVBoxLayout()
        url_layout.setSpacing(5)
        
        url_label = QLabel("Discord Channel URL:")
        url_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter Discord channel URL (e.g., https://discord.com/channels/...)")
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
            }
        """)

        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_group.setLayout(url_layout)

        # Discord Channel Message Placeholder
        placeholder_group = QWidget()
        placeholder_layout = QVBoxLayout()
        placeholder_layout.setSpacing(5)
        
        placeholder_label = QLabel("Discord Channel Message Placeholder:")
        placeholder_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.placeholder_input = QLineEdit()
        self.placeholder_input.setPlaceholderText("Enter message placeholder (e.g., 'Message #channel')")
        self.placeholder_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
            }
        """)

        placeholder_layout.addWidget(placeholder_label)
        placeholder_layout.addWidget(self.placeholder_input)
        placeholder_group.setLayout(placeholder_layout)

        # Save button
        button_group = QWidget()
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        self.save_button = QPushButton("💾 Save Settings")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.save_button.clicked.connect(self.save_settings)

        button_layout.addWidget(self.save_button)
        button_group.setLayout(button_layout)

        # Add all groups to main layout
        layout.addWidget(url_group)
        layout.addWidget(placeholder_group)
        layout.addWidget(button_group)
        layout.addStretch()

        self.setLayout(layout)

    def load_settings(self):
        """Load settings from .env file."""
        try:
            if os.path.exists(self.env_file):
                load_dotenv(self.env_file)
                self.url_input.setText(os.environ.get("DISCORD_CHANNEL_URL", ""))
                self.placeholder_input.setText(os.environ.get("DISCORD_CHANNEL_MESSAGE_PLACEHOLDER", ""))
                logger.info("Settings loaded successfully")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            QMessageBox.critical(self, "❌ Error", f"Failed to load settings: {str(e)}")

    def save_settings(self):
        """Save settings to .env file."""
        try:
            # Get the values from the input fields
            channel_url = self.url_input.text().strip()
            message_placeholder = self.placeholder_input.text().strip()

            # Validate inputs
            if not channel_url:
                QMessageBox.warning(self, "⚠️ Warning", "Discord Channel URL cannot be empty!")
                return
            if not message_placeholder:
                QMessageBox.warning(self, "⚠️ Warning", "Message Placeholder cannot be empty!")
                return

            # Create .env file if it doesn't exist
            if not os.path.exists(self.env_file):
                with open(self.env_file, 'w') as f:
                    f.write('')

            # Update environment variables
            set_key(self.env_file, 'DISCORD_CHANNEL_URL', channel_url)
            set_key(self.env_file, 'DISCORD_CHANNEL_MESSAGE_PLACEHOLDER', message_placeholder)

            # Reload environment variables
            load_dotenv(self.env_file, override=True)

            QMessageBox.information(self, "✅ Success", "Settings saved successfully!")
            logger.info("Settings updated successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "❌ Error", f"Failed to save settings: {str(e)}")


class TextFileProcessorApp(QWidget):
    def __init__(self):
        super().__init__()
        configure_logging()  # Configure logging when UI starts
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("📄 Midjourney Bot")
        self.setGeometry(400, 200, 700, 600)  # Increased window size
        self.setStyleSheet(self.load_styles())

        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create main tab
        main_tab = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Input section
        input_group = QWidget()
        input_layout = QVBoxLayout()
        input_layout.setSpacing(5)
        
        self.label_input = QLabel("📂 Input File")
        self.label_input.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.btn_select_input = QPushButton("📑 Select Input File")
        self.btn_select_input.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        input_layout.addWidget(self.label_input)
        input_layout.addWidget(self.btn_select_input)
        input_group.setLayout(input_layout)

        # Output section
        output_group = QWidget()
        output_layout = QVBoxLayout()
        output_layout.setSpacing(5)
        
        self.label_output = QLabel("📁 Output Directory")
        self.label_output.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.btn_select_output = QPushButton("📂 Select Output Directory")
        self.btn_select_output.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)

        output_layout.addWidget(self.label_output)
        output_layout.addWidget(self.btn_select_output)
        output_group.setLayout(output_layout)

        # Options section
        options_group = QWidget()
        options_layout = QVBoxLayout()
        options_layout.setSpacing(10)
        
        self.chk_upscale = QCheckBox("🔼 Enable Upscale Mode")
        self.chk_upscale.setStyleSheet("font-size: 14px;")

        options_layout.addWidget(self.chk_upscale)
        options_group.setLayout(options_layout)

        # Action buttons
        action_group = QWidget()
        action_layout = QVBoxLayout()
        action_layout.setSpacing(10)
        
        self.btn_process = QPushButton("🚀 Process File")
        self.btn_process.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                font-size: 16px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        self.btn_discard = QPushButton("🗑️ Clear Selection")
        self.btn_discard.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)

        action_layout.addWidget(self.btn_process)
        action_layout.addWidget(self.btn_discard)
        action_group.setLayout(action_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                height: 25px;
                font-size: 14px;
            }
        """)

        # Add all sections to main layout
        main_layout.addWidget(input_group)
        main_layout.addWidget(output_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(action_group)
        main_layout.addWidget(self.progress_bar)
        main_layout.addStretch()

        main_tab.setLayout(main_layout)

        # Create settings tab
        settings_tab = SettingsTab()

        # Add tabs to tab widget
        self.tabs.addTab(main_tab, "🖼️ Main")
        self.tabs.addTab(settings_tab, "⚙️ Settings")

        # Create main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Connect Buttons
        self.btn_select_input.clicked.connect(self.select_input_file)
        self.btn_select_output.clicked.connect(self.select_output_directory)
        self.btn_discard.clicked.connect(self.discard_selection)
        self.btn_process.clicked.connect(self.process_file)

        self.input_file = None
        self.output_dir = None

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Text File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            self.input_file = file_path
            self.label_input.setText(f"✅ Input: {file_path}")

    def select_output_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir = dir_path
            self.label_output.setText(f"✅ Output: {dir_path}")

    def discard_selection(self):
        """Clears the selected input file and output directory."""
        self.input_file = None
        self.output_dir = None
        self.label_input.setText("📂 No input file selected")
        self.label_output.setText("📁 No output directory selected")

    def process_file(self):
        if not self.input_file or not self.output_dir:
            QMessageBox.warning(
                self, "⚠️ Warning", "Please select an input file and output directory."
            )
            return

        upscale_enabled = self.chk_upscale.isChecked()
        self.progress_bar.setValue(0)
        self.processor = FileProcessor(
            self.input_file, self.output_dir, upscale_enabled
        )
        self.processor.progress.connect(self.progress_bar.setValue)
        self.processor.completed.connect(self.on_processing_done)
        self.processor.start()

    def on_processing_done(self, title, message):
        """Show the final status message."""
        if "Error" in title:
            QMessageBox.critical(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def load_styles(self):
        return """
        /* Main Window */
        QWidget {
            background-color: #2E2E2E;
            color: #E0E0E0;
            font-family: 'Segoe UI', Arial;
            font-size: 14px;
        }

        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #444;
            border-radius: 6px;
            background-color: #2E2E2E;
        }

        QTabWidget::tab-bar {
            alignment: center;
        }

        QTabBar::tab {
            background-color: #3E3E3E;
            color: #E0E0E0;
            padding: 8px 20px;
            margin: 2px;
            border: 1px solid #444;
            border-radius: 4px;
        }

        QTabBar::tab:selected {
            background-color: #0078D7;
            color: white;
        }

        QTabBar::tab:hover:!selected {
            background-color: #4E4E4E;
        }

        /* Labels */
        QLabel {
            font-size: 14px;
            padding: 8px;
            color: #E0E0E0;
        }

        /* Line Edits */
        QLineEdit {
            background-color: #3E3E3E;
            color: #E0E0E0;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 8px;
            margin: 4px;
            selection-background-color: #0078D7;
        }

        QLineEdit:focus {
            border: 1px solid #0078D7;
        }

        /* Buttons */
        QPushButton {
            background-color: #0078D7;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            margin: 4px;
            font-size: 14px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #005A9E;
        }

        QPushButton:pressed {
            background-color: #004080;
        }

        QPushButton#discard {
            background-color: #D9534F;
        }

        QPushButton#discard:hover {
            background-color: #C9302C;
        }

        /* Progress Bar */
        QProgressBar {
            border: 2px solid #555;
            border-radius: 4px;
            text-align: center;
            background-color: #3E3E3E;
            height: 20px;
            margin: 8px;
        }

        QProgressBar::chunk {
            background-color: #00BCF2;
            width: 10px;
            border-radius: 2px;
        }

        /* Checkbox */
        QCheckBox {
            font-size: 14px;
            color: #E0E0E0;
            padding: 8px;
            spacing: 8px;
        }

        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            background-color: #3E3E3E;
            border: 2px solid #555;
        }

        QCheckBox::indicator:checked {
            background-color: #00BCF2;
            border: 2px solid #00A0D2;
            image: url(check.png);
        }

        QCheckBox::indicator:hover {
            border: 2px solid #0078D7;
        }

        /* Message Box */
        QMessageBox {
            background-color: #2E2E2E;
        }

        QMessageBox QLabel {
            color: #E0E0E0;
        }

        QMessageBox QPushButton {
            min-width: 80px;
        }
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextFileProcessorApp()
    window.show()
    sys.exit(app.exec())
