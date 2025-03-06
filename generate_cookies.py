from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time

# Configure Chrome for headless mode
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# Initialize WebDriver
driver = webdriver.Chrome(options=chrome_options)

try:
    # Navigate to YouTube login
    driver.get("https://accounts.google.com/ServiceLogin?service=youtube")
    
    # Input email (from environment variable)
    email = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "identifierId"))
    )
    email.send_keys(os.getenv("YT_EMAIL"))
    driver.find_element(By.ID, "identifierNext").click()
    
    # Input password (from environment variable)
    password = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.NAME, "Passwd"))
    )
    password.send_keys(os.getenv("YT_PASSWORD"))
    driver.find_element(By.ID, "passwordNext").click()
    
    # Wait for login to complete (check for YouTube homepage)
    WebDriverWait(driver, 30).until(
        EC.url_contains("https://www.youtube.com")
    )
    
    # Save cookies in Netscape format for yt-dlp
    with open("youtube_cookies.txt", "w") as f:
        f.write("# Netscape HTTP Cookie File\n")
        for cookie in driver.get_cookies():
            domain = cookie["domain"]
            if domain.startswith("."):
                domain = domain[1:]
            f.write(
                f"{domain}\tTRUE\t{cookie['path']}\t"
                f"{'TRUE' if cookie['secure'] else 'FALSE'}\t"
                f"{int(cookie.get('expiry', 0))}\t"
                f"{cookie['name']}\t{cookie['value']}\n"
            )
    print("Cookies saved to youtube_cookies.txt")

finally:
    driver.quit()