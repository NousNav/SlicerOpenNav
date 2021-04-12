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
    apply.clicked.connect(self.apply)
    layout.addWidget(apply)

    layout.addStretch(1)
    layout.addWidget(self.createPlanningStepWidget(False, True))

  def apply(self):
    volume, *_ = slicer.mrmlScene.GetNodesByClass('vtkMRMLVolumeNode')

    self.logic.createSkinSegmentation(
      volume,
      thresholdMin=self.thresholdSlider.minimumValue,
      thresholdMax=self.thresholdSlider.maximumValue,
      smoothingSize=self.smoothingSlider.value,
    )

  def setupStep2(self, widget):
    layout = widget.layout()
    layout.addWidget(qt.QLabel("Segment the Target"))
    layout.addStretch(1)
    layout.addWidget(self.createPlanningStepWidget(True, True))

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

  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    pass

  def createSkinSegmentation(self, volume, thresholdMin=30, thresholdMax=1000, smoothingSize=3):
    seg_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    seg_node.CreateDefaultDisplayNodes()
    seg_node.SetReferenceImageGeometryParameterFromVolumeNode(volume)

    skin_id = seg_node.GetSegmentation().AddEmptySegment('skin')

    editor_widget = slicer.qMRMLSegmentEditorWidget()
    editor_widget.setMRMLScene(slicer.mrmlScene)
    # editor_widget.visible = True

    editor_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode')
    editor_widget.setMRMLSegmentEditorNode(editor_node)

    editor_node.SetAndObserveSegmentationNode(seg_node)
    editor_node.SetAndObserveMasterVolumeNode(volume)

    # compute threshold
    # remove islands
    # remove voids (inverted islands): invert, remove islands, invert
    # smooth

    # Thresholding
    editor_widget.setActiveEffectByName("Threshold")
    effect = editor_widget.activeEffect()
    effect.setParameter("MinimumThreshold", thresholdMin)
    effect.setParameter("MaximumThreshold", thresholdMax)
    effect.self().onApply()

    # Remove islands
    # Find largest component
    editor_widget.setActiveEffectByName("Islands")
    effect = editor_widget.activeEffect()
    effect.setParameterDefault("Operation", "KEEP_LARGEST_ISLAND")
    effect.self().onApply()

    # Remove voids
    # Invert
    editor_widget.setActiveEffectByName("Logical operators")
    effect = editor_widget.activeEffect()
    effect.setParameter("Operation", "INVERT")
    effect.self().onApply()

    # Find largest component
    editor_widget.setActiveEffectByName("Islands")
    effect = editor_widget.activeEffect()
    effect.setParameterDefault("Operation", "KEEP_LARGEST_ISLAND")
    effect.self().onApply()

    # Invert
    editor_widget.setActiveEffectByName("Logical operators")
    effect = editor_widget.activeEffect()
    effect.setParameter("Operation", "INVERT")
    effect.self().onApply()

    # Smooth
    editor_widget.setActiveEffectByName("Smoothing")
    effect = editor_widget.activeEffect()
    effect.setParameter('SmoothingMethod', 'MEDIAN')
    effect.setParameter('KernelSizeMm', smoothingSize)
    effect.self().onApply()

    slicer.mrmlScene.RemoveNode(editor_node)
    del editor_node
    del editor_widget

    # Make results visible in 3D
    seg_node.CreateClosedSurfaceRepresentation()

    return seg_node


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

