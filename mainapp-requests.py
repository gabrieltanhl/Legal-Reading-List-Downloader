import sys
from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot
import parsedocs
import subprocess
import lawnetsearch
import requests_lawnetsearch
import time

class ProgressBar(QtCore.QThread):
    progress_update = QtCore.Signal(int)
    download_status = QtCore.Signal(str)

    def __init__(self, USERNAME, PASSWORD, CITATION_LIST, parent=None):
        QtCore.QThread.__init__(self)
        self.username = USERNAME
        self.password = PASSWORD
        self.citation_list = CITATION_LIST

    def run(self):
        if len(self.citation_list) > 0:
            number_of_cases = len(self.citation_list)
            progress_per_case = int(100/number_of_cases)
            progress_counter = 0

            downloader = requests_lawnetsearch.RequestLawnetBrowser(
                self.username, self.password)
            downloader.login_lawnet()
            start_time = time.time()

            for i in self.citation_list:
                progress_counter += progress_per_case
                self.progress_update.emit(progress_counter)
                signal = downloader.download_case(i)
                self.download_status.emit(signal)

            self.progress_update.emit(100)
            file_to_show = downloader.homedir
            subprocess.call(["open", "-R", file_to_show])


class DownloaderApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.citation_list = []

        self.usernamebox = QtWidgets.QLineEdit()
        self.usernamebox.setPlaceholderText('Username e.g. johnlee.2014')
        self.passwordbox = QtWidgets.QLineEdit()
        self.passwordbox.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordbox.setPlaceholderText('Password')

        self.progress = QtWidgets.QProgressBar()
        self.progress.setValue(3)
        self.progress.setStyle(QtWidgets.QStyleFactory.create('fusion'))

        import_button = QtWidgets.QPushButton('Load Reading List', self)
        import_button.clicked.connect(self.showDialog)

        self.start_button = QtWidgets.QPushButton('Start Download', self)
        self.start_button.setDisabled(True)
        self.usernamebox.textChanged.connect(self.disableButton)
        self.passwordbox.textChanged.connect(self.disableButton)
        self.start_button.clicked.connect(self.start_download)

        self.messagebox = QtWidgets.QTextEdit()
        self.messagebox.setReadOnly(True)  # make it non-editable
        self.messagebox.insertPlainText(
            'This is a tool that helps you download Singapore cases from Lawnet.\n\nInstructions:\n(1)Enter your SMU login credentials.\n\n(2)Load a reading list (only in .docx or .pdf formats).\n\n(3)Click the download button.')

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(15, 5, 15, 5)  # left, top, right, bottom
        grid.setVerticalSpacing(5)
        grid.setColumnStretch(0, 6)
        grid.setColumnStretch(1, 4)

        grid.addWidget(self.usernamebox, 0, 1)
        grid.addWidget(self.passwordbox, 1, 1)
        grid.addWidget(import_button, 2, 1)
        grid.addWidget(self.start_button, 3, 1)
        grid.addWidget(self.messagebox, 0, 0, 4, 1)
        grid.addWidget(self.progress, 4, 0, 1, 2)

        self.setLayout(grid)

        self.setGeometry(600, 400, 550, 300)
        self.setWindowTitle('Reading List Downloader (SMU version)')
        self.show()
        self.progress.close()
    """
    Connectors
    """
    @Slot()
    def disableButton(self):
        if len(self.usernamebox.text()) > 0 and len(self.passwordbox.text()) > 0:
            self.start_button.setDisabled(False)
        else:
            self.start_button.setDisabled(True)

    @Slot()
    def showDialog(self):
        fname = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open file', '/home')
        if fname[0]:
            self.citation_list = parsedocs.start_extract(fname[0])
            self.messagebox.insertPlainText('\n\n'+str(len(
                self.citation_list)) + ' cases which can be found on LawNet:\n' + '\n'.join(self.citation_list))

    def start_download(self):
        if len(self.citation_list) > 0:
            self.calc = ProgressBar(self.usernamebox.text(),
                                    self.passwordbox.text(), self.citation_list)

            self.calc.start()
            # connecting signal emitters to UI
            self.calc.progress_update.connect(self.update_progress_bar)
            self.calc.download_status.connect(self.update_download_status)
            self.start_button.setDisabled(True)
            self.progress.show()
            self.messagebox.clear()
            self.messagebox.insertPlainText('Starting download...')
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
        self.messagebox.insertPlainText(download_status)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationDisplayName('Reading List Downloader')
    app.setWindowIcon(QtGui.QIcon('icon.icns'))
    widget = DownloaderApp()
    widget.show()

    sys.exit(app.exec_())
