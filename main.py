# imports
from builtins import Exception

import h5py
import numpy as np
import pandas as pd
from pathlib import Path

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtWebEngineWidgets as qtwew

import pyqtgraph as pg
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from PyQt5 import uic

import sys

import lib.cfel_filetools as fileTools
# import lib.cfel_geometry as geomTools
import lib.cfel_imgtools as imgTools

from lib.geometry_parser.GeometryFileParser import *


class DisplayImage(qtw.QWidget):
    panelSelected = qtc.pyqtSignal(dict)
    def __init__(self, fileName, geometry):
        super(DisplayImage, self).__init__()

        # setting the size and location of the window
        self.outgoingDict = None
        self.setGeometry(10, 100, 600, 600)

        # assigning the file name and the geometry
        self.fileName = fileName
        self.geometryName = geometry

        # class variables
        self.eventNumber = None
        self.imageToDraw = None
        self.cxi = None
        self.size = None
        self.panelLocFromGeom = {}
        self.panelFsSs = {}
        self.panelsXYEdges = {}
        self.outgoingDict = {}

        # main window for display the data
        self.mainWidget = pg.ImageView()

        # adding a checkBoxes
        self.foundPeaksChekckBox = qtw.QCheckBox('Found Peaks')

        # connecting the checkBoxes to a method
        self.foundPeaksChekckBox.stateChanged.connect(self.drawImage)

        # adding a layout and add checkbox and the mainwindow to the layout
        self.layout = qtw.QVBoxLayout()
        self.layout.addWidget(self.mainWidget)
        self.layout.addWidget(self.foundPeaksChekckBox)

        # reading the geometry file
        try:
            self.parser = GeometryFileParser(self.geometryName)
            self.geometry = self.parser.pixel_map_for_cxiview()

            for panelName in self.parser.dictionary['panels'].keys():
                self.panelFsSs[panelName] = [self.parser.dictionary['panels'][panelName]['min_fs'],
                                             self.parser.dictionary['panels'][panelName]['max_fs'],
                                             self.parser.dictionary['panels'][panelName]['min_ss'],
                                             self.parser.dictionary['panels'][panelName]['max_ss']]

            for panelName in self.panelFsSs.keys():
                # bottom left conner
                x1 = (self.panelFsSs[panelName][0], self.panelFsSs[panelName][2])
                # bottom right conner
                x2 = (self.panelFsSs[panelName][0], self.panelFsSs[panelName][3])
                # top right conner
                x3 = (self.panelFsSs[panelName][1], self.panelFsSs[panelName][3])
                # top left conner
                x4 = (self.panelFsSs[panelName][1], self.panelFsSs[panelName][2])

                self.panelLocFromGeom[panelName] = [x1, x2, x3, x4]

        except FileNotFoundError:
            qtw.QMessageBox.critical(self, 'Fail', self.geometryName, " was not found -reading geometery __init__")

        # adding an overlapping canvas to the found peaks
        self.foundPeaksCanvas = pg.ScatterPlotItem()
        self.mainWidget.getView().addItem(self.foundPeaksCanvas)

        # adding a canvas for displaying panel edges
        self.panelEdgesCanvas = pg.PlotDataItem()
        self.mainWidget.getView().addItem(self.panelEdgesCanvas)

        # connecting a mouse clicked event to a select panel method
        self.mainWidget.getView().scene().sigMouseClicked.connect(self.selectPanel)

        self.setLayout(self.layout)

    def drawImage(self, eventNumber):
        '''
         reading and displaying data
        :param eventNumber: event number to be displayed
        :return: pixel map from the cxi file
        '''

        try:
            # applying the geometry and displaying the image
            self.eventNumber = eventNumber
            # reading the given eventNumber from the cxi file
            self.cxi = fileTools.read_cxi(self.fileName, frameID=self.eventNumber, data=True, slab_size=True,
                                          peaks=True)
            self.size = self.cxi['stack_shape'][0]
            # reading data
            imgData = self.cxi['data']
            # converting data into a pixel map to display and applying geometry
            self.imageToDraw = imgTools.pixel_remap(imgData, self.geometry['x'], self.geometry['y'])
            # showing the pixel map in the main window
            self.mainWidget.setImage(self.imageToDraw)
            # print(self.imageToDraw.shape)
            # print(self.cxi['stack_shape'])
            # setting a window title with the eventNumber and the total number of event in the file
            self.setWindowTitle("Showing %i of %i " % (self.eventNumber, self.size - 1))

            if self.eventNumber == 0:
                self.drawInitialPanel()

            self.drawPeaks()

        except IndexError:
            # print(e)
            qtw.QMessageBox.critical(self, 'Fail', "Couldn't read the cxi file, Please Try again! -drawImage")

    def drawPeaks(self):
        '''

        :return: draw circles around the found peaks extracted from the cxi file
        '''
        try:
            if self.foundPeaksChekckBox.isChecked():
                peaks_x = []
                peaks_y = []

                # temp = fileTools.read_event()
                n_peaks = self.cxi['n_peaks']
                x_data = self.cxi['peakXPosRaw']
                y_data = self.cxi['peakYPosRaw']

                for i in range(0, n_peaks):
                    peak_fs = x_data[i]
                    peak_ss = y_data[i]

                    peak_in_slab = int(round(peak_ss)) * self.cxi['stack_shape'][2] + int(round(peak_fs))
                    peaks_x.append(self.geometry['x'][peak_in_slab] + self.imageToDraw.shape[0] / 2)
                    peaks_y.append(self.geometry['y'][peak_in_slab] + self.imageToDraw.shape[1] / 2)

                ring_pen = pg.mkPen('b', width=2)
                self.foundPeaksCanvas.setData(peaks_x, peaks_y, symbol='o', size=10, pen=ring_pen, brush=(0, 0, 0, 0),
                                              pxMode=False)
            else:
                self.foundPeaksCanvas.clear()
        except Exception as e:
            print(e, '-drawPeaks')

    def drawInitialPanel(self):

        try:
            for panelName in self.panelLocFromGeom.keys():
                x_edges = []
                y_edges = []

                for i in range(4):
                    edge_fs = self.panelLocFromGeom[panelName][i][0]
                    edge_ss = self.panelLocFromGeom[panelName][i][1]
                    peak_in_slab = int(round(edge_ss)) * self.cxi['stack_shape'][2] + int(round(edge_fs))
                    x_edges.append(self.geometry['x'][peak_in_slab] + self.imageToDraw.shape[0] / 2)
                    y_edges.append(self.geometry['y'][peak_in_slab] + self.imageToDraw.shape[1] / 2)
                x_edges.append(x_edges[0])
                y_edges.append(y_edges[0])

                self.panelsXYEdges[panelName] = [x_edges, y_edges]

            pen = pg.mkPen('r', width=3)
            # plotting a square along the edges of the selected panel
            self.panelEdgesCanvas.setData(self.panelsXYEdges['p6a0'][0],
                                          self.panelsXYEdges['p6a0'][1], pen=pen)
            self.outgoingDict = {'panel_name': 'p6a0',
                                 'min_fs': self.panelFsSs['p6a0'][0], 'max_fs': self.panelFsSs['p6a0'][1],
                                 'min_ss': self.panelFsSs['p6a0'][2], 'max_ss': self.panelFsSs['p6a0'][3]}

            self.panelSelected.emit(self.outgoingDict)
        except Exception as e:
            print(e, '-darawInitialPanel')

    def selectPanel(self, event):
        '''
        Draw a boarder around the selected ASIIC
        :param event: A mouse clicked event
        :return: Draw a Red boarder around the selected ASIIC
        '''

        try:
            # panel locations corrected for displayImage
            pos = event.scenePos()
            if self.mainWidget.getView().sceneBoundingRect().contains(pos):
                mouse_point = self.mainWidget.getView().mapSceneToView(pos)
                x_mouse = int(mouse_point.x())
                y_mouse = int(mouse_point.y())

                for panelName in self.panelsXYEdges.keys():
                    if x_mouse in range(int(min(self.panelsXYEdges[panelName][0])),
                                        int(max(self.panelsXYEdges[panelName][0]))) \
                            and y_mouse in range(int(min(self.panelsXYEdges[panelName][1])),
                                                 int(max(self.panelsXYEdges[panelName][1]))):
                        pen = pg.mkPen('r', width=3)
                        # plotting a square along the edges of the selected panel
                        self.panelEdgesCanvas.setData(self.panelsXYEdges[panelName][0],
                                                      self.panelsXYEdges[panelName][1], pen=pen)
                        # print(self.panelFsSs[panelName])

                        self.outgoingDict = {'panel_name': panelName,
                                             'min_fs': self.panelFsSs[panelName][0],
                                             'max_fs': self.panelFsSs[panelName][1],
                                             'min_ss': self.panelFsSs[panelName][2],
                                             'max_ss': self.panelFsSs[panelName][3]}
                        self.panelSelected.emit(self.outgoingDict)
                        # break
        except Exception as e:
            print(e, "-SelectPanel")


