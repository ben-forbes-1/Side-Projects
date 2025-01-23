import os
import numpy as np
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import csv
from fake_useragent import UserAgent

# Set up Selenium WebDriver with custom download directory
options = webdriver.ChromeOptions()
download_dir = "./cboe_csvs"  # Directory to save downloaded CSVs
os.makedirs(download_dir, exist_ok=True)

prefs = {
    "download.default_directory": os.path.abspath(download_dir),      # Set download directory
    "download.prompt_for_download": False,                            # Disable download prompts
    "download.directory_upgrade": True,                               # Allow directory upgrades
    "safebrowsing.enabled": True,                                     # Enable safe browsing
    "profile.default_content_setting_values.automatic_downloads": 1,  # Allow multiple downloads
    "profile.default_content_settings.popups": 0,                     # Disable popups
    "download.open_pdf_in_system_reader": False,                      # Prevent PDF popup
    "download.extensions_to_open": "",                                # Prevent any extensions from auto-opening
    "download.shelf.enabled": False                                   # Disables the "Download Complete" notification popup
}
options.add_experimental_option("prefs", prefs)

ua = UserAgent()
options.add_argument(f"user-agent={ua.random}")                       # Set a random user agent
options.add_argument("--window-size=1920x1080")                       # Set window size
# options.add_argument("--headless=new")                                # Run in headless mode to avoid opening a browser window
options.add_argument("--disable-blink-features=AutomationControlled") # Disable automation control
options.add_argument("--disable-gpu")                                 # Prevent GPU acceleration
options.add_argument("--disable-software-rasterizer")                 # Further UI rendering disabling
options.add_argument("--disable-extensions")                          # Prevent extension issues
options.add_argument("--no-sandbox")                                  # For running inside containers
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=options)

# Navigate to the Cboe SPX options page
url = "https://www.cboe.com/delayed_quotes/spx/quote_table"
driver.get(url)

# Wait for the page to load
wait = WebDriverWait(driver, 15)

from selenium.webdriver.common.keys import Keys

try:
    # Step 1: Dismiss cookies popup
    reject_button_xpath = "//button[contains(@class, 'cky-btn-reject') and @aria-label='Reject All']"
    reject_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, reject_button_xpath))
    )
    reject_button.click()
    print("Cookies popup dismissed.")

    # Step 2: Locate and click the dropdown containing 'Near the Money'
    dropdown_xpath = "//div[contains(@class, 'ReactSelect__control') and .//div[text()='Near the Money']]"
    dropdown = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
    )
    driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", dropdown)
    dropdown.click()
    print("Clicked 'Options Range' dropdown containing 'Near the Money'.")

    # Step 3: Type 'All' directly and press Enter
    actions = ActionChains(driver)
    actions.send_keys("All")  # Type 'All'
    actions.send_keys(Keys.RETURN)  # Press Enter
    actions.perform()
    print("Typed 'All' and pressed Enter.")

    # Step 4: Click 'View Chain' button
    view_button_xpath = "//button[contains(@class, 'Button__StyledButton') and contains(@class, 'QuoteTableLayout___StyledButton')]"
    view_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, view_button_xpath))
    )
    view_button.click()  # Attempt to click
    print("Clicked 'View Chain' button.")
    time.sleep(30)

except Exception as e:
    print(f"Error: {e}")
