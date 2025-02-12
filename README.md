## Demo

Here's a demo of the script in action:

https://github.com/user-attachments/assets/efeda116-a6a9-421f-8da1-4f3b55ef40cd


# Webshare Account Creator

This project automates the creation of accounts on Webshare.io using Selenium and a reCAPTCHA solver. It utilizes Outlook email accounts for registration and verification.

## Features

-   Automated account creation on Webshare.io
-   Email verification via Outlook
-   reCAPTCHA solving integration
-   Proxy support (optional)
-   IP authentication
-   Downloads proxy list from Webshare dashboard
-   Uses undetected-chromedriver to avoid detection

## Requirements

-   Python 3.6+
-   pip
-   A valid `combo.txt` file containing Outlook email and password combinations (email:password)


## Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/brackeys-xd/webshare-account-creator.git
    cd webshare-account-creator
    ```

2.  Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3.  Download the extension from the Chrome Web Store, then rename it to `extension.crx` and place it in the project directory.

4.  Configure your Byepass reCaptcha API key in the extension settings.

## Configuration

Create a `config.json` file with the following structure:

```json
{
  "ELEMENT_LOAD_WAIT_SEC": 30,
  "DELAY_SEC": 5,
  "EXTENSION_PATH": "extension.crx",
  "DOWNLOAD_DIR": ".",
  "FLASK_HOST": "127.0.0.1",
  "FLASK_PORT": 5001,
  "PROXY_UPDATE_INTERVAL_HOURS": 2,
  "USE_UNDETECTED_CHROMEDRIVER": false,
  "AUTH_IP": "",
  "CHROME_VERSION": 132,
  "USE_PROXIES": false
}
```

-   `ELEMENT_LOAD_WAIT_SEC`: Maximum time to wait for an element to load (seconds).
-   `DELAY_SEC`: Delay between actions (seconds).
-   `EXTENSION_PATH`: Path to the reCAPTCHA solver extension.
-   `DOWNLOAD_DIR`: Directory to download files to.
-   `USE_UNDETECTED_CHROMEDRIVER`: Use undetected-chromedriver to avoid detection (True/False).
-   `AUTH_IP`: IP address to whitelist on Webshare. If empty, the script will attempt to detect your current IP.
-   `CHROME_VERSION`: Chrome version to use with undetected-chromedriver.
-   `USE_PROXIES`: Enable or disable proxy usage (True/False).

## Usage

1.  Prepare your `combo.txt` file with email:password combinations.

2.  Run the script:

    ```bash
    python main.py
    ```

The script will attempt to create accounts using the provided credentials.

## Proxy Usage

The script supports proxy usage. To enable it:

1.  Ensure you have a valid `proxies.txt` file. The script downloads this file automatically from webshare.

2.  Set the `USE_PROXIES` variable to `true` in the `config.json` file.

3.  Uncomment the proxy related lines in `setup_chrome_options` function in `main.py`.

## Notes

-   The script uses Selenium to automate browser actions.
-   The `undetected-chromedriver` library is used to prevent bot detection.
-   Error handling and retries are implemented to handle temporary issues.
