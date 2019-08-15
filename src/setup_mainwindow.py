import sys
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import time
import datetime
import configparser
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.colors as mcolors

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.uic import *

from gui.mainwindow import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """Creates the pricetracker mainwindow:
    
    Args:
        db_path (str): Path to the database. Defaults to None.
        parent (qt_Object): Parent for the main Window to inherit. Defaults to None.
    """

    def __init__(self, db_path=None, parent=None):
        """ Init function for the MainWindow Class. """
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.db_path = db_path
        self.config_path = "config.ini"
        self.createDB()
        self.CHB_track.setChecked(True)
        self.id = 0
        self.read_config()

        # optical features
        self.setWindowIcon(QIcon('gui/pictures/dollar.png'))

        # connection of all Buttons
        self.PB_enter.clicked.connect(lambda: self.enter_data(change=False))
        self.PB_clear.clicked.connect(self.clear_entries)
        self.PB_change.clicked.connect(lambda: self.enter_data(change=True))
        self.PB_plot.clicked.connect(self.plot_price)
        
        # connects the LW to the function
        self.LW_products.itemClicked.connect(self.display_lw_item)

        # connect the action buttons
        self.action_agent.triggered.connect(self.call_user_agent)

        # insert the data into the LW
        self.load_listentries()

        # Check if the prices where get within the last half day
        self.dayly_check()

    def enter_data(self, change=False):
        """Checks and enters the data into the db. """
        # checks all LE
        validchecker = self.validcheck([self.LE_name, self.LE_url], ["product name", "product URL"])
        # if change without a product was clicked
        if validchecker:
            if not self.LW_products.selectedItems() and change:
                self.dialogbox("No product was selected to be changed!", "Missing Product", parent=self)
                validchecker = False
        # checks if this link already exists
        if validchecker and not change:
            existing_entry = self.queryDB("SELECT COUNT(*) FROM Tracklist WHERE Link = ?", (self.LE_url.text(),))[0][0]
            if existing_entry:
                self.dialogbox("This product Link is already existing in the database!", "Existing Product", parent=self)
                validchecker = False
        if validchecker:
            productname = self.LE_name.text()
            productlink = self.LE_url.text()
            trackproduct = 0
            if self.CHB_track.isChecked():
                trackproduct = 1
            # checks if the link is an amzon link
            shortlink = self.extract_url(productlink)
            if shortlink is not None and change:
                self.queryDB("UPDATE OR IGNORE Tracklist SET Name = ?, Link = ?, Shortlink = ?, Active = ? WHERE ID = ?", (productname, productlink, shortlink, trackproduct, self.id))
                self.LW_products.currentItem().setText(productname)
                self.clear_entries()
                self.dialogbox("Data was updagted into the Database successfully", "Data Updated", parent=self)
            elif shortlink is not None:
                # enters the data into the DB
                self.queryDB("INSERT OR IGNORE INTO Tracklist(Name, Link, Shortlink, Active) VALUES(?,?,?,?)", (productname, productlink, shortlink, trackproduct))
                new_id = self.queryDB("SELECT ID FROM Tracklist WHERE Name = ?", (productname,))[0][0]
                item = QListWidgetItem(str(productname), self.LW_products)
                item.setData(Qt.UserRole, new_id)
                self.LW_products.sortItems()
                self.clear_entries()
                self.dialogbox("Data was entered into the Database successfully", "Data Entered", parent=self)
            else:
                self.dialogbox("The given Link is no Amazon Link!", "Invalid Link given!", parent=self)

    def clear_entries(self):
        """Clears the entry labels. """
        self.LE_name.clear()
        self.LE_url.clear()
        self.CHB_track.setChecked(True)
        for i in range(self.LW_products.count()):
            self.LW_products.item(i).setSelected(False)
        self.id = 0

    def load_listentries(self):
        """Loads all the names and their ids into the ListWidget. """
        trackdata = self.queryDB("SELECT Name, ID FROM Tracklist ORDER BY Name asc")
        for product in trackdata:
            item = QListWidgetItem(str(product[0]), self.LW_products)
            # stores the id as the UserRole index
            item.setData(Qt.UserRole, product[1])
    
    def display_lw_item(self):
        self.id = self.LW_products.currentItem().data(Qt.UserRole)
        entries = self.queryDB("SELECT Name, Link, Active FROM Tracklist WHERE ID = ?", (self.id,))[0]
        self.LE_name.setText(entries[0])
        self.LE_url.setText(entries[1])
        if not entries[2]:
            self.CHB_track.setChecked(False)
        else:
            self.CHB_track.setChecked(True)

    def plot_price(self):
        """ Gets all the prices for the selected Item. """
        if self.id:
            # selects the price and the date, appends both to a seperate list to plot later
            pricetable = self.queryDB("SELECT Price, Date FROM Pricetracks WHERE ID = ?", (self.id,))
            x_values = []
            y_values = []
            for valuepair in pricetable:
                x_values.append(datetime.datetime.strptime(valuepair[1], '%Y-%m-%d'))
                y_values.append(valuepair[0])
            # Calls a new window, which shows the graph
            productname = self.queryDB("SELECT Name From Tracklist WHERE ID = ?", (self.id,))[0][0]
            self.gw = GraphWindow(self, [x_values, y_values], productname)
            self.gw.show()
        else:
            self.dialogbox("Please select a product to plot the price over the time.", "No Product Selected")

    def validcheck(self, lineedits, missingvals=[""]):
        """Checks if the input got a string or is empty. If empty, informs about the user
        
        Args:
            lineedits (listq): List of all lineedits that needs to be filled out
            missingvals (list, optional): List of the names of the values to fill in. Defaults to [""].
        
        Returns:
            bool: State if all lineedits were filled out
        """
        for lineedit, missingval in zip(lineedits, missingvals):
            if lineedit.text() == "":
                self.dialogbox(f"The value for {missingval} is missing!", windowtitle="Missing value!", parent=self)
                return False
        return True

    def extract_url(self, url):
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

    def get_converted_price(self, price):
        """Converts the price argument to a clean number
        
        Args:
            price (str): scrapped price
        
        Returns:
            float: converted price
        """
        price = price.replace(",", ".")
        converted_price = float(re.sub(r"[^\d.]", "", price))

        return converted_price

    def get_product_details(self, url):
        """Extract the needed product details out of the URL.
        
        Args:
            url (str): Adress/URL to scrape from
        
        Returns:
            dict: Details of the scraped product (name, price, deal, shorturl)
        """
        headers = {
            "User-Agent": self.user_agent
        }
        details = {"name": "", "price": 0, "deal": True, "url": ""}
        _url = self.extract_url(url)
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
                details["price"] = self.get_converted_price(price.get_text())
                details["url"] = _url
            else:
                return None
        return details

    def dayly_check(self):
        """Checks periodically if the prices where fetched within the last 12 hours, else fetch all the prices. """
        last_date = self.queryDB("SELECT Date FROM Timestamps WHERE Number = (SELECT MAX(Number) FROM Timestamps)")
        now_date = datetime.datetime.now()
        # when no entry is existing, always set time difference greater than a day
        if len(last_date) > 0:
            # otherwise get the last timestamp entry and subtract it from the current time, gets the difference in days
            last_date = last_date[0][0]
            last_date_time_obj = datetime.datetime.strptime(last_date, '%Y-%m-%d %H:%M:%S')
            delta_time = (now_date - last_date_time_obj).seconds
        else:
            delta_time = 100000
        # if the difference is greater then half a day, fetch all the prices.
        if delta_time >= 43000:
            cannot_write = []
            pricechecks = self.queryDB("SELECT Link, ID, Name FROM Tracklist WHERE Active = 1")
            for product in pricechecks:
                productinfo = self.get_product_details(product[0])
                if productinfo is not None:
                    self.queryDB("INSERT OR IGNORE INTO Pricetracks(ID, Price, Date) VALUES(?,?,?)",(product[1], productinfo["price"], datetime.datetime.strftime(now_date, '%Y-%m-%d')))
                else:
                    # generate a list of failed products
                    cannot_write.append(product[2])
            # at the end of the successfull process, enters the new timestamp
            timestamp = now_date.strftime('%Y-%m-%d %H:%M:%S')
            self.queryDB("INSERT OR IGNORE INTO Timestamps(Date) VALUES(?)",(timestamp,))
            # if there were some problems inform the user
            if len(cannot_write)>0:
                errorstring = ', '.join(cannot_write)
                dialogbox(f'At least for one product, it was not possible to get the price. The products are: {errorstring}. Please check those Links. In case all products failed, check your user-agent and internet connecton!', 'Error while fetching the prices')

    def dialogbox(self, textstring, windowtitle="Message", boxtype="standard", okstring="OK", cancelstring="Cancel", parent=None):
        """The default messagebox for the Maker. Uses a QMessageBox with OK-Button 
        
        Args:
            textstring (str): message displayed on the window
            windowtitle (str, optional): Title of the window. Defaults to "".
            boxtype (str, optional): boxtype, can either be "standard" or "okcancel". Defaults to "standard".
            okstring (str, optional): Text displayed on okay button. Defaults to "OK".
            cancelstring (str, optional): Text displayed on cancle button. Defaults to "Cancel".
            parent (qt_object, optional): Source window for the dialog. Defaults to None.
        
        Returns:
            int: qt specific return value from the dialog
        """
        # print(textstring)
        msgBox = QMessageBox(parent)
        if boxtype == "standard":
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.setIcon(QMessageBox.Information) 
        elif boxtype == "okcancel":
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            buttoncancel = msgBox.button(QMessageBox.Cancel)
            buttoncancel.setText("{: ^12}".format(cancelstring))
            msgBox.setIcon(QMessageBox.Question)
        buttonok = msgBox.button(QMessageBox.Ok)
        buttonok.setText("{: ^12}".format(okstring))
        msgBox.setText(textstring)
        msgBox.setWindowTitle(windowtitle)
        msgBox.setWindowIcon(QIcon('gui/pictures/dollar.png'))
        msgBox.show()
        retval = msgBox.exec_()
        if boxtype == "okcancel":
            return retval

    def connDB(self):
        """Connect to the database and generates a cursor. """
        self.DB = sqlite3.connect(self.db_path)
        self.c = self.DB.cursor()

    def queryDB(self, sql, serachtuple=()):
        """Executes the sql querry, closes the connection afterwards.
        
        Args:
            sql (str): Sql String to execute
            serachtuple (tuple): Aditional arguments to search for
        
        Returns:
            cursor: Data (tuple or None) if a select statement was chosen
        """
        self.connDB()
        self.c.execute(sql, serachtuple)

        if sql[0:6].lower() == 'select':
            result = self.c.fetchall()
            self.DB.close()
            return result
        else:
            self.DB.commit()
            self.DB.close()

    def call_user_agent(self):
        text, ok = QInputDialog.getText(self, 'User-Agent', 'please enter your User-Agent:')
        if ok:
            self.read_config(change=True, user_agent_change=text)
            self.dialogbox(f"Updating user agent: {text}", "User Agent Updated", parent=self)
    
    def createDB(self):
        """Creates the tables for the DB if not already created. """
        self.connDB()
        self.c.execute("CREATE TABLE IF NOT EXISTS Tracklist(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, Name Text NOT NULL, Link TEXT NOT NULL, Shortlink TEXT NOT NULL, Active BOOL NOT NULL);")
        self.c.execute("CREATE TABLE IF NOT EXISTS Pricetracks(Number INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, ID INTEGER NOT NULL, Price FLOAT(2) NOT NULL, Date DATETIME);")
        self.c.execute("CREATE TABLE IF NOT EXISTS Timestamps(Number INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, Date DATETIME);")
        # self.c.execute()
        self.DB.close()

    def read_config(self, change=False, user_agent_change=""):
        config = configparser.ConfigParser()
        config.read(self.config_path)
        if change:
            config["properties"]["useragent"] = user_agent_change
            with open(self.config_path, 'w') as configfile:
                config.write(configfile)
        self.user_agent = config["properties"]["useragent"]

