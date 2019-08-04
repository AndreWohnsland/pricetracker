import requests
from bs4 import BeautifulSoup
import re

URL = 'https://www.amazon.de/Raspberry-1373331-Pi-Modell-Mainboard/dp/B07BDR5PDW/ref=sr_1_3?__mk_de_DE=%C3%85M%C3%85%C5%BD%C3%95%C3%91&keywords=raspberyy+pi&qid=1564919205&s=gateway&sr=8-3'

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"
}

page = requests.get(URL, headers=headers)
soup = BeautifulSoup(page.content, 'html.parser')

title = soup.find(id="productTitle").get_text().strip()
print(title)

price = soup.find(id="priceblock_ourprice").get_text()
price = price.replace(",", ".")
converted_price = float(re.sub(r"[^\d.]", "", price))
print(converted_price)