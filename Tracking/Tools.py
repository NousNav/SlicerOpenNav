import os
import qt
import slicer
import vtk
from slicer.ScriptedLoadableModule import *
import numpy as np

from TrackingDevices import NDIDevices
from TrackingDevices import PLUSOptiTrack
import TrackingDevices.Interface as TrackingInterface


class Tools(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Tools"
    self.parent.categories = [""]
    self.parent.dependencies = ["PivotCalibration"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """Module for handling tracked tools"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """...""" # replace with organization, grant and thanks.


class TrackedTool:

  def __init__(self, toolname, transformNode, transformNodeTip):
    self.tubeModel = None
    self.toolname = toolname
    self.observers = []
    self.transformNode = transformNode
    self.transformNodeTip = transformNodeTip

    # self.transformNodeTip.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent,
    #         self.updateModel)
    self.updateModel()

  def updateModel(self, transformNode=None, unusedArg2=None, unusedArg3=None):
    if self.tubeModel is not  None:
        slicer.mrmlScene.RemoveNode(self.tubeModel)

    points = vtk.vtkPoints()
    points.SetNumberOfPoints(2)
    points.SetPoint(0, 0, 0, 0)

    m = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToParent(m)
    points.SetPoint(1, m.GetElement(0,3), m.GetElement(1,3), m.GetElement(2,3))
    if m.GetElement(0,3) + m.GetElement(1,3) + m.GetElement(2,3) == 0:
      points.SetPoint(1,0,0,1)

    line = vtk.vtkCellArray()
    line.InsertNextCell(2)
    line.InsertCellPoint(0)
    line.InsertCellPoint(1)
    linesPolyData = vtk.vtkPolyData()
    linesPolyData.SetPoints(points)
    linesPolyData.SetLines(line)

    tubeSegmentFilter = vtk.vtkTubeFilter()
    tubeSegmentFilter.SetInputData(linesPolyData)
    tubeSegmentFilter.SetRadius(1)
    tubeSegmentFilter.SetNumberOfSides(30)
    tubeSegmentFilter.CappingOn()
    tubeSegmentFilter.Update()
    tubePolyData = tubeSegmentFilter.GetOutput()
    self.tubeModel = slicer.modules.models.logic().AddModel(tubePolyData)
    self.tubeModel.SetName(self.toolname)
    self.tubeModel.SetSaveWithScene(False)
    self.tubeModel.SetAndObserveTransformNodeID(self.transformNode.GetID())

    modelDisplay = self.tubeModel.GetDisplayNode()
    modelDisplay.SetColor(0.2,0.2,0.7)
    modelDisplay.SetDiffuse(0.90)
    modelDisplay.SetAmbient(0.10)
    modelDisplay.SetSpecular(0.20)
    modelDisplay.SetPower(10.0)
    modelDisplay.SetOpacity(1)
    modelDisplay.SetVisibility2D(True)
    modelDisplay.SetVisibility3D(True)
    modelDisplay.SetSliceIntersectionThickness(3)

  def getName(self):
    return self.toolname

  def getTipWorld(self):
    m = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToParent(m)
    tipLocal = np.array([m.GetElement(0,3), m.GetElement(1,3), m.GetElement(2,3)])
    tipWorld = np.empty(3)
    self.transformNodeTip.TransformPointToWorld(tipLocal, tipWorld)
    return tipWorld

  def getBaseWorld(self):
    baseLocal = np.zeros(3)
    baseWorld = np.empty(3)
    self.transformNodeTip.TransformPointToWorld(baseLocal, baseWorld)
    return baseWorld

  def getRotation(self):
    mat = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToWorld(mat)
    npmat = np.zeros( [3,3] )
    for i in range(3):
      for j in range(3):
        npmat[i,j] = mat.GetElement(i,j)

    return np.linalg.inv( npmat )

  def getTranslation(self):
    mat = vtk.vtkMatrix4x4()
    self.transformNodeTip.GetMatrixTransformToWorld(mat)
    npmat = np.zeros(3)
    for i in range(3):
      npmat[i] = mat.GetElement(i,3)
    return npmat


class ToolsWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = ToolsLogic()
    # Setup tracking device and create tools
    templatePath = self.resourcePath('OptiTrack/ReplayOptiTrack.xml.in')
    dataPath = self.resourcePath('OptiTrack/Ellipse.mha')
    toolsPath = os.path.dirname(slicer.modules.tools.path)
    toolsPath = os.path.join( toolsPath, "Resources/NDITools" )
    toolFiles = [os.path.join(toolsPath, f) for f in os.listdir(toolsPath)
                        if os.path.isfile(os.path.join(toolsPath, f))]

    tracker = slicer.util.settingsValue('NousNav/Tracker', 'OptiTrack')
    if tracker == 'OptiTrack':
      PLUSOptiTrack.setupPLUSOptiTrackTrackingDevice(templatePath, dataPath)
    else:
      NDIDevices.setupNDIVegaTrackingDevice(toolFiles)

    self.logic.setupTools()

  def updateStatus(self, transformNode, unusedArg2=None, unusedArg3=None):
    for i, statusLabel in enumerate( self.toolStatusLabels ):
      if TrackingInterface.isTracking(i):
        statusLabel.setText(" Tracking On ")
        statusLabel.setStyleSheet("background-color: green;")
      else:
        statusLabel.setText(" Tracking Off ")
        statusLabel.setStyleSheet("background-color: red;")

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Setup tool calibrations
    self.toolsWidget = qt.QWidget()
    toolsLayout = qt.QVBoxLayout(self.toolsWidget)
    self.toolCalibrateButtons = []
    self.toolStatusLabels = []
    for i in range(self.logic.getNumberOfTools()):
      tool = self.logic.getTool(i)
      tool.transformNode.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent,
              self.updateStatus)

      # Create tool widget with calibrate button and status
      toolLayout = qt.QHBoxLayout()
      toolLayout.addWidget(qt.QLabel(tool.toolname))
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

    # Compress the layout
    self.layout.addStretch(1)

  def enter(self):
    self.registerWidget.enter()


class ToolsLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  _tools = []

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)

  def setupTools(self):
    if len(ToolsLogic._tools) > 0:
      return

    ToolsLogic._tools = []
    for i in range(TrackingInterface.getNumberOfTools()):
      toolname = "Tool_%d" % i
      (tNode, tNodeTip)  = TrackingInterface.getTransformsForTool(i)
      tool = TrackedTool(toolname, tNode, tNodeTip)

      # Add to tracking to scene transform
      tool.transformNode.SetAndObserveTransformNodeID(
              TrackingInterface.getTrackingToSceneTransform().GetID())
      ToolsLogic._tools.append(tool)

  def getNumberOfTools(self):
    return len(ToolsLogic._tools)

  def getTool(self, idx):
    return ToolsLogic._tools[idx]
