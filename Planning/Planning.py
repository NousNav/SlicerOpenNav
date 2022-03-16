import logging
import pathlib

import qt
import slicer

import slicer.modules

from slicer.ScriptedLoadableModule import (
  ScriptedLoadableModule,
  ScriptedLoadableModuleWidget,
  ScriptedLoadableModuleLogic,
)

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

    self.workflow = Home.Workflow(
      'planning',
      nested=(
        Home.Workflow('skin', setup=self.planningStep1, widget=self.ui.PlanningStep1),
        Home.Workflow('target', setup=self.planningStep2, widget=self.ui.PlanningStep2),
        Home.Workflow('trajectory', setup=self.planningStep3, widget=self.ui.PlanningStep3),
        Home.Workflow('landmarks', setup=self.planningStep4, widget=self.ui.PlanningStep4),
      ),
      setup=self.enter,
      teardown=self.exit,
    )

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

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

    self.ui.savePlanButton.clicked.connect(self.onSavePlanButtonClicked)

  def exit(self):
    # Hide current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = False
    self.planningTabBar.visible = False

    self.logic.skin_segmentation.SetDisplayVisibility(False)
    self.logic.seed_segmentation.SetDisplayVisibility(False)
    self.logic.trajectory_markup.SetDisplayVisibility(False)
    try:
      self.landmarkLogic.landmarks.SetDisplayVisibility(False)
    except:
      pass

  def enter(self):
    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True
    self.planningTabBar.visible = True

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    NNUtils.applyStyle([sidePanel, modulePanel], self.resourcePath("PanelLight.qss"))

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

    if self.logic.skin_segmentation is not None:
      self.logic.skin_segmentation.SetDisplayVisibility(True)

    volume = self.logic.master_volume
    if volume is None:
      self.advanceButton.enabled = False

  @NNUtils.backButton(text="Segment the Skin")
  @NNUtils.advanceButton(text="Plan the Trajectory")
  def planningStep2(self):
    self.tableManager.advanceButton = None

    if self.logic.seed_segmentation is not None:
      self.logic.seed_segmentation.SetDisplayVisibility(True)

  @NNUtils.backButton(text="Segment the Target")
  @NNUtils.advanceButton(text="Define Landmarks")
  def planningStep3(self):
    self.tableManager.advanceButton = None

    if self.logic.trajectory_markup is not None:
      self.logic.trajectory_markup.SetDisplayVisibility(True)

  @NNUtils.backButton(text="Plan the Trajectory")
  @NNUtils.advanceButton(text="")
  def planningStep4(self):
    self.tableManager.advanceButton = self.advanceButton
    try:
      landmarks = slicer.util.getNode('LandmarkDefinitions')
      landmarks.SetDisplayVisibility(True)
    except:
      pass

  def createSkinSegmentation(self):
    volume = self.logic.master_volume
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    self.logic.setupSkinSegmentationNode()

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

    self.logic.setupSeedSegmentationNode()

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

  def onSavePlanButtonClicked(self):
    default_dir = qt.QStandardPaths.writableLocation(qt.QStandardPaths.DocumentsLocation)

    dialog = qt.QFileDialog()
    plan_path = dialog.getSaveFileName(
      slicer.util.mainWindow(),
      'Save NousNav Plan',
      default_dir,
      '*.mrb',
    )
    if not plan_path:
      return

    plan_path = pathlib.Path(plan_path)
    if plan_path.suffix != '.mrb':
      plan_path = plan_path.with_suffix('.mrb')

    print(f'saving plan: {plan_path}')

    slicer.util.saveScene(str(plan_path))


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
      node.GetDisplayNode().SetSegmentOpacity3D(skin_segment.GetName(), 0.5)
      self.skin_segmentation = node

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
      self.seed_segmentation = node

  def setupTrajectoryMarkupNode(self):
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
    if effect.self().getPreviewNode() is None:
      return
    effect.self().onApply()

    # Make sure both segments are visible
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_INSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility(self.SEED_OUTSIDE_SEGMENT, True)
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility3D(self.SEED_OUTSIDE_SEGMENT, False)

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
    self.seed_segmentation.GetDisplayNode().SetSegmentVisibility3D(self.SEED_OUTSIDE_SEGMENT, False)

    self.editor_widget.setActiveEffectByName('Paint')
    # paint effect does not need onApply().

  def endEffect(self):
    """ End the active effect, returning mouse control to normal.
    """
    self.editor_widget.setActiveEffectByName('None')

  def placeTrajectory(self):
    """ Select the trajectory line markup and enter markup placement mode."""

    self.setupTrajectoryMarkupNode()

    trajectory = self.trajectory_markup

    selection_node = slicer.mrmlScene.GetNodeByID('vtkMRMLSelectionNodeSingleton')
    interaction_node = slicer.mrmlScene.GetNodeByID('vtkMRMLInteractionNodeSingleton')

    selection_node.SetActivePlaceNodeID(trajectory.GetID())
    selection_node.SetActivePlaceNodeClassName(trajectory.GetClassName())
    interaction_node.SetCurrentInteractionMode(interaction_node.Place)
