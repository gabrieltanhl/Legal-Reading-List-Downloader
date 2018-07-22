import sys
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot
import parsedocs
import subprocess
import chrome_lawnetsearch
import requests_lawnetsearch
import threading
from queue import Queue


class ProgressBar(QtCore.QThread):
    progress_update = QtCore.Signal(int)
    download_status = QtCore.Signal(str)

    def __init__(self,
                 USERNAME,
                 PASSWORD,
                 CITATION_LIST,
                 DOWNLOAD_DIR=None,
                 parent=None):
        QtCore.QThread.__init__(self)
        self.username = USERNAME
        self.password = PASSWORD
        self.citation_list = CITATION_LIST
        self.download_dir = DOWNLOAD_DIR
        self.backend = 'REQUESTS'
        self.progress_per_case = int(100 / len(self.citation_list))
        self.progress_counter = 0

    def finish_job(self, downloader):
        if self.progress_counter < 100:
            self.progress_update.emit(100)
        file_to_show = downloader.download_dir
        subprocess.call(["open", "-R", file_to_show])

    def run(self):
        if len(self.citation_list) > 0:
            if self.backend == 'CHROME':
                downloader = chrome_lawnetsearch.ChromeLawnetBrowser(self.username,
                                                                     self.password,
                                                                     self.download_dir)
                login_status = downloader.login_lawnet()
                if login_status == 'FAIL':
                    self.download_status.emit(login_status)

                elif login_status == 'SUCCESS':
                    self.download_status.emit('Login success!')

                    for i in self.citation_list:
                        self.progress_counter += self.progress_per_case
                        signal = downloader.download_case(i)
                        self.download_status.emit(signal)
                        self.progress_update.emit(self.progress_counter)

                    downloader.quit()
                    self.finish_job(downloader)

            elif self.backend == 'REQUESTS':
                downloader = requests_lawnetsearch.RequestLawnetBrowser(self.username,
                                                                        self.password,
                                                                        self.download_dir)

                login_status = downloader.login_lawnet()

                if login_status == 'FAIL':
                    self.download_status.emit(login_status)

                elif login_status == 'SUCCESS':
                    self.download_status.emit('\nLogin success!')

                    '''
                    Code below launches a thread for every case download.
                    Max # worker threads is 10. Each worker thread pulls a task
                    from the queue and executes it.
                    '''
                    search_lock = threading.Lock()
                    signal_lock = threading.Lock()

                    def threader():
                        while True:
                            case = q.get()
                            signal = downloader.download_case(
                                case, search_lock)
                            self.progress_counter += self.progress_per_case
                            signal_lock.acquire()
                            self.download_status.emit(signal)
                            signal_lock.release()
                            self.progress_update.emit(self.progress_counter)
                            q.task_done()

                    q = Queue()
                    for x in range(10):  # spawn up to 10 threads
                        t = threading.Thread(target=threader)
                        t.daemon = True
                        t.start()

                    for case in self.citation_list:  # putting cases into job pool
                        q.put(case)

                    q.join()

                    '''
                    End of multi-threading code
                    '''
                    self.finish_job(downloader)


