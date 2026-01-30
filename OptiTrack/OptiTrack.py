import os

import ctk
import qt
import slicer

from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)


#
# OptiTrack
#


class OptiTrack(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "OptiTrack"  # TODO make this more human readable by adding spaces
        self.parent.categories = ["OpenNav.Utilities"]
        self.parent.dependencies = ["OpenIGTLinkIF"]
        self.parent.contributors = ["Sam Horvath (Kitware Inc.)"]  # replace with "Firstname Lastname (Organization)"
        self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""  # replace with organization, grant and thanks.


#
# OptiTrackWidget
#


class OptiTrackWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        self.logic = OptiTrackLogic()
        self.logic.expectedNodes(["ReferenceToTracker", "LongToolToTracker", "ShortToolToTracker"])

        # Instantiate and connect widgets ...

        #
        # Parameters Area
        #
        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Parameters"
        self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the dummy collapsible button
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        self.launcherPathEdit = ctk.ctkPathLineEdit()

        self.launcherPathEdit.currentPath = self.logic.getPlusLauncherPath()
        parametersFormLayout.addRow("Launcher Path:", self.launcherPathEdit)

        self.configPathEdit = ctk.ctkPathLineEdit()
        self.configPathEdit.currentPath = self.resourcePath("ReplayOptiTrack.xml.in")
        parametersFormLayout.addRow("Config File Path (template):", self.configPathEdit)

        self.dataPathEdit = ctk.ctkPathLineEdit()
        self.dataPathEdit.currentPath = self.resourcePath("Ellipse.mha")
        parametersFormLayout.addRow("Data file path for replay:", self.dataPathEdit)

        #
        # Apply Button
        #
        self.applyButton = qt.QPushButton("Start OptiTrack")
        self.applyButton.toolTip = "Run the algorithm."
        self.applyButton.enabled = True
        parametersFormLayout.addRow(self.applyButton)

        # connections
        self.applyButton.connect("clicked(bool)", self.onApplyButton)

        # Add vertical spacer
        self.layout.addStretch(1)

    def cleanup(self):
        self.logic.shutdown()

    def onApplyButton(self):
        self.applyButton.enabled = False
        self.applyButton.text = "OptiTrack is starting..."
        slicer.app.processEvents()
        self.logic.start(self.launcherPathEdit.currentPath, self.configPathEdit.currentPath, self.dataPathEdit.currentPath)
        self.applyButton.enabled = True
        if self.logic.isRunning:
            self.applyButton.text = "Stop OptiTrack"
        else:
            self.applyButton.text = "Start OptiTrack"


#
# OptiTrackLogic
#


class OptiTrackLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        self.connector = None
        self.isRunning = False
        self.expectedNodes = []

    def setExpectedNodes(self, expectedNodes):
        self.expectedNodes = expectedNodes

    def shutdown(self, clean=False):
        if self.isRunning:
            self.connector.Stop()
            self.p.terminate()
            self.isRunning = False
            import shutil

            shutil.rmtree(self.tempDirectory)
            print("Shutdown")
            if clean:
                self.cleanupNodes()

    def writeConfigFile(self, configTemplateFileName, dataFileName):
        template = ""
        with open(configTemplateFileName) as fh:
            template = fh.read()

        configData = template.format(dataFileName)
        configDataFileName = os.path.join(self.tempDirectory, "Temp.xml")
        with open(configDataFileName, "w") as fh:
            fh.write(configData)
        print(configDataFileName)
        return configDataFileName

    def getPlusLauncherPath(self):
        basepath = ""
        for item in os.listdir(os.path.expanduser("~")):
            if item.startswith("PlusApp"):
                basepath = os.path.join(os.path.expanduser("~"), item)
                break

        return os.path.join(basepath, "bin/PlusServer.exe")

    def getTempDirectoryBase(self):
        tempDir = qt.QDir(slicer.app.temporaryPath)
        fileInfo = qt.QFileInfo(qt.QDir(tempDir), "OptiTrack")
        dirPath = fileInfo.absoluteFilePath()
        qt.QDir().mkpath(dirPath)
        return dirPath

    def createTempDirectory(self):
        import qt

        tempDir = qt.QDir(self.getTempDirectoryBase())
        tempDirName = qt.QDateTime().currentDateTime().toString("yyyyMMdd_hhmmss_zzz")
        fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
        dirPath = fileInfo.absoluteFilePath()
        qt.QDir().mkpath(dirPath)
        return dirPath

    def checkNode(self, nodeName):
        try:
            node = slicer.util.getNode(nodeName)
            node.CreateDefaultDisplayNodes()
            node.SaveWithSceneOff()
            return True
        except:
            return False

    def checkNodes(self, nodesList=None):
        if nodesList is None:
            nodesList = self.expectedNodes
        for nodeName in nodesList:
            self.checkNode(nodeName)

    def cleanupNodes(self, nodesList=None):
        if nodesList is None:
            nodesList = self.expectedNodes
        for nodeName in nodesList:
            self.cleanupNode(nodeName)

    def cleanupNode(self, nodeName):
        try:
            node = slicer.util.getNode(nodeName)
            slicer.mrmlScene.RemoveNode(node)
        except:
            pass

    def start(self, plusLauncherPath, plusConfigTemplatePath, plusDataPath):
        import time

        self.tempDirectory = self.createTempDirectory()
        plusConfigPath = self.writeConfigFile(plusConfigTemplatePath, plusDataPath)
        if not self.isRunning:
            self.isRunning = True
            self.p = slicer.util.launchConsoleProcess([plusLauncherPath, "--config-file=" + plusConfigPath])
            self.p.poll()

            if not self.connector:
                self.connector = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLIGTLConnectorNode")
                self.connector.SetTypeClient("localhost", 18944)
            self.connector.Start()

            connected = False
            # wait max 30 seconds for connection:
            start = time.time()
            while not connected and time.time() - start < 30:
                slicer.app.processEvents()
                if self.connector.GetState() == slicer.vtkMRMLIGTLConnectorNode.StateConnected:
                    connected = True
                    break
                time.sleep(0.1)

            if not connected:
                print("Server failed to launch:")
                self.shutdown()
                output = self.p.stdout.read()
                print(output)
                return
            print("PLUS Server launched")
            self.checkNodes()
        else:
            self.shutdown()