class ML(qtw.QWidget):

    def __init__(self, inDict):

        super(ML, self).__init__()

        self.model = None
        self.panelName = inDict['panel_name']
        self.min_fs = inDict['min_fs']
        self.max_fs = inDict['max_fs']
        self.min_ss = inDict['min_ss']
        self.max_ss = inDict['max_ss']

        uic.loadUi("machineLearningGUI.ui", self)

        self.setWindowTitle('Machine Learning')

        self.browseButton.clicked.connect(self.browseFiles)
        self.checkBox.stateChanged.connect(self.checkBoxClicked)
        self.trainButton.clicked.connect(self.train)
        self.testButton.clicked.connect(self.test)
        self.comboBox.activated.connect(self.rest)

    def browseFiles(self):
        """
            This method gets triggered when the browse button is Clicked in the GUI
        function: The function is to take in a text field where the value needs to be set and called in a dialog box with
        file struture view starting at the 'root' and lets the user select the file they want and set the file path to
        the test field.
        """

        fname = qtw.QFileDialog.getExistingDirectory(self, caption='Select Folder', directory=' ')

        self.parentDirectory.setText(fname)

    # model training using multiple runs needs to be implemented
    def checkBoxClicked(self):
        if self.checkBox.isChecked():
            self.startRun.setEnabled(True)
            self.endRun.setEnabled(True)
        else:
            self.startRun.setEnabled(False)
            self.endRun.setEnabled(False)

    def readPanelDetails(self, inDict):
        """
                :param inDict: Dictionery with ASIIC/panel information coming from the signal once the user clicked on a panel
                :return: Assigns panel deitail
                """
        self.panelName = inDict['panel_name']
        self.min_fs = inDict['min_fs']
        self.max_fs = inDict['max_fs']
        self.min_ss = inDict['min_ss']
        self.max_ss = inDict['max_ss']

    def modelSelection(self):

        modelSelected = self.comboBox.currentText()
        if modelSelected == 'LogisticRegression':
            from sklearn.linear_model import LogisticRegression
            self.model = LogisticRegression()
        elif modelSelected == 'KNeighborsClassifier':
            from sklearn.neighbors import KNeighborsClassifier
            self.model = KNeighborsClassifier(n_neighbors=1)
        elif modelSelected == 'DecisionTreeClassifier':
            from sklearn.tree import DecisionTreeClassifier
            self.model = DecisionTreeClassifier()
        elif modelSelected == 'RandomForestClassifier':
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(n_estimators=200)
        else:
            qtw.QMessageBox.critical(self, 'Caution', 'Please Select a model')

    # def dataPrep(self):
    #
    #     from sklearn.model_selection import train_test_split
    #
    #     try:
    #         if self.checkBox.isChecked():
    #             pass
    #         else:
    #             folder = self.parentDirectory.text()
    #     except Exception as e:
    #         qtw.QMessageBox.critical(self, 'Fail', e)
    #
    #     files = Path(folder).glob('badEvents-advanceSort-*-ML.list')
    #     dataFrame_bad = pd.DataFrame(columns=['FileName', 'EventNumber', 'InflectionPoint1', 'InflectionPoint2'])
    #
    #     for file in files:
    #
    #         try:
    #             temp_df = pd.read_csv(str(file), delimiter=" ")
    #             temp_df.columns = ['FileName', 'EventNumber', 'InflectionPoint1', 'InflectionPoint2']
    #             dataFrame_bad = pd.concat([dataFrame_bad, temp_df])
    #         except Exception as e:
    #             qtw.QMessageBox.information(self, 'information', e)
    #             continue
    #     dataFrame_bad['Flag'] = 0
    #
    #     files = Path(folder).glob('goodEvents-advanceSort-*-ML.list')
    #     dataFrame_good = pd.DataFrame(columns=['FileName', 'EventNumber', 'InflectionPoint1', 'InflectionPoint2'])
    #
    #     for file in files:
    #         try:
    #             temp_df = pd.read_csv(str(file), delimiter=" ")
    #             temp_df.columns = ['FileName', 'EventNumber', 'InflectionPoint1', 'InflectionPoint2']
    #             dataFrame_good = pd.concat([dataFrame_good, temp_df])
    #         except Exception as e:
    #             qtw.QMessageBox.information(self, 'information', e)
    #             continue
    #     dataFrame_good['Flag'] = 1
    #
    #     finalData = pd.concat([dataFrame_bad, dataFrame_good])
    #
    #     X = finalData[['InflectionPoint1', 'InflectionPoint2']]
    #     y = finalData['Flag']
    #
    #     self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(X, y, test_size=0.3)

    def dataPrep2(self):

        from sklearn.model_selection import train_test_split

        try:
            if self.checkBox.isChecked():
                pass
            else:
                folder = self.parentDirectory.text()
        except Exception as e:
            qtw.QMessageBox.critical(self, 'Fail', e)

        # Bad Events
        files = Path(folder).glob('badEvents-advanceSort-*.list')
        dataFrame_bad = pd.DataFrame(columns=['FileName', 'EventNumber', 'Data'])

        for file in files:

            try:
                temp_df = pd.read_csv(str(file), delimiter=" ")
                temp_df.columns = ['FileName', 'EventNumber']

                # reading the panel data from the file
                temp_df['EventNumber'] = temp_df['EventNumber'].apply(lambda x: x.split('/')[2])
                fileName = temp_df['FileName'].iloc[0]

                with h5py.File(fileName, "r") as f:
                    data = f['entry_1']['data_1']['data'][()]

                tempList = []
                for i in list(temp_df['EventNumber']):
                    frame = data[int(i)][self.min_ss:self.max_ss, self.min_fs+5:self.max_fs-5]
                    tempList.append(frame.flatten())

                temp_df['Data'] = tempList

                dataFrame_bad = pd.concat([dataFrame_bad, temp_df])
            except Exception as e:
                print(e, 'bad file: %s,  reading error -dataprep2()' % file)
                # qtw.QMessageBox.information(self, 'information', e)
                continue
        dataFrame_bad['Flag'] = 0

        # Good Events
        files = Path(folder).glob('goodEvents-advanceSort-*.list')
        dataFrame_good = pd.DataFrame(columns=['FileName', 'EventNumber', 'Data'])

        for file in files:
            try:
                temp_df = pd.read_csv(str(file), delimiter=" ")
                temp_df.columns = ['FileName', 'EventNumber']

                # reading the panel data from the file
                temp_df['EventNumber'] = temp_df['EventNumber'].apply(lambda x: x.split('/')[2])
                fileName = temp_df['FileName'].iloc[0]

                with h5py.File(fileName, "r") as f:
                    data = f['entry_1']['data_1']['data'][()]

                tempList = list()
                for i in list(temp_df['EventNumber']):
                    frame = data[int(i)][self.min_ss:self.max_ss, self.min_fs + 5:self.max_fs - 5]
                    tempList.append(frame.flatten())

                temp_df['Data'] = tempList

                dataFrame_good = pd.concat([dataFrame_good, temp_df])
            except Exception as e:
                print(e, 'good file: %s, reading error -dataprep2()' % file)
                # qtw.QMessageBox.information(self, 'information', e)
                continue
        dataFrame_good['Flag'] = 1

        finalData = pd.concat([dataFrame_bad, dataFrame_good])
        finalData = pd.concat([finalData['FileName'], finalData['EventNumber'], finalData.pop('Data').apply(pd.Series),
                               finalData['Flag']], axis=1)

        # print(finalData.columns)
        X = finalData.drop(['FileName','EventNumber','Flag'], axis=1)
        y = finalData['Flag']

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(X, y, test_size=0.25)

    def train(self):
        qtw.QMessageBox.information(self, 'info', "Training a modle from the panel selected %s" % self.panelName)
        self.modelSelection()
        self.dataPrep2()
        self.model.fit(self.X_train, self.y_train)
        self.testButton.setEnabled(True)

    def test(self):
        from sklearn.metrics import classification_report, confusion_matrix
        self.predictions = self.model.predict(self.X_test)
        self.confussionMetrix.setEnabled(True)
        self.classificationReport.setEnabled(True)
        self.confussionMetrix.setText(str(confusion_matrix(self.y_test, self.predictions)))
        self.classificationReport.setText(classification_report(self.y_test, self.predictions))

    def rest(self):
        self.confussionMetrix.clear()
        self.classificationReport.clear()
        self.testButton.setEnabled(False)


