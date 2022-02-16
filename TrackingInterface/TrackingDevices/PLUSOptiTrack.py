import logging
import vtk, qt, ctk, slicer
import numpy as np
import os
import subprocess

import TrackingDevices.Interface as TrackingInterface
from TrackingDevices.Interface import TrackingDevice


def setupPLUSOptiTrackTrackingDevice(templatePath, dataPath):
  if TrackingInterface.getTrackingDevice() is None:
        TrackingInterface.setTrackingDevice(PLUSOptiTrackTracker(templatePath, dataPath))


class PLUSOptiTrackTracker(TrackingDevice):

  def __init__(self, templatePath, dataPath):
    # Tracking toggle button action

    #Compute defaults
    basepath = ''
    for item in os.listdir(os.path.expanduser('~')):
      if item.startswith('PlusApp'):
        basepath = os.path.join(os.path.expanduser('~'), item)
        break
    launcherPath = os.path.join(basepath, 'bin/PlusServer.exe')
    self.settings_optitrack = {
          "tracker type": "plus-optitrack",
          "launcherPath": launcherPath,
          "templatePath": templatePath,
          "dataPath": dataPath,
        }
    self.connector = None
    self.tempDirectory = None
    self.p = None
    self.tools = []
    self.toolSources = []
    self.isTrackingActive = []
    self.addTool( 'Tool_0', 'ProbeToTracker' )

    self.tracker_timer = qt.QTimer()
    self.tracker_timer.timeout.connect( self.tracking )

    # default configuration widget
    self.configurationFrame = ctk.ctkCollapsibleGroupBox()
    configurationLayout = qt.QFormLayout(self.configurationFrame)
    self.configurationFrame.name = "Tracking Setup"
    self.configurationFrame.title = "Tracking Setup"
    self.configurationFrame.setChecked( False )

    self.launcherPathEdit = ctk.ctkPathLineEdit()
    self.launcherPathEdit.currentPath = self.settings_optitrack["launcherPath"]
    configurationLayout.addRow('Launcher Path:', self.launcherPathEdit)

    self.configPathEdit = ctk.ctkPathLineEdit()
    self.configPathEdit.currentPath = self.settings_optitrack["templatePath"]
    configurationLayout.addRow('PLUS Config File Path (template):', self.configPathEdit)

    self.dataPathEdit = ctk.ctkPathLineEdit()
    self.dataPathEdit.currentPath = self.settings_optitrack["dataPath"]
    configurationLayout.addRow('Data/Motive file path:', self.dataPathEdit)

    self.poll = qt.QSpinBox()
    self.poll.setMinimum(10)
    self.poll.setMaximum(500)
    self.poll.setValue(100)

    configurationLayout.addRow('Poll (ms)', self.poll)

  def addTool(self, toolname, toolsource):

    # Tool location
    transformNode = slicer.vtkMRMLLinearTransformNode()
    m = vtk.vtkMatrix4x4()
    m.Identity()
    transformNode.SetMatrixTransformToParent(m)
    transformNode.SetName(toolname)
    transformNode.SetSaveWithScene(False)
    slicer.mrmlScene.AddNode(transformNode)

    # Tool tip relative to tool location
    transformNodeTip = slicer.vtkMRMLLinearTransformNode()
    m = vtk.vtkMatrix4x4()
    m.Identity()
    transformNodeTip.SetMatrixTransformToParent(m)
    transformNodeTip.SetName(toolname + "_tip")
    transformNodeTip.SetSaveWithScene(False)

    slicer.mrmlScene.AddNode(transformNodeTip)
    transformNodeTip.SetAndObserveTransformNodeID(transformNode.GetID())

    self.tools.append((transformNode, transformNodeTip))
    self.isTrackingActive.append(False)
    self.toolSources.append(toolsource)

  def tracking(self):
    for i in range(self.getNumberOfTools()):
      (transformNode, transformNodeTip) = self.getTransformsForTool(i)
      if self.isTrackingActive[i]:
        sourceNode = slicer.util.getNode(self.toolSources[i])
        m = vtk.vtkMatrix4x4()
        sourceNode.GetMatrixTransformToParent(m)
        transformNode.SetMatrixTransformToParent(m)
      else:
        # Notify observers - TODO add status observation to interface?
        m = vtk.vtkMatrix4x4()
        transformNode.GetMatrixTransformToParent(m)
        transformNode.SetMatrixTransformToParent(m)

  def startTracking(self):
    print('Start tracking')
    self.stopTracking()
    self.settings_optitrack["launcherPath"] = self.launcherPathEdit.currentPath
    self.settings_optitrack["templatePath"] = self.configPathEdit.currentPath
    self.settings_optitrack["dataPath"] = self.dataPathEdit.currentPath
    print('Launch plus')
    self.launchPLUS(self.settings_optitrack)
    self.checkIncomingTransforms()
    self.tracker_timer.start( self.poll.value )

  def checkIncomingTransforms(self):

    for i in range(self.getNumberOfTools()):
      try:
        sourceNode = slicer.util.getNode(self.toolSources[i])
        self.isTrackingActive[i] = True
      except:
        print('WARNING: Could not find {}'.format(self.toolSources[i]))

  def launchPLUS(self, settings):
    import time

    self.tempDirectory = self.createTempDirectory()
    plusConfigPath = self.writeConfigFile(settings["templatePath"], settings["dataPath"])
    info = subprocess.STARTUPINFO()
    info.dwFlags = 1
    info.wShowWindow = 0
    self.p = subprocess.Popen([settings["launcherPath"], '--config-file='+plusConfigPath ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=info)
    time.sleep(5)
    if not self.connector:
      self.connector = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLIGTLConnectorNode')
      self.connector.SetTypeClient("localhost", 18944)
    self.connector.Start()

    time.sleep(5)
    slicer.app.processEvents()
    if self.connector.GetState() != slicer.vtkMRMLIGTLConnectorNode.StateConnected:
      print('Server failed to launch:')
      self.stopTracking()
      output = self.p.stdout.read()
      output = output.decode("utf-8")
      print(output)
      return
    print('PLUS Server launched')

  def stopTracking(self):
    if self.connector is not None:
      self.tracker_timer.stop()
      self.connector.Stop()
    else:
      logging.warning("OptiTrack Tracker already closed")

    if self.tempDirectory is not None:
      print('delete old temp directory')
      import shutil
      shutil.rmtree(self.tempDirectory)
      self.tempDirectory = None

    if self.p is not None:
      self.p.terminate()
      self.p = None

  def getConfiguration(self):
    self.settings_optitrack = {
          "tracker type": "plus-optitrack",
          "launcherPath": self.launcherPathEdit.currentPath,
          "templatePath": self.configPathEdit.currentPath,
          "dataPath": self.dataPathEdit.currentPath,
        }
    return self.settings_optitrack

  def setConfiguration(self, config):
    # TODO update tool transform etc
    # self.settings_vega = config
    pass

  def getNumberOfTools(self):
    return len( self.tools )

  def getTransformsForTool(self, index):
    try:
      return self.tools[index]
    except IndexError:
      return None

  def getConfigurationWidget(self):
    return self.configurationFrame

  def isTracking(self, index):
    return self.isTrackingActive[index]

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

  def getTempDirectoryBase(self):
    tempDir = qt.QDir(slicer.app.temporaryPath)
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), "OptiTrack")
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath

  def createTempDirectory(self):
    import qt, slicer
    tempDir = qt.QDir(self.getTempDirectoryBase())
    tempDirName = qt.QDateTime().currentDateTime().toString("yyyyMMdd_hhmmss_zzz")
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath
