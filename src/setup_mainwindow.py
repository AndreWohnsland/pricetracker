import sys
import sqlite3
import requests
from bs4 import BeautifulSoup
import re
import time
import datetime
import configparser
import traceback
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

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
        self.setWindowIcon(QIcon("gui/pictures/dollar.png"))

        # connection of all Buttons
        self.PB_enter.clicked.connect(lambda: self.enter_data(change=False))
        self.PB_clear.clicked.connect(self.clear_entries)
        self.PB_change.clicked.connect(lambda: self.enter_data(change=True))
        self.PB_plot.clicked.connect(self.plot_price)

        # connects the LW to the function
        self.LW_products.itemClicked.connect(self.display_lw_item)

        # connect the action buttons
        self.action_agent.triggered.connect(self.call_user_agent)
        self.action_exit.triggered.connect(lambda: self.close())
        self.action_fetch_price.triggered.connect(self.fetch_price_singleproduct)

        # generates the threadding for later fetching data
        self.threadpool = QThreadPool()

        # insert the data into the LW
        self.load_listentries()

    def enter_data(self, change=False):
        """Checks and enters the data into the db.
        
        Args:
            change (bool, optional): Checker if the data is new or existing shall be changed. Defaults to False.
        """
        # checks all LE
        validchecker = self.validcheck(
            [self.LE_name, self.LE_url], ["product name", "product URL"]
        )
        # if change without a product was clicked
        if validchecker:
            if not self.LW_products.selectedItems() and change:
                self.dialogbox(
                    "No product was selected to be changed!",
                    "Missing Product",
                    parent=self,
                )
                validchecker = False
        # checks if this link already exists
        if validchecker and not change:
            existing_entry = self.queryDB(
                "SELECT COUNT(*) FROM Tracklist WHERE Link = ?", (self.LE_url.text(),)
            )[0][0]
            if existing_entry:
                self.dialogbox(
                    "This product Link is already existing in the database!",
                    "Existing Product",
                    parent=self,
                )
                validchecker = False
        if validchecker:
            productname = self.LE_name.text()
            productlink = self.LE_url.text()
            trackproduct = 0
            if self.CHB_track.isChecked():
                trackproduct = 1
            # checks if the link is an amzon link
            land, shortlink = self.extract_url(productlink)
            if shortlink is not None and change:
                self.queryDB(
                    "UPDATE OR IGNORE Tracklist SET Name = ?, Link = ?, Shortlink = ?, Active = ?, Land = ? WHERE ID = ?",
                    (productname, productlink, shortlink, trackproduct, self.id, land),
                )
                self.LW_products.currentItem().setText(productname)
                self.clear_entries()
                self.dialogbox(
                    "Data was updagted into the Database successfully",
                    "Data Updated",
                    parent=self,
                )
            elif shortlink is not None:
                # enters the data into the DB
                self.queryDB(
                    "INSERT OR IGNORE INTO Tracklist(Name, Link, Shortlink, Active, Land) VALUES(?,?,?,?,?)",
                    (productname, productlink, shortlink, trackproduct, land),
                )
                # also adds the item into the list widget and sets its internal value to the id in case the name change somehow
                new_id = self.queryDB(
                    "SELECT ID FROM Tracklist WHERE Name = ?", (productname,)
                )[0][0]
                item = QListWidgetItem(str(productname), self.LW_products)
                item.setData(Qt.UserRole, new_id)
                self.LW_products.sortItems()
                self.clear_entries()
                self.dialogbox(
                    "Data was entered into the Database successfully",
                    "Data Entered",
                    parent=self,
                )
            else:
                self.dialogbox(
                    "The given Link is no Amazon Link!",
                    "Invalid Link given!",
                    parent=self,
                )

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
        entries = self.queryDB(
            "SELECT Name, Link, Active FROM Tracklist WHERE ID = ?", (self.id,)
        )[0]
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
            pricetable = self.queryDB(
                "SELECT Price, Date FROM Pricetracks WHERE ID = ?", (self.id,)
            )
            x_values = []
            y_values = []
            for valuepair in pricetable:
                x_values.append(datetime.datetime.strptime(valuepair[1], "%Y-%m-%d"))
                y_values.append(valuepair[0])
            # Calls a new window, which shows the graph
            productname, productland = self.queryDB(
                "SELECT Name, Land From Tracklist WHERE ID = ?", (self.id,)
            )[0]
            # print(productname, productland)
            self.gw = GraphWindow(self, x_values, y_values, productname, landcode=productland)
            self.gw.show()
        else:
            self.dialogbox(
                "Please select a product to plot the price over the time.",
                "No Product Selected",
            )

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
                self.dialogbox(
                    f"The value for {missingval} is missing!",
                    windowtitle="Missing value!",
                    parent=self,
                )
                return False
        return True

    # the concept of extract_url and get_product_details was found on:
    # https://medium.com/@deeprajpradhan/tutorial-amazon-price-tracker-using-python-and-mongodb-part-1-aece6347ec63
    # and adapted to be more flexible and suit the case of this programm
    def extract_url(self, url):
        """Creates a short version of the URL to work with. Also returns None if its not a valid adress.
        
        Args:
            url (str): The long version of the URL to shorten
        
        Returns:
            tuple: The land code and the short version of the URL in the format (land, url)
        """
        land = ""
        if url.find("www.amazon.de") != -1:
            index = url.find("/dp/")
            if index != -1:
                index2 = index + 14
                url = "https://www.amazon.de" + url[index:index2]
                land = "de"
            else:
                index = url.find("/gp/")
                if index != -1:
                    index2 = index + 22
                    url = "https://www.amazon.de" + url[index:index2]
                    land = "de"
                else:
                    url = None
        elif url.find("www.amazon.com") != -1:
            index = url.find("/dp/")
            if index != -1:
                index2 = index + 15
                url = "https://www.amazon.com" + url[index:index2]
                land = "com"
            else:
                index = url.find("/gp/")
                if index != -1:
                    index2 = index + 23
                    url = "https://www.amazon.com" + url[index:index2]
                    land = "com"
                else:
                    url = None 
        else:
            url = None
        return (land, url)

    def get_converted_price(self, price, landcode="de"):
        """Converts the price argument to a clean number
        
        Args:
            price (str): scrapped price
        
        Returns:
            float: converted price
        """
        sep = {
            "de": ".",
            "com": ","
        }
        decimal = {
            "de": ",",
            "com": "."
        }

        price = price.replace(sep[landcode], "")
        price = price.replace(decimal[landcode], ".")
        converted_price = float(re.sub(r"[^\d.]", "", price))

        return converted_price

    def get_product_details(self, url):
        """Extract the needed product details out of the URL.
        
        Args:
            url (str): Adress/URL to scrape from
        
        Returns:
            dict: Details of the scraped product (name, price, deal, shorturl)
        """
        headers = {"User-Agent": self.user_agent}
        details = {"name": "", "price": 0, "deal": True, "url": "", "land": ""}
        land, _url = self.extract_url(url)
        # print(land)
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
                # print(price.get_text())
                details["price"] = self.get_converted_price(price.get_text(), landcode=land)
                details["url"] = _url
            else:
                return None
        return details

    # in the end, this process should run in the background, but then the message box, or the progress box needs to be moves to the mainwindow
    # @lox.thread(4)
    def dayly_check(self, progress_callback, oneproduct=False, oneproduct_details=[]):
        """Checks periodically if the prices where fetched within the last 12 hours, else fetch all the prices. 
        
        Args:
            oneproduct (bool, optional): Set to true if only the selected Product shall be updated. Defaults to False.
            oneproduct_details (list, optional): List of Tuples for the productdetails, consists of the Link and the ID. Defaults to [].
        """
        checknow = False
        last_date = self.queryDB(
            "SELECT Date FROM Timestamps WHERE Number = (SELECT MAX(Number) FROM Timestamps)"
        )
        now_date = datetime.datetime.now()
        # when no entry is existing, always set time difference greater than a day
        if len(last_date) > 0:
            # otherwise get the last timestamp entry and subtract it from the current time, gets the difference in days
            last_date = last_date[0][0]
            last_date_time_obj = datetime.datetime.strptime(
                last_date, "%Y-%m-%d %H:%M:%S"
            )
            delta_time = now_date - last_date_time_obj
            if delta_time.days >= 1 or delta_time.seconds >= 43000:
                checknow = True
        else:
            checknow = True
        # if the difference is greater then half a day, fetch all the prices.
        if checknow or oneproduct:
            print("STARTING GETTING PRICES!")
            # self.prodia = QProgressDialog(
            #     "Check of the prices, please wait untill the process is finished.", None, 0, 100, self
            # )
            # self.prodia.show()
            # self.prodia.setWindowTitle("Getting Todays Prices")
            # self.prodia.setValue(0)
            # qApp.processEvents()
            cannot_write = []
            if oneproduct:
                pricechecks = oneproduct_details
            else:
                pricechecks = self.queryDB(
                    "SELECT Link, ID, Name FROM Tracklist WHERE Active = 1"
                )
            for step, product in enumerate(pricechecks):
                print(f"Getting {step+1}. Product")
                productinfo = self.get_product_details(product[0])
                if productinfo is not None:
                    self.queryDB(
                        "INSERT OR IGNORE INTO Pricetracks(ID, Price, Date) VALUES(?,?,?)",
                        (
                            product[1],
                            productinfo["price"],
                            datetime.datetime.strftime(now_date, "%Y-%m-%d"),
                        ),
                    )
                else:
                    # generate a list of failed products
                    cannot_write.append(product[2])
                # self.prodia.setValue((step + 1) / len(pricechecks) * 100)
                # qApp.processEvents()
            # at the end of the successfull process, enters the new timestamp
            if not oneproduct:
                timestamp = now_date.strftime("%Y-%m-%d %H:%M:%S")
                self.queryDB(
                    "INSERT OR IGNORE INTO Timestamps(Date) VALUES(?)", (timestamp,)
                )
            # self.prodia.close()
            # if there were some problems inform the user
            print("DONE WITH PRICEGETTING!")
            if len(cannot_write) > 0:
                errorstring = ", ".join(cannot_write)
                return errorstring
            else:
                return None

    def get_details_thread(self, oneproduct=False, oneproduct_details=[]):
        """Own thread start function to get the details of each tracked product
        
        Args:
            oneproduct (bool, optional): If only a single product is checked or the whole DB. Defaults to False.
            oneproduct_details (list, optional): Lists of products to check. Defaults to [].
        """
        # Pass the function to execute
        worker = Worker(
            self.dayly_check,
            oneproduct=oneproduct,
            oneproduct_details=oneproduct_details,
        )  # Any other args, kwargs are passed to the run function
        worker.signals.result.connect(self.get_thread_output)
        # worker.signals.finished.connect(self.thread_complete)
        # worker.signals.progress.connect(self.progress_fn)
        # Execute
        self.threadpool.start(worker)

    def get_thread_output(self, s):
        """Output function at end of the thread.
        
        Args:
            s (string): Summary of all failed products
        """
        if s is not None:
            self.dialogbox(
                f"At least for one product, it was not possible to get the price. The products are: {s}. Please check those Links. In case all products failed, check your user-agent and internet connecton!",
                "Error while fetching the prices",
            )

    def fetch_price_singleproduct(self):
        """Updates the Price for the selected product. """
        if self.LW_products.selectedItems():
            productlink = self.queryDB(
                "SELECT Link FROM Tracklist WHERE ID = ?", (self.id,)
            )[0][0]
            # self.dayly_check(None, oneproduct=True, oneproduct_details=[(productlink, self.id, "single product")])
            self.get_details_thread(
                oneproduct=True,
                oneproduct_details=[(productlink, self.id, "single product")],
            )
        else:
            self.dialogbox(
                "No product was selected to get the new price from.",
                "No Product Selected",
                parent=self,
            )

    def dialogbox(
        self,
        textstring,
        windowtitle="Message",
        boxtype="standard",
        okstring="OK",
        cancelstring="Cancel",
        parent=None,
    ):
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
        msgBox.setWindowIcon(QIcon("gui/pictures/dollar.png"))
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

        if sql[0:6].lower() == "select":
            result = self.c.fetchall()
            self.DB.close()
            return result
        else:
            self.DB.commit()
            self.DB.close()

    def call_user_agent(self):
        text, ok = QInputDialog.getText(
            self, "User-Agent", "please enter your User-Agent:"
        )
        if ok:
            self.read_config(change=True, user_agent_change=text)
            self.dialogbox(
                f"Updating user agent: {text}", "User Agent Updated", parent=self
            )

    def createDB(self):
        """Creates the tables for the DB if not already created. """
        self.connDB()
        self.c.execute(
            "CREATE TABLE IF NOT EXISTS Tracklist(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, Name Text NOT NULL, Link TEXT NOT NULL, Shortlink TEXT NOT NULL, Active BOOL NOT NULL);"
        )
        self.c.execute(
            "CREATE TABLE IF NOT EXISTS Pricetracks(Number INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, ID INTEGER NOT NULL, Price FLOAT(2) NOT NULL, Date DATETIME);"
        )
        self.c.execute(
            "CREATE TABLE IF NOT EXISTS Timestamps(Number INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, Date DATETIME);"
        )
        # self.c.execute()
        self.DB.close()

    def read_config(self, change=False, user_agent_change=""):
        config = configparser.ConfigParser()
        config.read(self.config_path)
        if change:
            config["properties"]["useragent"] = user_agent_change
            with open(self.config_path, "w") as configfile:
                config.write(configfile)
        self.user_agent = config["properties"]["useragent"]


