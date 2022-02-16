import os
import subprocess
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *


#
# OptiTrack
#

class OptiTrack(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "OptiTrack" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Examples"]
    self.parent.dependencies = ["OpenIGTLinkIF"]
    self.parent.contributors = ["John Doe (AnyWare Corp.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
It performs a simple thresholding on the input volume and optionally captures a screenshot.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


#
# OptiTrackWidget
#

class OptiTrackWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = OptiTrackLogic()
    self.logic.setTools(['ReferenceToTracker', 'LongToolToTracker', 'ShortToolToTracker'])

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
    parametersFormLayout.addRow('Launcher Path:', self.launcherPathEdit)

    self.configPathEdit = ctk.ctkPathLineEdit()
    self.configPathEdit.currentPath = self.resourcePath('ReplayOptiTrack.xml.in')
    parametersFormLayout.addRow('Config File Path (template):', self.configPathEdit)

    self.dataPathEdit = ctk.ctkPathLineEdit()
    self.dataPathEdit.currentPath = self.resourcePath('Ellipse.mha')
    parametersFormLayout.addRow('Data file path for replay:', self.dataPathEdit)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Start OptiTrack")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = True
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    self.logic.shutdown()

  def onApplyButton(self):

    self.applyButton.enabled = False
    self.applyButton.text = 'OptiTrack is starting...'
    slicer.app.processEvents()
    self.logic.start(self.launcherPathEdit.currentPath, self.configPathEdit.currentPath, self.dataPathEdit.currentPath)
    self.applyButton.enabled = True
    if self.logic.isRunning:
      self.applyButton.text = 'Stop OptiTrack'
    else:
      self.applyButton.text = 'Start OptiTrack'


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
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    self.connector = None
    self.isRunning = False
    self.tools = []

  def setTools(self, tools):
    self.tools = tools

  def shutdown(self, clean=False):
    if self.isRunning:
      self.connector.Stop()
      self.p.terminate()
      self.isRunning = False
      import shutil
      shutil.rmtree(self.tempDirectory)
      print('Shutdown')
      if clean:
        self.cleanupTools()

  def writeConfigFile(self, configTemplateFileName, dataFileName):
    template = ''
    with open(configTemplateFileName,"r") as fh:
      template = fh.read()

    configData = template.format(dataFileName)
    configDataFileName = os.path.join(self.tempDirectory, 'Temp.xml')
    with open(configDataFileName,"w") as fh:
      fh.write(configData)
    print(configDataFileName)
    return configDataFileName

  def getPlusLauncherPath(self):
    basepath = ''
    for item in os.listdir(os.path.expanduser('~')):
      if item.startswith('PlusApp'):
        basepath = os.path.join(os.path.expanduser('~'), item)
        break

    return os.path.join(basepath, 'bin/PlusServer.exe')

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

  def checkTool(self, toolName):
    try:
        node = slicer.util.getNode(toolName)
        node.CreateDefaultDisplayNodes()
        # node.GetDisplayNode().SetEditorVisibility(True)
        return True
    except:
      return False

  def checkTools(self, toolsList=None):
    if toolsList is None:
      toolsList = self.tools
    for toolName in toolsList:
      self.checkTool(toolName)

  def cleanupTools(self, toolsList=None):
    if toolsList is None:
      toolsList = self.tools
    for toolName in toolsList:
      self.cleanupTool(toolName)

  def cleanupTool(self, toolName):
    try:
        node = slicer.util.getNode(toolName)
        slicer.mrmlScene.RemoveNode(node)
    except:
      pass

  def start(self, plusLauncherPath, plusConfigTemplatePath, plusDataPath):
    import time

    self.tempDirectory = self.createTempDirectory()
    plusConfigPath = self.writeConfigFile(plusConfigTemplatePath, plusDataPath)
    if not self.isRunning:
      self.isRunning = True
      info = subprocess.STARTUPINFO()
      info.dwFlags = 1
      info.wShowWindow = 0
      self.p = subprocess.Popen([plusLauncherPath, '--config-file='+plusConfigPath ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=info)
      time.sleep(5)
      if not self.connector:
        self.connector = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLIGTLConnectorNode')
        self.connector.SetTypeClient("localhost", 18944)
      self.connector.Start()

      time.sleep(5)
      slicer.app.processEvents()
      if self.connector.GetState() != slicer.vtkMRMLIGTLConnectorNode.StateConnected:
        print('Server failed to launch:')
        self.shutdown()
        output = self.p.stdout.read()
        output = output.decode("utf-8", 'replace')
        print(output)
        return
      print('PLUS Server launched')
      self.checkTools()
    else:
      self.shutdown()


class OptiTrackTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_OptiTrack1()

  def test_OptiTrack1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    pass