class GraphWindow(QDialog):
    """Opens up a window where the the top five useres (highes quantity) are shown.

    Args:
        plotvalues (list): The x and y values for the plot as as list of lists
        plotname (str): The name for the prodcut
    """
    def __init__(self, parent, plotvalues=None, plotname=""):
        """ Generates the window and plots the diagram. """
        super(GraphWindow, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(1200, 800)
        self.setWindowTitle("Price development of {}".format(plotname))
        self.setWindowFlags(
            Qt.Window |
            Qt.CustomizeWindowHint |
            Qt.WindowTitleHint |
            Qt.WindowCloseButtonHint |
            Qt.WindowStaysOnTopHint
            )
        # self.setModal(True)
        self.ms = parent

        # a figure instance to plot on
        plt.rcParams["date.autoformatter.day"] = "%y/%m/%d"
        self.figure = plt.figure(figsize=(12, 8), dpi=128)
        # adds a button to go back
        self.backbutton = QPushButton('< Back')
        # sets the minimum size and the fontsize
        self.backbutton.setMinimumSize(QSize(0, 50))
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        font.setWeight(75)
        self.backbutton.setFont(font)
        self.backbutton.clicked.connect(lambda: self.close())
        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)
        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.backbutton)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        # clears the old values and then adds a subplot to isert all the data
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        # generates the grap
        print(plotvalues[0], plotvalues[1])
        ax.plot(plotvalues[0], plotvalues[1], 'x-')
        ax.yaxis.grid(linestyle='--', color='k')
        plt.tight_layout()
        # refresh canvas
        self.canvas.draw()