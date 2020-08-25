import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap
import numpy as np
from slicer.util import VTKObservationMixin


class Tracking(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Tracking" 
    self.parent.categories = [""]
    self.parent.dependencies = []
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
 
  def updateModel(self):
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

  def __init__(self, toolname):
    self.tubeModel = None
    self.toolname = toolname
    self.isTracking = False
    self.observers = []

    #TODO: connect to transforms from optitracker module
    #Tool location
    self.transformNode = slicer.vtkMRMLLinearTransformNode()
    m = vtk.vtkMatrix4x4()
    m.Identity()
    self.transformNode.SetMatrixTransformToParent( m )
    self.transformNode.SetName( toolname )
    self.transformNode.SetSaveWithScene(False)
    self.transformNode.SetSingletonTag("Tracking_" + self.toolname)
    slicer.mrmlScene.AddNode( self.transformNode )

    #Tool tip relative to tool location
    self.transformNodeTip = slicer.vtkMRMLLinearTransformNode()
    m = vtk.vtkMatrix4x4()
    m.Identity()
    self.transformNodeTip.SetMatrixTransformToParent( m )
    self.transformNodeTip.SetName( self.toolname + "_tip" )
    self.transformNodeTip.SetSaveWithScene(False)
    self.transformNodeTip.SetSingletonTag("Tracking_" + self.toolname + "_tip")

    slicer.mrmlScene.AddNode( self.transformNodeTip )
    self.transformNodeTip.SetAndObserveTransformNodeID( self.transformNode.GetID() )

    self.updateModel()


class TrackingWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)

    self.trackingNodeName = "TrackingToScene" 
    #Setup tracking transform node
    self.transformNode = slicer.vtkMRMLLinearTransformNode()
    self.transformNode.SetSaveWithScene(False)
    self.transformNode.SetSingletonTag("Tracking_" + self.trackingNodeName)
    m = vtk.vtkMatrix4x4()
    m.Identity()
    self.transformNode.SetMatrixTransformToParent( m )
    self.transformNode.SetName( self.trackingNodeName  )
    slicer.mrmlScene.AddNode( self.transformNode )


  def updateStatus(self):
    for i in range(len(self.tools)):
      tool = self.tools[i]
      if tool.isTracking:
        self.toolStatusLabels[i].setText("Tracking On")
        self.toolStatusLabels[i].setStyleSheet("background-color: green;")
      else:
        self.toolStatusLabels[i].setText("Tracking Off")
        self.toolStatusLabels[i].setStyleSheet("background-color: red;")
   

  def getActiveVolume(self):
    lm = slicer.app.layoutManager()
    sliceLogic = lm.sliceWidget('Red').sliceLogic()
    compositeNode = sliceLogic.GetSliceCompositeNode()
    return compositeNode.GetBackgroundVolumeID()
  
  def getRotation(self, tool):
    mat = vtk.vtkMatrix4x4()
    tool.transformNodeTip.GetMatrixTransformToWorld(mat)
    npmat = np.zeros( [3,3] )
    for i in range(3):
      for j in range(3):
        npmat[i,j] = mat.GetElement(i,j)

    return np.linalg.inv( npmat )

  def getTranslation(self, tool):
    mat = vtk.vtkMatrix4x4()
    tool.transformNodeTip.GetMatrixTransformToWorld(mat)
    npmat = np.zeros(3)
    for i in range(3):
      npmat[i] = mat.GetElement(i,3)
    return npmat

  def resetSliceViews(self):
    nodeID = self.getActiveVolume()
    if nodeID is None:
      return
    volumeNode = slicer.mrmlScene.GetNodeByID(nodeID) 

    sliceNode = slicer.app.layoutManager().sliceWidget('Yellow').mrmlSliceNode()
    sliceNode.RotateToVolumePlane(volumeNode)
   
    sliceNode = slicer.app.layoutManager().sliceWidget('Green').mrmlSliceNode()
    sliceNode.RotateToVolumePlane(volumeNode)

    sliceNode = slicer.app.layoutManager().sliceWidget('Red').mrmlSliceNode()
    sliceNode.RotateToVolumePlane(volumeNode)
    
  def updateSliceViews(self, tool):

    pos = self.getTranslation( tool )
    rot = np.linalg.inv( self.getRotation(tool) )

    sliceNode = slicer.app.layoutManager().sliceWidget('Yellow').mrmlSliceNode()
    sliceNode.SetSliceToRASByNTP( rot[0,0], rot[1,0], rot[2,0], 
                                  rot[0,1], rot[1,1], rot[2,1], 
                                  pos[0], pos[1], pos[2], 0)
    sliceNode.UpdateMatrices()
   
    sliceNode = slicer.app.layoutManager().sliceWidget('Green').mrmlSliceNode()
    sliceNode.SetSliceToRASByNTP( rot[0,1], rot[1,1], rot[2,1], 
                                  rot[0,2], rot[1,2], rot[2,2], 
                                  pos[0], pos[1], pos[2], 0)
    sliceNode.UpdateMatrices()

    sliceNode = slicer.app.layoutManager().sliceWidget('Red').mrmlSliceNode()
    sliceNode.SetSliceToRASByNTP( rot[0,2], rot[1,2], rot[2,2], 
                                  rot[0,0], rot[1,0], rot[1,0], 
                                  pos[0], pos[1], pos[2], 0)
    sliceNode.UpdateMatrices()

  def tracking(self):
    try:
      #TODO update tool tarnsformations here and set status to tracking 
      #if succesful transform is set from tracking device
      tool.isTracking=False
      self.updateStatus()
      slicer.app.processEvents()
      #connect cooridnates to transforms
    except Exception as e:
      print( "Tracking error")
      print(e)
      pass



  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    
    self.layout.setSpacing(0)
    self.layout.setMargin(0)

    #Tools
    #self.toolsPath = os.path.dirname(slicer.modules.ndivegatracker.path) 
    #self.toolsPath = os.path.join( self.toolsPath, "Resources/Tools" )
    #self.toolFiles = [os.path.join(self.toolsPath, f) for f in os.listdir(self.toolsPath) 
    #                    if os.path.isfile(os.path.join(self.toolsPath, f))]
    self.toolFiles =["Tool1", "Tool2", "Tool3"]

    #Connect button
    self.isTracking = False
    self.connectButton = qt.QPushButton("Start Tracking")
    self.layout.addWidget(self.connectButton)

    #Configuration
    self.configurationFrame = ctk.ctkCollapsibleGroupBox(self.parent)
    configurationLayout = qt.QGridLayout(self.configurationFrame)
    self.layout.addWidget(self.configurationFrame)
    self.configurationFrame.name = "Tracking Setup"
    self.configurationFrame.title = "Tracking Setup"
    self.configurationFrame.setChecked( False )

    self.configurationWidget = qt.QWidget()
    configurationLayout.addWidget( qt.QLabel("IP Address:"), 0, 0 )
    self.ipaddress = qt.QLineEdit("192.168.1.8")
    configurationLayout.addWidget(self.ipaddress, 0, 1)

    configurationLayout.addWidget( qt.QLabel("Port:"), 1,0 )
    self.port = qt.QLineEdit("8765")
    configurationLayout.addWidget(self.port,1,1)

    configurationLayout.addWidget( qt.QLabel("Poll (ms):"), 2,0 )
    self.poll = qt.QSpinBox()
    self.poll.setMinimum(10)
    self.poll.setMaximum(500)
    self.poll.setValue(100)
    configurationLayout.addWidget(self.poll,2,1)

    #Setup tools including transforms
    self.toolsWidget = qt.QWidget()
    toolsLayout = qt.QVBoxLayout(self.toolsWidget)
    self.tools = []
    self.toolCalibrateButtons = []
    self.toolStatusLabels = []
    for i in range(len(self.toolFiles)):
      toolname = "Tool_" + str(i)
      tool = TrackedTool( toolname )
      tool.transformNode.SetAndObserveTransformNodeID( self.transformNode.GetID() )
      self.tools.append( tool )

      toolLayout = qt.QHBoxLayout()
      
      toolLayout.addWidget( qt.QLabel( toolname ) )
      
      calibrateButton = qt.QPushButton( "Calibrate" )
      toolLayout.addWidget( calibrateButton )
      
      calibrationWidget = slicer.modules.pivotcalibration.createNewWidgetRepresentation()
      inputBox = calibrationWidget.findChild(slicer.qMRMLNodeComboBox, "InputComboBox")
      inputBox.setCurrentNode( tool.transformNode )
      inputBox.setEnabled(False)
      outputBox = calibrationWidget.findChild(slicer.qMRMLNodeComboBox, "OutputComboBox")
      outputBox.setCurrentNode( tool.transformNodeTip )
      outputBox.setEnabled(False)
      doneButton = qt.QPushButton("Done")
      calibrationWidget.layout().addWidget(doneButton)
      calibrationDialog = qt.QDialog()
      calibrationDialog.setModal( False )
      calibrationDialog.setLayout( calibrationWidget.layout() )
      def doneFunction():
          calibrationDialog.accept()
          tool.updateModel()
      doneButton.clicked.connect( doneFunction )

      calibrateButton.clicked.connect( lambda : calibrationDialog.show() )
      
      statusLabel = qt.QLabel( " Tracking Off " )
      statusLabel.setStyleSheet("background-color: red;")
      toolLayout.addWidget( statusLabel )
      self.toolStatusLabels.append(statusLabel)

      toolWidget = qt.QWidget(self.parent )
      toolWidget.setLayout(toolLayout)
      toolsLayout.addWidget(toolWidget)
    self.layout.addWidget(self.toolsWidget)

    #Track slice view
    self.trackCameraWidget = qt.QWidget(self.parent)
    trackCameraLayout = qt.QHBoxLayout()
    self.trackCameraWidget.setLayout( trackCameraLayout )
    trackCameraLabel = qt.QLabel( "Align Slice Views to: ")
    trackCameraLayout.addWidget( trackCameraLabel)
    
    self.cameraTool = qt.QComboBox()
    self.cameraTool.addItem("None")
    for i in range(len(self.toolFiles)):
      toolname = "Tool_" + str(i)
      self.cameraTool.addItem(toolname)
    self.cameraTool.currentIndexChanged.connect( 
            lambda index: self.resetSliceViews() if index == 0 else None )
    trackCameraLayout.addWidget( self.cameraTool)
    self.layout.addWidget( self.trackCameraWidget )


    self.layout.addWidget(self.configurationFrame)

    #Tracking toogle button action
    def toggleTracking():
      for tool in self.tools:
        tool.isTracking = False
      if self.isTracking:
        self.tracker_timer.stop()
        self.isTracking = False
        self.tracker.stop_tracking()
        self.tracker.close()
        self.connectButton.setText("Start Tracking")
        return 
      
      try:
        #Tracker config 
        #TODO connect to tracker here 
        self.isTracking = True
        self.connectButton.setText("Stop Tracking")
        self.tracker_timer = qt.QTimer( self.layout )
        self.tracker_timer.timeout.connect( self.tracking ) 
        self.tracker_timer.start( self.poll.value() )
        self.updateStatus()
      except OSError as err:
        slicer.util.errorDisplay( str(err) ) 
      except Exception as err:
        slicer.util.errorDisplay( str(err) ) 

        
    self.connectButton.clicked.connect( toggleTracking )

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
    

#
# NDIVegaTrackerLogic
#

class TrackingLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """



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
