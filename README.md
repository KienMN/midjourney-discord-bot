# Midjourney Discord Bot

## Introduction

Automate submit prompts and download images from Midjourney and Discord.
This tool works with Discord web version.

Reference: https://github.com/passivebot/midjourney-automation-bot

## Prerequisite
- Install Python from website python.org
- Verify python installation by open terminal/powershell and run
```
python --version

# Expected output: Python <version>
```
- Create a virtual environment. Use terminal/powershell and go to folder you want to store the virtual environment
```
# Change directory to the folder storing the environment
cd <folder_path>

# Create a virtual environment
python -m venv <env-name>
```

- Activate the virtual environment. It is used to run python code. This step is needed everytimes you want to run the code in terminal/powershell.
```
# Windows
<folder_path>/<env-name>/Scripts/Activate.ps1
# MacOS
source <folder_path>/<env-name>/bin/activate
```

- Install Python libraries.
Change directory to the folder holding this `requirement.txt` file and run command
```
pip install -r requirement.txt
```

- Install Playwright dependencies. This tool helps to use browser.
```
playwright install
```

## Usage
### Start the bot with Command lines
- Create a `.env` file and provide information similar to `.env.sample`
- Create a `prompts.txt` file containing your prompts, 1 per line.
- Run chrome in debugging mode by typing this command in
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```
- Use a Chrome profile that has already logged in to Discord.
- Run command to start bot.
```
python main.py
```

- If you prefer a UI version, run this command instead
```
python ui.py
```

### Package the code in an EXE file
You can package the code in an EXE file and skip all starting steps overhead. But you need to build the application first.

#### Build EXE file
Use activated environment in terminal/powershell
```
# Change directory to the folder storing `ui.py` file
cd <code_folder_path>

# Run command to build exe file
pyarmor gen -r --pack onefile -b <MAC address> ui.py
```

Note:
- If you do not want to lock application for a specific computer, omit `-b <MAC address>` in the above command.
- Clean the folder (delete build files) before starting building a new EXE file.

#### Use EXE file
- Run chrome in debugging mode by typing this command in
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

- Open EXE file in `<code_folder_path>/dist`

#### Transfer EXE file to a new computer
- Install Python and create virtual environment in the new computer (refer to Prerequisite).
- Copy `requirement.txt` to the new computer and install libraries (requirement, and playwright).
- Copy EXE file to the new computer.
- Run chrome in debugging mode and open EXE file.
