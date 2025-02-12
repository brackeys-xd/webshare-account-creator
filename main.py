import json
import os
import re
import time
import random
import requests
import logging
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service  # new import
import random

# Load configuration
with open("config.json", "r") as f:
    config = json.load(f)

# ANSI color codes
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

# Set up minimal logging for our own process.
logging.basicConfig(level=logging.INFO, format='%(message)s')
# Suppress selenium's debug logs.
logging.getLogger('selenium.webdriver.remote.remote_connection').setLevel(logging.WARNING)

ELEMENT_LOAD_WAIT_SEC = config.get("ELEMENT_LOAD_WAIT_SEC", 30)
DELAY_SEC = config.get("DELAY_SEC", 5)
EXTENSION_PATH = config.get("EXTENSION_PATH", "extension.crx")

def preprocess_element_class(x: str):
    return x.replace(" ", ".")

def load_combo_file(file_path):
    with open(file_path, "r") as f:
        return f.read().splitlines()

def get_random_combo(combo):
    if not combo:
        raise Exception("No available accounts in combo.txt")
    index = random.randrange(len(combo))
    combo_line = combo.pop(index).strip()
    parts = combo_line.split(":")
    if len(parts) >= 2:
        return {"username": parts[0], "password": parts[1]}
    return get_random_combo(combo)

def get_random_proxy():
    with open("proxies.txt", "r") as f:
        proxy_list = [line.strip() for line in f if line.strip()]
    return random.choice(proxy_list) if proxy_list else None
    
def setup_chrome_options(use_uc=False):
    if use_uc:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()

        ext_path = os.path.abspath(os.path.join(os.path.dirname(__file__), EXTENSION_PATH))

        # Remove the .crx from the extension path
        ext_path = re.sub(r'\.crx$', '', ext_path)
        
        options.add_argument(r'--load-extension=' + ext_path)
        # Added arguments to disable save password popup and other infobars
        options.add_argument("--disable-save-password-bubble")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        # Add proxy argument.
        if config.get("USE_PROXIES", False):
            proxy = get_random_proxy()
            if proxy:
                options.add_argument(f"--proxy-server={proxy}")
        options.add_argument("--log-level=3")
        return options
    else:
        options = webdriver.ChromeOptions()
        options.add_experimental_option("prefs", {
            "download.default_directory": config.get("DOWNLOAD_DIR", os.getcwd()),
            "download.prompt_for_download": False,
        })
        options.add_argument("--log-level=3")
        options.add_extension(EXTENSION_PATH)
        # Add proxy argument.
        if config.get("USE_PROXIES", False):
            proxy = get_random_proxy()
            if proxy:
                options.add_argument(f"--proxy-server={proxy}")
        return options

def login_to_outlook(driver, driver_wait, authen):
    global combo  # allow use of global combo for retries
    try:
        driver.get("https://outlook.office.com/mail/")
        login_box = driver_wait.until(EC.presence_of_element_located((By.NAME, "loginfmt")))
        login_box.clear()  # clear any pre-filled data
        login_box.send_keys(authen["username"])
        login_box.send_keys(Keys.RETURN)
        time.sleep(DELAY_SEC)
        password_box = driver_wait.until(EC.presence_of_element_located((By.NAME, "passwd")))
        password_box.clear()  # clear any pre-filled data
        password_box.send_keys(authen["password"])
        password_box.send_keys(Keys.ENTER)
        time.sleep(DELAY_SEC)

        # Check if "Your account or password is incorrect. If you don't remember your password, reset it now." is present in the page's html
        if "Your account or password is incorrect. If you don't remember your password, reset it now." in driver.page_source:
            raise Exception("Invalid credentials, retrying with another account")

        # Check if url contains "Abuse" in it, which means the account is banned, retry with another account.
        if "Abuse" in driver.current_url:
            raise Exception("Account is banned, retrying with another account")


        stay_sign_in = driver_wait.until(EC.presence_of_element_located((By.ID, "acceptButton")))
        stay_sign_in.click()
        time.sleep(DELAY_SEC)

        # Fix: force navigation back to mail page to exit a potential about:blank state
        driver.get("https://outlook.office.com/mail/")
        driver_wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']")))
        return authen
    except Exception as e:
        print(f"Login error: {str(e)}, retrying with another account")
        driver.delete_all_cookies()  # clear cookies to start fresh
        new_authen = get_random_combo(combo)
        return login_to_outlook(driver, driver_wait, new_authen)

