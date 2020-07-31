import os
import sys
import subprocess
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

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

    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    

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

    self.logic = OptiTrackLogic()
    self.logic.setup()

    

  def cleanup(self):
    self.logic.shutdown()

  

  def onApplyButton(self):   
    
    self.applyButton.enabled = False
    self.applyButton.text = 'OptiTrack is starting...'
    slicer.app.processEvents()
    self.logic.start()   
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

  def setup(self):
    self.connector = None
    self.isRunning = False
    self.plusLauncherPath = 'C:/Users/Sam/PlusApp-2.8.0.20191105-Win64/bin/PlusServer.exe'
    self.plusConfigPath = 'E:/NousNav/Modules/Scripted/OptiTrack/Resources/PlusDeviceSet_Server_OptiTrack_Profile.xml'
  
  def shutdown(self):
    if self.isRunning:
      self.connector.Stop()
      self.p.terminate()
      self.isRunning = False 
  
  def start(self):
    """
    Run the actual algorithm
    """
    import time

    if not self.isRunning:
      self.isRunning = True
      info = subprocess.STARTUPINFO()
      info.dwFlags = 1
      info.wShowWindow = 0
      self.p = subprocess.Popen([self.plusLauncherPath, '--config-file='+self.plusConfigPath ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=info)
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
        output = output.decode("utf-8")
        print(output)
        return
      print('PLUS Server launched')
      try:
        node = slicer.util.getNode('ProbeToTracker')
        node.CreateDefaultDisplayNodes()
        print('Found ProbeToTracker')
        node.GetDisplayNode().SetEditorVisibility(True)
      except:
        print('WARNING: Could not find probe')
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

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import SampleData
    SampleData.downloadFromURL(
      nodeNames='FA',
      fileNames='FA.nrrd',
      uris='http://slicer.kitware.com/midas3/download?items=5767',
      checksums='SHA256:12d17fba4f2e1f1a843f0757366f28c3f3e1a8bb38836f0de2a32bb1cd476560')
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = OptiTrackLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
