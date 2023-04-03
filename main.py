import os
import sys
from functools import partial
from threading import Thread

# The LGPL license does not require you to share the source code of your own applications,
# even if they are bundled with PySide2.
from PySide2 import QtCore, QtGui, QtSerialPort, QtWidgets
from PySide2.QtCore import Qt, QTimer, QObject, QPropertyAnimation, QPoint, Signal, Slot, QSize, QRectF
from PySide2.QtGui import QFont, QMovie, QPixmap, QPainter, QLinearGradient, QStandardItemModel
from PySide2.QtSerialPort import QSerialPort
from PySide2.QtWidgets import QMainWindow, QWidget, QToolButton, QApplication, QVBoxLayout, \
    QFileDialog, QDialog, QCompleter, QLabel, QMessageBox, QProgressBar, QSplashScreen
# Watchdog is licensed under the terms of the Apache License, version 2.0.
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
# To show system notification (tost msg)
# TODO look for better lib - system notification  maybe "winotify"
from windowstoast import Toast

from IniFile import handle_ini  # Function To handle INI file
from JobInputDialog import Ui_JobInputDialog
from List_lbl import Ui_ListViewWidget  # List view custom widget class UI file
from Main_UI import Ui_MainWindow  # Main window UI file
from Product_lbl import Ui_Product
from Tray_icon import SystemTrayIcon  # To handle System tray ICON function
from db_CU_widget import Ui_CU_list  # Dashboard custom widget - for monitoring Control units
from db_oil_widget import Ui_db_oil_widget  # Dashboard  custom Oil level widget  UI file
# import sqlCode  # SQLITE dada base function
from sqlCode import handle_database
from tank_lbl import Ui_tank_list
from splash import Ui_Splash
from report_gen import Ui_Dialog
from SerialCommunicator import SerialCommunicator
# Importing local class and functions


css_file = "css_file.css"
with open(css_file, "r") as fh:
    this_qss = fh.read()


def load_qss():
    global css_file
    css_file = "css_file.css"
    with open(css_file, "r") as fh1:
        global this_qss
        this_qss = fh1.read()


def set_qss(for_this):
    global this_qss
    for_this.setStyleSheet(this_qss)

    # app.setStyleSheet(fh.read())


# class LoadingScreen(QDialog):
class LoadingScreen(QtWidgets.QWidget):
    def __init__(self, steps=5, *args, **kwargs):
        super(LoadingScreen, self).__init__(*args, **kwargs)
        self.ui = Ui_Splash()
        self.ui.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('app_icon.ico'))
        # self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.show()
        app.processEvents()


class LoadingScreen11(QObject):
    def __init__(self):
        super().__init__()
        splash_pix = QPixmap('R:/ATS_clms_v01_0123/Icons/flc_design2022090867482.png')

        self.splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        self.splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.splash.setEnabled(False)
        self.splash.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.splash.setMask(splash_pix.mask())
        # splash = QSplashScreen(splash_pix)
        # adding progress bar

        self.splash.setMask(splash_pix.mask())

        self.splash.show()
        self.splash.showMessage("<h1><font color='green'>ATS Elgi</font></h1>", Qt.AlignTop | Qt.AlignCenter, Qt.black)


# File watcher Class
class Watchdog(PatternMatchingEventHandler, Observer):
    def __init__(self, path='.', patterns='*', logfunc=print):
        PatternMatchingEventHandler.__init__(self, patterns)
        Observer.__init__(self)
        self.schedule(self, path=path, recursive=False)
        self.log = logfunc

    def on_created(self, event):
        # This function is called when a file is created
        self.log(f"{event.src_path} has been created!")

    def on_deleted(self, event):
        # This function is called when a file is deleted
        self.log(f"deleted {event.src_path}!")

    def on_modified(self, event):
        # This function is called when a file is modified
        self.log(f"{event.src_path} has been modified")

    def on_moved(self, event):
        # This function is called when a file is moved
        self.log(f"moved {event.src_path} to {event.dest_path}")


