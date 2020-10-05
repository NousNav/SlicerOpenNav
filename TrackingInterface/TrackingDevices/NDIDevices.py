import logging
import vtk, qt, ctk, slicer
import numpy as np
from TrackingDevices.Interface import TrackingDevice

class NDIVegaTracker(TrackingDevice):

  def __init__(self, toolFiles):
    # Tracking toggle button action
    # TODO add to build process instead of installing here
    slicer.util.pip_install("scikit-surgerynditracker")

    self.settings_vega = {
          "tracker type": "vega",
          "ip address": "192.168.1.3",
          "port": 8765,
          "romfiles": toolFiles,
        }
    self.tracker = None
    self.tracker_timer = qt.QTimer()
    self.tracker_timer.timeout.connect( self.tracking )

    self.tools = []
    self.isTrackingActive = []
    for idx, _ in enumerate(toolFiles):
      self.addTool( "Tool_%d" % idx )

    # default configuration widget
    self.configurationFrame = ctk.ctkCollapsibleGroupBox()
    configurationLayout = qt.QGridLayout(self.configurationFrame)
    self.configurationFrame.name = "Tracking Setup"
    self.configurationFrame.title = "Tracking Setup"
    self.configurationFrame.setChecked( False )

    configurationLayout.addWidget(qt.QLabel("IP Address:"), 0, 0)
    self.ipaddress = qt.QLineEdit("192.168.1.3")
    configurationLayout.addWidget(self.ipaddress, 0, 1)

    configurationLayout.addWidget(qt.QLabel("Port:"), 1, 0)
    self.port = qt.QLineEdit("8765")
    configurationLayout.addWidget(self.port, 1, 1)

    configurationLayout.addWidget(qt.QLabel("Poll (ms):"), 2, 0)
    self.poll = qt.QSpinBox()
    self.poll.setMinimum(10)
    self.poll.setMaximum(500)
    self.poll.setValue(100)
    configurationLayout.addWidget(self.poll, 2, 1)

  def addTool(self, toolname):
    # Tool location
    transformNode = slicer.vtkMRMLLinearTransformNode()
    m = vtk.vtkMatrix4x4()
    m.Identity()
    transformNode.SetMatrixTransformToParent(m)
    transformNode.SetName(toolname)
    transformNode.SetSaveWithScene(False)
    slicer.mrmlScene.AddNode(transformNode)

    # Tool tip relative to tool location
    transformNodeTip = slicer.vtkMRMLLinearTransformNode()
    m = vtk.vtkMatrix4x4()
    m.Identity()
    transformNodeTip.SetMatrixTransformToParent(m)
    transformNodeTip.SetName(toolname + "_tip")
    transformNodeTip.SetSaveWithScene(False)

    slicer.mrmlScene.AddNode(transformNodeTip)
    transformNodeTip.SetAndObserveTransformNodeID(transformNode.GetID())

    self.tools.append((transformNode, transformNodeTip))
    self.isTrackingActive.append(False)

  def tracking(self):
    frame = self.tracker.get_frame()
    transformMatricesIndex = 3
    matrices = frame[ transformMatricesIndex ]
    for i, m in enumerate( matrices ) :
      (transformNode, transformNodeTip) = self.getTransformsForTool(i)
      self.isTrackingActive[i] = not np.isnan(np.sum(m))
      if self.isTrackingActive[i]:
        vm = slicer.util.vtkMatrixFromArray(np.array(m))
        transformNode.SetMatrixTransformToParent(vm)
      else:
        # Notify observers - TODO add status observation to interface?
        m = vtk.vtkMatrix4x4()
        transformNode.GetMatrixTransformToParent(m)
        transformNode.SetMatrixTransformToParent(m)

  def startTracking(self):
    self.stopTracking()
    from sksurgerynditracker.nditracker import NDITracker
    self.settings_vega["ip address"] = self.ipaddress.text
    self.settings_vega["port"] = int(self.port.text)
    self.tracker = NDITracker(self.settings_vega)
    self.tracker.start_tracking()
    self.tracker_timer.start( self.poll.value )

  def stopTracking(self):
    if self.tracker is not None:
      try:
        self.tracker_timer.stop()
        self.tracker.stop_tracking()
        self.tracker.close()
        self.tracker = None
      except ValueError:
        logging.warning("NDI Vega Tracker already closed")

  def getConfiguration(self):
    self.settings_vega = {
          "tracker type": "vega",
          "ip address": self.ipaddress.text,
          "port": int(self.port.text),
          "romfiles": self.toolFiles
        }
    return self.settings_vega

  def setConfiguration(self, config):
    # TODO update tool transform etc
    # self.settings_vega = config
    pass

  def getNumberOfTools(self):
    return len( self.tools )

  def getTransformsForTool(self, index):
    try:
      return self.tools[index]
    except IndexError:
      return None

  def getConfigurationWidget(self):
    return self.configurationFrame

  def isTracking(self, index):
    return self.isTrackingActive[index]
