from abc import ABC

import slicer
import vtk


class TrackingDevice(ABC):
  """Abstract base class interfacing to tracker
  """

  def startTracking(self):
    pass

  def stopTracking(self):
    pass

  def getConfiguration(self):
    pass

  def setConfiguration(self, config):
    pass

  def getNumberOfTools(self):
    pass

  def getTransformsForTool(self, index):
    """Return tuple (baseTransform, tipTransform)
    """
    pass

  def isTracking(self, index):
    pass


# Access to tracking through static methods
import sys
this = sys.modules[__name__]
this._trackingDevice = None


def setTrackingDevice(device):
  if this._trackingDevice is not None:
    this._trackingDevice.stopTracking()
  this._trackingDevice = device


def getTrackingDevice():
  return this._trackingDevice


def getNumberOfTools():
  if this._trackingDevice is None:
    return 0
  return this._trackingDevice.getNumberOfTools()


def startTracking():
  if this._trackingDevice is not None:
    this._trackingDevice.startTracking()


def stopTracking():
  if this._trackingDevice is not None:
     this._trackingDevice.stopTracking()


def getConfiguration():
  if this._trackingDevice is None:
    return None
  return this._trackingDevice.getConfiguration()


def setConfiguration(config):
  if this._trackingDevice is not None:
    this._trackingDevice.setConfiguration(config)


def getTransformsForTool(index):
  """Return tuple (baseTransform, tipTransform)
  """
  if this._trackingDevice is None:
    return (None, None)
  return this._trackingDevice.getTransformsForTool(index)


def isTracking(index):
  if this._trackingDevice is None:
    return False
  return this._trackingDevice.isTracking(index)


def getTrackingToSceneTransform():
  """Return tracking to scene transform for access from different modules.
  Note, needs to be connected to transforms from tracking device seperately.
  """
  # Ensure only one transform exists; create and add if needed
  trackingNodeName = "TrackingToScene"
  nodes = slicer.mrmlScene.GetNodesByName(trackingNodeName)
  transformNode = None
  if nodes.GetNumberOfItems() > 0:
    transformNode = nodes.GetItemAsObject(0)
  else:
    transformNode = slicer.vtkMRMLLinearTransformNode()
    transformNode.SetSaveWithScene(False)
    transformNode.SetSingletonTag("TrackingInterface_" + trackingNodeName)
    m = vtk.vtkMatrix4x4()
    m.Identity()
    transformNode.SetMatrixTransformToParent(m)
    transformNode.SetName(trackingNodeName)
    slicer.mrmlScene.AddNode(transformNode)
  return transformNode
