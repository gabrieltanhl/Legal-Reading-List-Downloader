# Legal-Reading-List-Downloader (Beta)
Automatically download cases in your reading lists from LawNet using a desktop app.

For now it only supports SLR, SLR(R), SGCA, SGHC, WLR, MLR and Ch cases. To enable more case types, edit ```parsedocs.py```.

**DOCUMENTATION STILL IN PROGRESS**

## Prerequisites
1. Download the latest chromedriver from http://chromedriver.chromium.org/downloads and place it in the project directory
2. Make sure the dependencies in requirements.txt are installed and you have Python 3.6 or higher. The dependencies should be installed in a virtual environment e.g. using ```virtualenv```.
3. Install PySide2 (see https://doc.qt.io/qtforpython/gettingstarted.html)

## Running the app without compiling
1. Run ```python mainapp.py``` or ```python3 mainapp.py``` in your terminal

## Instructions for compiling to binaries (macOS)
In the project directory, run:
```
pyi-makespec mainapp.py --onefile --windowed
```
This will generate the mainapp.spec file in your project directory which provides compilation instructions to PyInstaller. Open mainapp.spec in a code editor and replace the binaries line with ```binaries=[('chromedriver','.')]```. This instructs PyInstaller to bundle the chromedriver binary when it is compiling the app.

For the app to have its own name and icon, also make sure mainapp.spec contains the following:
```
app = BUNDLE(exe,
             name='Reading List Downloader.app',
             icon='icons.icns',
             bundle_identifier=None)
```

Next, go into your virtualenv folder and find the ```pdfminer``` folder in the ```site-packages``` directory. In the ```pdfminer``` folder,
open ```pdfdocument.py``` and replace all mentions of Crypto to Cryptodome. Without performing this step, compilation will not work.

Finally, go back to the project directory and run:
```
pyinstaller mainapp.spec
```
The binaries will be located in the ```dist``` folder.
