from mj_bot import Browser, BrowserConfig, Controller

browser = Browser(
	config=BrowserConfig(
		headless=False,
		cdp_url='http://localhost:9222',
	)
)
controller = Controller()

print(controller.registry.get_prompt_description())