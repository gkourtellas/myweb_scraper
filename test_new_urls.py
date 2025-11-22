import requests
from bs4 import BeautifulSoup

# Example URL and selector - change as needed
url = "https://example.com"
selector = "#example"

response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
element = soup.select_one(selector)
if element:
    print(element.get_text())
else:
    print("Element not found")
