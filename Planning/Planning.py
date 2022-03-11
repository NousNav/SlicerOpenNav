import qt
import slicer
from slicer.ScriptedLoadableModule import *
import slicer.modules
import logging
import NNUtils

from LandmarkManager import PlanningLandmarkTableManager, LandmarkManagerLogic


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
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def nextPlanningStep(self):
    self.ui.PlanningWidget.setCurrentIndex( self.ui.PlanningWidget.currentIndex + 1)

  def previousPlanningStep(self):
    self.ui.PlanningWidget.setCurrentIndex( self.ui.PlanningWidget.currentIndex - 1)

  def createNextPlanningButton(self):
    btn = qt.QPushButton("Next Step")
    btn.clicked.connect(self.nextPlanningStep)
    return btn

  def createPreviousPlanningButton(self):
    btn = qt.QPushButton("Previous Step")
    btn.clicked.connect(self.previousPlanningStep)
    return btn

  def createPlanningStepWidget(self, prevOn, nextOn):
     w = qt.QWidget()
     l = qt.QGridLayout()
     w.setLayout(l)
     if prevOn:
       l.addWidget(self.createPreviousPlanningButton(), 0, 0 )
     if nextOn:
       l.addWidget(self.createNextPlanningButton(), 0, 1 )
     return w

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Planning.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    # Create logic class
    self.logic = PlanningLogic()

    # Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    # Planning Tab Bar
    self.planningTabBar = qt.QTabBar()
    self.planningTabBar.setObjectName("PlanningTabBar")
    self.planningTabBar.visible = False
    secondaryTabWidget = slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryCenteredWidget')
    secondaryTabWidgetUI = slicer.util.childWidgetVariables(secondaryTabWidget)
    secondaryTabWidgetUI.CenterArea.layout().addWidget(self.planningTabBar)

    self.segmentSkinTabIndex = self.planningTabBar.addTab("Segment the Skin")
    self.segmentTargetTabIndex = self.planningTabBar.addTab("Segment the Target")
    self.trajectoryTabIndex = self.planningTabBar.addTab("Plan the Trajectory")
    self.landmarksTabIndex = self.planningTabBar.addTab("Define Landmarks")

    self.planningTabBar.currentChanged.connect(self.onTabChanged)

    # Bottom toolbar
    (
      self.bottomToolBar,
      self.backButtonPlan,
      self.backButtonAction,
      self.advanceButtonPlan,
      self.advanceButtonAction,
    ) = NNUtils.setupWorkflowToolBar("Planning")

    # Stacked widgets navigation changes
    self.CurrentPlanningIndex = -1
    self.ui.PlanningWidget.currentChanged.connect(self.onPlanningChanged)

    self.ui.skinThresholdSlider.setValue(30)
    self.ui.skinSmoothingSlider.setValue(3)
    self.ui.skinApply.clicked.connect(self.createSkinSegmentation)

    self.ui.targetPaintInside.clicked.connect(self.paintInside)
    self.ui.targetPaintOutside.clicked.connect(self.paintOutside)
    self.ui.targetPreview.clicked.connect(self.previewTarget)
    self.ui.targetApply.clicked.connect(self.segmentTarget)

    self.ui.trajectoryPlace.clicked.connect(self.setTrajectory)

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

  def exit(self):
    self.logic.skin_segmentation.SetDisplayVisibility(False)
    self.logic.seed_segmentation.SetDisplayVisibility(False)
    self.logic.trajectory_markup.SetDisplayVisibility(False)
    try:
      self.landmarkLogic.landmarks.SetDisplayVisibility(False)
    except:
      pass

  def enter(self):
    # Hide other toolbars
    slicer.util.findChild(slicer.util.mainWindow(), 'PatientsBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'NavigationBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationTabBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationBottomToolBar').visible = False

    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True
    self.planningTabBar.visible = True

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    NNUtils.applyStyle([sidePanel, modulePanel], self.resourcePath("PanelLight.qss"))

    self.planningTabBar.setCurrentIndex(self.segmentSkinTabIndex)
    self.onTabChanged(self.segmentSkinTabIndex)
    
    # set slice viewer background
    volume = self.logic.master_volume
    if volume is None:
      slicer.util.errorDisplay(
        'No master volume is set and no volume is active. Choose a master volume.'
      )
      return

    slicer.util.setSliceViewerLayers(foreground=volume, background=None, label=None, fit=True)
    NNUtils.setSliceViewBackgroundColor('#000000')
    self.goToFourUpLayout()

    # Set threshold slider extremes and default
    volumeDisplay = self.logic.master_volume.GetDisplayNode()
    min = volumeDisplay.GetWindowLevelMin()
    max = volumeDisplay.GetWindowLevelMax()
    window = volumeDisplay.GetWindow()
    self.ui.skinThresholdSlider.setMinimum( min - window )
    self.ui.skinThresholdSlider.setMaximum( max + window )
    self.ui.skinThresholdSlider.setValue( min + window / 10 )

    self.landmarkLogic.landmarks.SetDisplayVisibility(True)

  def onTabChanged(self, index):
    self.tableManager.advanceButton = None

    if index == self.segmentSkinTabIndex:
      self.planningStep1()

    if index == self.segmentTargetTabIndex:
      self.planningStep2()

    if index == self.trajectoryTabIndex:
      self.planningStep3()

    if index == self.landmarksTabIndex:
      self.planningStep4()

  def goToFourUpLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    NNUtils.setSliceWidgetSlidersVisible(True)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(False)

  def disconnectAll(self, widget):
    try:
      widget.clicked.disconnect()
    except Exception:
      pass

  def planningStep1(self):
    self.disconnectAll(self.advanceButtonPlan)
    self.disconnectAll(self.backButtonPlan)

    self.backButtonAction.visible = True
    self.backButtonPlan.text = 'Return to Patients'
    self.backButtonPlan.clicked.connect(lambda: self.openPreviousModule())

    self.advanceButtonAction.visible = True
    self.advanceButtonPlan.text = 'Segment the Target'
    self.advanceButtonPlan.clicked.connect(lambda: self.planningTabBar.setCurrentIndex(self.segmentTargetTabIndex))
    self.logic.skin_segmentation.SetDisplayVisibility(True)
    self.ui.PlanningWidget.setCurrentWidget(self.ui.PlanningStep1)

    volume = self.logic.master_volume
    if volume is None:
      self.advanceButtonPlan.enabled = False

  def planningStep2(self):
    self.disconnectAll(self.advanceButtonPlan)
    self.disconnectAll(self.backButtonPlan)

    self.backButtonAction.visible = True
    self.backButtonPlan.text = 'Segment the Skin'
    self.backButtonPlan.clicked.connect(lambda: self.planningTabBar.setCurrentIndex(self.segmentSkinTabIndex))

    self.advanceButtonAction.visible = True
    self.advanceButtonPlan.text = 'Plan the Trajectory'
    self.advanceButtonPlan.clicked.connect(lambda: self.planningTabBar.setCurrentIndex(self.trajectoryTabIndex))
    self.logic.seed_segmentation.SetDisplayVisibility(True)
    self.ui.PlanningWidget.setCurrentWidget(self.ui.PlanningStep2)

  def planningStep3(self):
    self.disconnectAll(self.advanceButtonPlan)
    self.disconnectAll(self.backButtonPlan)

    self.backButtonAction.visible = True
    self.backButtonPlan.text = 'Segment the Target'
    self.backButtonPlan.clicked.connect(lambda: self.planningTabBar.setCurrentIndex(self.segmentSkinTabIndex))

    self.advanceButtonAction.visible = True
    self.advanceButtonPlan.text = 'Define Landmarks'
    self.advanceButtonPlan.clicked.connect(lambda: self.planningTabBar.setCurrentIndex(self.landmarksTabIndex))
    self.logic.trajectory_markup.SetDisplayVisibility(True)
    self.ui.PlanningWidget.setCurrentWidget(self.ui.PlanningStep3)

  def planningStep4(self):
    self.disconnectAll(self.advanceButtonPlan)
    self.disconnectAll(self.backButtonPlan)

    self.backButtonAction.visible = True
    self.backButtonPlan.text = 'Plan the Trajectory'
    self.backButtonPlan.clicked.connect(lambda: self.planningTabBar.setCurrentIndex(self.segmentSkinTabIndex))

    self.advanceButtonAction.visible = True
    self.advanceButtonPlan.text = ''
    self.advanceButtonPlan.clicked.connect(self.openNextModule)
    self.tableManager.advanceButton = self.advanceButtonPlan
    try:
      landmarks = slicer.util.getNode('LandmarkDefinitions')
      landmarks.SetDisplayVisibility(True)
    except:
      pass
    self.ui.PlanningWidget.setCurrentWidget(self.ui.PlanningStep4)

  def openNextModule(self):
    home = slicer.modules.HomeWidget
    home.primaryTabBar.setCurrentIndex(home.registrationTabIndex)

    print('we should move to registration now...')

  def openPreviousModule(self):
    home = slicer.modules.HomeWidget
    home.primaryTabBar.setCurrentIndex(home.patientsTabIndex)

    print('we should move to patients now...')
  
  def createSkinSegmentation(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    segmentation = self.logic.skin_segmentation
    segment = self.logic.SKIN_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    # Only use a lower threshold and use the max value of volume as upper bound:
    self.logic.applySkinSegmentation(
      thresholdMin=self.ui.skinThresholdSlider.value,
      thresholdMax=self.logic.master_volume.GetImageData().GetScalarRange()[1],
      smoothingSize=self.ui.skinSmoothingSlider.value,
    )
    self.logic.endEffect()

    # Make results visible in 3D
    segmentation.CreateClosedSurfaceRepresentation()

    NNUtils.centerCam()

  def paintInside(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    segmentation = self.logic.seed_segmentation
    segment = self.logic.SEED_INSIDE_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.beginPaint()

  def paintOutside(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    segmentation = self.logic.seed_segmentation
    segment = self.logic.SEED_OUTSIDE_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.beginPaint()

  def previewTarget(self):
    self.logic.endEffect()
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return
    segmentation = self.logic.seed_segmentation
    self.logic.setEditorTargets(volume, segmentation)
    self.logic.previewTargetSegmentation()

  def segmentTarget(self):
    self.logic.applyTargetSegmentation()
    self.logic.endEffect()

    segmentation = self.logic.seed_segmentation
    segmentation.CreateClosedSurfaceRepresentation()

  def setTrajectory(self):
    self.logic.placeTrajectory()

  def onPlanningChanged(self, tabIndex):
    if tabIndex == self.CurrentPlanningIndex:
      return

    # Update Current Tab
    self.CurrentPlanningIndex = tabIndex


def default_master_volume():
  logging.warning('No master volume is set.')

  node_id = NNUtils.getActiveVolume()
  if not node_id:
    logging.warning('There is no active volume.')
    return None

  node = slicer.mrmlScene.GetNodeByID(node_id)
  logging.warning("Using active volume %r", node)
  return node


class PlanningLogic(ScriptedLoadableModuleLogic):
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
  trajectory_markup = NNUtils.nodeReferenceProperty("TRAJECTORY_MARKUP", default=None)

  current_step = NNUtils.parameterProperty("CURRENT_TAB")

  def __init__(self):
    super().__init__()

    self.SKIN_SEGMENT = 'NN_SKIN'

    self.SEED_INSIDE_SEGMENT = 'NN_INSIDE'
    self.SEED_OUTSIDE_SEGMENT = 'NN_OUTSIDE'

    self.editor_widget = slicer.qMRMLSegmentEditorWidget()
    self.editor_widget.setMRMLScene(slicer.mrmlScene)
    # self.editor_widget.visible = True

    self.editor_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode')
    self.editor_widget.setMRMLSegmentEditorNode(self.editor_node)

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
      node.GetDisplayNode().SetSegmentOpacity3D(skin_segment.GetName(), 0.5)
      self.skin_segmentation = node

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
      self.seed_segmentation = node

    if not self.trajectory_markup:
      node = slicer.mrmlScene.AddNewNodeByClass(
        'vtkMRMLMarkupsLineNode',
        'NN_TRAJECTORY',
      )
      node.CreateDefaultDisplayNodes()
      display = node.GetDisplayNode()
      display.SetPropertiesLabelVisibility(False)
      display.SetLineDiameter(3)  # mm
      display.SetCurveLineSizeMode(display.UseLineDiameter)
      self.trajectory_markup = node

  def setEditorTargets(self, volume, segmentation, segmentID=''):
    """Set the persistent segment editor to edit the given volume and segmentation.
    If segmentID is provided, also select that segment in the editor.
    """
    # make sure the active segmentation uses the active volume
    segmentation.SetReferenceImageGeometryParameterFromVolumeNode(volume)

    self.editor_node.SetAndObserveMasterVolumeNode(volume)
    self.editor_node.SetAndObserveSegmentationNode(segmentation)

    if segmentID:
      self.editor_widget.setCurrentSegmentID(segmentID)

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
    self.editor_widget.setActiveEffectByName('Grow from seeds')
    effect = self.editor_widget.activeEffect()
    effect.setParameter('AutoUpdate', 0)
    effect.self().onPreview()

  def applyTargetSegmentation(self, smoothingSize=3):
    """ Preview target segmentation effects. Be sure to use setEditorTargets
     beforehand, so the effect is applied correctly.

    Effects: Grow from seeds, Smoothing
    """
    self.editor_widget.setActiveEffectByName('Grow from seeds')
    effect = self.editor_widget.activeEffect()
    effect.self().onApply()

    # Make sure both segments are visible
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, True)

    self.editor_widget.setActiveEffectByName("Smoothing")
    effect = self.editor_widget.activeEffect()
    effect.setParameter('SmoothingMethod', 'MEDIAN')
    effect.setParameter('KernelSizeMm', smoothingSize)
    effect.self().onApply()

    # Rehide outside segment
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, False)

  def beginPaint(self):
    """ Begin a paint effect. Be sure to use setEditorTargets beforehand, so
     the effect is applied correctly.
    """

    # Make both segments visible when painting
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, True)

    self.editor_widget.setActiveEffectByName('Paint')
    # paint effect does not need onApply().

  def endEffect(self):
    """ End the active effect, returning mouse control to normal.
    """
    self.editor_widget.setActiveEffectByName('None')

  def placeTrajectory(self):
    """ Select the trajectory line markup and enter markup placement mode."""

    trajectory = self.trajectory_markup

    selection_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSelectionNodeSingleton')
    interaction_node = slicer.mrmlScene.GetNodeByID('vtkMRMLInteractionNodeSingleton')

    selection_node.SetActivePlaceNodeID(trajectory.GetID())
    selection_node.SetActivePlaceNodeClassName(trajectory.GetClassName())
    interaction_node.SetCurrentInteractionMode(interaction_node.Place)
