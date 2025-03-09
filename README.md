## Midjourney Discord Bot

Automate submit prompts and download images from Midjourney and Discord.
This tool works with Discord web.

Reference: https://github.com/passivebot/midjourney-automation-bot

## Usage
- Create a `.env` file and provide information similar to `.env.sample`
- Create a `prompts.txt` file containing your prompts, 1 per line.
- Run chrome in debugging mode by typing this command in
```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```
- Use a Chrome profile that has already logged in to Discord.
- Run commands to install dependencies and start bot.
```
pip install -r requirements.txt
playwright install
python main.py
```