# List view widget UI file call
class JobList(QWidget):
    def __init__(self, in_data, parent=None):
        super().__init__(parent)
        self.JobListUI = Ui_ListViewWidget()
        self.JobListUI.setupUi(self)
        set_qss(self)
        self.JobListUI.job_del.clicked.connect(lambda: self.local_buttonClick_func(QToolButton, 'job_del'))
        self.JobListUI.job_pause.clicked.connect(lambda: self.local_buttonClick_func(QToolButton, 'job_pause'))
        self.JobListUI.job_edit.clicked.connect(lambda: self.local_buttonClick_func(QToolButton, 'job_edit'))
        self.JobListUI.job_no.setText(str(in_data['JobID']))
        self.JobListUI.ref_no.setText('ID - ' + str((in_data['RefID'])))
        self.JobListUI.oil_dec.setText(in_data['OilID'])
        self.JobListUI.preset.setText(str(in_data['PreSetValue']))
        self.JobListUI.model.setText(in_data['VehicleModel'])
        self.JobListUI.date_info.setText(in_data['DateOfCreation'][:19])
        self.JobListUI.auto_del.setEnabled(False)
        self.JobListUI.print.setEnabled(False)
        if in_data['Print']:
            self.JobListUI.print.setChecked(True)
        # TODO - this is to highlight to the user for the job he is searching for, just a POC as of now need to improve
        self.anim = QPropertyAnimation(self.JobListUI.animate, b"pos")
        self.anim.setEndValue(QPoint(324, 1))
        self.anim.setDuration(200)

    # called when clicking buttons in joblist widgets and pass it to MainWindow buttonclick function
    def local_buttonClick_func(self, object, button_id):
        print(button_id, object)
        Main_Window.buttonClick_from_job_view(self.JobListUI, button_id)


# Dashboard oil tank view widget UI file call
class TankList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.TankID = None
        self.TankName = None
        self.OilID = None
        self.MaxLevel = 0
        self.WarningLevel = 0
        self.AlarmLevel = 0
        self.LevelSensor = False
        self.TankEnabled = False
        self.TankListUI = Ui_db_oil_widget()
        self.TankListUI.setupUi(self)
        # self.TankListUI.toolButton.clicked.connect(lambda: self.buttonClick(QToolButton))

    # Todo - Reading data base for active jobs and assign object name based on table ID
    def set_obj_name(self, text):
        i = 20000 + int(text)
        self.setObjectName("_{}".format(i))
        # self.TankListUI.Tank_name.setText("Tank - " + text)


class CUList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.CUName = None
        self.Addon = False
        self.CUID = None
        self.CUEnabled = True
        self.CUPrinter = False
        self.CUPrinterEnabled = False
        self.CURfID = False
        self.CURfIDEnabled = False
        self.CUStatus = None
        self.Guns = {}
        self.CUListUI = Ui_CU_list()
        self.CUListUI.setupUi(self)
        self.CUListUI.Gun_7.setEnabled(False)
        # Todo - Add functions to manage gun enable/disable, add function to assign variables


