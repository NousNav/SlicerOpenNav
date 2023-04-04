from enum import Enum

import slicer


class TracingState(Enum):
  NOT_STARTED = 0
  IN_PROGRESS = 1
  DONE = 2


class Trace:
  def __init__(self):
    self.state = TracingState.NOT_STARTED
    self.traceNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Trace')
    self.traceNode.GetMarkupsDisplayNode().SetVisibility(False)
    self.traceNode.GetMarkupsDisplayNode().SetVisibility2D(False)
    self.traceNode.GetMarkupsDisplayNode().SetSelectedColor(35 / 255.0, 76 / 255.0, 79 / 255.0)
    self.traceNode.GetMarkupsDisplayNode().SetColor(72 / 255.0, 72 / 255.0, 72 / 255.0)
    self.traceNode.GetMarkupsDisplayNode().SetTextScale(0)
    self.traceNode.GetMarkupsDisplayNode().SetGlyphScale(5)
    self.traceNode.SetLocked(True)
    self.traceNode.SaveWithSceneOff()
    self.initialized_with_landmarks = False
    self.lastAcquisitionLength = 0

  def addPoint(self, point):
    self.traceNode.AddControlPoint(point[0], point[1], point[2])
    self.lastAcquisitionLength += 1

  def clearTrace(self):
    self.state = TracingState.NOT_STARTED
    self.traceNode.RemoveAllMarkups()
    self.initialized_with_landmarks = False
    self.lastAcquisitionLength = 0

  def discardLastAcquisition(self):
    for _ in range(self.lastAcquisitionLength):
      self.traceNode.RemoveMarkup(self.traceNode.GetNumberOfMarkups() - 1)
    self.lastAcquisitionLength = 0

  def setVisible(self, visible):
    self.traceNode.GetMarkupsDisplayNode().SetVisibility(visible)