class GraphWindow(QDialog):
    """Opens up a window where the the top five useres (highes quantity) are shown.

    Args:
        plotvalues (list): The x and y values for the plot as as list of lists
        plotname (str): The name for the prodcut
    """

    def __init__(self, parent, x=None, y=None, plotname="", landcode="de"):
        """ Generates the window and plots the diagram. """
        super(GraphWindow, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(1200, 800)
        self.setWindowTitle("Price development of {}".format(plotname))
        self.setWindowFlags(
            Qt.Window
            | Qt.CustomizeWindowHint
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowStaysOnTopHint
        )
        # self.setModal(True)
        self.ms = parent

        # initialize the different currency of the lands
        currency_code = {
            "de": "€",
            "com": "$",
        }

        self.currency = currency_code[landcode]

        # a figure instance to plot on
        plt.rcParams["date.autoformatter.day"] = "%y/%m/%d"
        self.figure = plt.figure(figsize=(12, 8), dpi=128)
        # adds a button to go back
        self.backbutton = QPushButton("< Back")
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
        # print(x, y)
        y_mean = np.mean(y)
        y_max = np.max(y)
        y_min = np.min(y)
        y_m = [y_mean for val in y]
        checker1 = [0 if a > b else 1 for a, b in zip(y, y_m)]
        checker2 = [0 if a < b else 1 for a, b in zip(y, y_m)]
        ax.plot(x, y, "+-", linewidth=3, markersize=10)
        ax.plot(x, y_m, linestyle="-.", c="k")
        if len(x) > 1:
            ax.fill_between(
                x, y, y_m, color="g", alpha=0.2, where=checker1, interpolate=True
            )
            ax.fill_between(
                x, y, y_m, color="r", alpha=0.2, where=checker2, interpolate=True
            )
            ax.set_xlim(min(x), max(x))
            # generates the legend elements and labels
            legend_elements = [
                Patch(facecolor="g", edgecolor="g", alpha=0.15),
                Patch(facecolor="r", edgecolor="r", alpha=0.15),
                Line2D([0], [0], ls="-.", color="k", lw=3),
            ]
            legend_labels = [
                f"minimal value = {y_min} {self.currency}",
                f"maximal value = {y_max} {self.currency}",
                f"mean value = {y_mean:.2f} {self.currency}",
            ]
            plt.legend(legend_elements, legend_labels)
        ax.yaxis.grid(linestyle="--", color="k")
        plt.tight_layout()
        # refresh canvas
        self.canvas.draw()


# the concept of multitreading is taken out of:
# Create Simple GUI Applications Book from Martin Fitzpatrick
# and was adapted to my problem accordingly
class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data
    
    error
        `tuple` (exctype, value, traceback.format_exc() )
    
    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress 

    """

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    """
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs["progress_callback"] = self.signals.progress

    @pyqtSlot()
    def run(self):
        """
        Initialise the runner function with passed args, kwargs.
        """

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
