import qt
import slicer
import vtk
import os.path

import RegistrationUtils


class LandmarkDefinitions:
  """Wrap a vtkMRMLMarkupsFiducialNode, keeping track of which points are defined."""

  LANDMARK_NAMES = [
    # 'Inion',
    # 'Left tragus',
    'Left outer canthus',
    # 'Left inner canthus',
    # 'Nasion',
    'Acanthion',
    # 'Right inner canthus',
    'Right outer canthus',
    # 'Right tragus',
  ]
  LANDMARKS_NEEDED = 3

  def __init__(self, table, moduleName):
    self.moduleName = moduleName
    self._advanceButton = None

    # stealing icons from registration module.
    self.notStartedIcon = qt.QIcon(self.resourcePath('Icons/NotStarted.svg'))
    self.doneIcon = qt.QIcon(self.resourcePath('Icons/Done.svg'))
    # self.skippedIcon = qt.QIcon(self.resourcePath('Icons/Skipped.svg'))
    # self.startedIcon = qt.QIcon(self.resourcePath('Icons/Started.svg'))

    self.table = table
    self.setupTable()

    # todo name, idx, row, should probably just be objects, same as in
    #  registration module. should get rid of *IdxMap and *RowMap

    self.landmarkNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'LandmarkDefinitions')

    self.rebuildMaps()
    self.updateLandmarksDisplay()

    self.interactionNode = slicer.mrmlScene.GetNodeByID('vtkMRMLInteractionNodeSingleton')
    self.selectionNode = slicer.mrmlScene.GetNodeByID('vtkMRMLSelectionNodeSingleton')

    self.landmarkNode.AddObserver(self.landmarkNode.PointAddedEvent, self.onPointsChanged)
    self.landmarkNode.AddObserver(self.landmarkNode.PointModifiedEvent, self.onPointsChanged)
    self.landmarkNode.AddObserver(self.landmarkNode.PointRemovedEvent, self.onPointsChanged)

  @property
  def advanceButton(self):
    return self._advanceButton

  @advanceButton.setter
  def advanceButton(self, value):
    self._advanceButton = value
    self.updateAdvanceButton()

  def resourcePath(self, filename):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(scriptedModulesPath, 'Resources', filename)

  def setupTable(self):
    self.table.setFrameStyle(qt.QFrame.NoFrame)

    self.landmarkRowMap = {}

    for name in self.LANDMARK_NAMES:
      row = self.table.rowCount
      self.table.insertRow(row)
      self.landmarkRowMap[name] = row

      iconLabel = qt.QLabel()
      iconLabel.setAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
      iconLabel.setPixmap(self.notStartedIcon.pixmap(16, 16))
      self.table.setCellWidget(row, 0, iconLabel)

      nameLabel = qt.QLabel(name)
      self.table.setCellWidget(row, 1, nameLabel)

      button = qt.QPushButton('')
      button.maximumWidth = 70
      button.maximumHeight = 16
      button.enabled = True
      button.clicked.connect(lambda state, name=name, row=row: self.onButtonClick(name, row))
      self.table.setCellWidget(row, 2, button)

  def updateLandmarksDisplay(self):
    for name, row in self.landmarkRowMap.items():
      self.updateLandmarkDisplay(name, row)

  def updateLandmarkDisplay(self, name, row):
    iconLabel = self.table.cellWidget(row, 0)
    nameLabel = self.table.cellWidget(row, 1)
    button = self.table.cellWidget(row, 2)

    if name in self.landmarkIdxMap:
      # position is defined
      iconLabel.setPixmap(self.doneIcon.pixmap(16, 16))
      # statLabel.text = 'defined'
      button.text = 'remove'
    else:
      # position not defined
      iconLabel.setPixmap(self.notStartedIcon.pixmap(16, 16))
      # statLabel.text = 'not defined'
      button.text = 'place'

  def updateAdvanceButton(self):
    if not self.advanceButton:
      return

    landmarksCollected = len(self.landmarkIdxMap)
    landmarksRemaining = self.LANDMARKS_NEEDED - landmarksCollected

    self.advanceButton.enabled = False
    if landmarksRemaining > 1:
      self.advanceButton.text = 'Touch ' + str(landmarksRemaining) + ' more landmarks'
    elif landmarksRemaining == 1:
      self.advanceButton.text = 'Touch 1 more landmark'
    else:
      self.advanceButton.text = 'Press to continue'
      self.advanceButton.enabled = True

  def onButtonClick(self, name, row):
    # nameLabel = self.table.cellWidget(row, 0)
    # statLabel = self.table.cellWidget(row, 1)
    # button = self.table.cellWidget(row, 2)

    if name in self.landmarkIdxMap:
      # position is defined, so remove point
      # triggers onPointsChanged
      self.landmarkNode.RemoveNthControlPoint(self.landmarkIdxMap[name])
    else:
      # position is not defined, so add point
      # once user defs point, triggers onPointsChanged
      self.selectionNode.SetActivePlaceNodeID(self.landmarkNode.GetID())
      mode = self.interactionNode.Place
      self.selectionNode.SetActivePlaceNodeClassName(self.landmarkNode.GetClassName())
      self.interactionNode.SetCurrentInteractionMode(mode)

      self.landmarkNode.SetMarkupLabelFormat(name)  # hacky but hey it works

  def onPointsChanged(self, sender, event):
    self.rebuildMaps()
    self.updateLandmarksDisplay()
    self.updateAdvanceButton()

  def rebuildMaps(self):
    self.landmarkIdxMap = {}

    count = self.landmarkNode.GetNumberOfControlPoints()
    for idx in range(count):
      name = self.landmarkNode.GetNthControlPointLabel(idx)
      status = self.landmarkNode.GetNthControlPointPositionStatus(idx)

      if status == self.landmarkNode.PositionDefined:
        self.landmarkIdxMap[name] = idx

  @property
  def positions(self):
    data = {}
    for name, idx in self.landmarkIdxMap.items():
      point = [0,0,0]
      self.landmarkNode.GetNthControlPointPositionWorld(idx, point)
      data[name] = point

    return data
