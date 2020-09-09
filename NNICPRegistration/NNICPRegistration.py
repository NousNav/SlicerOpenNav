import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap
import NNUtils
from vtk.util import numpy_support



class NNICPRegistration(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NousNav ICP Registration"
    self.parent.categories = [""]
    self.parent.dependencies = ["TrackingInterface"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the ICP registration module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class NNICPRegistrationWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = NNICPRegistrationLogic()
    self.trackingLogic = slicer.modules.trackinginterface.widgetRepresentation().self().logic
    self.traceObserver = None
    self.tracePoints = []

  def startTracing(self):
    self.tracePoints.clear()
    (tNode, tNodeTip) = self.trackingLogic.getTransformsForTool(self.tools.currentIndex)
    self.traceObserver = tNodeTip.AddObserver( slicer.vtkMRMLTransformNode.TransformModifiedEvent,
            self.doTracing )
    self.samplingTimer.start(50)
    self.traceButton.setEnabled(False)
    self.tools.setEnabled(False)

  def stopTracing(self):
    if self.traceObserver is not None:
      (tNode, tNodeTip) = self.trackingLogic.getTransformsForTool(self.tools.currentIndex)
      tNodeTip.RemoveObserver(self.traceObserver)
      self.traceObserver=None
    self.samplingTimer.stop()
    self.traceButton.setEnabled(True)
    self.tools.setEnabled(True)

    segmentation = self.segmentationComboBox.currentNode
    if segmentation is not None:
      segmentIDs = []
      segmentation.GetSegmentation().GetSegmentationIDs(segmentIDs)
      segmentationPointSets = []
      for sid in segmentIDs:
        polyData = segmentation.GetClosedSurfaceInternalRepresentation(sid)
        tmpPoints = ployData.GetPoints()
        segmentationPointSets.append(numpy_support.vtk_to_numpy(tmpPoints))
      segmentationPoints = np.concatenate(segmentationPointSets)
      tracingPoints = np.concatenate(self.tracePoints)
      transformMatrix = self.logic.run(segmentationPoints, tracingPoints)
      node = slicer.mrmlScene.GetNodesByName("TrackingToScene").GetItemAsObject(0)
      node.SetMatrixTransformToParent( transformMatrix )
      NNUtils.centerOnActiveVolume()

  def doTracing(self, transformNode=None, unusedArg2=None, unusedArg3=None):
    m = vtk.vtkMatrix4x4()
    transformNode.GetMatrixTransformToParent(m)
    tipLocal = np.array( [m.GetElement(0,3), m.GetElement(1,3), m.GetElement(2,3)] )
    tipWorld = np.empty(3)
    transformNode.TransformPointToWorld(tipLocal, tipWorld)
    self.tracePoints.append( tipWorld )

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    segmentationWidget = qt.QWidget(self.parent)
    segmentationLayout = qt.QHBoxLayout()
    segmentationLayout.addWidget(qt.QLabel("Segmentation"))
    self.segmentationComboBox = slicer.qMRMLNodeComboBox()
    self.segmentationComboBox.setMRMLScene( slicer.mrmlScene )
    self.segmentationComboBox.addEnabled = False
    self.segmentationComboBox.removeEnabled = False
    self.segmentationComboBox.noneEnabled = True
    self.segmentationComboBox.nodeTypes = ["vtkMRMLSegmentationNode"]
    segmentationLayout.addWidget(self.segmentationComboBox)
    segmentationWidget.setLayout(segmentationLayout)
    self.layout.addWidget(segmentationWidget)

    traceWidget = qt.QWidget(self.parent)
    traceLayout = qt.QHBoxLayout()
    traceWidget.setLayout(traceLayout)
    self.traceButton = qt.QPushButton("Start Tracing")
    self.traceButton.setCheckable(False)
    traceLayout.addWidget(self.traceButton)
    self.tools = qt.QComboBox()
    for toolIndex in range( self.trackingLogic.getNumberOfTools() ):
      toolname = "Tool_" + str(toolIndex)
      self.tools.addItem(toolname)
    traceLayout.addWidget( self.tools )
    self.traceTime = qt.QSpinBox()
    self.traceTime.setMinimum(1)
    self.traceTime.setMaximum(20)
    traceLayout.addWidget(self.traceTime)
    self.layout.addWidget(traceWidget)

    self.traceTimer = qt.QTimer()
    self.traceTimer.timeout.connect(self.stopTracing)
    traceButton.clicked.connect(self.startTracing)

  def onClose(self, unusedOne, unusedTwo):
    pass

  def cleanup(self):
    pass


class NNICPRegistrationLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    ScriptedLoadableModuleLogic(self)
    slicer.utils.pip_install("pycpd")


  def run(self, fixed, moving):
    """
    Run coherent point drift algorithm and return transfrom from moving to fixed point set
    Fixed and moving point sets are two numpy arrays of 3 x number of points
    """
    import pycpd

    rigidCPD = pycpd.RigidRegistration(**{'X': fixed, 'Y': moving})
    moved, s, A, t = rigidCPD.register()

    transform = vtk.vtkMatrix4x4()
    for i in range(3):
      for j in range(3):
        transform.SetElement(i, j, A[i,j] * s)
      transform.SetElement(i, 3, t[i])

    return transform


class NNICPRegistrationTest(ScriptedLoadableModuleTest):
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
    self.test_NNICPRegistration1()

  def test_NNICPRegistration1(self):
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

    logic = NNICPRegistrationLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class NNICPRegistrationFileWriter(object):
  def __init__(self, parent):
    pass
