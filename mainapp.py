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
                    self.download_status.emit('\nLogin success!')

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

                    def threader():
                        while True:
                            case = q.get()
                            signal = downloader.download_case(case)
                            self.progress_counter += self.progress_per_case
                            self.download_status.emit(signal)
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
                    self.finish_job(downloader)


class DownloaderApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.citation_list = []
        self.download_directory = None
        self.welcome_message = 'This is a tool that helps you download Singapore cases from Lawnet.\n\nInstructions:\n(1) Enter your SMU login credentials.\n\n(2) Load a reading list (only in .docx or .pdf formats).\n\n(3) Click the download button.'

        self.usernamebox = QtWidgets.QLineEdit()
        self.usernamebox.setPlaceholderText('Username e.g. johnlee.2014')
        self.passwordbox = QtWidgets.QLineEdit()
        self.passwordbox.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordbox.setPlaceholderText('Password')

        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(3)
        self.progress.setStyle(QtWidgets.QStyleFactory.create('fusion'))

        self.import_button = QtWidgets.QPushButton('Load Reading List', self)
        self.import_button.clicked.connect(self.showDialog)

        self.directory_button = QtWidgets.QPushButton(
            'Select Download Directory', self)
        self.directory_button.clicked.connect(self.select_download_directory)

        self.start_button = QtWidgets.QPushButton('Start Download', self)
        self.start_button.setDisabled(True)
        self.usernamebox.textChanged.connect(self.disableButton)
        self.passwordbox.textChanged.connect(self.disableButton)
        self.start_button.clicked.connect(self.start_download)

        self.messagebox = QtWidgets.QTextEdit()
        self.messagebox.setReadOnly(True)  # make it non-editable
        self.messagebox.insertPlainText(self.welcome_message)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(15, 5, 15, 5)  # left, top, right, bottom
        grid.setVerticalSpacing(5)
        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 4)

        grid.addWidget(self.usernamebox, 0, 1)
        grid.addWidget(self.passwordbox, 1, 1)
        grid.addWidget(self.import_button, 2, 1)
        grid.addWidget(self.directory_button, 3, 1)
        grid.addWidget(self.start_button, 4, 1)
        grid.addWidget(self.messagebox, 0, 0, 5, 1)
        grid.addWidget(self.progress, 5, 0, 1, 2)

        self.setLayout(grid)

        self.setGeometry(600, 400, 650, 390)
        self.setWindowTitle('Reading List Downloader (SMU version)')
        self.show()
        self.progress.close()

    """
    Connectors
    """

    @Slot()
    def disableButton(self):
        if len(self.usernamebox.text()) > 0 and len(
                self.passwordbox.text()) > 0:
            self.start_button.setDisabled(False)
        else:
            self.start_button.setDisabled(True)

    @Slot()
    def showDialog(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file',
                                                      '/home')
        if fname[0]:
            self.citation_list = parsedocs.start_extract(fname[0])
            self.messagebox.insertPlainText(
                '\n\n' + str(len(self.citation_list)) +
                ' cases which can be found on LawNet:\n' +
                '\n'.join(self.citation_list))

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
            self.messagebox.clear()
            self.messagebox.insertPlainText('Logging in...')
        else:
            self.messagebox.clear()
            self.messagebox.insertPlainText(
                'No cases detected. Please load a reading list.')

    def update_progress_bar(self, progress_counter):
        self.progress.setValue(progress_counter)

        if progress_counter == 100 and self.progress.value != 5:
            self.start_button.setDisabled(False)
            self.progress.close()
            self.progress.setValue(5)
            self.messagebox.insertPlainText('\nDownload complete!')

    def update_download_status(self, download_status):
        if download_status == 'FAIL':
            self.start_button.setDisabled(False)
            self.progress.close()
            self.progress.setValue(5)
            self.messagebox.clear()
            self.messagebox.insertPlainText(
                'Login failed, please try again.\n\n')
            self.messagebox.insertPlainText(self.welcome_message)
        else:
            self.messagebox.insertPlainText(download_status)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationDisplayName('Reading List Downloader')
    app.setWindowIcon(QtGui.QIcon('icon.icns'))
    widget = DownloaderApp()
    widget.show()

    sys.exit(app.exec_())