class AdvanceSorting(qtw.QWidget):
    readyToSaveGood = qtc.pyqtSignal(dict, str)
    readyToSaveBad = qtc.pyqtSignal(dict, str)

    def __init__(self, fileName, oft, inDict):

        super(AdvanceSorting, self).__init__()

        self.setWindowTitle('Advance Sorting')

        uic.loadUi("AdvanceSortGUI.ui", self)

        # for plotting with matplotlib
        # self.layout = qtw.QHBoxLayout()
        # self.figure = plt.figure()
        # self.canvas = FigureCanvasQTAgg(self.figure)
        # self.layout.addWidget(self.canvas)
        # self.graphSpace.setLayout(self.layout)

        # for plotting with plotly
        self.layout = qtw.QHBoxLayout()
        self.browser = qtwew.QWebEngineView()
        self.layout.addWidget(self.browser)
        self.graphSpace.setLayout(self.layout)

        self.file_name = fileName
        self.orderOfFit = oft
        self.panelName = inDict['panel_name']
        self.min_fs = inDict['min_fs']
        self.max_fs = inDict['max_fs']
        self.min_ss = inDict['min_ss']
        self.max_ss = inDict['max_ss']

        # self.plotInflectionPointsButton.clicked.connect(self.plotInflectionPoints)
        self.plotInflectionPoints()
        self.sortButton.clicked.connect(self.advanceSort)

    def readPanelDetails(self, inDict):
        """
                :param inDict: Dictionery with ASIIC/panel information coming from the signal once the user clicked on a panel
                :return: Assigns panel deitail
                """
        self.panelName = inDict['panel_name']
        self.min_fs = inDict['min_fs']
        self.max_fs = inDict['max_fs']
        self.min_ss = inDict['min_ss']
        self.max_ss = inDict['max_ss']

        self.plotInflectionPoints()

    def plotInflectionPoints(self):

        self.x1_list = []
        self.x2_list = []

        try:
            with h5py.File(self.file_name, "r") as f:
                self.data = f['entry_1']['data_1']['data'][()]

            for i in range(len(self.data)):
                frame = self.data[i]

                avgIntensities = []
                for j in range(self.min_fs+5, self.max_fs-5):
                    avgIntensities.append(np.average(frame[self.min_ss:self.max_ss, j]))

                fit = np.polyfit(np.arange(self.min_fs+5, self.max_fs-5), avgIntensities, deg=int(self.orderOfFit))
                # calculating the inflection points (second derivative of the forth order polynomial)
                # print(fit)
                try:
                    x1 = round((-6 * fit[1] + np.sqrt(36 * fit[1] * fit[1] - 96 * fit[0] * fit[2])) / (24 * fit[0]), 2)
                    x2 = round((-6 * fit[1] - np.sqrt(36 * fit[1] * fit[1] - 96 * fit[0] * fit[2])) / (24 * fit[0]), 2)
                    self.x1_list.append(x1)
                    self.x2_list.append(x2)
                except IndexError:
                    qtw.QMessageBox.information(self, 'Error', 'Please try a different order polynomial')
                except ValueError:
                    qtw.QMessageBox.information(self, 'Skip', 'Calculation Error! \n \n Skipping the frame %i' % i)
                    continue

        except Exception as e:
            print(e, '-plotInflectionPoint')

        ## with ploty
        df = pd.DataFrame()
        df['Inflection_poit1'] = self.x1_list
        df['Inflection_poit2'] = self.x2_list
        fig = px.histogram(df, nbins=200, opacity=0.5)
        self.browser.setHtml(fig.to_html(include_plotlyjs='cdn'))

        # print(df['Inflection_poit1'])
        print(df['Inflection_poit1'].max())
        print(df['Inflection_poit1'].idxmax())
        # print(df['Inflection_poit2'])
        print(df['Inflection_poit2'].max())
        print(df['Inflection_poit2'].idxmax())


        ## with seaborn
        # self.figure.clear()
        # sns.histplot(self.x1_list, label='x1', kde=True, alpha=0.5)
        # sns.histplot(self.x2_list, label='x2', kde=True, alpha=0.5)
        # plt.legend()
        # #
        # # # plt.hist(self.x1_list,bins=30,label='x1', alpha=0.5)
        # # # plt.hist(self.x2_list,bins=30,label='x2', alpha=0.5)
        #
        # self.canvas.draw()

        # Enabling button and check box after plotting
        self.inflectionPoint1.setEnabled(True)
        self.inflectionPoint1.setText(str(np.round_(np.median(df['Inflection_poit1']), 2)))
        self.inflectionPoint2.setEnabled(True)
        self.inflectionPoint2.setText(str(np.round_(np.median(df['Inflection_poit2']), 2)))
        self.sortButton.setEnabled(True)


    def advanceSort(self):

        tag = str(self.file_name).split('/')[-1].split('.')[0]

        self.goodEvents = {}
        self.badEvents = {}

        # goodList to store all the events with expected pixel intensities for the file
        goodList = []
        # badList to store all the events with detector artifacts for the file
        badList = []

        try:

            for (i, x1, x2) in zip(range(len(self.data)), self.x1_list, self.x2_list):

                if (float(self.inflectionPoint1.text()) - 15) <= x1 <= (float(self.inflectionPoint1.text()) + 15)  \
                        and \
                        (float(self.inflectionPoint2.text()) - 15) <= x2 <= (float(self.inflectionPoint2.text()) + 15):

                    goodList.append(i)
                else:
                    badList.append(i)

            self.goodEvents[str(self.file_name)] = goodList
            self.badEvents[str(self.file_name)] = badList

            self.readyToSaveGood.emit(self.goodEvents, 'goodEvents-advanceSort-%s.list' % tag)
            self.readyToSaveBad.emit(self.badEvents, 'badEvents-advanceSort-%s.list' % tag)

            qtw.QMessageBox.information(self, 'Success', "Done Sorting")

        except ValueError:
            qtw.QMessageBox.critical(self, 'Fail', ValueError)
        except AttributeError:
            qtw.QMessageBox.critical(self, 'Fail', AttributeError)


