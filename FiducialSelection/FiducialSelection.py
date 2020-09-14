import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap
import numpy as np
import NNUtils
import TrackingDevices.Interface as TrackingInterface


class FiducialSelection(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Fiducial Selection"
    self.parent.categories = [""]
    self.parent.dependencies = []
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """This is the FiducialSelection module for the NousNav application"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """...""" # replace with organization, grant and thanks.


class FiducialSelectionWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.statusLessThanThreePoints = "Less than three fiducials pairs"
    self.statusTransformUpdated = "Transform updated. Average mismatch: "
    self.statusNumberOfPointsUnequal = "Unequal number of Fiducials"
    self.statusToolNotTracked = "Tool not tracked for placement"
    self.observerToTags = []
    self.currentTo = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    resourcePath = os.path.dirname(slicer.modules.fiducialselection.path)
    trashIconPath = os.path.join(resourcePath, "Resources/Icons/trash.png")
    pixmap = qt.QPixmap(trashIconPath)
    self.trashIcon = qt.QIcon(pixmap)

    # Create logic class
    self.logic = FiducialSelectionLogic()
    self.setupRegistrationWidget()


  def createItem(self, text, row, col):
    item = qt.QTableWidgetItem()
    layout = qt.QHBoxLayout()
    layout

  def fiducialsToPoints( self, n):
    points = vtk.vtkPoints()
    for i in range(0, n.GetNumberOfFiducials()):
      point = [0,0,0]
      n.GetMarkupPoint(i,0,point)
      points.InsertNextPoint(point[0], point[1], point[2])
    return points


  def updateTransform(self):
    nfrom = self.FromNode.GetNumberOfFiducials()
    nto = 0
    if self.currentTo != None:
      nto = self.currentTo.GetNumberOfFiducials()
    if nto != nfrom:
      self.statusLabel.setText( self.statusNumberOfPointsUnequal )
      return
    if nto < 3:
      self.statusLabel.setText( self.statusLessThanThreePoints )
      return

    transform = vtk.vtkLandmarkTransform();

    fromPoints = self.fiducialsToPoints(self.FromNode)
    toPoints = self.fiducialsToPoints(self.currentTo)
    transform.SetSourceLandmarks( fromPoints );
    transform.SetTargetLandmarks( toPoints );
    transform.SetModeToRigidBody();
    transform.Update()

    fromPointsTf = vtk.vtkPoints()
    transform.TransformPoints(fromPoints, fromPointsTf)
    rmse = 0
    for i in range(fromPoints.GetNumberOfPoints()):
      p1 = toPoints.GetPoint(i)
      p2 = fromPointsTf.GetPoint(i)
      rmse = [(x - y)**2 for x,y in zip(p1,p2)]
      rmse = np.mean( rmse )
      rmse = np.sqrt( rmse )
    self.statusLabel.setText( self.statusTransformUpdated + str(rmse) )
    node = TrackingInterface.getTrackingToSceneTransform()
    node.SetMatrixTransformToParent( transform.GetMatrix() )
    NNUtils.centerOnActiveVolume()

  def onNumberOfPointsChanged(self, caller, event):
    # Update table
    nfrom = self.FromNode.GetNumberOfFiducials()
    nto = 0
    if self.currentTo != None:
      nto = self.currentTo.GetNumberOfFiducials()
    nrows = max( nfrom, nto )
    self.table.clear()
    self.table.setRowCount(nrows)
    for i in range(nfrom):
      self.table.setItem( i, 2, qt.QTableWidgetItem( self.FromNode.GetNthFiducialLabel(i) ) )
    for i in range(nto):
      self.table.setItem( i, 0, qt.QTableWidgetItem( self.currentTo.GetNthFiducialLabel(i) ) )

    def removeFrom( row ):
      nfrom = self.FromNode.GetNumberOfFiducials()
      if nfrom > row:
        self.FromNode.RemoveNthControlPoint(row)
    def removeTo( row ):
      nto = 0
      if self.currentTo != None:
        nto = self.currentTo.GetNumberOfFiducials();
      if nto > row:
        self.currentTo.RemoveNthControlPoint(row)

    def addButtonWidget(row, col):
      pWidget = qt.QWidget();
      btn_edit = qt.QPushButton();
      btn_edit.setIcon(self.trashIcon);
      btn_edit.setIconSize( qt.QSize(16,16) );
      pLayout = qt.QHBoxLayout(pWidget);
      pLayout.addWidget(btn_edit);
      pLayout.setAlignment(qt.Qt.AlignCenter);
      pLayout.setContentsMargins(0, 0, 0, 0);
      pWidget.setLayout(pLayout);
      self.table.setCellWidget(row, col, pWidget);
      return btn_edit

    for i in range(nrows):
      fromButton = addButtonWidget(i, 3)
      fromButton.clicked.connect( (lambda row: lambda : removeFrom(row) )(i) )
      toButton = addButtonWidget(i, 1)
      toButton.clicked.connect( (lambda row: lambda : removeTo(row) )(i) )

    self.updateTransform()

  def onPointsChanged(self, caller, event):
    self.updateTransform()

  def changeCurrentVolume(self, node):
    fTo = self.logic.getFiducialToNode( node )
    self.changeActiveFiducialNode( fTo)

  def changeActiveFiducialNode(self, node):
    # Remove observers from current active fiducial node
    if self.currentTo is not None:
      if node is not None:
        if self.currentTo.GetID() == node.GetID():
          return
      self.currentTo.GetDisplayNode().VisibilityOff()
      for tag in self.observerToTags:
        self.currentTo.RemoveObserver( tag )

    self.currentTo = node
    if self.currentTo is None:
      return
    #Add observers to new fiducial node
    self.observerToTags.clear()
    self.observerToTags.append(
      self.currentTo.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent,
          self.onNumberOfPointsChanged) )
    self.observerToTags.append(
      self.currentTo.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent,
          self.onNumberOfPointsChanged) )
    self.observerToTags.append(
      self.currentTo.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
          self.onPointsChanged) )

    self.currentTo.GetDisplayNode().VisibilityOn()
    selectionNode = slicer.app.applicationLogic().GetSelectionNode()
    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
    selectionNode.SetActivePlaceNodeID( self.currentTo.GetID() )

  def setupRegistrationWidget(self):
    node = TrackingInterface.getTrackingToSceneTransform()
    FromName = "TrackerFiducial"
    nodes = slicer.mrmlScene.GetNodesByName(FromName)
    if nodes.GetNumberOfItems() > 0:
      self.FromNode = nodes.GetItemAsObject(0)
    else:
      self.FromNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
      self.FromNode.SetName(FromName)
      self.FromNode.CreateDefaultDisplayNodes()
      self.FromNode.GetMarkupsDisplayNode().SetSelectedColor(0.94, 0.29, 0.06)
      self.FromNode.GetMarkupsDisplayNode().VisibilityOff()
      self.FromNode.SetSingletonTag("FiducialSelection_" + FromName)
      self.FromNode.GetDisplayNode().VisibilityOn()
      self.FromNode.SetSaveWithScene( False )

      self.FromNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointAddedEvent,
            self.onNumberOfPointsChanged)
      self.FromNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointRemovedEvent,
            self.onNumberOfPointsChanged)
      self.FromNode.AddObserver(slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
            self.onPointsChanged)

    volumeWidget = qt.QWidget(self.parent)
    volumeLayout = qt.QHBoxLayout()
    volumeLayout.addWidget( qt.QLabel("Master Volume") )
    self.volumeComboBox = slicer.qMRMLNodeComboBox()
    self.volumeComboBox.setMRMLScene( slicer.mrmlScene )
    self.volumeComboBox.addEnabled = False
    self.volumeComboBox.removeEnabled = False
    self.volumeComboBox.noneEnabled = True
    self.volumeComboBox.nodeTypes =  [ "vtkMRMLScalarVolumeNode" ]
    self.volumeComboBox.currentNodeChanged.connect( self.changeCurrentVolume )
    volumeLayout.addWidget( self.volumeComboBox )
    volumeWidget.setLayout( volumeLayout )
    self.layout.addWidget( volumeWidget )

    # Fiducial table
    self.table = qt.QTableWidget()
    self.table.setColumnCount(4)
    self.table.setRowCount(0)
    self.table.setHorizontalHeaderLabels(["Scene", "", "Tracker", ""])
    self.table.setSizePolicy( qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)

    header = self.table.horizontalHeader();
    header.setSectionResizeMode(0, qt.QHeaderView.Stretch)
    header.setSectionResizeMode(1, qt.QHeaderView.ResizeToContents)
    header.setSectionResizeMode(2, qt.QHeaderView.Stretch)
    header.setSectionResizeMode(3, qt.QHeaderView.ResizeToContents)


    #Add fiducials buttons
    buttonLayout = qt.QHBoxLayout()
    self.sceneButton = qt.QPushButton("Start Place in Scene")
    self.sceneButton.setCheckable(True)
    def setPlaceMode(checked):
      if(checked):
        self.sceneButton.setText("Stop Place in Scene")
        selectionNode = slicer.app.applicationLogic().GetSelectionNode()
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        if self.currentTo is not None:
           selectionNode.SetActivePlaceNodeID(self.currentTo.GetID())
        placeModePersistence = 1
        interactionNode = slicer.app.applicationLogic().GetInteractionNode()
        interactionNode.SetPlaceModePersistence(placeModePersistence)
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
      else:
        self.sceneButton.setText("Start Place in Scene")
        interactionNode = slicer.app.applicationLogic().GetInteractionNode()
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
    self.sceneButton.toggled.connect( setPlaceMode )
    buttonLayout.addWidget( self.sceneButton )

    self.trackerButton = qt.QPushButton("Place from Tool: ")
    buttonLayout.addWidget( self.trackerButton )

    self.tools = qt.QComboBox()
    for toolIndex in range( TrackingInterface.getNumberOfTools() ):
      toolname = "Tool_" + str(toolIndex)
      self.tools.addItem(toolname)
    buttonLayout.addWidget( self.tools )

    def placeFromTool():
        (tNodeBase, tNodeTip) =  TrackingInterface.getTransformsForTool( self.tools.currentIndex )
        m = vtk.vtkMatrix4x4()
        tNodeTip.GetMatrixTransformToWorld(m)
        x1 = m.GetElement(0,3)
        x2 = m.GetElement(1,3)
        x3 = m.GetElement(2,3)
        if not np.isnan( x1+x2+x3):
          self.FromNode.AddFiducial(x1, x2, x3)
        else:
          self.statusLabel.setText( self.statusToolNotTracked )
    self.trackerButton.clicked.connect( placeFromTool )


    self.fiducialWidget = qt.QWidget(self.parent)
    self.fiducialWidget.setLayout( buttonLayout )
    self.layout.addWidget( self.fiducialWidget )

    # Add table below buttons
    self.layout.addWidget( self.table )

    self.fiducialsVisibilityButton = qt.QPushButton("Hide Fiducials")
    self.fiducialsVisibilityButton.setCheckable(True)
    def toggleVisibility(checked):
      if checked:
        self.FromNode.GetDisplayNode().VisibilityOff()
        if self.currentTo != None:
          self.currentTo.GetDisplayNode().VisibilityOff()
        self.fiducialsVisibilityButton.setText("Show Fiducials")
      else:
        self.FromNode.GetDisplayNode().VisibilityOn()
        if self.currentTo != None:
          self.currentTo.GetDisplayNode().VisibilityOn()
        elf.fiducialsVisibilityButton.setText("Hide Fiducials")
    self.fiducialsVisibilityButton.toggled.connect(toggleVisibility)
    self.layout.addWidget( self.fiducialsVisibilityButton )

    #Status message
    self.statusLabel = qt.QLabel(self.statusLessThanThreePoints)
    self.layout.addWidget( qt.QLabel("Fiducial registration status:" ) )
    self.layout.addWidget( self.statusLabel )

    # compress the layout
    self.layout.addStretch(1)

  def onClose(self, unusedOne, unusedTwo):
    pass

  def cleanup(self):
    pass

  def enter(self):
    nodeID = NNUtils.getActiveVolume()
    self.volumeComboBox.setCurrentNodeID( nodeID )


class FiducialSelectionLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)

  def getFiducialToNode(self, node):
    if node is None:
      return None
    # Add observers
    fiducialNodeID = node.GetNodeReferenceID("Fiducials")
    fiducialNode = None
    if fiducialNodeID is None:
      fiducialNode = slicer.mrmlScene.AddNewNodeByClass( 'vtkMRMLMarkupsFiducialNode' )
      fiducialNode.SetName( node.GetName() + "_Fiducials" )
      fiducialNode.CreateDefaultDisplayNodes()
      fiducialNode.GetMarkupsDisplayNode().SetSelectedColor(0.06, 0.69, 0.95)
      fiducialNode.GetMarkupsDisplayNode().VisibilityOff()
      node.SetAndObserveNodeReferenceID("Fiducials", fiducialNode.GetID() )
    else:
      fiducialNode = slicer.mrmlScene.GetNodeByID( fiducialNodeID )
    return fiducialNode


class FiducialSelectionTest(ScriptedLoadableModuleTest):
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
    self.test_FiducialSelection1()

  def test_FiducialSelection1(self):
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

    logic = FiducialSelectionLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class FiducialSelectionFileWriter(object):
  def __init__(self, parent):
    pass
