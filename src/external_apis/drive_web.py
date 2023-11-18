from selenium import webdriver
from tempfile import mkdtemp
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from pathlib import Path
from dotenv import dotenv_values


dotenv_path = Path(__file__).parent.parent.parent / '.env'
env_values = dotenv_values(dotenv_path)


class _BrowserDriver:
    wait_time = 5
    url = env_values['CONTROL_URL']
    login = env_values['CONTROL_LOGIN']
    password = env_values['CONTROL_PASSWORD']

    def __init__(self):
        options = webdriver.ChromeOptions()
        service = webdriver.ChromeService("/opt/chromedriver")

        options.binary_location = '/opt/chrome/chrome'
        options.add_argument("--headless=new")
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280x1696")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-dev-tools")
        options.add_argument("--no-zygote")
        options.add_argument(f"--user-data-dir={mkdtemp()}")
        options.add_argument(f"--data-path={mkdtemp()}")
        options.add_argument(f"--disk-cache-dir={mkdtemp()}")
        options.add_argument("--remote-debugging-port=9222")

        self.driver = webdriver.Chrome(options=options, service=service)

    def driver_wait(self):
        return WebDriverWait(self.driver, self.wait_time)

    def wait_for_element_and_click(self, *args, click: bool = True):
        element = self.driver_wait().until(ec.element_to_be_clickable(*args))
        if click:
            element.click()
        return element

    def wait_for_element_visibility(self, *args):
        return self.driver_wait().until(ec.visibility_of_element_located(*args))