class MainWindow(qtw.QMainWindow):
    clickedNext = qtc.pyqtSignal(int)
    clickedPrevious = qtc.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        uic.loadUi("mainWindow.ui", self)
        self.setGeometry(700, 100, 800, 700)
        # connecting elements to functions
        self.browseButton.clicked.connect(self.browseFiles)
        self.browseButton_2.clicked.connect(self.browseGeom)
        self.viewFileButton.clicked.connect(self.viewFiles)

        # initializing the popup windows
        self.imageViewer = None
        self.sortGUI = None
        self.mlDialog = None

        self.fileSize = None
        self.totalEvents = None
        self.buttonClicked = None

        # button and input line for calling plotCurves() method to plot vertically average intensity profile for the
        # panel
        self.plotPixelIntensityButton.clicked.connect(self.plotCurve)
        # button for call the fit_curve() method to fit a 4th order polynomial for
        # the vertically average intensity profile
        self.fitPolynormialButton.clicked.connect(self.plotFit)
        # button for calling plot_max_pixels() method to plot the pixel with the highest intensity for all
        # the frames of the
        self.plotPeakPixelButton.clicked.connect(lambda: self.plotMaxPixels(self.fileField.text()))

        self.sortButton.clicked.connect(lambda: self.sortFrames(self.fileField.text()))
        self.advanceSortButton.clicked.connect(self.advanceSortFrames)
        self.MLButton.clicked.connect(self.machineLearning)

        self.orderOfFit.editingFinished.connect(self.plotFit)
        self.eventNumber.editingFinished.connect(self.curveToPlot)
        self.eventNumber.editingFinished.connect(self.selectDisplay)

        # incrementing through eventnumbers
        self.nextButton.clicked.connect(lambda: self.nextEvent(self.eventNumber.text()))
        self.previousButton.clicked.connect(lambda: self.previousEvent(self.eventNumber.text()))

        # graphing
        self.graphWidget = pg.PlotWidget()
        self.layout = qtw.QHBoxLayout()
        self.layout.addWidget(self.graphWidget)
        self.graphingSpace.setLayout(self.layout)

        self.setWindowTitle("Detector Analyser")
        self.show()

    def browseFiles(self):
        """
            This method gets triggered when the browse button is Clicked in the GUI
        function: The function is to take in a text field where the value needs to be set and called in a dialog box with
        file struture view starting at the 'root' and lets the user select the file they want and set the file path to
        the test field.
        """
        dialog_box = qtw.QDialog()
        fname = qtw.QFileDialog.getOpenFileNames(dialog_box, 'Open File', ' ', 'CXI Files (*.cxi)')
        self.fileField.setText(fname[0][0])
        self.browseButton_2.setEnabled(True)

        # restting the main window for the next cxi file
        if self.imageViewer:
            self.imageViewer.close()
            self.plotPixelIntensityButton.setEnabled(False)
            self.fitPolynormialButton.setEnabled(False)
            self.plotPeakPixelButton.setEnabled(False)
            self.advanceSortButton.setEnabled(False)
            self.sortButton.setEnabled(False)
            self.eventNumber.setText("0")
            self.nextButton.setEnabled(False)
            self.previousButton.setEnabled(False)
            self.graphWidget.clear()
        if self.sortGUI:
            self.sortGUI.close()

        if self.mlDialog:
            self.mlDialog.close()

    def browseGeom(self):
        """
            This method gets triggered when the browse button is Clicked in the GUI
        function: The function is to take in a text field where the value needs to be set and called in a dialog box with
        file struture view starting at the 'root' and lets the user select the file they want and set the file path to
        the test field.
        """
        dialog_box = qtw.QDialog()
        geomName = qtw.QFileDialog.getOpenFileNames(dialog_box, 'Open File', ' ', 'geom Files (*.geom)')
        self.fileField_2.setText(geomName[0][0])
        self.viewFileButton.setEnabled(True)

    def curveToPlot(self):
        if int(self.eventNumber.text()) >= self.totalEvents:
            self.eventNumber.setText(str(self.totalEvents -1))

        if self.buttonClicked is None:
            # print('curve to plot got triggered')
            pass
            # qtw.QMessageBox.information(self,'Info','Plot a curve first!')
        elif self.buttonClicked == 'plotCurve':
            self.plotCurve()
        elif self.buttonClicked == 'plotFit':
            self.plotFit()

    def selectDisplay(self):
        if int(self.eventNumber.text()) >= self.totalEvents:
            self.eventNumber.setText(str(self.totalEvents -1))

        if self.imageViewer:
            self.imageViewer.drawImage(int(self.eventNumber.text()))
            # print(" selectDisplay image viewr exist")
        else:
            self.viewFiles()
            # print(" selectDisplay image viewr not exist")

    def panelDetails(self, inDict):
        """
        :param inDict: Dictionery with ASIIC/panel information coming from the signal once the user clicked on a panel
        :return: Assigns panel deitail
        """
        self.panelName = inDict['panel_name']
        self.min_fs = inDict['min_fs']
        self.max_fs = inDict['max_fs']
        self.min_ss = inDict['min_ss']
        self.max_ss = inDict['max_ss']

        self.curveToPlot()

    def viewFiles(self):
        if not self.eventNumber.text():
            self.eventNumber.setEnabled(True)
            self.eventNumber.setText("0")

        self.imageViewer = DisplayImage(self.fileField.text(), self.fileField_2.text())
        self.imageViewer.drawImage(int(self.eventNumber.text()))
        self.totalEvents = self.imageViewer.size

        # initial panel assignment
        self.panelName = self.imageViewer.outgoingDict['panel_name']
        self.min_fs = self.imageViewer.outgoingDict['min_fs']
        self.max_fs = self.imageViewer.outgoingDict['max_fs']
        self.min_ss = self.imageViewer.outgoingDict['min_ss']
        self.max_ss = self.imageViewer.outgoingDict['max_ss']

        self.imageViewer.panelSelected.connect(self.panelDetails)
        self.clickedNext.connect(self.imageViewer.drawImage)
        self.clickedPrevious.connect(self.imageViewer.drawImage)

        self.imageViewer.show()

        if not self.plotPixelIntensityButton.isEnabled():
            self.plotPixelIntensityButton.setEnabled(True)
            self.fitPolynormialButton.setEnabled(True)
            self.plotPeakPixelButton.setEnabled(True)

    def machineLearning(self):

        self.mlDialog = ML(self.imageViewer.outgoingDict)
        self.mlDialog.show()
        self.imageViewer.panelSelected.connect(self.mlDialog.readPanelDetails)

    def nextEvent(self, eventNumber):
        try:
            if int(self.eventNumber.text()) < self.totalEvents - 1:
                self.eventNumber.setText(str(int(eventNumber) + 1))
            elif int(self.eventNumber.text()) == self.totalEvents - 1:
                self.eventNumber.setText(str(0))

            self.curveToPlot()

            self.clickedNext.emit(int(self.eventNumber.text()))
        except Exception as e:
            print(e, '-nextEvent()')
            qtw.QMessageBox.critical(self, 'Fail', 'Please Enter a valid input')

    def previousEvent(self, eventNumber):
        try:
            if int(self.eventNumber.text()) > 0:
                self.eventNumber.setText(str(int(eventNumber) - 1))
            elif int(self.eventNumber.text()) == 0:
                self.eventNumber.setText(str(self.totalEvents - 1))

            self.curveToPlot()

            self.clickedPrevious.emit(int(self.eventNumber.text()))
        except Exception as e:
            print(e, '-previousEvent()')
            qtw.QMessageBox.critical(self, 'Fail', 'Please Enter a valid input')

    def writeToFile(self, eventsList, fileName):
        f = open(fileName, 'w')

        for key in eventsList.keys():
            for i in eventsList[key]:
                f.write(key)
                f.write(' ')
                f.write('//')
                f.write(str(i))
                f.write('\n')

        f.close()

    def sortFrames(self, file_name):
        """
            this method only works on single cxi file. for multiple files code needs to be changed
            function for sorting good frames from the bad frames based on the average intensity ratio of the peak of the
            curve vs crest of the curve
        """

        try:
            tag = str(file_name).split('/')[-1].split('.')[0]
            goodEvents = {}
            badEvents = {}
            # exit()
            # goodList to store all the events with expected pixel intensities for the file
            goodList = []

            # badList to store all the events with detector artifacts for the file
            badList = []

            with h5py.File(file_name, "r") as f:
                data = f['entry_1']['data_1']['data'][()]

            for i in range(0, len(data)):
                frame = data[i]

                peakMeanIntensities = []
                for j in range(60, 80):
                    peakMeanIntensities.append(np.average(frame[2112:2288, j]))

                crestMeanIntensities = []
                for k in range(165, 185):
                    crestMeanIntensities.append(np.average(frame[2112:2288, k]))

                peakMean = np.average(peakMeanIntensities)
                crestMean = np.average(crestMeanIntensities)

                if peakMean / crestMean > 1.3:
                    goodList.append(i)
                else:
                    badList.append(i)

            goodEvents[str(file_name)] = goodList
            badEvents[str(file_name)] = badList

            self.writeToFile(goodEvents, 'goodEvents-simpleSort-%s.list' % tag)
            self.writeToFile(badEvents, 'badEvents-%s.list' % tag)

            qtw.QMessageBox.information(self, 'Success', "Done Sorting")

        except FileNotFoundError:
            qtw.QMessageBox.critical(self, 'Fail', "Couldn't find file %s" % file_name)

        except ValueError:
            qtw.QMessageBox.critical(self, 'Fail', "Please Enter a file path")

    def advanceSortFrames(self):

        self.sortGUI = AdvanceSorting(self.fileField.text(), self.orderOfFit.text(), self.imageViewer.outgoingDict)
        self.sortGUI.show()
        self.imageViewer.panelSelected.connect(self.sortGUI.readPanelDetails)

        self.sortGUI.readyToSaveGood.connect(self.writeToFile)
        self.sortGUI.readyToSaveBad.connect(self.writeToFile)
        self.MLButton.setEnabled(True)

    def returnMaxPixel(self, coeff, x_range):
        """
            coeff (object): out put of a numpy curve fit.
            xRange (tup) : a tuple with (min, max)

            returns the value where the coeff is maximized
        """

        storing_list = []
        for i in range(x_range[0], x_range[1]):
            storing_list.append((np.polyval(coeff, i), i))

        storing_list.sort()

        return storing_list[-1][1]

    def returnMaxPixelsList(self, file_name, deg=1, *args):
        """ fileName(str) : name of the file to be open
            deg (int) : order of the fit ex: is the fit a straight line (1) or quadratic (2 or more)
            *args(list) : expects a list of events to be considered. **TO BE IMPLEMENTED**
        """
        filename = file_name
        max_pixels = []

        with h5py.File(filename, "r") as f:
            data = f['entry_1']['data_1']['data'][()]

        for i in range(len(data)):
            frame = data[i]

            avgIntensities = []
            for j in range(10, 186):
                avgIntensities.append(np.average(frame[2112:2288, j]))

            fit = np.polyfit(np.arange(10, 186), avgIntensities, deg=deg)

            max_pixels.append(self.returnMaxPixel(fit, (10, 186)))

        return max_pixels

    def plotCurve(self):
        try:
            file_name = self.fileField.text()
            event_number = int(self.eventNumber.text())

            with h5py.File(file_name, "r") as f:
                data = f['entry_1']['data_1']['data'][()]

            frame = data[event_number]

            avgIntensities = []

            for i in range(int(self.min_fs)+5, int(self.max_fs)-5):
                avgIntensities.append(np.average(frame[int(self.min_ss):int(self.max_ss), i]))
            self.graphWidget.clear()
            self.graphWidget.plot(list(np.linspace(int(self.min_fs)+5, int(self.max_fs)-5,181)), avgIntensities)
            self.graphWidget.setTitle(str.capitalize('Average Intensity Over The Selected Panel- %s' % self.panelName), size='15pt')
            self.graphWidget.setLabel('left', "Avg. Pixel intensity")
            self.graphWidget.setLabel('bottom', "Pixel Number")

            self.buttonClicked = 'plotCurve'

            if not self.sortButton.isEnabled():
                self.sortButton.setEnabled(True)
                self.nextButton.setEnabled(True)
                self.previousButton.setEnabled(True)

        except FileNotFoundError:
            qtw.QMessageBox.critical(self, 'Fail', "Couldn't find file %s -plotCurve" % file_name)

        except ValueError:
            qtw.QMessageBox.critical(self, 'Fail', "Please Enter a file path -plotCurve")

        except IndexError:
            qtw.QMessageBox.critical(self, 'Fail',
                                     'Value you ,%s,  entered is out of bound for this cxi file -plotCurve'
                                     % self.eventNumber.text())

    def plotFit(self):
        """ fileName(str) : name of the file to be open
                eventNumber(int) : event number for the file
                deg (int) : order of the fit ex: is the fit a straight line (1) or quadratic (2 or more)
        """
        try:
            if not self.orderOfFit.text():
                self.orderOfFit.setEnabled(True)
                self.orderOfFit.setText("4")

            file_name = self.fileField.text()
            eventNumber = int(self.eventNumber.text())
            avgIntensities = []
            degry = int(self.orderOfFit.text())

            filename = file_name
            with h5py.File(filename, "r") as f:
                data = f['entry_1']['data_1']['data'][()]

            frame = data[int(eventNumber)]

            for i in range(int(self.min_fs)+5, int(self.max_fs)-5):
                avgIntensities.append(np.average(frame[int(self.min_ss):int(self.max_ss), i]))

            fit = np.polyfit(np.arange(int(self.min_fs)+5, int(self.max_fs)-5), avgIntensities, deg=degry)

            self.graphWidget.clear()
            self.graphWidget.plot(range(int(self.min_fs)+5, int(self.max_fs)-5), avgIntensities, name='data')
            self.graphWidget.plot(range(int(self.min_fs)+5, int(self.max_fs)-5),
                                  np.polyval(fit, range(int(self.min_fs)+5, int(self.max_fs)-5)),
                                  name='fit', pen=pg.mkPen(color='r', width=2))
            self.graphWidget.setTitle(str.capitalize('Fitting A Polynomial To Average Intensity Over The Selected Panel- %s' % self.panelName), size='15pt')
            self.graphWidget.setLabel('left', "Avg. Pixel intensity")
            self.graphWidget.setLabel('bottom', "Pixel Number")
            self.graphWidget.addLegend()

            self.buttonClicked = 'plotFit'

            if not self.advanceSortButton.isEnabled():
                self.advanceSortButton.setEnabled(True)
                self.nextButton.setEnabled(True)
                self.previousButton.setEnabled(True)

        except FileNotFoundError:
            qtw.QMessageBox.critical(self, 'Fail', "Couldn't find file %s" % file_name)

        except ValueError:
            qtw.QMessageBox.critical(self, 'Fail', "Please Enter a file path")

        except IndexError:
            qtw.QMessageBox.critical(self, 'Fail', 'Value you entered is out of bound -plotFit()')

    def plotMaxPixels(self, file_name):
        try:
            y = self.returnMaxPixelsList(file_name, deg=6)
            x = range(len(y))
            self.graphWidget.clear()
            self.graphWidget.plot(x, y, pen=None, symbol='o')
            self.graphWidget.setTitle('change of the pixel with the highest average intensity', size='15pt')
            self.graphWidget.setLabel('left', "Pixel Number")
            self.graphWidget.setLabel('bottom', "Frame Number")

        except FileNotFoundError:
            qtw.QMessageBox.critical(self, 'Fail', "Couldn't find file %s" % file_name)

        except ValueError:
            qtw.QMessageBox.critical(self, 'Fail', "Please Enter a file path")

    def closeEvent(self, QCloseEvent):
        if self.imageViewer:
            self.imageViewer.close()

        if self.sortGUI:
            self.sortGUI.close()

        if self.mlDialog:
            self.mlDialog.close()


# main .
if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())
