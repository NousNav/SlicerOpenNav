import logging
import vtk, qt, ctk, slicer
import numpy as np
import os
import subprocess

import TrackingDevices.Interface as TrackingInterface
from TrackingDevices.Interface import TrackingDevice

def setupPLUSOptiTrackTrackingDevice(templatePath, dataPath):
  if TrackingInterface.getTrackingDevice() is None:
        TrackingInterface.setTrackingDevice(PLUSOptiTrack(templatePath, dataPath))

class PLUSOptiTrack(TrackingDevice):

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
    self.tools = []
    self.isTrackingActive = []
    self.addTool( 'ProbeToTracker' )

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
    configurationLayout.addRow('Config File Path (template):', self.configPathEdit)

    self.dataPathEdit = ctk.ctkPathLineEdit()
    self.dataPathEdit.currentPath = self.settings_optitrack["dataPath"]
    configurationLayout.addRow('Data file path for replay:', self.dataPathEdit)

  def addTool(self, toolname):
    
    # Tool tip relative to tool location
    transformNodeTip = slicer.vtkMRMLLinearTransformNode()
    m = vtk.vtkMatrix4x4()
    m.Identity()
    transformNodeTip.SetMatrixTransformToParent(m)
    transformNodeTip.SetName(toolname + "_tip")
    transformNodeTip.SetSaveWithScene(False)

    slicer.mrmlScene.AddNode(transformNodeTip)

    self.tools.append((toolname, transformNodeTip))
    self.isTrackingActive.append(False)

  def tracking(self):
    pass

  def startTracking(self):
    self.stopTracking()
    self.settings_optitrack["launcherPath"] = self.launcherPathEdit.currentPath
    self.settings_optitrack["templatePath"] = self.configPathEdit.currentPath
    self.settings_optitrack["dataPath"] = self.dataPathEdit.currentPath
    self.launchPLUS(self.settings_optitrack)
    self.checkIncomingTransforms()

  def checkIncomingTransforms(self):

    for index, data_tuple in enumerate(self.tools):
      transformNodeName = data_tuple[0]
      transformNodeTip = data_tuple[1]
      try:
        transformNode = slicer.util.getNode(transformNodeName)
        print('Found {}'.format(transformNodeName))
        transformNodeTip.SetAndObserveTransformNodeID(transformNode.GetID())
        self.isTrackingActive[index] = True
      except:
        print('WARNING: Could not find {}'.format(transformNodeName))
  
  def launchPLUS(self, settings):
    import time

    if not self.connector:
      self.connector = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLIGTLConnectorNode')
      self.connector.SetTypeClient("localhost", 18944)

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
      self.connector.Stop()
      slicer.mrmlScene.RemoveNode(self.connector)
      self.connector = None
      self.p.terminate()
      import shutil
      shutil.rmtree(self.tempDirectory)
    else:
      logging.warning("OptiTrack Tracker already closed")

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
