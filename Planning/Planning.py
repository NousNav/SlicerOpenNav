import logging

import qt
import slicer
import vtk

import slicer.modules

from slicer.ScriptedLoadableModule import (
  ScriptedLoadableModule,
  ScriptedLoadableModuleWidget,
  ScriptedLoadableModuleLogic,
)
from slicer.util import VTKObservationMixin

import Home
import NNUtils

from LandmarkManager import (
  LandmarkManagerLogic,
  PlanningLandmarkTableManager,
)


class Planning(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NousNav Planning"
    self.parent.categories = [""]
    self.parent.dependencies = ["VolumeRendering", "SegmentEditor"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the Home module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class PlanningWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    super().__init__(parent)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Planning.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    # Create logic class
    self.logic = PlanningLogic()

    self.workflow = Home.Workflow(
      'planning',
      nested=(
        Home.Workflow('skin', setup=self.planningStep1, teardown=self.teardownPlanningStep1, widget=self.ui.PlanningStep1, validate=self.validate),
        Home.Workflow('target', setup=self.planningStep2, teardown=self.logic.resetDefaultNodeAppearance, widget=self.ui.PlanningStep2,
          validate=self.validateTargetSegmentation),
        Home.Workflow('trajectory', setup=self.planningStep3, teardown=self.logic.resetDefaultNodeAppearance, widget=self.ui.PlanningStep3,
          validate=self.validateTrajectorySegmentation),
        Home.Workflow('landmarks', setup=self.planningStep4, teardown=self.logic.resetDefaultNodeAppearance, widget=self.ui.PlanningStep4,
          validate=self.validateDefineLandmarks),
      ),
      setup=self.enter,
      teardown=self.exit,
      validate=self.validate
    )

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    # Planning Tab Bar
    self.planningTabBar = qt.QTabBar()
    self.planningTabBar.setObjectName("PlanningTabBar")
    NNUtils.addCssClass(self.planningTabBar, "secondary-tabbar")
    self.planningTabBar.visible = False
    secondaryTabWidget = slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryCenteredWidget')
    secondaryTabWidgetUI = slicer.util.childWidgetVariables(secondaryTabWidget)
    secondaryTabWidgetUI.CenterArea.layout().addWidget(self.planningTabBar)

    def addSecondaryTab(name, text):
      tabIndex = self.planningTabBar.addTab(text)
      self.planningTabBar.setTabData(tabIndex, name)

    addSecondaryTab("skin", "Segment the Skin")
    addSecondaryTab("target", "Segment the Target")
    addSecondaryTab("trajectory", "Plan the Trajectory")
    addSecondaryTab("landmarks", "Define Landmarks")

    # Bottom toolbar
    (
      self.bottomToolBar,
      self.backButton,
      self.backButtonAction,
      self.advanceButton,
      self.advanceButtonAction,
    ) = NNUtils.setupWorkflowToolBar("Planning")

    self.ui.skinThresholdSlider.setValue(30)
    self.ui.skinThresholdSlider.valueChanged.connect(self.updateSkinSegmentationPreview)
    self.ui.skinSmoothingSlider.setValue(3)
    self.ui.skinApply.clicked.connect(self.createSkinSegmentation)

    self.ui.targetPaintInside.clicked.connect(self.paintInside)
    self.ui.targetPaintOutside.clicked.connect(self.paintOutside)
    self.ui.targetErase.clicked.connect(self.eraseAll)
    self.ui.targetPreview.clicked.connect(self.previewTarget)
    self.ui.targetApply.clicked.connect(self.segmentTarget)

    self.ui.trajectoryEntry.clicked.connect(self.setTrajectoryEntry)
    self.ui.trajectoryTarget.clicked.connect(self.setTrajectoryTarget)

    header = self.ui.defineLandmarkTableWidget.horizontalHeader()
    header.setSectionResizeMode(header.Stretch)

    self.landmarkLogic = LandmarkManagerLogic()
    self.tableManager = PlanningLandmarkTableManager(
      self.landmarkLogic,
      self.ui.defineLandmarkTableWidget,
      {
        'NotStarted': qt.QIcon(self.resourcePath('Icons/NotStarted.svg')),
        'Done': qt.QIcon(self.resourcePath('Icons/Done.svg')),
      }
    )

    self.ui.savePlanButton.clicked.connect(NNUtils.savePlan)
  
  def exit(self):
    # Hide current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = False
    self.planningTabBar.visible = False

    self.logic.setPlanningNodesVisibility(skinModel=False, targetSegmentation=False, seedSegmentation=False, trajectory=False, landmarks=False)

  def validateTargetSegmentation(self):
    skin = self.logic.skin_segmentation
    if skin is None:
      return 'Please segment skin before proceeding'

    # check for 3d representation
    # poly = vtk.vtkPolyData()
    if not self.logic.skin_model:
      return 'Finalize skin segmentation before continuing'

  def validateTrajectorySegmentation(self):
    
    error = self.validateTargetSegmentation()
    if error:
      return error
    
    if not self.logic.target_segmentation:
      return 'Create target segmentation before continuing'

     # check for 3d representation
    poly = vtk.vtkPolyData()
    if not self.logic.target_segmentation.GetClosedSurfaceRepresentation(self.logic.SEED_INSIDE_SEGMENT, poly):
      return 'Finalize target segmentation before continuing'
  
  def validateDefineLandmarks(self):
    error = self.validateTrajectorySegmentation()
    if error:
      return error
    
    trajectory = self.logic.trajectory_markup
    if trajectory is None:
      return 'Define trajectory before continuing'
  
  def validate(self):
    volume = self.logic.master_volume
    if volume is None:
      return 'No master volume is set and no volume is active. Choose a master volume.'
  
  def enter(self):
    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True
    self.planningTabBar.visible = True

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    centralPanel = slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidget')
    for widget in [modulePanel ,sidePanel, centralPanel]:
      NNUtils.setCssClass(widget, "widget--color-light")
      NNUtils.polish(widget)

    # set slice viewer background
    volume = self.logic.master_volume
    if volume is None:
      slicer.util.errorDisplay(
        'No master volume is set and no volume is active. Choose a master volume.'
      )
      return

    slicer.util.setSliceViewerLayers(foreground=volume, background=None, label=None, fit=True)
    NNUtils.setSliceViewBackgroundColor('#000000')
    NNUtils.goToFourUpLayout(volumeNode=volume)

    # Set threshold slider extremes and default
    volumeDisplay = self.logic.master_volume.GetDisplayNode()
    min = volumeDisplay.GetWindowLevelMin()
    max = volumeDisplay.GetWindowLevelMax()
    window = volumeDisplay.GetWindow()
    self.ui.skinThresholdSlider.setMinimum( min - window )
    self.ui.skinThresholdSlider.setMaximum( max + window )
    self.ui.skinThresholdSlider.setValue( min + window / 10 )
    if self.landmarkLogic.landmarks:
      self.landmarkLogic.landmarks.SetDisplayVisibility(True)

  def disconnectAll(self, widget):
    try:
      widget.clicked.disconnect()
    except Exception:
      pass

  @NNUtils.backButton(text="Return to Patients")
  @NNUtils.advanceButton(text="Segment the Target")
  def planningStep1(self):

    self.tableManager.advanceButton = None
    
    self.logic.setPlanningNodesVisibility(skinModel=False, seedSegmentation=False, trajectory=False, landmarks=False)
    self.logic.setSkinSegmentForEditing()

    self.advanceButton.enabled = self.logic.master_volume is not None
    self.updateSkinSegmentationPreview()

  def teardownPlanningStep1(self):
    self.logic.endEffect()
    self.logic.resetDefaultNodeAppearance()

  @NNUtils.backButton(text="Segment the Skin")
  @NNUtils.advanceButton(text="Plan the Trajectory")
  def planningStep2(self):

    self.tableManager.advanceButton = None

    self.logic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=True, trajectory=False, landmarks=False)
    self.logic.skin_model.GetDisplayNode().SetOpacity(0.5)
    self.logic.setSkinSegmentFor3DDisplay()
    if self.logic.target_segmentation:
      self.logic.target_segmentation.GetDisplayNode().SetOpacity3D(1.)

  @NNUtils.backButton(text="Segment the Target")
  @NNUtils.advanceButton(text="Define Landmarks")
  def planningStep3(self):

    self.tableManager.advanceButton = None

    self.logic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=False, targetSegmentation=True, trajectory=True, landmarks=False)
    self.logic.skin_model.GetDisplayNode().SetOpacity(0.8)
    self.logic.skin_segmentation.GetDisplayNode().SetVisibility2D(False)
    self.logic.setSkinSegmentFor3DDisplay()
    self.logic.target_segmentation.GetDisplayNode().SetOpacity3D(0.3)

  @NNUtils.backButton(text="Plan the Trajectory")
  @NNUtils.advanceButton(text="")
  def planningStep4(self):

    self.landmarkLogic.setupPlanningLandmarksNode()
    self.tableManager.reconnect()
    self.tableManager.updateLandmarksDisplay()
    self.logic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=False, trajectory=False, landmarks=True)
    self.logic.setSkinSegmentFor3DDisplay()

    self.tableManager.advanceButton = self.advanceButton
   
  def updateSkinSegmentationPreview(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    self.logic.setupSkinSegmentationNode()

    segmentation = self.logic.skin_segmentation
    segment = self.logic.SKIN_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    # Only use a lower threshold and use the max value of volume as upper bound:
    self.logic.updateSkinSegmentationPreview(
      thresholdMin=self.ui.skinThresholdSlider.value,
      thresholdMax=self.logic.master_volume.GetImageData().GetScalarRange()[1]
    )

  def createSkinSegmentation(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    self.logic.setupSkinSegmentationNode()
    self.logic.setupSkinModelNode()

    segmentation = self.logic.skin_segmentation
    segment = self.logic.SKIN_SEGMENT

    messageBox = qt.QMessageBox(qt.QMessageBox.Information, "Computing", "Computing segmentation", qt.QMessageBox.NoButton)
    messageBox.setStandardButtons(0)
    messageBox.show()
    slicer.app.processEvents()
    messageBox.deleteLater()

    self.logic.setEditorTargets(volume, segmentation, segment)
    # Only use a lower threshold and use the max value of volume as upper bound:
    self.logic.applySkinSegmentation(
      thresholdMin=self.ui.skinThresholdSlider.value,
      thresholdMax=self.logic.master_volume.GetImageData().GetScalarRange()[1],
      smoothingSize=self.ui.skinSmoothingSlider.value,
    )
    self.logic.endEffect()

    # Make results visible in 3D and make model
    segmentation.CreateClosedSurfaceRepresentation()
    
    skinSegment = segmentation.GetSegmentation().GetSegment(segment)
    slicer.modules.segmentations.logic().ExportSegmentToRepresentationNode(skinSegment, self.logic.skin_model)
    self.logic.skin_model.GetDisplayNode().SetVisibility(True)
    self.logic.skin_model.GetDisplayNode().SetColor(177.0/255.0,122.0/255.0,101.0/255.0)
    
    NNUtils.centerCam()

    messageBox.hide()
  
  def eraseAll(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    self.logic.setupSeedSegmentationNode()
    self.logic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=True, trajectory=False, landmarks=False)

    segmentation = self.logic.seed_segmentation
    segment = self.logic.SEED_INSIDE_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.beginErase()
  
  def paintInside(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    self.logic.setupSeedSegmentationNode()
    self.logic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=True, trajectory=False, landmarks=False)

    segmentation = self.logic.seed_segmentation
    segment = self.logic.SEED_INSIDE_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.beginPaint()

  def paintOutside(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    self.logic.setupSeedSegmentationNode()
    self.logic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=True, trajectory=False, landmarks=False)

    segmentation = self.logic.seed_segmentation
    segment = self.logic.SEED_OUTSIDE_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.beginPaint()

  def previewTarget(self):
    self.logic.endEffect()
    self.logic.setupTargetSegmentationNode()
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return
    segmentation = self.logic.target_segmentation
    self.logic.copySeedSegmentsToTargetSegmentationNode()
    self.logic.setPlanningNodesVisibility(skinModel=True, targetSegmentation=True, trajectory=False, landmarks=False)

    self.logic.setEditorTargets(volume, segmentation)
    self.logic.previewTargetSegmentation()

  def segmentTarget(self):
    self.logic.applyTargetSegmentation()
    self.logic.endEffect()

    self.logic.setPlanningNodesVisibility(skinModel=True, targetSegmentation=True, trajectory=False, landmarks=False)
    segmentation = self.logic.target_segmentation
    segmentation.CreateClosedSurfaceRepresentation()

  def setTrajectoryEntry(self):
    self.logic.placeTrajectoryEntry()

  def setTrajectoryTarget(self):
    self.logic.placeTrajectoryTarget()

  
def default_master_volume():
  logging.warning('No master volume is set.')

  node_id = NNUtils.getActiveVolume()
  if not node_id:
    logging.warning('There is no active volume.')
    return None

  node = slicer.mrmlScene.GetNodeByID(node_id)
  logging.warning("Using active volume %r", node)
  return node


class PlanningLogic(ScriptedLoadableModuleLogic, VTKObservationMixin):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  master_volume = NNUtils.nodeReferenceProperty("MASTER_VOLUME", factory=default_master_volume)
  skin_segmentation = NNUtils.nodeReferenceProperty("SKIN_SEGMENTATION", default=None)
  seed_segmentation = NNUtils.nodeReferenceProperty("SEED_SEGMENTATION", default=None)
  target_segmentation = NNUtils.nodeReferenceProperty("TARGET_SEGMENTATION", default=None)
  trajectory_markup = NNUtils.nodeReferenceProperty("TRAJECTORY_MARKUP", default=None)
  trajectory_target_markup = NNUtils.nodeReferenceProperty("TRAJECTORY_TARGET", default=None)
  trajectory_entry_markup = NNUtils.nodeReferenceProperty("TRAJECTORY_ENTRY", default=None)
  skin_model = NNUtils.nodeReferenceProperty("SKIN_MODEL", default=None)

  current_step = NNUtils.parameterProperty("CURRENT_TAB")
  case_name = NNUtils.parameterProperty("CASE_NAME", default=None)

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    VTKObservationMixin.__init__(self)

    self.SKIN_SEGMENT = 'NN_SKIN'

    self.SEED_INSIDE_SEGMENT = 'NN_INSIDE'
    self.SEED_OUTSIDE_SEGMENT = 'NN_OUTSIDE'

    self.SMOOTHING_LEVEL_TARGET_SEGMENTATION = 5

    self.editor_widget = slicer.qMRMLSegmentEditorWidget()
    self.editor_widget.setMRMLScene(slicer.mrmlScene)
    # self.editor_widget.visible = True

    self.editor_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode')
    self.editor_widget.setMRMLSegmentEditorNode(self.editor_node)

    self.landmarkLogic = LandmarkManagerLogic()
  
  def removePatientImageData(self):
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    nodeItem = shNode.GetItemByDataNode(self.master_volume)
    studyItem = shNode.GetItemAncestorAtLevel(nodeItem, 'Study')
    patientItem = shNode.GetItemAncestorAtLevel(nodeItem, 'Patient')
    
    slicer.mrmlScene.RemoveNode(self.master_volume)
    if studyItem != 0:
      shNode.RemoveItem(studyItem)
    if patientItem != 0:
      shNode.RemoveItem(patientItem)
  
  def clearPlanningData(self):
    self.removePatientImageData()
    slicer.mrmlScene.RemoveNode(self.skin_segmentation)
    slicer.mrmlScene.RemoveNode(self.seed_segmentation)
    slicer.mrmlScene.RemoveNode(self.target_segmentation)
    slicer.mrmlScene.RemoveNode(self.trajectory_markup)
    slicer.mrmlScene.RemoveNode(self.trajectory_entry_markup)
    slicer.mrmlScene.RemoveNode(self.trajectory_target_markup)
    slicer.mrmlScene.RemoveNode(self.skin_model)
    self.case_name = None
     
  def setPlanningNodesVisibility(self, skinModel=False, seedSegmentation=False, targetSegmentation=False, trajectory=False, landmarks=False):
    if self.skin_segmentation:
      # Display 3D model instead of segmentation node:
      if self.skin_model:
        self.skin_model.GetDisplayNode().SetVisibility(skinModel)
        self.setSkinSegmentFor3DDisplay()
      
    if self.seed_segmentation:
      self.seed_segmentation.SetDisplayVisibility(seedSegmentation)
    if self.target_segmentation:
      self.target_segmentation.SetDisplayVisibility(targetSegmentation)
    if self.trajectory_markup:
      self.trajectory_markup.SetDisplayVisibility(trajectory)
    if self.trajectory_target_markup:
      self.trajectory_target_markup.SetDisplayVisibility(trajectory)
    if self.trajectory_entry_markup:
      self.trajectory_entry_markup.SetDisplayVisibility(trajectory)
    if self.landmarkLogic.landmarks:
      self.landmarkLogic.landmarks.SetDisplayVisibility(landmarks)

  def resetDefaultNodeAppearance(self):
    if self.skin_model:
      self.skin_model.GetDisplayNode().SetOpacity(1.)
    if self.target_segmentation:
      self.target_segmentation.GetDisplayNode().SetOpacity3D(1.)
      self.target_segmentation.GetDisplayNode().SetVisibility(False)

  def setupSkinModelNode(self):
    if not self.skin_model:
      node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLModelNode",
        "NN_SKIN_MODEL",
      )
      node.CreateDefaultDisplayNodes()
      node.GetDisplayNode().SetVisibility(False)
      self.skin_model = node

  def setupSkinSegmentationNode(self):
    if not self.skin_segmentation:
      node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode",
        "NN_SKIN_SEGMENTATION",
      )
      node.CreateDefaultDisplayNodes()
      segmentation = node.GetSegmentation()
      skin_segment = segmentation.GetSegment(segmentation.AddEmptySegment(
        "NN_SKIN",
        "NN_SKIN",
        [0.40, 0.35, 0.35],
      ))
      node.GetDisplayNode().SetSegmentOpacity3D(skin_segment.GetName(), 1.)
      self.skin_segmentation = node

  def setSkinSegmentForEditing(self):
    segment = self.skin_segmentation.GetSegmentation().GetSegment(self.SKIN_SEGMENT)
    segment.SetColor(0,1,0)
    self.skin_segmentation.SetDisplayVisibility(True)
    self.skin_segmentation.GetDisplayNode().SetVisibility2D(True)
    self.skin_segmentation.GetDisplayNode().SetVisibility3D(False)

  def setSkinSegmentFor3DDisplay(self):
    self.skin_segmentation.SetDisplayVisibility(False)
    self.skin_segmentation.GetDisplayNode().SetVisibility2D(False)
    self.skin_segmentation.GetDisplayNode().SetVisibility3D(False)

  def setupSeedSegmentationNode(self):
    if not self.seed_segmentation:
      node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode",
        "NN_SEED_SEGMENTATION",
      )
      node.CreateDefaultDisplayNodes()
      segmentation = node.GetSegmentation()
      inside_segment = segmentation.GetSegment(segmentation.AddEmptySegment(  # noqa: F841
        "NN_INSIDE",
        "NN_INSIDE",
        [0.10, 0.90, 0.10],
      ))
      outside_segment = segmentation.GetSegment(segmentation.AddEmptySegment(  # noqa: F841
        "NN_OUTSIDE",
        "NN_OUTSIDE",
        [0.90, 0.10, 0.10],
      ))

      node.GetDisplayNode().SetOpacity2DFill(0.2)
      node.GetDisplayNode().SetOpacity2DOutline(0.5)
      node.GetDisplayNode().SetSliceIntersectionThickness(1)
      self.seed_segmentation = node

  def setupTargetSegmentationNode(self):
    if not self.target_segmentation:
      node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode",
        "NN_TARGET_SEGMENTATION",
      )
      node.CreateDefaultDisplayNodes()
      self.target_segmentation = node
      node.GetDisplayNode().SetVisibility2DFill(False)
      node.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, False)
      node.GetDisplayNode().SetSliceIntersectionThickness(1)
  
  def copySeedSegmentsToTargetSegmentationNode(self):
    targetSegmentation = self.target_segmentation.GetSegmentation()
    seedSegmentation = self.seed_segmentation.GetSegmentation()
    targetSegmentation.RemoveAllSegments()
    targetSegmentation.CopySegmentFromSegmentation(seedSegmentation, self.SEED_INSIDE_SEGMENT)
    targetSegmentation.CopySegmentFromSegmentation(seedSegmentation, self.SEED_OUTSIDE_SEGMENT)

  def setupTrajectoryMarkupNodes(self):
    if not self.trajectory_markup:
      node = slicer.mrmlScene.AddNewNodeByClass(
        'vtkMRMLMarkupsLineNode',
        'NN_TRAJECTORY',
      )
      node.CreateDefaultDisplayNodes()
      display = node.GetDisplayNode()
      display.SetPropertiesLabelVisibility(False)
      display.SetLineDiameter(3)  # mm
      display.SetUseGlyphScale(False)
      display.SetGlyphSize(4)  # 4mm
      display.SetCurveLineSizeMode(display.UseLineDiameter)
      node.AddControlPointWorld(vtk.vtkVector3d())
      node.AddControlPointWorld(vtk.vtkVector3d())
      node.SetLocked(True)
      display.SetVisibility(False)
      self.trajectory_markup = node

    if not self.trajectory_target_markup:
      node = slicer.mrmlScene.AddNewNodeByClass(
        'vtkMRMLMarkupsFiducialNode',
        'NN_TRAJECTORY_TARGET',
      )
      display = node.GetDisplayNode()
      display.SetPointLabelsVisibility(False)
      display.SetUseGlyphScale(False)
      display.SetGlyphSize(4)  # 4mm
      display.SetSelectedColor(0.0, 0.9, 0.0)  # green
      display.SetActiveColor(0.4, 1.0, 0.4)  # hover: pale green
      self.trajectory_target_markup = node

    if not self.trajectory_entry_markup:
      node = slicer.mrmlScene.AddNewNodeByClass(
        'vtkMRMLMarkupsFiducialNode',
        'NN_TRAJECTORY_ENTRY',
      )
      display = node.GetDisplayNode()
      display.SetPointLabelsVisibility(False)
      display.SetUseGlyphScale(False)
      display.SetGlyphSize(4)  # 4mm
      display.SetSelectedColor(0.8, 0.4, 0.4)  # skin color; brighter, saturated
      display.SetActiveColor(1.0, 0.7, 0.7)  # hover: paler selected color
      self.trajectory_entry_markup = node

    self.reconnect()

  def reconnect(self):
    self.endEffect()
    self.removeObservers()

    for event in [
      slicer.vtkMRMLMarkupsNode.PointAddedEvent,
      slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
      slicer.vtkMRMLMarkupsNode.PointRemovedEvent,
    ]:
      if self.trajectory_target_markup:
        self.addObserver(self.trajectory_target_markup, event, self.updateTrajectory)
      if self.trajectory_entry_markup:
        self.addObserver(self.trajectory_entry_markup, event, self.updateTrajectory)

  def setEditorTargets(self, volume, segmentation, segmentID=''):
    """Set the persistent segment editor to edit the given volume and segmentation.
    If segmentID is provided, also select that segment in the editor.
    """
    # make sure the active segmentation uses the active volume
    segmentation.SetReferenceImageGeometryParameterFromVolumeNode(volume)

    self.editor_node.SetAndObserveSourceVolumeNode(volume)
    self.editor_node.SetAndObserveSegmentationNode(segmentation)

    if segmentID:
      self.editor_widget.setCurrentSegmentID(segmentID)

  def isEffectActive(self):
    effect = self.editor_widget.activeEffect()
    if effect is None:
      return False
    else:
      return True
  
  def updateSkinSegmentationPreview(self, thresholdMin=30,thresholdMax=1000):

    """ Update the preview of skin segmentation effects. Be sure to use setEditorTargets
     beforehand, so the effect is applied correctly.

    Effects: Threshold
    """

    # Thresholding
    effect = self.editor_widget.activeEffect()
    if effect is None:
      self.editor_widget.setActiveEffectByName("Threshold")
      effect = self.editor_widget.activeEffect()
      
    effect.setParameter("MinimumThreshold", thresholdMin)
    effect.setParameter("MaximumThreshold", thresholdMax)
    effect.self().onApply()
  
  def applySkinSegmentation(
      self,
      thresholdMin=30,
      thresholdMax=1000,
      smoothingSize=3,
  ):
    """ Apply skin segmentation effects. Be sure to use setEditorTargets
     beforehand, so the effect is applied correctly.

    Effects: Threshold, close morphologically, remove islands, remove voids, smoothing
    """
    # Thresholding
    self.editor_widget.setActiveEffectByName("Threshold")
    effect = self.editor_widget.activeEffect()
    effect.setParameter("MinimumThreshold", thresholdMin)
    effect.setParameter("MaximumThreshold", thresholdMax)
    effect.self().onApply()

    # Remove islands
    # Find largest component
    self.editor_widget.setActiveEffectByName("Islands")
    effect = self.editor_widget.activeEffect()
    effect.setParameterDefault("Operation", "KEEP_LARGEST_ISLAND")
    effect.self().onApply()

    # Morphological closure
    self.editor_widget.setActiveEffectByName("Smoothing")
    effect = self.editor_widget.activeEffect()
    effect.setParameter('SmoothingMethod', 'CLOSING')
    effect.setParameter('KernelSizeMm', 5)
    effect.self().onApply()

    # Remove voids
    self.editor_widget.setActiveEffectByName("Logical operators")
    effect = self.editor_widget.activeEffect()
    effect.setParameter("Operation", "INVERT")
    effect.self().onApply()

    self.editor_widget.setActiveEffectByName("Islands")
    effect = self.editor_widget.activeEffect()
    effect.setParameterDefault("Operation", "KEEP_LARGEST_ISLAND")
    effect.self().onApply()

    self.editor_widget.setActiveEffectByName("Logical operators")
    effect = self.editor_widget.activeEffect()
    effect.setParameter("Operation", "INVERT")
    effect.self().onApply()

    # Smooth
    if smoothingSize > 0 :
      self.editor_widget.setActiveEffectByName("Smoothing")
      effect = self.editor_widget.activeEffect()
      effect.setParameter('SmoothingMethod', 'MEDIAN')
      effect.setParameter('KernelSizeMm', smoothingSize)
      effect.self().onApply()

    self.endEffect()

  def previewTargetSegmentation(self):
    """ Preview target segmentation effects. Be sure to use setEditorTargets
     beforehand, so the effect is applied correctly.

    Effects: Grow from seeds
    """
    messageBox = qt.QMessageBox(qt.QMessageBox.Information, "Computing", "Computing segmentation", qt.QMessageBox.NoButton)
    messageBox.setStandardButtons(0)
    messageBox.show()
    slicer.app.processEvents()
    messageBox.deleteLater()

    self.editor_widget.setActiveEffectByName('Grow from seeds')
    effect = self.editor_widget.activeEffect()
    # Make sure both segments are visible
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, True)
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility3D(self.SEED_OUTSIDE_SEGMENT, False)

    effect.setParameter('AutoUpdate', 0)
    effect.self().onPreview()

    # Rehide target segments:
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, False)
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, False)

    # Set preview style:
    previewDisplayNode = slicer.util.getNode(self.target_segmentation.GetName()+" preview").GetDisplayNode()
    previewDisplayNode.SetVisibility2DOutline(True)
    previewDisplayNode.SetVisibility2DFill(False)
    previewDisplayNode.SetOpacity2DOutline(1.)
    previewDisplayNode.SetSliceIntersectionThickness(1)
    previewDisplayNode.SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    previewDisplayNode.SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, False)

    messageBox.hide()

  def applyTargetSegmentation(self):
    """ Preview target segmentation effects. Be sure to use setEditorTargets
     beforehand, so the effect is applied correctly.

    Effects: Grow from seeds, Smoothing
    """
    messageBox = qt.QMessageBox(qt.QMessageBox.Information, "Finalizing", "Finalizing segmentation", qt.QMessageBox.NoButton)
    messageBox.setStandardButtons(0)
    messageBox.show()
    slicer.app.processEvents()
    messageBox.deleteLater()

    self.editor_widget.setActiveEffectByName('Grow from seeds')
    effect = self.editor_widget.activeEffect()
    if effect.self().getPreviewNode() is None:
      return
    effect.self().onApply()

    # Make sure both segments are visible
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, True)
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility3D(self.SEED_OUTSIDE_SEGMENT, False)

    self.editor_widget.setActiveEffectByName("Smoothing")
    effect = self.editor_widget.activeEffect()
    effect.setParameter('SmoothingMethod', 'MEDIAN')
    effect.setParameter('KernelSizeMm', self.SMOOTHING_LEVEL_TARGET_SEGMENTATION)
    effect.self().onApply()

    # Rehide outside segment
    self.target_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, False)

    messageBox.hide()

  def beginPaint(self):
    """ Begin a paint effect. Be sure to use setEditorTargets beforehand, so
     the effect is applied correctly.
    """

    # Make both segments visible when painting
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility3D(self.SEED_OUTSIDE_SEGMENT, False)

    self.editor_widget.setActiveEffectByName('Paint')
    paint = self.editor_widget.effectByName("Paint")
    paint.setCommonParameter("BrushRelativeDiameter", 1.5)
    # paint effect does not need onApply().

  def beginErase(self):
    print('Erase')
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility3D(self.SEED_OUTSIDE_SEGMENT, False)
    self.editor_widget.setActiveEffectByName('Erase')
    erase = self.editor_widget.effectByName("Erase")
    erase.setCommonParameter("BrushRelativeDiameter", 1.5)
    erase.setParameter("EraseAllSegments", 1)

  def endEffect(self):
    """ End the active effect, returning mouse control to normal.
    """
    self.editor_widget.setActiveEffectByName('None')

  def placeTrajectoryEntry(self):
    self.setupTrajectoryMarkupNodes()

    markup = self.trajectory_entry_markup
    markup.RemoveAllControlPoints()

    selection_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSelectionNodeSingleton')
    interaction_node = slicer.mrmlScene.GetNodeByID('vtkMRMLInteractionNodeSingleton')

    selection_node.SetActivePlaceNodeID(markup.GetID())
    selection_node.SetActivePlaceNodeClassName(markup.GetClassName())
    interaction_node.SetCurrentInteractionMode(interaction_node.Place)

  def placeTrajectoryTarget(self):
    self.setupTrajectoryMarkupNodes()

    markup = self.trajectory_target_markup
    markup.RemoveAllControlPoints()

    selection_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSelectionNodeSingleton')
    interaction_node = slicer.mrmlScene.GetNodeByID('vtkMRMLInteractionNodeSingleton')

    selection_node.SetActivePlaceNodeID(markup.GetID())
    selection_node.SetActivePlaceNodeClassName(markup.GetClassName())
    interaction_node.SetCurrentInteractionMode(interaction_node.Place)

  def updateTrajectory(self, o, e):
    line = self.trajectory_markup

    entry = self.trajectory_entry_markup
    target = self.trajectory_target_markup

    entry_exists = entry.GetNumberOfControlPoints() > 0
    target_exists = target.GetNumberOfControlPoints() > 0
    enabled = entry_exists and target_exists

    line.GetDisplayNode().SetVisibility(enabled)
    if enabled:
      line.SetNthControlPointPosition(
        0,
        entry.GetNthControlPointPositionVector(0)[0],
        entry.GetNthControlPointPositionVector(0)[1],
        entry.GetNthControlPointPositionVector(0)[2]
      )
      line.SetNthControlPointPosition(
        1,
        target.GetNthControlPointPositionVector(0)[0],
        target.GetNthControlPointPositionVector(0)[1],
        target.GetNthControlPointPositionVector(0)[2],
      )
