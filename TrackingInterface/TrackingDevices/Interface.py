from abc import ABC


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
