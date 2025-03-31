import asyncio
import os
import random
import sys

from dotenv import load_dotenv
from loguru import logger
from playwright.async_api import async_playwright
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
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


class FileProcessor(QThread):
    progress = pyqtSignal(int)
    completed = pyqtSignal()

    def __init__(self, input_file, output_dir, upscale):
        super().__init__()
        self.input_file = input_file
        self.output_dir = output_dir
        self.upscale = upscale  # Upscale option
        self.bot_command = "/imagine"
        self.channel_url = os.environ.get("DISCORD_CHANNEL_URL")
        self.PROMPTS = []

    def run(self):
        with open(self.input_file, "r") as f:
            line = f.readline()
            while line:
                if line.strip():
                    self.PROMPTS.append(line.strip())
                line = f.readline()
        # logger.info(f"PROMPTS: {self.PROMPTS}")
        logger.info(f"Channel URL: {self.channel_url}")
        if len(self.PROMPTS) != 0:
            asyncio.run(
                self.process_file_async()
            )  # Run the async function inside the thread
        else:
            logger.error("No prompts found in the input file.")
            self.completed.emit()

    async def process_file_async(self):
        try:
            total_prompts = len(self.PROMPTS)
            browser = None
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
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
                        self.completed.emit()
                    random_sleep()

        except Exception as e:
            logger.error(f"Error occurred: {e} while executing the main function.")
            raise e
        finally:
            if browser:
                await browser.close()

    async def write_to_file(self, filename, content):
        """Asynchronously writes content to a file."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_write, filename, content)

    def _sync_write(self, filename, content):
        """Synchronous write function to be used with asyncio's executor."""
        with open(filename, "w", encoding="utf-8") as out_file:
            out_file.write(content)


class TextFileProcessorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("📄 Midjourney bot")
        self.setGeometry(400, 200, 450, 400)
        self.setStyleSheet(self.load_styles())

        layout = QVBoxLayout()

        self.label_input = QLabel("📂 No input file selected")
        self.label_output = QLabel("📁 No output directory selected")

        self.btn_select_input = QPushButton("📑 Select Input File")
        self.btn_select_output = QPushButton("📂 Select Output Directory")
        self.btn_discard = QPushButton("🗑️ Discard Selection")
        self.chk_upscale = QCheckBox("🔼 Enable Upscale Mode")  # Upscale mode checkbox
        self.btn_process = QPushButton("🚀 Process File")
        self.progress_bar = QProgressBar()

        layout.addWidget(self.label_input)
        layout.addWidget(self.btn_select_input)
        layout.addWidget(self.label_output)
        layout.addWidget(self.btn_select_output)
        layout.addWidget(self.btn_discard)
        layout.addWidget(self.chk_upscale)
        layout.addWidget(self.btn_process)
        layout.addWidget(self.progress_bar)

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

    def on_processing_done(self):
        QMessageBox.information(self, "✅ Done", "Processing completed successfully!")

    def load_styles(self):
        return """
        QWidget {
            background-color: #2E2E2E;
            color: #E0E0E0;
            font-family: Arial;
            font-size: 14px;
        }
        QLabel {
            font-size: 14px;
            padding: 5px;
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 8px;
            padding: 10px;
            font-size: 14px;
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
        QProgressBar {
            border: 2px solid #555;
            border-radius: 5px;
            text-align: center;
            background-color: #444;
            height: 20px;
        }
        QProgressBar::chunk {
            background-color: #00BCF2;
            width: 10px;
        }
        QCheckBox {
            font-size: 14px;
            color: #E0E0E0;
            padding: 5px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            background-color: #444;
            border: 2px solid #888;
        }
        QCheckBox::indicator:checked {
            background-color: #00BCF2;
            border: 2px solid #00A0D2;
        }
        QMessageBox {
            background-color: #3E3E3E;
            color: #E0E0E0;
        }
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TextFileProcessorApp()
    window.show()
    sys.exit(app.exec())
