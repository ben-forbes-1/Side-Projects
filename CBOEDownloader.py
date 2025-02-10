import os
import csv
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent

class CBOEDownloader:
    def __init__(self, download_dir="./cboe_csvs"):
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        self.driver = self._setup_driver()

    def _setup_driver(self):
        options = webdriver.ChromeOptions()
        prefs = {
            "download.default_directory": os.path.abspath(self.download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.default_content_settings.popups": 0,
            "download.open_pdf_in_system_reader": False,
            "download.extensions_to_open": "",
            "download.shelf.enabled": False
        }
        options.add_experimental_option("prefs", prefs)
        ua = UserAgent()
        options.add_argument(f"user-agent={ua.random}")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=options)

    def download_data(self):
        url = "https://www.cboe.com/delayed_quotes/spx/quote_table"
        self.driver.get(url)
        wait = WebDriverWait(self.driver, 15)

        try:
            # Dismiss cookies popup
            reject_button_xpath = "//button[contains(@class, 'cky-btn-reject') and @aria-label='Reject All']"
            reject_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, reject_button_xpath))
            )
            reject_button.click()

            # Select "All" from the dropdown
            dropdown_xpath = "//div[contains(@class, 'ReactSelect__control') and .//div[text()='Near the Money']]"
            dropdown = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, dropdown_xpath))
            )
            self.driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", dropdown)
            dropdown.click()

            actions = ActionChains(self.driver)
            actions.send_keys("All").send_keys(Keys.RETURN).perform()

            # Click 'View Chain' button
            view_button_xpath = "//button[contains(@class, 'Button__StyledButton') and contains(@class, 'QuoteTableLayout___StyledButton')]"
            view_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, view_button_xpath))
            )
            view_button.click()
            print("Clicked 'View Chain' button.")
        except Exception as e:
            print(f"Error interacting with the dropdown: {e}")

        processed_expirations = []
        while True:
            try:
                expiration_buttons = wait.until(EC.presence_of_all_elements_located(
                    (By.XPATH, "//button[contains(@class, 'Button__StyledButton-cui__sc-1ahwe65-2')]")
                ))
                expiration_buttons = [btn for btn in expiration_buttons if "20" in btn.text]

                for i in range(len(expiration_buttons)):
                    expiration_buttons = wait.until(EC.presence_of_all_elements_located(
                        (By.XPATH, "//button[contains(@class, 'Button__StyledButton-cui__sc-1ahwe65-2')]")
                    ))
                    expiration_buttons = [btn for btn in expiration_buttons if "20" in btn.text]

                    button = expiration_buttons[i]
                    expiration = button.text.strip()

                    if expiration in processed_expirations:
                        continue

                    print(f"Processing expiration: {expiration}")
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", button)
                    time.sleep(3)

                    export_button_xpath = "//a[span[text()='Download CSV']]"
                    export_button = wait.until(EC.presence_of_element_located((By.XPATH, export_button_xpath)))
                    print(f"Clicking 'Download CSV' button for {expiration}")
                    self.driver.execute_script("arguments[0].click();", export_button)
                    time.sleep(5)

                    latest_file = max([os.path.join(self.download_dir, f) for f in os.listdir(self.download_dir)], key=os.path.getctime)
                    new_file_name = os.path.join(self.download_dir, f"{expiration.replace(' ', '_')}.csv")
                    os.rename(latest_file, new_file_name)
                    print(f"File saved as {new_file_name}")
                    processed_expirations.append(expiration)

                if len(processed_expirations) >= len(expiration_buttons):
                    break
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error locating or processing expiration buttons: {e}")
                break

        self.driver.quit()

    def combine_csv_files(self):
        all_data = pd.DataFrame()
        current_idx_flag = False
        for file in os.listdir(self.download_dir):
            if file.endswith(".csv"):
                file_path = os.path.join(self.download_dir, file)
                try:
                    if not current_idx_flag:
                        with open(file_path, newline='') as f:
                            reader = csv.reader(f)
                            row1 = next(reader)
                            row2 = next(reader)
                            idx_spot = row2[1].split(" ")[1]
                        current_idx_flag = True

                    df = pd.read_csv(file_path, skiprows=3).fillna('')
                    call_column_headers = ['Expiration Date', 'Last Sale', 'Net', 'Bid', 'Ask', 'Volume', 'IV', 'Delta', 'Gamma', 'Open Interest', 'Strike']
                    put_column_headers = ['Expiration Date', 'Last Sale.1', 'Net.1', 'Bid.1', 'Ask.1', 'Volume.1', 'IV.1', 'Delta.1', 'Gamma.1', 'Open Interest.1', 'Strike']

                    df_calls = df[call_column_headers].copy().dropna(how='any', axis=1)
                    df_calls['Type'] = 'Call'
                    df_calls.columns = df_calls.columns.str.replace(r'\.1$', '', regex=True)

                    df_puts = df[put_column_headers].copy().dropna(how='any', axis=1)
                    df_puts['Type'] = 'Put'
                    df_puts.columns = df_puts.columns.str.replace(r'\.1$', '', regex=True)

                    df = pd.concat([df_calls, df_puts], ignore_index=True)
                    all_data = pd.concat([all_data, df], ignore_index=True)
                except pd.errors.ParserError as e:
                    print(f"Error parsing file {file_path}: {e}")
                    continue

        if len(all_data.index) != 0:
            final_df = all_data.copy()
            final_df['Expiration Date'] = pd.to_datetime(final_df['Expiration Date'], format='%a %b %d %Y')
            final_df = final_df.sort_values(by=['Expiration Date', 'Strike'])
            final_df['Index Spot'] = idx_spot

            combined_csv_path = "spx_options_combined.csv"
            if os.path.exists(combined_csv_path):
                os.remove(combined_csv_path)
            final_df.to_csv(combined_csv_path, index=False)
            print(f"Data saved to {combined_csv_path}")

            for file in os.listdir(self.download_dir):
                if file.endswith(".csv"):
                    file_path = os.path.join(self.download_dir, file)
                    try:
                        os.remove(file_path)
                        print(f"Deleted file: {file_path}")
                    except OSError as e:
                        print(f"Error deleting file {file_path}: {e}")
        else:
            print("No valid data to save.")