class product_list(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ProductUI = Ui_Product()
        self.ProductUI.setupUi(self)


class Tank_list(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.TankUI = Ui_tank_list()
        self.TankUI.setupUi(self)


# class for input form widget
class InputForm(QDialog):
    def __init__(self, make_dict, model_dict, parent):
        super(InputForm, self).__init__(parent)
        self.make_dict = make_dict
        self.model_dict = model_dict
        self.InputFormUI = Ui_JobInputDialog()
        self.InputFormUI.setupUi(self)
        # self.setWindowTitle("no title")
        set_qss(self)
        Oildes = ["CASTROL MAGNATEC 10W-40", "CASTROL GTX SUV 5W-30"]

        self.validator_to_upper_case = ValidatorToUpper(self)
        self.InputFormUI.JobNo.setValidator(self.validator_to_upper_case)
        #self.InputFormUI.LPNo.setValidator(self.validator_to_upper_case)
        self.InputFormUI.Model.setValidator(self.validator_to_upper_case)
        self.InputFormUI.Make.setValidator(self.validator_to_upper_case)
        self.InputFormUI.PreSet.setValidator(QtGui.QDoubleValidator(
            0.0,  # bottom
            1000.0,  # top
            2,  # decimals
            notation=QtGui.QDoubleValidator.StandardNotation
        ))
        self.InputFormUI.comboBox.addItems(Oildes)
        self.InputFormUI.Make.returnPressed.connect(self.checkText)
        self.InputFormUI.Make.textChanged.connect(self.checkText)
        make_list = []
        for i in range(len(self.make_dict)):
            temp = make_dict[i]
            make_list.append(temp['Make'])
        # print(make_list)
        completer_car_make_list = QCompleter(make_list)
        completer_car_make_list.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.InputFormUI.Make.setCompleter(completer_car_make_list)

        self.setWindowTitle("New Job")

    def mousePressEvent(self, event):
        # Disable dragging of the dialog
        pass

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Down:
            self.focusNextPrevChild(True)
        elif e.key() == Qt.Key_Up:
            self.focusNextPrevChild(False)

    def checkText(self):
        self.InputFormUI.Model.setText("")
        car_models = []
        for i in range(len(self.model_dict)):
            if self.model_dict[i]['Make'].upper() == self.InputFormUI.Make.text():
                car_models.append(self.model_dict[i]["Model"])
        completer_car_model = QCompleter(car_models)
        completer_car_model.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.InputFormUI.Model.setCompleter(completer_car_model)

    # Move focus to next item in dialog box when press Enter key
    def event(self, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self.focusNextPrevChild(True)
        return super().event(event)

    def ResetForm(self):
        self.InputFormUI.JobNo.setFocus()
        self.InputFormUI.JobNo.setText("")
        self.InputFormUI.Make.setText("")
        self.InputFormUI.Model.setText("")

    def GetData(self):
        # (JobID, VehicleNumber, OilID, UOMID, CUID, GunID, UserIDDispensed, OdoMeter, VehicleMake, VehicleModel,
        # DateOfCreation, DateOfCompletion,
        # DateOfModification, StatusNow, UserTerminated, UserTerminatedID, PreSetValue, ActualValue,SentToCU)
        # current_time = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        # TODO -  on testing,  not completted for all data
        TempData = {'JobID': self.InputFormUI.JobNo.text(), 'VehicleNumber': self.InputFormUI.LPNo.text(),
                    'OilID': self.InputFormUI.comboBox.currentText(), 'UOMID': "", 'CUID': "",
                    'GunID': self.InputFormUI.GunID.text(), 'UserIDDispensed': "", 'OdoMeter': 0,
                    'VehicleMake': self.InputFormUI.Make.text(), 'VehicleModel': self.InputFormUI.Model.text(),
                    'DateOfCreation': "", 'DateOfModification': "", 'StatusNow': "",
                    'UserTerminated': "", 'UserTerminatedID': "", 'PreSetValue': self.InputFormUI.PreSet.text(),
                    'ActualValue': 0, 'SentToCU': False, 'AutoDelete': self.InputFormUI.AutoDelete.isChecked(),
                    'Print': self.InputFormUI.Print.isChecked()}
        return TempData


class report_config(QDialog):
    def __init__(self, parent):
        super(report_config, self).__init__(parent)
        self.report_config_UI = Ui_Dialog()
        self.report_config_UI.setupUi(self)
        self.report_config_UI.Product_selector.setVisible(False)
        self.report_config_UI.User_frame.setVisible(False)
        self.report_config_UI.Date_from.setVisible(False)
        self.report_config_UI.Date_to.setVisible(False)
        self.report_config_UI.Job_frame.setVisible(False)
        self.report_config_UI.Product_frame.setVisible(False)
        self.report_config_UI.CU_frame.setVisible(False)
        self.report_config_UI.Others_frame.setVisible(False)
        self.report_config_UI.Product_all.clicked.connect(self.radio_prd_clicked)
        self.report_config_UI.Product_single.clicked.connect(self.radio_prd_clicked)
        self.report_config_UI.Date_all.clicked.connect(self.radio_date_clicked)
        self.report_config_UI.Date_single.clicked.connect(self.radio_date_clicked)
        self.report_config_UI.Date_intervel.clicked.connect(self.radio_date_clicked)
        self.report_config_UI.User_single.clicked.connect(self.radio_user_clicked)
        self.report_config_UI.User_all.clicked.connect(self.radio_user_clicked)
        self.report_config_UI.Job_all.clicked.connect(self.radio_job_clicked)
        self.report_config_UI.Job_single.clicked.connect(self.radio_job_clicked)
        self.report_config_UI.CU_all.clicked.connect(self.radio_CU_clicked)
        self.report_config_UI.CU_single.clicked.connect(self.radio_CU_clicked)
        self.report_config_UI.Others_all.clicked.connect(self.radio_Others_clicked)
        self.report_config_UI.Others_selected.clicked.connect(self.radio_Others_clicked)

        # self.report_config_UI.Product_single.toggled.connect(self.radio_prd_clicked)

    def radio_prd_clicked(self, enabled):
        sender_ = self.sender()
        if self.report_config_UI.Product_all.isChecked():
            self.report_config_UI.Product_selector.setVisible(False)
            self.report_config_UI.Product_frame.setVisible(False)
        else:
            self.report_config_UI.Product_selector.setVisible(True)
            self.report_config_UI.Product_frame.setVisible(True)

    def radio_date_clicked(self, enabled):
        sender_ = self.sender()
        if self.report_config_UI.Date_all.isChecked():
            self.report_config_UI.Date_from.setVisible(False)
            self.report_config_UI.Date_to.setVisible(False)
        if self.report_config_UI.Date_single.isChecked():
            self.report_config_UI.Date_from.setVisible(True)
            self.report_config_UI.Date_to.setVisible(False)
        if self.report_config_UI.Date_intervel.isChecked():
            self.report_config_UI.Date_from.setVisible(True)
            self.report_config_UI.Date_to.setVisible(True)

    def radio_user_clicked(self, enabled):
        if self.report_config_UI.User_single.isChecked():
            self.report_config_UI.User_frame.setVisible(True)
        else:
            self.report_config_UI.User_frame.setVisible(False)

    def radio_job_clicked(self,enabled):
        if self.report_config_UI.Job_all.isChecked():
            self.report_config_UI.Job_frame.setVisible(False)
        if self.report_config_UI.Job_single.isChecked():
            self.report_config_UI.Job_frame.setVisible(True)

    def radio_CU_clicked(self, enabled):
        if self.report_config_UI.CU_all.isChecked():
            self.report_config_UI.CU_frame.setVisible(False)
        if self.report_config_UI.CU_single.isChecked():
            self.report_config_UI.CU_frame.setVisible(True)
            
    def radio_Others_clicked(self, enabled):
        if self.report_config_UI.Others_all.isChecked():
            self.report_config_UI.Others_frame.setVisible(False)
        if self.report_config_UI.Others_selected.isChecked():
            self.report_config_UI.Others_frame.setVisible(True)


# to validate the Qline input to uppercase
class ValidatorToUpper(QtGui.QValidator):
    def validate(self, string, pos):
        return QtGui.QValidator.Acceptable, string.upper(), pos


# Class for Signals
class MySignalBasket(QtCore.QObject):
    SigDataReady = Signal(
        str)  # to handle RS485 data,get triggered when a data packet (as str) is ready @ function # name??
    SigWriteDB = Signal()
    SigTest = Signal()



def XORcipher(plaintext):
    output = ""
    key = 'ATS'
    for i, character in enumerate(plaintext):
        output += chr(ord(character) ^ ord(key[i % len(key)]))
    return output


# Mainwindow class
class Main_Window(QMainWindow):
    oldPos = None
    serial_buffer = bytearray()
    BorderWidth = 5

    def __init__(self):
        super(Main_Window, self).__init__()
        self.alt_key_press = False
        self.RS485Frame = None
        self.ini_file = handle_ini()
        print(self.ini_file.read("time"))
        self.Dms_file_name = None
        self.Dms_dir_name = None
        self.watchdog = None
        self.watch_path = None
        self.car_list_make_dict = None
        # ------------------------------------

        # Testing singanls and slots #############
        self.SignalBasket = MySignalBasket()
        self.SignalBasket.SigTest.connect(self.sig_test)
        #self.SignalBasket.SigDataReady.connect(self.data_ready)
        # Set up the user interface from Designer.
        self.Main_WindowUI = Ui_MainWindow()
        self.Main_WindowUI.setupUi(self)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        self.Main_WindowUI.scrollArea.setWidgetResizable(True)
        self.job_widget = QWidget()


        self.t_wid = QWidget()
        self.t_wid.setMinimumWidth(400)
        self.t_wid.setMaximumHeight(13)

        # --------Table_wid trial ----
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(['Name', 'Age', 'Sex', 'Add'])

        ### Adding anything to status bar - now on trial

        self.test = QLabel("V - 1.0")
        self.Main_WindowUI.statusbar.addPermanentWidget(self.test)
        self.Main_WindowUI.statusbar.showMessage("Not Connected")
        self.Main_WindowUI.stackedWidget.setCurrentIndex(0)
        self.Main_WindowUI.tabWidget.setAttribute(QtCore.Qt.WA_StyledBackground)

        # /////////////////////////////////////////////#
        current_windows_dir = os.getcwd()
        self.MainDbName = "Clms_main.db"
        self.SystemDbName = "Clms_settings.db"
        self.DataBaseDir = current_windows_dir + "/database/"
        self.dB = handle_database()
        self.temp_dir11 = current_windows_dir + "/database/" + self.MainDbName
        self.dB.check_database(self.temp_dir11)
        temp_dir = current_windows_dir + "/database"
        self.dB.try_sql(temp_dir)
        self.job_list_dict = self.dB.sql_data_to_list_of_dicts(self.temp_dir11, "SELECT * FROM Jobs ")
        self.oil_list_dict = self.dB.sql_data_to_list_of_dicts(self.temp_dir11, "SELECT * FROM oilData")
        self.user_list_dict = self.dB.sql_data_to_list_of_dicts(self.temp_dir11, "SELECT * FROM userData")
        self.car_list_make_dict = self.dB.sql_data_to_list_of_dicts(self.temp_dir11,
                                                                    "SELECT  DISTINCT Make FROM carData")
        self.car_list_model_dict = self.dB.sql_data_to_list_of_dicts(self.temp_dir11, "SELECT  * FROM carData")
        # print(self.job_list_dict)

        print(len(self.job_list_dict))
        print("in job list")
        self.job_list_dict = self.dB.sql_data_to_list_of_dicts(self.temp_dir11, "SELECT * FROM Jobs ")
        print(len(self.job_list_dict))
        self.job_list_vbox = QVBoxLayout(
            self)  # The Vertical Box that contains the Horizontal Boxes of  labels and buttons
        self.job_list_vbox.setAlignment(Qt.AlignTop)
        self.job_list_vbox.setSpacing(35)
        self.Main_WindowUI.tableWidget.setRowCount(len(self.job_list_dict))
        for i in range(len(self.job_list_dict)):
            dict_data = self.extract_from_job_list_dict(i)
            self.Main_WindowUI.tableWidget.setItem(i, 0, QtWidgets.QTableWidgetItem(str(dict_data['RefID'])))
            self.dynamic_class_variable = "Ref_" + str(dict_data['RefID'])
            vars(self)[self.dynamic_class_variable] = JobList(dict_data)
            self.new_item = vars(self)[self.dynamic_class_variable]
            self.job_list_vbox.addWidget(self.new_item)
        # self.job_widget.setLayout( self.job_list_vbox)
        self.Main_WindowUI.job_scr.setLayout(self.job_list_vbox)

        # /////////////////////////////////////////////#
        ## ==> MOVE WINDOW / MAXIMIZE / RESTORE
        ########################################################################
        def moveWindow(event):
            if event.buttons() == Qt.LeftButton:
                self.move(self.pos() + event.globalPos() - self.dragPos)
                self.dragPos = event.globalPos()
                event.accept()

        # WIDGET TO MOVE
        self.Main_WindowUI.Title.mouseMoveEvent = moveWindow

        ## ==> END ##
        def dobleClickMaximizeRestore(event):
            # IF DOUBLE CLICK CHANGE STATUS
            if event.type() == QtCore.QEvent.MouseButtonDblClick:
                self.showMaximized()

        self.Main_WindowUI.Title.mouseDoubleClickEvent = dobleClickMaximizeRestore
        ### ==> MINIMIZE
        # self.Main_WindowUI.btn_minimize.clicked.connect(lambda: self.showMinimized())
        self.Main_WindowUI.Btn_min.clicked.connect(lambda: self.btn_min_clicked())

        ## ==> MAXIMIZE/RESTORE
        self.Main_WindowUI.Btn_max.clicked.connect(lambda: self.maximize_restore())

        ## SHOW ==> CLOSE APPLICATION
        self.Main_WindowUI.Btn_close.clicked.connect(lambda: self.hide())

        # Handle button event inside the gui
        self.Main_WindowUI.LBtn_1.clicked.connect(partial(self.handle_button_clicked, 0))
        self.Main_WindowUI.LBtn_2.clicked.connect(partial(self.handle_button_clicked, 1))
        self.Main_WindowUI.LBtn_3.clicked.connect(partial(self.handle_button_clicked, 2))
        self.Main_WindowUI.LBtn_4.clicked.connect(partial(self.handle_button_clicked, 3))
        self.Main_WindowUI.LBtn_5.clicked.connect(partial(self.handle_button_clicked, 4))
        self.Main_WindowUI.LBtn_6.clicked.connect(partial(self.handle_button_clicked, 5))
        self.Main_WindowUI.pb1.clicked.connect(partial(self.select_path))
        self.Main_WindowUI.Port_list.currentTextChanged.connect(self.on_combobox_changed)
        self.Main_WindowUI.Listbtn_add.clicked.connect(partial(self.ShowInputForm))
        self.Main_WindowUI.Listbtn_search.clicked.connect(partial(self.search_job))
        self.Main_WindowUI.Report_gen.clicked.connect(partial(self.show_report_gen))

        # Dashboard oil level widget fill up
        self.fill_db_CU_window()
        self.fill_db_oil_window()
        self.fill_list_view_window()
        self.fill_product_window()
        self.fill_tank_window()

        self.tempForm = InputForm(self.car_list_make_dict, self.car_list_model_dict, self)
        self.tempForm.InputFormUI.Cancel.clicked.connect(lambda: self.tempForm.close())
        self.tempForm.InputFormUI.toolButton.clicked.connect(partial(self.SaveData))
        self.Treport_gen = report_config(self)
        self.Treport_gen.report_config_UI.Cancel.clicked.connect(lambda: self.Treport_gen.close())
        self.Treport_gen.report_config_UI.OK.clicked.connect(partial(self.report_gen))

        child = self.Main_WindowUI.db_oil_view_scrl.findChild(QObject, "_{}".format(20003))
        # child.TankListUI.Oil_ID_dash.setText("Hello")


        # All initialization have been completed and ready to start communication
        # TODO need to check the port status and config file settings for port config.
        # Serial port info set up
        self.serial = SerialCommunicator()
        self.serial.set_rx_callback(self.handle_rx)
        self.serial.set_error_callback(self.handle_error)
        self.serial.rx_signal.connect(self.handle_rx)

        self.port_name = "COM3"
        self.populate_ports()
        self.open_port()
        self.send_message()


        self.SOF = "~"
        self.EOF = "^"
        self.frame_int = "I"
        self.frame_new = "N"
        self.frame_sts = "S"
        self.frame_del = "D"
        self.frame_mod = "M"
        self.frame_cfg = "C"
        self.frame_add = "0"
        self.frame_sep = ","



        #######  All set, now ready to show the main window #####
        set_qss(self)
        loading_window.hide()
        app.processEvents()
        self.show()
        loading_window.close()
        self.handle_button_clicked(0)  # this to simulate the fist left menu button press, so that the dashboard will be the default window
        ################################

    def msgButtonClick(self, i):
        print("Button clicked is:", i.text())

    def SaveData(self):
        temp_data = self.dB.save_database(self.temp_dir11, self.tempForm.GetData())
        temp_data = temp_data
        data_out = temp_data[0]
        self.dynamic_class_variable = "Ref_" + str(data_out['RefID'])
        vars(self)[self.dynamic_class_variable] = JobList(data_out)
        self.new_item = vars(self)[self.dynamic_class_variable]
        self.Main_WindowUI.job_scr.layout().addWidget(self.new_item)

    def scroll_wheel_track(self):
        pass

    def report_gen(self):
        self.Treport_gen.close()

        pass

    def search_job(self):
        item_to_search, state_ = QtWidgets.QInputDialog.getText(self, 'Find Job No.', 'Enter Job No:')
        if state_:
            print(item_to_search)
            if item_to_search != "":
                temp_job_no = 'Ref_' + item_to_search
                print(temp_job_no)
                Dynamic_Class_Variable = temp_job_no
                print(Dynamic_Class_Variable)
                item_to_find = vars(self)[Dynamic_Class_Variable]
                item_to_find.JobListUI.date_info.setText("XXXXXXXXXXXXX")
                item_to_find.JobListUI.label_9.setStyleSheet("background-color: red")
                print(item_to_find.JobListUI.oil_dec.text())
                # last_widget = self.job_list_vbox.itemAt(int(item_to_search)).widget()
                self.show()
                self.Main_WindowUI.scrollArea.ensureWidgetVisible(item_to_find)
                print(self.Main_WindowUI.Listbtn_search.pos())
                item_to_find.anim.start()



    @Slot()
    def sig_test(self):
        print("yes, signal is working")

    def ShowInputForm(self):
        print("show input form")
        self.tempForm.setWindowFlags(Qt.Window | Qt.Dialog)
        self.tempForm.setModal(True)
        self.tempForm.ResetForm()
        self.tempForm.exec_()

    def fill_list_view_window(self):
        pass
        ## Creating list view of job list

    def extract_from_job_list_dict(self, index_):
        data_out = self.job_list_dict[index_]
        return data_out

    def fill_db_oil_window(self):
        # TODO add function to update view while new tank added or tank modified / deleted
        # TODO add function to update oil level (accept level value)
        danger = "QProgressBar { border: solid grey; border-radius: 15px; color: black; } QProgressBar::chunk { " \
                 "background-color: #F50000; border-radius :15px; } "
        safe = "QProgressBar { border: solid grey; border-radius: 15px; color: black; } QProgressBar::chunk { " \
               "background-color: #00f800; border-radius :15px; } "
        self.tank_list_vbox1 = QVBoxLayout()  # The Vertical Box that contains the Horizontal Boxes of  labels and buttons
        self.tank_list_vbox1.setAlignment(Qt.AlignTop)
        self.tank_list_vbox1.setSpacing(15)
        for i in range(0, 8):
            s = str(i)
            item_to_add = TankList()
            item_to_add.TankListUI.Tank_name.setTitle("Tank - " + s)
            item_to_add.TankListUI.Oli_level_dash.setFont(QFont('Arial', 10))
            item_to_add.TankListUI.Oli_level_dash.setAlignment(Qt.AlignLeft)
            # self.btn.setupUi(self)
            if (i % 2) == 0:
                item_to_add.setStyleSheet(safe)
                item_to_add.TankListUI.Oli_level_dash.setValue(80)
            else:
                item_to_add.setStyleSheet(danger)
                item_to_add.TankListUI.Oli_level_dash.setValue(10)
            item_to_add.set_obj_name(s)
            self.tank_list_vbox1.addWidget(item_to_add)
        self.Main_WindowUI.db_oil_view_scrl.setLayout(self.tank_list_vbox1)

    def fill_db_CU_window(self):
        vbox1 = QVBoxLayout()  # The Vertical Box that contains the Horizontal Boxes of  labels and buttons
        vbox1.setAlignment(Qt.AlignTop)
        vbox1.setSpacing(15)
        for i in range(0, 6):
            s = "Control Unit - " + str(i + 1)
            item_to_add = CUList()
            # item_to_add.CUListUI.Tank_name.setTitle(s)
            item_to_add.CUListUI.CUBox.setTitle(s)
            # self.btn.setupUi(self)
            vbox1.addWidget(item_to_add)
        self.Main_WindowUI.db_CU_view_scrl.setLayout(vbox1)

    def fill_product_window(self):
        vbox1 = QVBoxLayout()  # The Vertical Box that contains the Horizontal Boxes of  labels and buttons
        vbox1.setAlignment(Qt.AlignTop)
        vbox1.setSpacing(8)
        for i in range(len(self.oil_list_dict)):
            dict_data = self.oil_list_dict[i]
            item_to_add = product_list()
            item_to_add.ProductUI.label_3.setText(dict_data["Oil_Name"])
            item_to_add.ProductUI.label_4.setText(dict_data["OilID"])
            vbox1.addWidget(item_to_add)

        self.Main_WindowUI.Product_scr.setLayout(vbox1)

    def fill_tank_window(self):
        vbox1 = QVBoxLayout()  # The Vertical Box that contains the Horizontal Boxes of  labels and buttons
        vbox1.setAlignment(Qt.AlignTop)
        vbox1.setSpacing(8)
        for i in range(0, 8):
            item_to_add = Tank_list()
            vbox1.addWidget(item_to_add)
        self.Main_WindowUI.tank_list_scr.setLayout(vbox1)

    def show_report_gen(self):
        print("show Treport_gen")
        for i in range(len(self.oil_list_dict)):
            dict_data = self.oil_list_dict[i]
            self.Treport_gen.report_config_UI.Product_selector.addItem(dict_data["Oil_Name"])
        # self.Treport_gen.setWindowFlag(Qt.FramelessWindowHint)
        for i in range(len(self.user_list_dict)):
            dict_data = self.user_list_dict[i]
            self.Treport_gen.report_config_UI.User_select.addItem(dict_data["User_name"])
        self.Treport_gen.exec_()

    def handle_button_clicked(self, number):
        print("T button No " + "LBtn_" + str(number + 1))
        if number == 5:
            self.SignalBasket.SigTest.emit()
        if number == 4:
            self.SignalBasket.SigDataReady.emit("1234")
        for x in range(6):
            rr = self.findChild(QToolButton, "LBtn_" + str(x + 1))
            if number == x:
                rr.setChecked(True)
            else:
                rr.setChecked(False)
        self.Main_WindowUI.stackedWidget.setCurrentIndex(number)

    def on_combobox_changed(self, value):
        pass
        print("combobox changed", value)
        # if value != None:

    ## EVENT ==> MOUSE DOUBLE CLICK
    ########################################################################
    def eventFilter(self, watched, event):
        if watched == self.le and event.type() == QtCore.QEvent.MouseButtonDblClick:
            print("pos: ", event.pos())

    ## ==> END ##

    ## EVENT ==> MOUSE CLICK
    ########################################################################
    def mousePressEvent(self, event):
        self.dragPos = event.globalPos()
        if event.buttons() == Qt.LeftButton:
            print('Mouse click: LEFT CLICK')
        if event.buttons() == Qt.RightButton:
            print('Mouse click: RIGHT CLICK')
        if event.buttons() == Qt.MidButton:
            print('Mouse click: MIDDLE BUTTON')

    ## ==> END ##

    ## EVENT ==> KEY PRESSED
    ########################################################################
    def keyPressEvent(self, event):
        print('Key: ' + str(event.key()) + ' | Text Press: ' + str(event.text()))
        if event.key() == 16777251:
            self.alt_key_press = True
            print('Alt key pressed')
            return
        if self.alt_key_press:
            if event.key() == 83:
                print("Alt+s")
                load_qss()
                set_qss(self)
            self.alt_key_press = False

    ## ==> END ##

    def btn_min_clicked(self):
        self.showNormal()

    def maximize_restore(self):
        print("i am here")
        self.showMaximized()
        t = Toast("ATS Elgi CLMS", "Hello", ActivationType='protocol', Duration='short', Launch='file:',
                  Scenario='default', Popup=True)
        t.add_image("icon.png", placement='logo', )
        t.add_text("Job 4567 - Completed", maxlines=2, attribution=None)
        t.show()

    def buttonClick_from_job_view(object, btn_id):
        if btn_id == "job_pause":
            if object.job_pause.isChecked():
                object.label_9.setStyleSheet("background-color: yellow")
            else:
                object.label_9.setStyleSheet("background-color: gray")
        print(object.ref_no.text())

    # File watcher functions
    def start_watchdog(self):
        if self.watchdog is None:
            self.watchdog = Watchdog(path=self.watch_path, logfunc=self.log)
            self.watchdog.start()
            self.log('Watchdog started')
        else:
            self.log('Watchdog already started')

    def stop_watchdog(self):
        if self.watchdog:
            self.watchdog.stop()
            self.watchdog = None
            self.log('Watchdog stopped')
        else:
            self.log('Watchdog is not running')

    def select_path(self):
        # file_name = QFileDialog.getExistingDirectory(self, 'select directory to watch')
        file_name_file = QFileDialog.getOpenFileName(self, "Select DMS File to watch")
        file_name_temp = os.path.split(file_name_file[0])
        self.Dms_dir_name = file_name_temp[0]
        self.Dms_file_name = file_name_temp[1]
        self.ini_file.write("DMS_file_name", self.Dms_file_name)
        self.ini_file.write("DMS_file_dir", self.Dms_dir_name)
        if self.Dms_dir_name:
            print(self.Dms_dir_name)
            self.watch_path = self.Dms_dir_name
            self.start_watchdog()

    def log(self, message):
        self.Main_WindowUI.label_2.setText(message)

    # Handle Tray_menu
    def safe_close(self):
        print("close")
        temp_var = QMessageBox.question(self, "Attention", "Are sure to close")
        if temp_var == QMessageBox.Yes:
            self.close()

    def show_window(self):
        # self.RxTimer.start()
        self.TxCount = 0
        print("show")
        self.show()

    # Serial port management
    def update_status_bar(self, message):
        self.status_bar.showMessage(message)

    def populate_ports(self):
        # Populate the available ports in the combobox
        ports = self.serial.list_serial_ports()
        for port in ports:
            self.Main_WindowUI.Port_list.addItem(port)
            #self.comboBox.addItem(port)

    def select_port(self):
        # Select the port in the combobox
        self.port_name = self.Main_WindowUI.Port_list.currentText()

    def open_port(self):
        # Open the selected port
        if not self.serial.is_open():
            if not self.serial.open_serial_port(self.port_name):
                QMessageBox.critical(self, "Error", "Could not open serial port.")
            else:
                pass

    def close_port(self):
        # Close the opened port
        if self.serial.is_open():
            self.serial.close_serial_port()
            self.open_button.setEnabled(True)
            self.close_button.setEnabled(False)

    def send_message(self):
        if self.serial.is_open():
            message = b"\x01Hello\x04"  # Change this to your desired message format
            self.serial.send_message("A1", message)
        else:
            QMessageBox.critical(self, "Error", "Port not opened")

    def handle_rx(self, data):
        # Handle the received data
        print(f"Received data: {data}")

    def handle_error(self, error_message):
        # Handle the communication error
        print(f"Communication error: {error_message}")




if __name__ == "__main__":
    app = QApplication(sys.argv)
    loading_window = LoadingScreen()
    app.processEvents()

    window = Main_Window()
    app.setWindowIcon(QtGui.QIcon('app_icon.ico'))
    window.setWindowIcon(QtGui.QIcon('app_icon.ico'))

    tray_icon = SystemTrayIcon(QtGui.QIcon("app_icon.ico"), window)
    tray_icon.exit_.triggered.connect(window.safe_close)
    tray_icon.show_.triggered.connect(window.show_window)
    tray_icon.show()
    sys.exit(app.exec_())
