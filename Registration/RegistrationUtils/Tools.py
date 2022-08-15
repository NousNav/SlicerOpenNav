from enum import Enum
import qt
import slicer


class ToolState(Enum):
  NEVER_SEEN = 0
  NOT_SEEN = 1
  SEEN = 2


class Tool:
  def __init__(self, ID, name, displayGeometry=None):
    self.id = ID # {Name}ToTracker transform
    self.name = name
    self.displayGeometry = displayGeometry
    self.state = ToolState.NEVER_SEEN
    self.xposition = None


class Tools:
  def __init__(self, seenTableWidget, unseenTableWidget, moduleName):
    self.tools = []
    self.moduleName = moduleName
    self.seenTableWidget = seenTableWidget
    self.unseenTableWidget = unseenTableWidget
    self.optitrack = None
    self.showToolMarkers = False

    self.checkToolsTimer = qt.QTimer()
    self.checkToolsTimer.interval = 100
    self.checkToolsTimer.timeout.connect(self.checkTools)

  def addTool(self, ID, name, geometry=None):
    newTool = Tool(ID, name, geometry)
    self.tools.append(newTool)
    self.updateToolsDisplay()

  def setToolsStatusCheckEnabled(self, enabled):
    """Check the status of the tracking tool every 100ms and
    update the table summarizing the status of each tools.

    See :func:`RegistrationUtils.Tools.checkTools`
    and :func:`RegistrationUtils.Tools.updateToolsDisplay()`.
    """
    if enabled:
      # If timer is already started, it will stop and restart it.
      self.checkToolsTimer.start()
    else:
      self.checkToolsTimer.stop()

  def checkTools(self):
    if self.optitrack is None:
      print("Fail")
      return

    for tool in self.tools:
      if not self.optitrack.checkTool(tool.id):
        tool.state = ToolState.NEVER_SEEN
        break

      self.checkIfNodeIsActive(tool)

    self.updateToolsDisplay()

  def checkIfNodeIsActive(self, tool):
    try:
      node = slicer.util.getNode(tool.id)
      matrix = node.GetMatrixTransformToParent()
      xposition = matrix.GetElement(0,3)

      # if position, then tool is current

      if tool.xposition is None:
        tool.state = ToolState.SEEN
      else:
        # has position updated since last time?
        if tool.xposition == xposition :
          tool.state = ToolState.NOT_SEEN
        else:
          tool.state = ToolState.SEEN

      # Update position
      tool.xposition = xposition

      if tool.displayGeometry:
        tool.displayGeometry.SetAndObserveTransformNodeID(node.GetID())
    except:
      print("Fail")
      pass

  def updateToolsDisplay(self):

    self.seenTableWidget.setRowCount(0)
    self.unseenTableWidget.setRowCount(0)

    for tool in self.tools:
      if tool.state == ToolState.SEEN:
        self.addToolToTable(tool, self.seenTableWidget)
        if tool.displayGeometry:
          tool.displayGeometry.GetDisplayNode().SetVisibility(self.showToolMarkers)
      else:
        self.addToolToTable(tool, self.unseenTableWidget)
        if tool.displayGeometry:
          tool.displayGeometry.GetDisplayNode().SetVisibility(False)

    self.seenTableWidget.resizeColumnToContents(0)
    self.seenTableWidget.setShowGrid(False)
    self.seenTableWidget.setFocusPolicy(qt.Qt.NoFocus)
    self.seenTableWidget.setSelectionMode(qt.QAbstractItemView.NoSelection)
    self.seenTableWidget.setFrameStyle(qt.QFrame.NoFrame)

    self.unseenTableWidget.resizeColumnToContents(0)
    self.unseenTableWidget.setShowGrid(False)
    self.unseenTableWidget.setFocusPolicy(qt.Qt.NoFocus)
    self.unseenTableWidget.setSelectionMode(qt.QAbstractItemView.NoSelection)
    self.unseenTableWidget.setFrameStyle(qt.QFrame.NoFrame)

  def addToolToTable(self, tool, table):
    row = table.rowCount
    table.insertRow(row)
    nameLabel = qt.QLabel(tool.name)
    nameLabel.setAlignment(qt.Qt.AlignVCenter)
    table.setCellWidget(row, 0, nameLabel)
