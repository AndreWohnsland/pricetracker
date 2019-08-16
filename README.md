# pricetracker
A Python and Qt App which lets you track various Amazon Products over time, display their course and determine the price behavior.

## Minimal Requirements

```
- Python 3.6
- requests
- bs4
- html5lib
- PyQt5
- Matplotlib 3.1
- numpy
```
The packages can usually be installed from PyPi with the `pip install 'packagename'` or your system according command.

## Features

This app gives you the possibility to enter your short name for the product and the amazon link according to it. The program will check once a day all prices, which are set as active and save them into a database. You can also check single prices of a product on demand via options. You can also plot the price of selected products to see the change over the time.


![alt text](https://github.com/AndreWohnsland/pricetracker/blob/master/gui/pictures/app_example.PNG "mainscreen")


## Setting some options

The program is used for german (.de) Amazon and therefore also uses a dot for a thousand separator as well as a comma for decimal separator. If your country specific separation differs you can change this in the `setup_mainwindow.py`file:

```python
price = price.replace(".", "") # Change here the thousand separator for your country
price = price.replace(",", ".")	# Change here the decimal separator for your country
```

Also you may need to change the option in the `extract_url` method from ".de" to your specific country domain.
```python
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
```

Or complete remove that check/transforming option of the link by changing the lines in the `get_product_details` method from

```python
_url = self.extract_url(url)
if _url == "":
	details = None
```

to

```python
if url == "":
	details = None
```

In addition, you need to set your User-Agent once for your program. You can Google "My User Agent" to get it. Simply go to `Options>select User Agent` to set your User-Agent for the program. 