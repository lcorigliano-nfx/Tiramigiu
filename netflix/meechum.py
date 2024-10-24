import os
import pickle
import random
import string
from typing import Optional
from urllib.parse import urlparse

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import webdriver

from classes.log import Log


class Meechum:
    def __init__(self, profile_dir: Optional[str] = None):
        self.logger = Log().get_logger(self.__class__.__name__)
        self.profile_dir = profile_dir or './profile'
        os.makedirs(self.profile_dir, exist_ok=True)
        self.session_file = os.path.join(self.profile_dir, 'session.pkl')
        self.session = requests.Session()
        self.load_session()
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'priority': 'u=1, i',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/130.0.0.0 Safari/537.36')
        }
        self.session.headers.update(self.headers)

    def save_session(self) -> None:
        with open(self.session_file, 'wb') as f:
            pickle.dump(self.session, f)

    def load_session(self) -> None:
        if os.path.exists(self.session_file):
            with open(self.session_file, 'rb') as f:
                self.session = pickle.load(f)
                self.logger.debug("Loaded cookies:")
                for cookie in self.session.cookies:
                    self.logger.debug(cookie)

    def authenticate(self, redirect_url: str) -> None:
        def generate_random_string(length: int = 32) -> str:
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

        params = {
            'client_id': 'sourcedeliveriesui',
            'scope': 'default+sourcedeliveriesui+studiogateway+jet_sap_sap_ui_backlot_ui-prod+studioplayback+e2eToken',
            'response_type': 'code',
            'redirect_uri': redirect_url,
            'state': generate_random_string(),
            'nonce': generate_random_string(),
            'auth_strategy': 'NetflixPartnerLogin'
        }
        base_url = 'https://meechum.netflix.com/as/authorization.oauth2'
        auth_url = f"{base_url}?{requests.compat.urlencode(params)}"

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-infobars")
        options.add_experimental_option("excludeSwitches", ['enable-automation'])
        options.add_argument("--window-size=640,800")
        options.add_argument("--no-sandbox")
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument(f"--app={auth_url}")

        driver = webdriver.Chrome(options=options)
        try:
            self.logger.info("Attempting automatic authentication...")
            success = False

            # Wait for the user to complete the login
            while not success:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                for request in driver.requests:
                    if request.response:
                        parsed_url = urlparse(request.url)
                        if (parsed_url.netloc == urlparse(redirect_url).netloc and
                            request.response.status_code in [302, 200] and
                            "error_description" not in request.url):
                            self.logger.info("Login successful via redirect.")
                            request.abort()
                            success = True
                            break

            # After login, navigate to the redirect URL to capture cookies
            driver.get(redirect_url)
            self.logger.info(f"Navigating to {redirect_url} to capture cookies.")
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            # Transfer cookies from the browser session to requests.Session
            for cookie in driver.get_cookies():
                self.logger.debug(cookie)
                self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
            self.save_session()
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
        finally:
            driver.quit()