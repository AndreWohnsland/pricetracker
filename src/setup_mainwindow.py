import sys
import sqlite3

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
        self.createDB()

        # connection of all Buttons
        self.PB_enter.clicked.connect(self.enter_data)
        self.PB_clear.clicked.connect(self.clear_entries)
        self.PB_plot.clicked.connect(self.plot_price)

    def enter_data(self):
        """ Checks and enters the data into the db. """
        validchecker = self.validcheck([self.LE_name, self.LE_url], ["product name", "product URL"])
        if validchecker:
            print("yay everything is fine!")

    def clear_entries(self):
        """ Clears the entry labels. """
        self.LE_name.clear()
        self.LE_url.clear()
        self.CHB_track.setChecked(False)

    def plot_price(self):
        """ Gets all the prices for the selected Item. """
        pass

    def validcheck(self, lineedits, missingvals=[""]):
        for lineedit, missingval in zip(lineedits, missingvals):
            if lineedit.text() == "":
                self.dialogbox(f"The value for {missingval} is missing!", windowtitle="Missing value!", parent=self)
                return False
        return True

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
            [int]: [qt specific return value from the dialog]
        """
        # print(textstring)
        msgBox = QMessageBox(parent)
        if boxtype == "standard":
            msgBox.setStandardButtons(QMessageBox.Ok)   
        elif boxtype == "okcancel":
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            buttoncancel = msgBox.button(QMessageBox.Cancel)
            buttoncancel.setText("{: ^12}".format(cancelstring))
        buttonok = msgBox.button(QMessageBox.Ok)
        buttonok.setText("{: ^12}".format(okstring))
        msgBox.setText(textstring)
        msgBox.setWindowTitle(windowtitle)
        msgBox.setWindowIcon(QIcon(''))
        msgBox.show()
        retval = msgBox.exec_()
        if boxtype == "okcancel":
            return retval

    def connDB(self):
        """Connect to the database and generates a cursor
        """
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
    
    def createDB(self):
        """ Creates the tables for the DB if not already created. """
        self.connDB()
        self.c.execute("CREATE TABLE IF NOT EXISTS Tracklist(ID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, Name Text NOT NULL, Link TEXT NOT NULL, Active BOOL NOT NULL);")
        self.c.execute("CREATE TABLE IF NOT EXISTS Tracklist(Number INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, ID INTEGER NOT NULL, Price FLOAT(2) NOT NULL);")
        # self.c.execute()
        self.DB.close()