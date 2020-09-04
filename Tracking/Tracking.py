import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap
import numpy as np

import NNUtils
from TrackingDevices.NDIDevices import NDIVegaTracker


class Tracking(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Tracking" 
    self.parent.categories = [""]
    self.parent.dependencies = ["TrackingInterface", "PivotCalibration", "FiducialSelection"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"] 
    self.parent.helpText = """
This is the tracking module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class TrackedTool:
 
  def updateModel(self, transformNode=None, unusedArg2=None, unusedArg3=None):
    if self.tubeModel is not  None:
        slicer.mrmlScene.RemoveNode( self.tubeModel )

    points = vtk.vtkPoints()
    points.SetNumberOfPoints(2)
    points.SetPoint(0, 0, 0, 0 )

    m = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToParent(m)
    points.SetPoint(1, m.GetElement(0,3), m.GetElement(1,3), m.GetElement(2,3) )
    if m.GetElement(0,3) + m.GetElement(1,3) + m.GetElement(2,3) == 0:
      points.SetPoint(1,0,0,1)

    # Create a cell array to store the lines in and add the lines to it
    line = vtk.vtkCellArray()
    line.InsertNextCell(2)
    line.InsertCellPoint(0)
    line.InsertCellPoint(1)
    linesPolyData = vtk.vtkPolyData()
    linesPolyData.SetPoints(points)
    linesPolyData.SetLines(line)

    tubeSegmentFilter = vtk.vtkTubeFilter();
    tubeSegmentFilter.SetInputData( linesPolyData );
    tubeSegmentFilter.SetRadius( 4 );
    tubeSegmentFilter.SetNumberOfSides( 30 );
    tubeSegmentFilter.CappingOn();
    tubeSegmentFilter.Update();
    tubePolyData = tubeSegmentFilter.GetOutput();
    self.tubeModel = slicer.modules.models.logic().AddModel( tubePolyData )
    self.tubeModel.SetName( self.toolname )
    self.tubeModel.SetSaveWithScene(False)
    self.tubeModel.SetAndObserveTransformNodeID( self.transformNode.GetID() )
    

    modelDisplay = self.tubeModel.GetDisplayNode()
    modelDisplay.SetColor(0.2,0.2,0.7)
    modelDisplay.SetDiffuse(0.90)
    modelDisplay.SetAmbient(0.10)
    modelDisplay.SetSpecular(0.20)
    modelDisplay.SetPower(10.0)
    modelDisplay.SetOpacity(0.5)
    modelDisplay.SetVisibility2D(True)
    modelDisplay.SetVisibility3D(True)
    modelDisplay.SetSliceIntersectionThickness(3)

  def __init__(self, toolname, toolID, transformNode, transformNodeTip):
    self.tubeModel = None
    self.toolname = toolname
    self.observers = []
    self.transformNode = transformNode
    self.transformNodeTip = transformNodeTip

    transformNodeTip.AddObserver( slicer.vtkMRMLTransformNode.TransformModifiedEvent,
            self.updateModel )
    self.updateModel()

  def getTipWorld(self):
    m = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToParent(m)
    tipLocal = np.array( [m.GetElement(0,3), m.GetElement(1,3), m.GetElement(2,3)] )
    tipWorld = np.empty(3)
    self.transformNodeTip.TransformPointToWorld(tipLocal, tipWorld)
    return tipWorld

  def getBaseWorld(self):
    baseLocal = np.zeros(3)
    baseWorld = np.empty(3)
    self.transformNodeTip.TransformPointToWorld(baseLocal, baseWorld)
    return baseWorld

  def getRotation(self, tool):
    mat = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToWorld(mat)
    npmat = np.zeros( [3,3] )
    for i in range(3):
      for j in range(3):
        npmat[i,j] = mat.GetElement(i,j)

    return np.linalg.inv( npmat )

  def getTranslation(self, tool):
    mat = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToWorld(mat)
    npmat = np.zeros(3)
    for i in range(3):
      npmat[i] = mat.GetElement(i,3)
    return npmat


class TrackingWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    
    self.logic = TrackingLogic()
    self.trackingLogic = slicer.modules.trackinginterface.widgetRepresentation().self().logic

    self.trackingNodeName = "TrackingToScene"
    # Setup tracking transform node
    self.transformNode = slicer.vtkMRMLLinearTransformNode()
    self.transformNode.SetSaveWithScene(False)
    self.transformNode.SetSingletonTag("Tracking_" + self.trackingNodeName)
    m = vtk.vtkMatrix4x4()
    m.Identity()
    self.transformNode.SetMatrixTransformToParent(m)
    self.transformNode.SetName(self.trackingNodeName)
    slicer.mrmlScene.AddNode(self.transformNode)

  def updateStatus(self, transformNode, unusedArg2=None, unusedArg3=None):
    for i, statusLabel in enumerate( self.toolStatusLabels ):
      if self.trackingLogic.isTracking(i):
        statusLabel.setText(" Tracking On ")
        statusLabel.setStyleSheet("background-color: green;")
      else:
        statusLabel.setText(" Tracking Off ")
        statusLabel.setStyleSheet("background-color: red;")
   
  def updateSliceViews(self, tool):
    pos = tool.getTranslation()
    rot = np.linalg.inv(tool.getRotation())
    NNUtils.updateSliceViews(pos, rot)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    tracker = self.logic.getTrackingDevice()
    self.trackingLogic.setTrackingDevice( tracker )

    #Connect button
    self.connectButton = qt.QPushButton("Start Tracking")
    self.connectButton.setCheckable(True)
    self.layout.addWidget(self.connectButton)
    # Tracking toogle button action
    def toggleTracking(checked):
      if not checked:
        self.connectButton.setText("Start Tracking")
        self.trackingLogic.stopTracking()
      else:
        try:
          self.trackingLogic.startTracking()
          self.connectButton.setText("Stop Tracking")
        except OSError as err:
          #TODO figure out error message handling
          slicer.util.errorDisplay( str(err) )
    self.connectButton.toggled.connect(toggleTracking)

    # Setup tool calibrations
    self.toolsWidget = qt.QWidget()
    toolsLayout = qt.QVBoxLayout(self.toolsWidget)
    self.tools = []
    self.toolCalibrateButtons = []
    self.toolStatusLabels = []
    for i in range( self.trackingLogic.getNumberOfTools() ):
      toolname = "Tool_%d" % i
      (tNode, tNodeTip)  = self.trackingLogic.getTransformsForTool(i)
      tNode.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent,
              self.updateStatus)
      tool = TrackedTool(toolname, i, tNode, tNodeTip)

      # Add to tracking to scene transform
      tool.transformNode.SetAndObserveTransformNodeID( self.transformNode.GetID() )
      
      # Create tool widget with calibrate button and status
      toolLayout = qt.QHBoxLayout()
      toolLayout.addWidget(qt.QLabel(toolname))
      calibrateButton = qt.QPushButton("Calibrate")
      toolLayout.addWidget(calibrateButton)

      calibrationWidget = slicer.modules.pivotcalibration.createNewWidgetRepresentation()
      doneButton = qt.QPushButton("Done")
      calibrationWidget.layout().addWidget(doneButton)
      calibrationDialog = qt.QDialog()
      calibrationDialog.setModal( False )
      calibrationDialog.setLayout(calibrationWidget.layout())

      def doneFunction( tool ):
        def doneFunc():
          calibrationDialog.accept()
          tool.updateModel()
        return doneFunc
      doneButton.clicked.connect(doneFunction(tool))

      def showFunction(cWidget, dlg, tool):
        def showFunc():
          inputBox = dlg.findChild(slicer.qMRMLNodeComboBox, "InputComboBox")
          inputBox.setCurrentNode( tool.transformNode )
          inputBox.setEnabled(False)
          outputBox = dlg.findChild(slicer.qMRMLNodeComboBox, "OutputComboBox")
          outputBox.setCurrentNode( tool.transformNodeTip )
          outputBox.setEnabled(False)
          dlg.show()
        return showFunc
      calibrateButton.clicked.connect( showFunction(calibrationWidget, calibrationDialog, tool) )
      
      statusLabel = qt.QLabel(" Tracking Off ")
      statusLabel.setStyleSheet("background-color: red;")
      toolLayout.addWidget(statusLabel)
      self.toolStatusLabels.append(statusLabel)

      toolWidget = qt.QWidget(self.parent)
      toolWidget.setLayout(toolLayout)
      toolsLayout.addWidget(toolWidget)


    self.layout.addWidget(self.toolsWidget)

    #Track slice view
    self.trackCameraWidget = qt.QWidget(self.parent)
    trackCameraLayout = qt.QHBoxLayout()
    self.trackCameraWidget.setLayout(trackCameraLayout)
    trackCameraLabel = qt.QLabel("Align Slice Views To: ")
    trackCameraLayout.addWidget(trackCameraLabel)

    self.cameraTool = qt.QComboBox()
    self.cameraTool.addItem("None")
    for i  in range(self.trackingLogic.getNumberOfTools()):
      toolname = "Tool_%d" % i
      self.cameraTool.addItem(toolname)
    self.cameraTool.currentIndexChanged.connect( 
            lambda index: self.resetSliceViews() if index == 0 else None )
    trackCameraLayout.addWidget(self.cameraTool)
    self.layout.addWidget(self.trackCameraWidget)

    # Configuration
    self.configurationFrame = tracker.getConfigurationWidget()
    self.layout.addWidget(self.configurationFrame)

    #Fiducial registration
    self.fiducialFrame = ctk.ctkCollapsibleGroupBox(self.parent)
    fiducialLayout = qt.QVBoxLayout(self.fiducialFrame)
    self.layout.addWidget(self.fiducialFrame)
    self.fiducialFrame.name = "Register Tracking to Scene"
    self.fiducialFrame.title = "Register Tracking to Scene"
    self.fiducialFrame.setChecked( True )

    self.registerWidget = slicer.modules.fiducialselection.createNewWidgetRepresentation()
    fiducialLayout.addWidget(self.registerWidget)

    # compress the layout
    self.layout.addStretch(1)
  
  def enter(self):
    self.registerWidget.enter() 
    

class TrackingLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  tracker = None

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)

  def getTrackingDevice(self):
    if TrackingLogic.tracker is None:

      # TODO needs to be adapted for Optitracker
      # Setup NDI Vega tracker
      self.toolsPath = os.path.dirname(slicer.modules.tracking.path)
      self.toolsPath = os.path.join( self.toolsPath, "Resources/NDITools" )
      self.toolFiles = [os.path.join(self.toolsPath, f) for f in os.listdir(self.toolsPath)
                        if os.path.isfile(os.path.join(self.toolsPath, f))]
      TrackingLogic.tracker = NDIVegaTracker(self.toolFiles)
    return TrackingLogic.tracker


class TrackingTest(ScriptedLoadableModuleTest):
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
    self.test_Tracking1()

  def test_Tracking1(self):
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
    
    logic = TrackingLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class TrackingFileWriter(object):
  def __init__(self, parent):
    pass
