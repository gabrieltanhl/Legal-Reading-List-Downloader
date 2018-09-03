import sys
import subprocess
import threading
import pathlib
import datetime
import requests
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot, QSettings
from distutils.version import StrictVersion
from multiprocessing.dummy import Pool as ThreadPool

import lawnetsearch
import parsedocs

VERSION = '1.0.2'


class ProgressBar(QtCore.QThread):
    progress_update = QtCore.Signal(int)
    download_status = QtCore.Signal(str)

    def __init__(self, downloader, parent=None):
        QtCore.QThread.__init__(self)
        self.downloader = downloader
        self.citation_list = downloader.citation_list
        self.progress_per_case = 100 / len(self.citation_list)
        self.progress_counter = 0

    def finish_job(self, downloader):
        if self.progress_counter < 100:
            self.progress_update.emit(100)
        file_to_show = downloader.download_dir
        subprocess.call(["open", "-R", file_to_show])

    def run(self):
        login_status = self.downloader.login_lawnet()

        if login_status == 'FAIL':
            self.download_status.emit(login_status)

        elif login_status == 'SUCCESS':
            self.download_status.emit('Login success!')
            search_lock = threading.Lock()
            signal_lock = threading.Lock()

            def run_download(case):
                signal = self.downloader.download_case(
                    case, search_lock)
                self.progress_counter += self.progress_per_case
                signal_lock.acquire()
                self.download_status.emit(case + "{" + signal)
                signal_lock.release()
                self.progress_update.emit(int(self.progress_counter))

            with ThreadPool(10) as pool:
                pool.map(run_download, self.citation_list)

            self.finish_job(self.downloader)


