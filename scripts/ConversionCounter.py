"""Scans a directories immediate sub-directories for media files that have video streams that aren't in the target
encoding. Tallies up size of media files not in target encoding and groups them based on sub-directory. Good for finding
what folders/shows/seasons are taking up the most space or are most advantageous to convert."""

from __future__ import print_function

import os, sys, time, math

from tympeg import MediaObject

from PyQt5.QtGui import QTextCursor
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QLineEdit, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QApplication


class Window(QDialog):

    def __init__(self):
        QDialog.__init__(self)

        self.target_codec = 'hevc'
        self.logIsTerse = True
        self.printProgress = True
        defaultDirectory = "/media/"

        screen1 = QHBoxLayout()

        self.setLayout(screen1)
        self.inputBox = QLineEdit(defaultDirectory)
        browseContainer = QVBoxLayout()
        inputBrowseContainer = QHBoxLayout()
        inputBrowseContainer.addWidget(self.inputBox)

        self.consoleBox = QPlainTextEdit()

        analyzeButton = QPushButton("Analyze")
        analyzeButton.clicked.connect(self.analyze)
        saveLogButton = QPushButton("Save log to directory")
        saveLogButton.clicked.connect(self.saveLog)

        browseContainer.addLayout(inputBrowseContainer)

        browseContainer.addWidget(analyzeButton)
        browseContainer.addWidget(self.consoleBox)
        browseContainer.addWidget(saveLogButton)

        screen1.addLayout(browseContainer)

    def getDirectorySize(self, directoryPath):
        #Collect directory size recursively
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(directoryPath):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def saveLog(self):
        savedir = self.getDirString()
        os.chdir(savedir)

        if self.consoleBox.blockCount() <= 1:
            self.analyze()

        with open("ConversionLog" + str(time.strftime("%Y%m%d")) + ".txt", 'w', encoding="utf8") as logFile:
            logFile.write("Generated on: " + str(time.strftime("%b %d %Y, %I:%M %p")) + "\n")
            if self.logIsTerse:
                logFile.write("Log is Terse\n\n")
            logFile.write(str(self.consoleBox.toPlainText()))

    def analyze(self):

        self.consoleBox.clear()
        print("Analyzing")

        rootdir = self.getDirString()
        directoryList = []
        infoTuples = []
        fileExtensionsToAnalyze = ['.mp4', '.mkv', '.avi', '.m4v', '.wmv',
                                   '.MP4', '.MKV', '.AVI', '.M4V', '.wmv']
        invalidFilesList = []

        # Build list of immediate subdirectories
        for fileNames in os.listdir(rootdir):
            if os.path.isdir(rootdir + fileNames):
                directoryList.append(fileNames)
        directoryList = sorted(directoryList)

        # Scan subdirectories and tally info
        for dirs in directoryList:

            numberOfFiles = 0
            sizeOfFiles = 0

            numberOfInvalidFiles=0
            sizeOfInvalidFiles = 0


            sizeOfOtherFiles = 0
            if self.printProgress:
                print()
                print(dirs)

            # Build filelist for subdirectories, start tallying by type
            for fileNames in os.listdir(rootdir + dirs):
                filePath = os.path.join(rootdir + dirs, fileNames)

                if os.path.isdir(filePath):
                    sizeOfOtherFiles += self.getDirectorySize(filePath)

                else:
                    if any(extensions in fileNames for extensions in fileExtensionsToAnalyze):
                        mediaInfo = MediaObject(filePath)
                        mediaInfo.run()

                        if mediaInfo.fileIsValid:
                            codec = mediaInfo.videoCodec

                            if codec != self.target_codec:
                                numberOfFiles += 1
                                sizeOfFiles += os.path.getsize(filePath)
                        else:
                            invalidFilesList.append(filePath)
                            numberOfInvalidFiles += 1
                            sizeOfInvalidFiles += os.path.getsize(filePath)
                    else:
                        sizeOfOtherFiles += os.path.getsize(filePath)

            #  Changes bytes to Megabytes
            sizeOfFiles /= 1000000
            sizeOfInvalidFiles /= 1000000
            sizeOfOtherFiles /= 1000000

            # Don't worry about directories with nothing to convert
            if numberOfFiles > 0:
                infoTuples.append((sizeOfFiles, numberOfFiles, dirs, sizeOfInvalidFiles, numberOfInvalidFiles, sizeOfOtherFiles))

        # Sorts by file sizes
        printableList = sorted(infoTuples)
        self.printAnalysis(printableList, invalidFilesList)

    def printAnalysis(self, printableList, invalidFilesList):
        # Print the tuples, big numbers first
        for i in range(len(printableList) - 1, -1, -1):
            sys.stdout = EmittingStream(textWritten=self.normalOutputWritten)
            print(printableList[i][2])
            print()
            print("Size of h264 files: " + str(math.floor((printableList[i][0] * 100)) / 100) + " MB")
            print("Number of h264 files: " + str(printableList[i][1]))
            print()

            if self.logIsTerse == False or printableList[i][4] > 0:
                print("Size of invalid files: " + str(math.floor((printableList[i][3] * 100)) / 100) + " MB")
                print("Number of invalid files: " + str(printableList[i][4]))
                print()

            if self.logIsTerse == False or printableList[i][5] > 0:
                print("Size of other files & folders: " + str(math.floor((printableList[i][5] * 100)) / 100) + " MB")
                print()

            print()
            print()

        print("Invalid/malformed files:")
        for i in range(0, len(invalidFilesList) - 1):
            print("     " + invalidFilesList[i])

        # Scrolls back to top of list for reading
        cursor = self.consoleBox.textCursor()
        cursor.setPosition(0)
        self.consoleBox.setTextCursor(cursor)

    def getDirString(self):
        inputText = self.inputBox.text()
        if sys.platform == 'win32':
          if inputText[len(inputText) - 1] is not "\\":
            inputText += "\\"
        return inputText

    def normalOutputWritten(self, text):
        cursor = self.consoleBox.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.consoleBox.setTextCursor(cursor)
        self.consoleBox.ensureCursorVisible()

    def __del__(self):
        sys.stdout = sys.__stdout__

class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

    def flush(self):
        pass

app = QApplication(sys.argv)
dialog = Window()
dialog.show()
app.exec_()