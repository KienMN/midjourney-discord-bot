from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import Playwright, async_playwright
from pydantic import BaseModel
from loguru import logger
from typing import Literal


class BrowserConfig(BaseModel):
    headless: bool = False
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36  (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
    )
    timeout: int = 30
    cdp_url: str | None = None
    browser_class: Literal["chromium", "firefox", "webkit"] = "chromium"


class BrowserContextConfig(BaseModel):
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36  (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
    )


class Browser:
    """Playwright browser."""

    def __init__(self, config: BrowserConfig):
        self.config = config or BrowserConfig()
        self.playwright: Playwright | None = None
        self.playwright_browser: PlaywrightBrowser | None = None

    async def new_context(self, config: BrowserContextConfig | None = None):
        browser_config = self.config.model_dump() if self.config else {}
        context_config = config.model_dump() if config else {}
        merge_config = {**browser_config, **context_config}
        return BrowserContext(browser=self, config=BrowserContextConfig(**merge_config))

    async def get_playwright_browser(self) -> PlaywrightBrowser:
        if self.playwright_browser is None:
            return await self._init()
        return self.playwright_browser

    async def _init(self):
        playwright = await async_playwright().start()
        self.playwright = playwright

        browser = self._setup_browser(playwright)
        self.playwright_browser = browser

        return self.playwright_browser

    async def _setup_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        try:
            if self.config.cdp_url:
                return await self._setup_remote_cdp_browser(playwright)
            return await self._setup_builtin_browser(playwright)
        except Exception as e:
            logger.exception("Failed to initialize playwright browser {e}")
            raise

    async def _setup_remote_cdp_browser(
        self, playwright: Playwright
    ) -> PlaywrightBrowser:
        if 'firefox' in (self.config.browser_binary_path or '').lower():
            raise ValueError(
                'CDP has been deprecated for firefox, check: https://fxdx.dev/deprecating-cdp-support-in-firefox-embracing-the-future-with-webdriver-bidi/'
            )
        if not self.config.cdp_url:
            raise ValueError('CDP URL is required')
        logger.info(f'🔌  Connecting to remote browser via CDP {self.config.cdp_url}')
        browser_class = getattr(playwright, self.config.browser_class)
        browser = await browser_class.connect_over_cdp(self.config.cdp_url)
        return browser

    async def _setup_builtin_browser(self, playwright: Playwright) -> PlaywrightBrowser:
        pass


class BrowserContext:
    def __init__(self, browser: Browser, config: BrowserContextConfig):
        self.config = config or BrowserContextConfig()
        self.browser = browser