def register_to_webshare(driver, driver_wait, authen):
    # Use Selenium's native new tab method
    driver.switch_to.new_window('tab')
    
    # Wait for new window explicitly
    WebDriverWait(driver, 15).until(
        lambda d: len(d.window_handles) == 2
    )
    
    driver.switch_to.window(driver.window_handles[1])
    driver.get("https://dashboard.webshare.io/register")
    time.sleep(DELAY_SEC)
    
    email_box = driver_wait.until(EC.presence_of_element_located((By.ID, "email-input")))
    email_box.send_keys(authen["username"])
    
    password_box = driver_wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id=":R5aqecqjej6:"]')))
    password_box.send_keys(authen["password"])
    
    login_button = driver_wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[1]/div[1]/div/div[2]/form/div/div[5]/button')))
    login_button.click()
    time.sleep(DELAY_SEC)
    handle_recaptcha(driver)
    # Registration is now submitted; verification will be performed separately.
    print(f"{YELLOW}Registration submitted. Proceeding to email verification...{RESET}")

def verify_email(driver, driver_wait, authen):
    driver.switch_to.window(driver.window_handles[0])
    driver.get("https://outlook.office.com/mail/")
    login_box = driver_wait.until(EC.presence_of_element_located((By.NAME, "loginfmt")))
    login_box.send_keys(authen["username"])
    login_box.send_keys(Keys.RETURN)
    time.sleep(DELAY_SEC)
    # Navigate to the correct folder
    folder_selector = "#folderPaneDroppableContainer > div.qQbyL > div:nth-child(3) > div > div.e4_J1 > div > div > div:nth-child(2) > div"
    driver_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, folder_selector))).click()
    # Locate activation email and verify activation
    activation_email_xpath = ("//div[@role='option' and contains(@aria-label, 'Activate Your Webshare Account')]")
    activation_email = driver_wait.until(EC.element_to_be_clickable((By.XPATH, activation_email_xpath)))
    driver.execute_script("arguments[0].scrollIntoView(true);", activation_email)
    activation_email.click()
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='document']")))
        verify_selector = "a[href*='/activation/'][href*='/confirm/']:not([title='Unsubscribe'])"
        verification_link = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, verify_selector)))
        activation_url = verification_link.get_attribute("href")
        print(f"Found verification link: {activation_url}")
        driver.get(activation_url)
        WebDriverWait(driver, 15).until(lambda d: "dashboard.webshare.io" in d.current_url)
        print("Account activation confirmed!")
    except Exception as e:
        print(f"Verification failed: {str(e)}. Attempting fallback...")
        try:
            verification_link = driver.find_element(By.CSS_SELECTOR, verify_selector)
            activation_url = verification_link.get_attribute("href")
            print(f"Direct activation URL: {activation_url}")
            driver.execute_script(f"window.open('{activation_url}', '_blank');")
            driver.switch_to.window(driver.window_handles[-1])
            WebDriverWait(driver, 15).until(lambda d: "dashboard.webshare.io" in d.current_url)
            print("Activation via direct URL successful!")
        except Exception as fallback_error:
            print(f"Fallback failed: {str(fallback_error)}")
            raise

def handle_recaptcha(driver):
    # Open a new (third) tab for the reCAPTCHA extension
    driver.switch_to.new_window('tab')
    driver.get("chrome-extension://hlifkpholllijblknnmbfagnkjneagid/popup/popup.html#/")
    time.sleep(DELAY_SEC)
    
    # Switch back to the webshare registration tab (assumed second tab)
    driver.switch_to.window(driver.window_handles[1])
    current_url = driver.current_url
    # Wait until the URL changes as an indication that recaptcha is handled
    while current_url == driver.current_url:
        time.sleep(1)

