from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Example URL and selector - change as needed
url = "https://example.com"
selector = "#example"

options = Options()
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)
driver.get(url)
try:
    element = driver.find_element(By.CSS_SELECTOR, selector)
    print(element.text)
except Exception as e:
    print(f"Error: {e}")
driver.quit()
