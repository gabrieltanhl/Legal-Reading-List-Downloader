# LawNet Reading List Downloader - LRLD
A desktop app that automatically downloads cases in your reading lists from LawNet. **The latest release can be found [here](https://github.com/gabrieltanhl/Legal-Reading-List-Downloader/releases).**

The Singapore Academy of Law has approved the use of the LRLD by students and faculty members of Singapore Management University (SMU). 

Only SMU LawNet accounts and MacOS are supported (as of now).

Start screen             |  Downloading cases
:-------------------------:|:-------------------------:
![](https://i.imgur.com/f06VQKb.png "Start page of app")  |  ![](https://i.imgur.com/fDYfId7.png "Downloading cases")

Built by the law students from SMU: [Gabriel Tan](https://github.com/gabrieltanhl), [Ng Jun Xuan](https://github.com/njunxuan), [Wan Ding Yao](https://github.com/DingYao)

# Development
## Prerequisites for compiling
1. Make sure the dependencies in requirements.txt are installed and you have Python 3.6 or higher. The dependencies should be installed in a virtual environment e.g. using ```virtualenv```.
2. Install PySide2==5.9 with ```python -m pip install --index-url=http://download.qt.io/snapshots/ci/pyside/5.9/latest pyside2 --trusted-host download.qt.io```

## Running the app without compiling
Run ```mainapp.py``` in your terminal

## Compilation instructions
In the project directory, run:
```
pyi-makespec mainapp.py --onefile --windowed
```
This will generate a ```mainapp.spec``` file in your project directory which provides compilation instructions to PyInstaller.

For the app to have its own name and icon, also make sure ```mainapp.spec``` contains the following:
```
app = BUNDLE(exe,
             name='LawNet Reading List Downloader (LRLD).app',
             icon='icon.icns',
             bundle_identifier=None,
             info_plist={'NSPrincipalClass':'NSApplication',
                         'NSHighResolutionCapable': 'True'}
            )
```

Next, go into your virtualenv folder and find the ```site-packages``` directory. Make the following 2 changes within ```site-packages```:
1) In the ```pdfminer``` folder, open ```pdfdocument.py``` and replace all mentions of Crypto to Cryptodome.
2) In the ```xhtml2pdf``` folder, open ```tags.py``` and replace ```from reportlab.graphics.barcode import createBarcodeDrawing``` with
```
try:
    from reportlab.graphics.barcode import createBarcodeDrawing
except:
    pass
```
Finally, go back to the project directory and run:
```
pyinstaller mainapp.spec
```
The binaries will be located in the ```dist``` folder.

## Testing
Testing is done using the PyTest framework. VCR.py is used to save the http responses, to minimise hits to the LawNet servers. On the first testing run, a folder ```cassettes``` will be created inside the ```tests``` folder. Delete this folder if you want the tests to make real requests to the LawNet servers.
1. Make sure to install the testing dependencies as provided inside requirements.txt.
2. Create a file ```credentials.py``` inside the ```tests``` folder. This file should contain 2 dicts called ```login``` and ```false_login```. Each dict should contain 2 keys ```username``` and ```password```. ```login``` dict should contain correct credentials, while ```false_login``` should contain fake credentials.
3. Run the tests from the project root with ```python -m pytest tests```.

#### SHA hashes
The tests use SHA 256 to compare the downloaded files. Helper methods are provided inside ```tests/sha_helpers.py``` to generate and write the sha to a file.
