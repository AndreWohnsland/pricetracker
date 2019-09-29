# pricetracker

A Python and Qt App which lets you track various Amazon Products over time, display their course and determine the price behavior. The prices will be fetched automatically on program start if they haven't been fetched within the last twelve hours. You can always fetch the price of a single product by selecting it in the listwidget and press `ctrl+f` or go to `Options>fetch price for product`. Once you have tracked at least on time the price of the product, you can plot the price behaviour of the time by selecting it in the listwidget and then click `Plot the Price Graph`. The program theen displays a graph of the price over the time, indicating values above and below the average mean value (given you have at least two dates/values for the mean). as well as the mean value of the product. It got also build in support for commercial (.com) and german (.de) amazon links (including their decimal/thousand separators and currency) but implementing your own country is quite easy as well. For more information go to section `Setting some options`.

## Minimal Requirements

```
- Python 3.6
- requests
- bs4
- html5lib
- PyQt5
- matplotlib 3.1
- numpy (included with matplotlib)
```
The packages can usually be installed from PyPi with the `pip install 'packagename'` or your system according command.

## Features

This app gives you the possibility to enter your short name for the product and the amazon link according to it. The program will check once a day all prices, which are set as active and save them into a database. You can also check single prices of a product on demand via options. You can also plot the price of selected products to see the change over the time. It got build in reasonability check for the entry values as well as validation check on the link (if the link is a valid amazon link from the supported domains, which are by default .com and .de). Since the fetching of the prices (with the request module) takes some time, the process was split up to an own thread, to prevent freezing of the application.


![Mainwindow](https://github.com/AndreWohnsland/pricetracker/blob/master/gui/pictures/app_example.PNG "mainscreen")


![Plotwindow](https://github.com/AndreWohnsland/pricetracker/blob/master/gui/pictures/plot_example.PNG "plotscreen")


## Setting some options

The program is currently programmed for german (.de) or commercial (.com) Amazon and therefore also uses the according thousand separator as well according decimal separator. If your country specific separation differs you can change this in the `setup_mainwindow.py`file:

```python
# Change here the thousand separator for your country
sep = {
	"de": ".",
	"com": ","
}
# Change here the decimal separator for your country
decimal = {
	"de": ",",
	"com": "."
}
```

Also you may need to add the option in the `extract_url` method for your specific country domain. Currently there is only for .de and for .com pages. Other will return none and thereby be invalid by code checking. If you want to implement your code the two numbers are `12 + countrycode = 14` (for .de) or `20 + countrycode = 22` (for .de) (de is 2, com is 3 and so on):
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
elif url.find("www.amazon.com") != -1:
	....
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
But I would recommend implementing your countrycode to the dict and the code, since it's not so hard and you can lean on existing code quite easily.

In addition, you need to set your User-Agent once for your program. You can Google "My User Agent" to get it. Simply go to `Options>select User Agent` to set your User-Agent for the program. The User Agent will be saved in the `config.ini` file.

## Troubleshooting

It may happen that sometimes not all Links can be fetched. This can have multiple reasons. The easier ones are that you are not connected to the internet or your User Agent is wrong. Further things can be the display of the Amazon product. currently this programm only supports normal price display in the `id="priceblock_ourprice"` or `id="priceblock_dealprice"` but if the page layout for the product is more complex (price is displayed in different buttons where you can choose your setup or options) the programm won't find the pricetag and there will fail for this product. An error Message will occour.