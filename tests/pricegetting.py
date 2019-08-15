import requests
from bs4 import BeautifulSoup
import re
import time

def extract_url(url):
    """Creates a short version of the URL to work with. Also returns None if its not a valid adress.
    
    Args:
        url (str): The long version of the URL to shorten
    
    Returns:
        str: The short version of the URL
    """
    if url.find("www.amazon.de") != -1:
        index = url.find("/dp/")
        if index != -1:
            index2 = index + 14
            url = "https://www.amazon.de" + url[index:index2]
        else:
            index = url.find("/gp/")
            if index != -1:
                index2 = index + 22
                url = "https://www.amazon.de" + url[index:index2]
            else:
                url = None
    else:
        url = None
    return url

def get_converted_price(price):
    """Converts the price argument to a clean number
    
    Args:
        price (str): scrapped price
    
    Returns:
        float: converted price
    """
    # stripped_price = price.strip("€ ,")
    # replaced_price = stripped_price.replace(",", "")
    # find_dot = replaced_price.find(".")
    # to_convert_price = replaced_price[0:find_dot]
    # converted_price = int(to_convert_price)
    price = price.replace(",", ".")
    converted_price = float(re.sub(r"[^\d.]", "", price))

    return converted_price

def get_product_details(url):
    """Extract the needed product details out of the URL.
    
    Args:
        url (str): Adress/URL to scrape from
    
    Returns:
        dict: Details of the scraped product
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.100 Safari/537.36"
    }
    details = {"name": "", "price": 0, "deal": True, "url": ""}
    _url = extract_url(url)
    if _url == "":
        details = None
    else:
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.content, "html5lib")
        title = soup.find(id="productTitle")
        price = soup.find(id="priceblock_dealprice")
        if price is None:
            price = soup.find(id="priceblock_ourprice")
            details["deal"] = False
        if title is not None and price is not None:
            details["name"] = title.get_text().strip()
            details["price"] = get_converted_price(price.get_text())
            details["url"] = _url
        else:
            return None
    return details

product_list = [
    "https://www.amazon.de/Raspberry-1373331-Pi-Modell-Mainboard/dp/B07BDR5PDW/ref=sr_1_3?__mk_de_DE=%C3%85M%C3%85%C5%BD%C3%95%C3%91&keywords=raspberyy+pi&qid=1564919205&s=gateway&sr=8-3",
    "https://www.amazon.de/Kuman-Raspberry-Touchscreen-Resolution-Protective/dp/B07D4FHBNW/ref=sr_1_7?__mk_de_DE=%C3%85M%C3%85%C5%BD%C3%95%C3%91&keywords=raspberry+pi+touch&qid=1564920076&s=gateway&sr=8-7",
    "https://www.amazon.de/gp/product/B07G9V43VR/ref=ppx_yo_dt_b_asin_title_o03_s00?ie=UTF8&psc=1,",
    "https://www.amazon.de/offizielles-Geh%C3%A4use-Raspberry-Himbeer-wei%C3%9F/dp/B01CCPKCSK/ref=pd_bxgy_147_img_3/261-3406078-0384204?_encoding=UTF8&pd_rd_i=B01CCPKCSK&pd_rd_r=59876f41-8349-4a8f-9d18-ac448cafb876&pd_rd_w=9jKH0&pd_rd_wg=tBMOw&pf_rd_p=98c98f04-e797-4e4b-a352-48f7266a41af&pf_rd_r=CBN0CW3TJAWSVPWSMBQX&psc=1&refRID=CBN0CW3TJAWSVPWSMBQX"   
]

# while(True):
    # time.sleep(60)
print(50*"-" + "\n Getting all the prices\n" + 50*"-")
for product in product_list:
    print(get_product_details(product))
    