import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap
import NNUtils

class Planning(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NousNav Planning"
    self.parent.categories = [""]
    self.parent.dependencies = ["VolumeRendering", "NNSegmentation", "SegmentEditor"]
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

    #Create logic class
    self.logic = PlanningLogic()

    # Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    ###Stacked widgets navigation changes
    self.CurrentPlanningIndex = -1
    self.ui.PlanningWidget.currentChanged.connect(self.onPlanningChanged)

    self.setupStep1(self.ui.PlanningStep1)
    self.setupStep2(self.ui.PlanningStep2)
    self.setupStep3(self.ui.PlanningStep3)

  def setupStep1(self, widget):
    """Skin Segmentation Step"""

    layout = widget.layout()
    layout.addWidget(qt.QLabel("Segment the Skin"))

    self.thresholdSlider = ctk.ctkRangeSlider(widget)
    self.thresholdSlider.orientation = qt.Qt.Horizontal
    self.thresholdSlider.setMinimum(0)
    self.thresholdSlider.setMaximum(1000)
    self.thresholdSlider.setValues(30, 700)

    self.smoothingSlider = qt.QSlider(widget)
    self.smoothingSlider.orientation = qt.Qt.Horizontal
    self.smoothingSlider.setMinimum(0)
    self.smoothingSlider.setMaximum(10)
    self.smoothingSlider.setValue(3)

    layout.addWidget(qt.QLabel("Threshold"))
    layout.addWidget(self.thresholdSlider)

    layout.addWidget(qt.QLabel("Smoothness"))
    layout.addWidget(self.smoothingSlider)

    # layout.addWidget(qt.QPushButton("Undo"))
    # layout.addWidget(qt.QPushButton("Reset"))

    apply = qt.QPushButton('Apply')
    apply.clicked.connect(self.createSkinSegmentation)
    layout.addWidget(apply)

    layout.addStretch(1)
    layout.addWidget(self.createPlanningStepWidget(False, True))

  def createSkinSegmentation(self):
    volume = self.logic.getMasterVolume()
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    segmentation = self.logic.getSkinSegmentation()
    segment = self.logic.SKIN_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.applySkinSegmentation(
      thresholdMin=self.thresholdSlider.minimumValue,
      thresholdMax=self.thresholdSlider.maximumValue,
      smoothingSize=self.smoothingSlider.value,
    )
    self.logic.endEffect()

    # Make results visible in 3D
    segmentation.CreateClosedSurfaceRepresentation()

  def setupStep2(self, widget):
    layout = widget.layout()
    layout.addWidget(qt.QLabel("Segment the Target"))

    inside = qt.QPushButton('Paint Inside')
    inside.clicked.connect(self.paintInside)
    layout.addWidget(inside)

    outide = qt.QPushButton('Paint Outide')
    outide.clicked.connect(self.paintOutside)
    layout.addWidget(outide)

    preview = qt.QPushButton('Preview')
    preview.clicked.connect(self.previewTarget)
    layout.addWidget(preview)

    apply = qt.QPushButton('Apply')
    apply.clicked.connect(self.segmentTarget)
    layout.addWidget(apply)

    layout.addStretch(1)
    layout.addWidget(self.createPlanningStepWidget(True, True))

  def paintInside(self):
    volume = self.logic.getMasterVolume()
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    segmentation = self.logic.getSeedSegmentation()
    segment = self.logic.SEED_INSIDE_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.beginPaint()

  def paintOutside(self):
    volume = self.logic.getMasterVolume()
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return

    segmentation = self.logic.getSeedSegmentation()
    segment = self.logic.SEED_OUTSIDE_SEGMENT

    self.logic.setEditorTargets(volume, segmentation, segment)
    self.logic.beginPaint()

  def previewTarget(self):
    self.logic.endEffect()
    volume = self.logic.getMasterVolume()
    if not volume:
      slicer.util.errorDisplay('There is no volume in the scene.')
      return
    segmentation = self.logic.getSeedSegmentation()
    self.logic.setEditorTargets(volume, segmentation)
    self.logic.previewTargetSegmentation()

  def segmentTarget(self):
    self.logic.applyTargetSegmentation()
    self.logic.endEffect()

    segmentation = self.logic.getSeedSegmentation()
    segmentation.CreateClosedSurfaceRepresentation()

  def setupStep3(self, widget):
    layout = widget.layout()
    layout.addWidget(qt.QLabel("Plan the Trajectory"))
    layout.addStretch(1)
    layout.addWidget(self.createPlanningStepWidget(True, False))

  def onPlanningChanged(self, tabIndex):
    if tabIndex == self.CurrentPlanningIndex:
      return
    if tabIndex == self.ui.PlanningWidget.indexOf(self.ui.PlanningStep2):
      nodeID = NNUtils.getActiveVolume()
      if nodeID is not None:
        node = slicer.mrmlScene.GetNodeByID(nodeID)
        volumeComboBox = slicer.util.findChild(self.volumerenderWidget, "VolumeNodeComboBox")
        volumeComboBox.setCurrentNode(node)
        volRenLogic = slicer.modules.volumerendering.logic()
        displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(node)
        displayNode.SetVisibility(True)
        displayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName('CT-Bones'))
        controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
        controller.resetFocalPoint()

    #Update Current Tab
    self.CurrentPlanningIndex = tabIndex


class PlanningLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    self.MASTER_VOLUME = 'NN_Master_Volume'
    self.SKIN_SEGMENTATION = 'NN_Skin_Segmentation'
    self.SKIN_SEGMENT = 'NN_Skin'

    self.SEED_SEGMENTATION = 'NN_Seed_Segmentation'
    self.SEED_INSIDE_SEGMENT = 'NN_Inside'
    self.SEED_OUTSIDE_SEGMENT = 'NN_Outside'

    self.editor_widget = slicer.qMRMLSegmentEditorWidget()
    self.editor_widget.setMRMLScene(slicer.mrmlScene)
    # self.editor_widget.visible = True

    self.editor_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode')
    self.editor_widget.setMRMLSegmentEditorNode(self.editor_node)

  def getMasterVolume(self):
    """Get the master volume node, with name PlanningLogic.MASTER_VOLUME.
    If none exists, use the first volume node in the scene.
    """
    node = slicer.mrmlScene.GetFirstNodeByName(self.MASTER_VOLUME)
    if node:
      return node

    node = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLVolumeNode')
    if node:
      logging.warning('No master volume node is set. Using volume %s', node.GetName())
      return node

    logging.error('No volume in scene.')
    return None

  def getSegment(self, segmentation, segmentID):
    """Get a segment from a segmentation. If none exists, create one and return it."""
    segment = segmentation.GetSegmentation().GetSegment(segmentID)
    if segment:
      return segment

    logging.info('Creating new segment %s', segmentID)

    segmentation.GetSegmentation().AddEmptySegment(segmentID)
    segment = segmentation.GetSegmentation().GetSegment(segmentID)
    return segment


  def getSkinSegmentation(self):
    """Get the skin segmentation node, with name PlanningLogic.SKIN_SEGMENTATION.
    If none exists, create one and return it.
    """
    # get or create the node
    node = slicer.mrmlScene.GetFirstNodeByName(self.SKIN_SEGMENTATION)
    if not node:
      logging.info('Creating new segmentation node')
      node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
      node.SetName(self.SKIN_SEGMENTATION)
      node.CreateDefaultDisplayNodes()

      segment = self.getSegment(node, self.SKIN_SEGMENT)
      node.GetDisplayNode().SetSegmentOpacity3D(self.SKIN_SEGMENT, 0.5)
      segment.SetColor(0.3, 0.1, 0.9)

    return node

  def getSeedSegmentation(self):
    """Get the target seed segmentation node, with name PlanningLogic.SEED_SEGMENTATION.
    If none exists, create one and return it.
    """
    # get or create the node
    node = slicer.mrmlScene.GetFirstNodeByName(self.SEED_SEGMENTATION)
    if not node:
      logging.info('Creating new segmentation node')
      node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
      node.SetName(self.SEED_SEGMENTATION)
      node.CreateDefaultDisplayNodes()

      segment = self.getSegment(node, self.SEED_INSIDE_SEGMENT)
      segment.SetColor(0.9, 0.1, 0.1)

      segment = self.getSegment(node, self.SEED_OUTSIDE_SEGMENT)
      segment.SetColor(0.4, 0.4, 0.4)

    return node

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

    Effects: Threshold, remove islands, remove voids, smoothing
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
    effect.self().onPreview()

  def applyTargetSegmentation(self, smoothingSize=3):
    """ Preview target segmentation effects. Be sure to use setEditorTargets
     beforehand, so the effect is applied correctly.

    Effects: Grow from seeds, Smoothing
    """
    self.editor_widget.setActiveEffectByName('Grow from seeds')
    effect = self.editor_widget.activeEffect()
    effect.self().onApply()

    self.editor_widget.setActiveEffectByName("Smoothing")
    effect = self.editor_widget.activeEffect()
    effect.setParameter('SmoothingMethod', 'MEDIAN')
    effect.setParameter('KernelSizeMm', smoothingSize)
    effect.self().onApply()

  def beginPaint(self):
    """ Begin a paint effect. Be sure to use setEditorTargets beforehand, so
     the effect is applied correctly.
    """

    self.editor_widget.setActiveEffectByName('Paint')
    effect = self.editor_widget.activeEffect()
    # paint effect does not need onApply().

  def endEffect(self):
    """ End the active effect, returning mouse control to normal.
    """
    self.editor_widget.setActiveEffectByName('None')

class PlanningTest(ScriptedLoadableModuleTest):
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
    self.test_Planning1()

  def test_Planning1(self):
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

    logic = PlanningLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class PlanningFileWriter(object):
  def __init__(self, parent):
    pass