class App(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'LawNet Reading List Downloader (LRLD)'
        self.left = 600
        self.top = 400
        self.width = 800
        self.height = 500
        self.download_directory = None
        self.reading_list_directory = None
        self.citation_list = []
        self.stared_only = False
        self.settings = QSettings('LegalList')
        self.load_settings()
        self.initUI()
        self.downloader = lawnetsearch.LawnetBrowser()
        self.successful_downloads = 0

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

    def load_settings(self):
        if (self.settings.value('download_directory')):
            self.download_directory = self.settings.value('download_directory')
        if (self.settings.value('reading_list_directory')):
            self.reading_list_directory = self.settings.value(
                'reading_list_directory')
        if self.settings.value('stared_only'):
            self.stared_only = bool(self.settings.value('stared_only'))

    def createProgressBar(self):
        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(1)
        self.progress.setStyle(QtWidgets.QStyleFactory.create('fusion'))

    def createLeftColumn(self):
        self.usernamebox = QtWidgets.QLineEdit()
        self.usernamebox.setPlaceholderText(' Username')
        if self.settings.value('login_username'):
            self.usernamebox.setText(self.settings.value('login_username'))
        self.usernamebox.textChanged.connect(self.disableButton)
        self.usernamebox.textChanged.connect(self.save_username)

        self.passwordbox = QtWidgets.QLineEdit()
        self.passwordbox.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordbox.setPlaceholderText(' Password')
        self.passwordbox.textChanged.connect(self.disableButton)

        self.institution = QtWidgets.QComboBox()
        self.institution.addItems(['SMU', 'NUS'])

        self.lawnet_type = QtWidgets.QComboBox()
        self.lawnet_type.addItems(['Student', 'Faculty'])
        if (self.settings.value('login_usertype')):
            self.lawnet_type.setCurrentIndex(
                self.settings.value('login_usertype'))
        self.lawnet_type.currentIndexChanged.connect(self.save_usertype)

        self.stared_checkbox = QtWidgets.QCheckBox('Star-ed Cases Only')
        self.stared_checkbox.setChecked(self.stared_only)
        self.stared_checkbox.stateChanged.connect(self.update_stared_only)

        self.start_button = QtWidgets.QPushButton('Start Download', self)
        self.start_button.clicked.connect(self.start_download)
        self.start_button.setDisabled(True)

        self.import_button = QtWidgets.QPushButton('Load Reading List', self)
        self.import_button.clicked.connect(self.showDialog)

        self.directory_button = QtWidgets.QPushButton(
            'Select Download Directory', self)
        self.directory_button.clicked.connect(self.select_download_directory)

        self.left_layout = QtWidgets.QVBoxLayout()
        self.left_layout.addWidget(self.usernamebox)
        self.left_layout.addWidget(self.passwordbox)
        self.left_layout.addWidget(self.institution)
        self.left_layout.addWidget(self.lawnet_type)
        self.left_layout.addWidget(self.stared_checkbox)
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
            ['Case Citation', 'Download Status'])
        self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.tableWidget.itemChanged.connect(self.update_citation_list)

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

        update_required, dl_link = self.check_update_required()
        if update_required:
            toolbar_update = QtWidgets.QAction('New update available. Click here to download', self)
            self.menu_bar.addAction(toolbar_update)
            toolbar_update.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(dl_link)))


    def show_popup(self, header, body=None):
        popup = QtWidgets.QMessageBox()
        popup.setTextFormat(QtCore.Qt.RichText)
        popup.setText(header)
        popup.setInformativeText(body)
        popup.exec_()

    def save_reading_list_directory(self, reading_list_directory):
        self.settings.setValue('reading_list_directory',
                               reading_list_directory)

    def save_download_directory(self, download_directory):
        self.settings.setValue('download_directory', download_directory)

    @Slot()
    def update_stared_only(self):
        self.stared_only = self.stared_checkbox.isChecked()
        self.settings.setValue('stared_only', self.stared_only)

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

        default_dir = str(
            pathlib.Path.home()
        ) if self.reading_list_directory is None else self.reading_list_directory
        reading_list = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open file', default_dir)

        if (reading_list[0].split('.')[-1] == 'doc'):
            popup = QtWidgets.QMessageBox()
            popup.setText('Error: doc file not supported')
            popup.setInformativeText(
                'Please convert the doc file to docx or pdf.')
            popup.exec_()
            return

        # with the case names, construct the table
        if reading_list[0]:
            self.citation_list = parsedocs.start_extract(
                reading_list[0], self.stared_only)

            for row_num, case_title in enumerate(self.citation_list):
                self.construct_table_row_from_list(row_num, case_title)

            reading_list_directory = str(pathlib.Path(reading_list[0]).parent)
            self.save_reading_list_directory(reading_list_directory)

    @Slot()
    def update_citation_list(self, row):
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

    @Slot()
    def disableButton(self):
        if len(self.usernamebox.text()) > 0 and len(
                self.passwordbox.text()) > 0:
            self.start_button.setDisabled(False)
        else:
            self.start_button.setDisabled(True)

    @Slot()
    def select_download_directory(self):
        default_dir = str(pathlib.Path.home(
        )) if self.download_directory is None else self.download_directory
        download_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select the download directory', default_dir)

        if download_dir:
            self.download_directory = download_dir + '/'
            self.save_download_directory(download_dir)

    @Slot()
    def start_download(self):
        if self.download_num() <= 150:
            if len(self.citation_list) > 0:
                self.successful_downloads = 0
                usertype = 'smustf' if self.lawnet_type.currentIndex() == 1 else 'smustu'
                self.downloader.update_download_info(self.usernamebox.text(),
                                                     self.passwordbox.text(),
                                                     usertype,
                                                     self.citation_list,
                                                     self.download_directory)
                self.download_runner = ProgressBar(self.downloader)

                self.download_runner.start()
                # connecting signal emitters to UI
                self.download_runner.progress_update.connect(self.update_progress_bar)
                self.download_runner.download_status.connect(self.update_download_status)

                self.start_button.setDisabled(True)
                self.progress.show()
                self.status_label.clear()
                self.status_label.setText('Logging in...')
            else:
                self.status_label.clear()
                self.status_label.setText(
                    'No cases detected. Please load a reading list.')
        else:
            self.status_label.clear()
            self.status_label.setText('Daily Download Limit Exceeded')

    @Slot()
    def update_progress_bar(self, progress_counter):
        self.progress.setValue(progress_counter)

        if progress_counter == 100 and self.progress.value != 5:
            self.update_download_num(self.successful_downloads)
            self.start_button.setDisabled(False)
            self.progress.close()
            self.progress.setValue(1)
            self.status_label.clear()
            self.show_popup('Download complete!')

    @Slot()
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
                if 'downloaded' in download_status:
                    self.successful_downloads += 1

                num_rows = self.tableWidget.rowCount()
                for row in range(num_rows):
                    table_item = self.tableWidget.item(row, 0)
                    case_citation = str(table_item.text())

                    if case_citation == current_case:
                        case_status = self.tableWidget.item(row, 1)
                        case_status.setText(download_status)

    def download_num(self):
        today_date = datetime.date.today()
        if self.settings.value('latest_date'):
            settings_date = datetime.datetime.strptime(self.settings.value('latest_date'), '%d-%m-%Y').date()
        else:
            self.settings.setValue('latest_date', today_date.strftime('%d-%m-%Y'))
            self.settings.setValue('downloads', 0)
            return 0

        if settings_date != today_date:
            self.settings.setValue('latest_date', today_date.strftime('%d-%m-%Y'))
            self.settings.setValue('downloads', 0)
            return 0
        else:
            return self.settings.value('downloads')

    def update_download_num(self, downloads):
        new_downloads = int(self.settings.value('downloads')) + downloads
        self.settings.setValue('downloads', new_downloads)
        self.settings.sync()

    def show_instructions(self):
        popup = QtWidgets.QMessageBox()
        popup.setText('The LawNet Reading List Downloader (LRLD) helps you download your reading list cases from LawNet.\n\nInstructions')
        popup.setInformativeText(
            '(1) Enter your SMU login credentials\n\n(2) Load a reading list (.docx or .pdf)\n\n(3) Select a download directory\n\n(4) Check the cases you wish to download\n\n(5) Click \"Start Download\"'
        )
        popup.exec_()

    def show_about(self):
        popup = QtWidgets.QMessageBox()
        popup.setTextFormat(QtCore.Qt.RichText)
        popup.setText(f'LawNet Reading List Downloader (LRLD) {VERSION} (MacOS version)')
        popup.setInformativeText(
            "The LRLD was developed by Singapore Management University (SMU) law students Gabriel Tan (Class of 2018), Ng Jun Xuan (Class of 2019), Wan Ding Yao (Class of 2021) and is maintained by Legal Innovation and Technology (LIT), a SMU Co-curricular Activity (CCA).<br><br>The LRLD is distributed under the GNU General Public License Terms and its source code is available on <a href='https://github.com/gabrieltanhl/Legal-Reading-List-Downloader'>GitHub</a>.<br><br>The cases and materials downloaded using the LRLD program come from LawNet and are subject to their <a href='https://www.lawnet.sg/lawnet/web/lawnet/terms-and-conditions'>Terms and Conditions</a>.<br><br>Copyright (C) 2018 Gabriel Tan, Ng Jun Xuan, Wan Ding Yao."
        )
        popup.exec_()

    def check_update_required(self):
        gh_release_info = requests.get('https://api.github.com/repos/gabrieltanhl/Legal-Reading-List-Downloader/releases/latest').json()
        latest_version = gh_release_info['tag_name'][1:]
        update_required = StrictVersion(latest_version) > StrictVersion(VERSION)
        download_link = gh_release_info['assets'][0]['browser_download_url']
        return update_required, download_link

    def setStyles(self):
        self.setStyleSheet("""
        QToolBar {
            border-bottom: 1px solid #808d97;
            border-top: 1px solid #808d97;
            background-color: #4a166e;
            }
        QToolButton {
            background:#4a166e; border: 1px solid #585858;
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
