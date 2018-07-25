import sys
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot, QSettings
import parsedocs
import subprocess
import chrome_lawnetsearch
import requests_lawnetsearch
import threading
from queue import Queue
import pathlib


class ProgressBar(QtCore.QThread):
    progress_update = QtCore.Signal(int)
    download_status = QtCore.Signal(str)
    current_case = QtCore.Signal(str)

    def __init__(self,
                 USERNAME,
                 PASSWORD,
                 CITATION_LIST,
                 lawnet_type,
                 DOWNLOAD_DIR=None,
                 parent=None):
        QtCore.QThread.__init__(self)
        self.username = USERNAME
        self.password = PASSWORD
        self.citation_list = CITATION_LIST
        self.download_dir = DOWNLOAD_DIR
        self.backend = 'REQUESTS'
        self.progress_per_case = 100 / len(self.citation_list)
        self.progress_counter = 0
        if lawnet_type == 0:
            self.login_prefix = 'smustu'
        elif lawnet_type == 1:
            self.login_prefix = 'smustf'
        else:
            self.login_prefix = 'smustu'

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
                                                                     self.login_prefix,
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
                                                                        self.login_prefix,
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
                            print(case + "{" + signal)
                            self.download_status.emit(case + "{" + signal)
                            # self.current_case.emit(case)
                            signal_lock.release()
                            self.progress_update.emit(
                                int(self.progress_counter))
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
        self.reading_list_directory = None
        self.citation_list = []
        # Temporary "app name" with no organisation until details are confirmed
        self.settings = QSettings("LegalList")
        self.initUI()
        self.load_settings()

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

    def load_settings(self):
        if (self.settings.value('login_username')):
            self.usernamebox.setText(self.settings.value('login_username'))
        if (self.settings.value('login_usertype')):
            self.lawnet_type.setCurrentIndex(self.settings.value('login_usertype'))
        if (self.settings.value('download_directory')):
            self.download_directory = self.settings.value('download_directory')
        if (self.settings.value('reading_list_directory')):
            self.reading_list_directory = self.settings.value('reading_list_directory')

    def createProgressBar(self):
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(1)
        self.progress.setStyle(QtWidgets.QStyleFactory.create('fusion'))

    def createLeftColumn(self):
        self.usernamebox = QtWidgets.QLineEdit()
        self.usernamebox.setPlaceholderText(' Username e.g. johnlee.2014')
        self.usernamebox.textChanged.connect(self.disableButton)
        self.usernamebox.textChanged.connect(self.save_username)

        self.passwordbox = QtWidgets.QLineEdit()
        self.passwordbox.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordbox.setPlaceholderText(' Password')
        self.passwordbox.textChanged.connect(self.disableButton)

        self.lawnet_type = QtWidgets.QComboBox()
        self.lawnet_type.addItems(['SMU (student)', 'SMU (faculty)'])
        self.lawnet_type.currentIndexChanged.connect(self.save_usertype)

        self.start_button = QtWidgets.QPushButton('Start Download', self)
        self.start_button.clicked.connect(self.start_download)
        self.start_button.setDisabled(True)

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

    def construct_table_row_from_list(self, row_num, case_title):

        self.tableWidget.insertRow(row_num)

        checkbox = QtWidgets.QTableWidgetItem(case_title)
        checkbox.setCheckState(QtCore.Qt.Checked)

        downloadstatus = QtWidgets.QTableWidgetItem("-")
        downloadstatus.setFlags(QtCore.Qt.ItemIsEditable)

        self.tableWidget.setItem(row_num, 0, checkbox)
        self.tableWidget.setItem(row_num, 1, downloadstatus)

    def createMenuBar(self):
        self.menu_bar = QtWidgets.QToolBar()
        toolbar_instructions = QtWidgets.QAction('Instructions', self)
        toolbar_about = QtWidgets.QAction('About', self)

        self.menu_bar.addAction(toolbar_instructions)
        self.menu_bar.addAction(toolbar_about)

        toolbar_instructions.triggered.connect(self.show_instructions)
        toolbar_about.triggered.connect(self.show_about)

    def show_popup(self, message):
        popup = QtWidgets.QMessageBox()
        popup.setText(message)
        popup.exec_()

    def save_reading_list_directory(self, reading_list_directory):
        self.settings.setValue('reading_list_directory', reading_list_directory)

    def save_download_directory(self, download_directory):
        self.settings.setValue('download_directory', download_directory)

    @Slot()
    def save_usertype(self, usertype_index):
        self.settings.setValue('login_usertype', usertype_index)

    @Slot()
    def save_username(self, text):
        self.settings.setValue('login_username', text)

    @Slot()
    def showDialog(self):
        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(0)
        default_dir = str(pathlib.Path.home()) if self.reading_list_directory is None else self.reading_list_directory
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file',
                                                      default_dir)
        # with the case names, construct the table
        if fname[0]:
            self.citation_list = parsedocs.start_extract(fname[0])
            for row_num, case_title in enumerate(self.citation_list):
                self.construct_table_row_from_list(row_num, case_title)

            reading_list_directory = str(pathlib.Path(fname[0]).parent)
            self.save_reading_list_directory(reading_list_directory)

        # after table is constructed, make it emit signals when
        # any of the cases are checked
        self.tableWidget.itemChanged.connect(self.update_citation_list)

    @Slot()
    def disableButton(self):
        if len(self.usernamebox.text()) > 0 and len(
                self.passwordbox.text()) > 0:
            self.start_button.setDisabled(False)
        else:
            self.start_button.setDisabled(True)

    @Slot()
    def select_download_directory(self):
        default_dir = str(pathlib.Path.home()) if self.download_directory is None else self.download_directory
        download_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select the download directory', default_dir)

        if download_dir:
            self.download_directory = download_dir + '/'
            self.save_download_directory(download_dir)

    def start_download(self):
        if len(self.citation_list) > 0:
            self.calc = ProgressBar(self.usernamebox.text(),
                                    self.passwordbox.text(),
                                    self.citation_list,
                                    self.lawnet_type.currentIndex(),
                                    self.download_directory)

            self.calc.start()
            # connecting signal emitters to UI
            self.calc.progress_update.connect(self.update_progress_bar)
            self.calc.download_status.connect(self.update_download_status)
            # self.calc.current_case.connect(self.update_download_status_column)

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
            self.status_label.clear()
            self.show_popup('Download complete!')

    def update_download_status(self, download_status):
        if '{' in download_status:
            current_case, download_status = download_status.split('{')
        else:
            current_case = None

        if download_status == 'FAIL':
            self.start_button.setDisabled(False)
            self.progress.close()
            self.progress.setValue(1)
            self.status_label.clear()
            self.show_popup('Login failed, please try again.')

        elif download_status == 'Login Success!':
            self.status_label.setText(download_status)
        else:
            self.status_label.setText('Downloading in progress...')

            if current_case:
                num_rows = self.tableWidget.rowCount()
                for row in range(num_rows):
                    table_item = self.tableWidget.item(row, 0)
                    case_citation = str(table_item.text())

                    if case_citation == current_case:
                        case_status = self.tableWidget.item(row, 1)
                        case_status.setText(download_status)

    def show_instructions(self):
        popup = QtWidgets.QMessageBox()
        popup.setText('Instructions')
        popup.setInformativeText(
            'This is a tool that helps you download cases from Lawnet.\n\nSteps:\n(1) Enter your login credentials.\n\n(2) Load a reading list (only in .docx or .pdf formats) and select a download directory.\n\n(3) Choose the cases you want to download\n\n(4) Click the download button.')
        popup.exec_()

    def show_about(self):
        popup = QtWidgets.QMessageBox()
        popup.setText('About')

        popup.setInformativeText(
            "This app was developed by SMU Law students: Gabriel Tan (Class of 2018), Ng Jun Xuan (Class of 2019), Wan Ding Yao (Class of 2021). The app's source code and license are available at https://github.com/gabrieltanhl/Legal-Reading-List-Downloader.\n\nCases are downloaded from SAL LawNet and are subject to their terms and conditions (https://www.lawnet.sg/lawnet/web/lawnet/terms-and-conditions).\n\n\nCopyright (C) 2018 Gabriel Tan, Ng Jun Xuan.\n\nThis program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.\n\nThis program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.\n\nYou should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.")
        popup.exec_()

    def setStyles(self):
        self.setStyleSheet("""
        QToolBar {
            border-bottom: 1px solid #808d97;
            border-top: 1px solid #808d97;
            background-color: #3a4f5e
            }
        QToolButton {
            background:#3a4f5e; border: 1px solid #585858;
            border-style: outset;
            border-radius: 4px;
            min-width: 5em;
            min-height: 1.5em;
            color: white;
            }

        QToolButton:hover {
            background: #5d7180;
            border: 1px groove #293843;}

        QToolButton:pressed {background:#475864; border: 1px groove #293843;}
         """)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