class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'Reading List Downloader'
        self.left = 600
        self.top = 400
        self.width = 800
        self.height = 500
        self.download_directory = None
        self.citation_list = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.createMenuBar()
        self.createTable()
        self.createLeftColumn()
        self.createProgressBar()
        self.setStyles()  # styling the menubar

        # main_layout consists of button column + download table
        # ratio of left_column width to table width is 1:3
        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.addLayout(self.left_layout, 1)
        self.main_layout.addWidget(self.tableWidget, 3)

        # overall layout which consists of the main_layout and the menu_bar
        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.addWidget(self.menu_bar)
        self.overall_layout.addLayout(self.main_layout)
        self.overall_layout.addWidget(self.progress)
        self.status_label = QtWidgets.QLabel()
        self.overall_layout.addWidget(self.status_label)

        # add overall_layout to app
        self.setLayout(self.overall_layout)

        # hide progress bar on initial launch
        self.progress.close()

        # Show widget
        self.show()

    def update_citation_list(self):
        """
        updates citation list whenever a case is checked/unchecked
        this method is triggered by a signal from tableWidget.itemChanged.connect
        """
        num_rows = self.tableWidget.rowCount()

        for row in range(num_rows):
            table_item = self.tableWidget.item(row, 0)
            checkbox_state = table_item.checkState()
            case_citation = str(table_item.text())

            if checkbox_state == QtCore.Qt.CheckState.Unchecked:
                if case_citation in self.citation_list:
                    self.citation_list.remove(case_citation)

            elif checkbox_state == QtCore.Qt.CheckState.Checked:
                if case_citation not in self.citation_list:
                    self.citation_list.append(case_citation)

    def createProgressBar(self):
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(1)
        self.progress.setStyle(QtWidgets.QStyleFactory.create('fusion'))

    def createLeftColumn(self):
        self.usernamebox = QtWidgets.QLineEdit()
        self.usernamebox.setPlaceholderText(' Username e.g. johnlee.2014')

        self.passwordbox = QtWidgets.QLineEdit()
        self.passwordbox.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordbox.setPlaceholderText(' Password')

        self.lawnet_type = QtWidgets.QComboBox()
        self.lawnet_type.addItems(['SMU (student)', 'SMU (faculty)'])

        self.start_button = QtWidgets.QPushButton('Start Download', self)
        self.start_button.clicked.connect(self.start_download)

        self.import_button = QtWidgets.QPushButton(
            'Load Reading List', self)
        self.import_button.clicked.connect(self.showDialog)

        self.directory_button = QtWidgets.QPushButton(
            'Select Download Directory', self)
        self.directory_button.clicked.connect(self.select_download_directory)

        self.left_layout = QtWidgets.QVBoxLayout()
        self.left_layout.addWidget(self.usernamebox)
        self.left_layout.addWidget(self.passwordbox)
        self.left_layout.addWidget(self.lawnet_type)
        self.left_layout.addStretch()
        self.left_layout.addWidget(self.import_button)
        self.left_layout.addWidget(self.directory_button)
        self.left_layout.addWidget(self.start_button)

    def createTable(self):
        # Create table
        self.tableWidget = QtWidgets.QTableWidget()

        # create columns and set sizing options
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(
            ['Case Title', 'Download Status'])
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)

    def construct_row_from_list(self, row_num, case_title):
        self.tableWidget.insertRow(row_num)

        checkbox = QtWidgets.QTableWidgetItem(case_title)
        checkbox.setCheckState(QtCore.Qt.Checked)

        self.tableWidget.setItem(row_num, 0, checkbox)
        self.tableWidget.setItem(row_num, 1, QtWidgets.QTableWidgetItem("-"))

    def createMenuBar(self):
        self.menu_bar = QtWidgets.QMenuBar(self)
        self.menu_bar.addMenu('Instructions')
        self.menu_bar.addMenu('About')
        self.menu_bar.setNativeMenuBar(False)

    def setStyles(self):
        self.setStyleSheet("""
        QMenuBar {
            background-color: rgb(49,49,49);
            color: rgb(255,255,255);
            border: 1px solid #000;
        }

        QMenuBar::item {
            background-color: rgb(49,49,49);
            color: rgb(255,255,255);
        }

        QMenuBar::item::selected {
            background-color: rgb(30,30,30);
        }

        QMenu {
            background-color: rgb(49,49,49);
            color: rgb(255,255,255);
            border: 1px solid #000;
        }

        QMenu::item::selected {
            background-color: rgb(30,30,30);
        }
    """)

    @Slot()
    def showDialog(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file',
                                                      '/home')
        # with the case names, construct the table
        if fname[0]:
            self.citation_list = parsedocs.start_extract(fname[0])
            for row_num, case_title in enumerate(self.citation_list):
                self.construct_row_from_list(row_num, case_title)

        # after table is constructed, make it emit signals when
        # any of the cases are checked
        self.tableWidget.itemChanged.connect(self.update_citation_list)

    @Slot()
    def on_click(self):
        print("\n")
        for currentQTableWidgetItem in self.tableWidget.selectedItems():
            print(currentQTableWidgetItem.row(),
                  currentQTableWidgetItem.column(), currentQTableWidgetItem.text())

    @Slot()
    def disableButton(self):
        if len(self.usernamebox.text()) > 0 and len(
                self.passwordbox.text()) > 0:
            self.start_button.setDisabled(False)
        else:
            self.start_button.setDisabled(True)

    @Slot()
    def select_download_directory(self):
        dialogue = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select the download directory')

        if dialogue:
            self.download_directory = dialogue + '/'

    def start_download(self):
        if len(self.citation_list) > 0:
            self.calc = ProgressBar(self.usernamebox.text(),
                                    self.passwordbox.text(),
                                    self.citation_list,
                                    self.download_directory)

            self.calc.start()
            # connecting signal emitters to UI
            self.calc.progress_update.connect(self.update_progress_bar)
            self.calc.download_status.connect(self.update_download_status)
            self.start_button.setDisabled(True)
            self.progress.show()
            self.status_label.clear()
            self.status_label.setText('Logging in...')
        else:
            self.status_label.clear()
            self.status_label.setText(
                'No cases detected. Please load a reading list.')

    def update_progress_bar(self, progress_counter):
        self.progress.setValue(progress_counter)

        if progress_counter == 100 and self.progress.value != 5:
            self.start_button.setDisabled(False)
            self.progress.close()
            self.progress.setValue(1)
            self.status_label.setText('Download complete!')

    def update_download_status(self, download_status):
        if download_status == 'FAIL':
            self.start_button.setDisabled(False)
            self.progress.close()
            self.progress.setValue(1)
            self.status_label.setText(
                'Login failed, please try again.')
        else:
            self.status_label.setText(download_status)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
