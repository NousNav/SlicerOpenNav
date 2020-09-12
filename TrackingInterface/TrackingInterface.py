import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy as np


class TrackingInterface(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Tracking Interface"
    self.parent.categories = [""]
    self.parent.dependencies = []
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the tracking interface module for the NousNav application. This module contains no UI elements. It defines the logic for interfacing with the tracking device"
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class TrackingInterfaceWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.logic = TrackingInterfaceLogic()


class TrackingInterfaceLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    self.trackingDevice = None

  def setTrackingDevice(self, device):
    if self.trackingDevice is not None:
      self.trackingDevice.stopTracking()
    self.trackingDevice = device

  def getNumberOfTools(self):
    if self.trackingDevice is None:
      return 0
    return self.trackingDevice.getNumberOfTools()

  def startTracking(self):
    if self.trackingDevice is not None:
      self.trackingDevice.startTracking()

  def stopTracking(self):
    if self.trackingDevice is not None:
      self.trackingDevice.stopTracking()

  def getConfiguration(self):
    if self.trackingDevice is None:
      return None
    return self.trackingDevice.getConfiguration()

  def setConfiguration(self, config):
    if self.trackingDevice is not None:
      self.trackingDevice.setConfiguration(config)

  def getTransformsForTool(self, index):
    """Return tuple (baseTransform, tipTransform)
    """
    if self.trackingDevice is None:
      return (None, None)
    return self.trackingDevice.getTransformsForTool(index)

  def isTracking(self, index):
    if self.trackingDevice is None:
      return False
    return self.trackingDevice.isTracking(index)

  def getTrackingToSceneTransform(self):
    """Return tracking to scene transform for access from different modules.
    Note, needs to be connected to transforms from tacking device seperately.
    """
    # Ensure only one transform exists and create and add if needed
    self.trackingNodeName = "TrackingToScene"
    nodes = slicer.mrmlScene.GetNodesByName(self.trackingNodeName)
    transformNode = None
    if nodes.GetNumberOfItems() > 0:
      transformNode = nodes.GetItemAsObject(0)
    else:
      transformNode = slicer.vtkMRMLLinearTransformNode()
      transformNode.SetSaveWithScene(False)
      transformNode.SetSingletonTag("Tracking_" + self.trackingNodeName)
      m = vtk.vtkMatrix4x4()
      m.Identity()
      transformNode.SetMatrixTransformToParent(m)
      transformNode.SetName(self.trackingNodeName)
      slicer.mrmlScene.AddNode(transformNode)
    return transformNode


class TrackingInterfaceTest(ScriptedLoadableModuleTest):
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

    logic = TrackingInterfaceLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class TrackingInterfaceFileWriter(object):
  def __init__(self, parent):
    pass