if __name__ == "__main__":
    while True:
        driver = None
        try:
            combo = load_combo_file("combo.txt")
            authen = get_random_combo(combo)
            use_uc = config.get("USE_UNDETECTED_CHROMEDRIVER", False)
            chrome_options = setup_chrome_options(use_uc)
            if use_uc:
                import undetected_chromedriver as uc
                # Retrieve expected main version from config, defaulting to 132.
                version_main = config.get("CHROME_VERSION", 132)
                driver = uc.Chrome(options=chrome_options, version_main=version_main)
            else:
                driver_service = Service(log_path=os.devnull)
                driver = webdriver.Chrome(service=driver_service, options=chrome_options)
            driver_wait = WebDriverWait(driver, ELEMENT_LOAD_WAIT_SEC)
            driver.maximize_window()

            # Logging in to Outlook with elapsed time display.
            print(f"{YELLOW}Logging in to Outlook...{RESET}")
            t1 = time.time()
            authen = login_to_outlook(driver, driver_wait, authen)
            print(f"{GREEN}Successfully logged into Outlook, time elapsed: {time.time() - t1:.2f} seconds{RESET}")

            # Registering on Webshare
            print(f"{YELLOW}Registering on Webshare...{RESET}")
            t2 = time.time()
            register_to_webshare(driver, driver_wait, authen)
            # Now perform email verification separately.
            verify_email(driver, driver_wait, authen)
            print(f"{GREEN}Successfully registered and verified on Webshare, time elapsed: {time.time() - t2:.2f} seconds{RESET}")

            print(f"{YELLOW}Adding IP...{RESET}")
            # Retrieve specific IP from config
            auth_ip = config.get("AUTH_IP", "").strip()
            
            time.sleep(DELAY_SEC)
            driver.get("https://dashboard.webshare.io/proxy/settings?tab=1")
           
            t3 = time.time()
            ip_element = driver_wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.css-14xdbal"))
            )
            current_ip = ip_element.text
            if auth_ip is not "":
                print(f"{YELLOW}Using specified IP for authentication: {auth_ip}{RESET}")
            else:
                print(f"{YELLOW}No AUTH_IP specified; detected IP: {current_ip}{RESET}")

            driver_wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='add-ip-auth']"))
            ).click()
            ip_input = driver_wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[data-testid='ip-auth']"))
            )
            # Use specified IP if provided; otherwise, fall back to detected IP.
            ip_input.send_keys(auth_ip if auth_ip else current_ip)
            save_button_xpath = "//button[.//span[text()='Save']]"
            WebDriverWait(driver, 10).until(
                lambda d: not d.find_element(By.XPATH, save_button_xpath).get_attribute("disabled")
            )
            driver.find_element(By.XPATH, save_button_xpath).click()
            time.sleep(DELAY_SEC)
            print(f"{GREEN}IP added, time elapsed: {time.time() - t3:.2f} seconds{RESET}")
            
            t4 = time.time()
            driver.get("https://dashboard.webshare.io/proxy/list?authenticationMethod=%22ip%22&connectionMethod=%22direct%22&proxyControl=%220%22&rowsPerPage=10&page=0&order=%22asc%22&orderBy=null&searchValue=%22%22&modals=eyJkb3dubG9hZFByb3h5TGlzdE9wZW4iOnRydWV9")
            time.sleep(DELAY_SEC)
            download_input = driver_wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='download-test-link'] input"))
            )
            download_url = download_input.get_attribute("value")
            print(f"{YELLOW}Downloading proxies from: {download_url}{RESET}")
            response = requests.get(download_url)
            with open("proxies.txt", "wb") as f:
                f.write(response.content)
            print(f"{GREEN}Proxies downloaded successfully, time elapsed: {time.time() - t4:.2f} seconds{RESET}")
            driver.quit()
            break   # Exit loop on success.
        except Exception as e:
            print(f"{YELLOW}Error: {e}. Retrying with a different account.{RESET}")
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass
            continue
