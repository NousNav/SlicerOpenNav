from enum import Enum
import qt
import os
import slicer

class LandmarkState(Enum):
  NOT_STARTED = 0
  IN_PROGRESS = 1
  DONE = 2
  SKIPPED = 3

class Landmark:
  def __init__(self, name, modelPos = [0,0,0]):
    self.name = name
    self.row = -1
    self.state = LandmarkState.NOT_STARTED
    self.modelPosition = modelPos
    self.imagePosition = None
    self.trackerPosition = None

    

class Landmarks:
  def __init__(self, tableWidget, moduleName):
    self.landmarks = []
    self.moduleName = moduleName
    self.tableWidget = tableWidget
    self.currentLandmark = None
    self.tableWidget.resizeColumnToContents(0)
    self.tableWidget.setShowGrid(False)
    self.tableWidget.setFocusPolicy(qt.Qt.NoFocus)
    self.tableWidget.setSelectionMode(qt.QAbstractItemView.NoSelection)
    self.tableWidget.setFrameStyle(qt.QFrame.NoFrame)

    # TODO: improve method of looking up icons
    self.notStartedIcon = qt.QIcon(self.resourcePath('Icons/NotStarted.svg'))
    self.doneIcon = qt.QIcon(self.resourcePath('Icons/Done.svg'))
    self.SkippedIcon = qt.QIcon(self.resourcePath('Icons/Skipped.svg'))
    self.startedIcon = qt.QIcon(self.resourcePath('Icons/Started.svg'))

  def resourcePath(self, filename):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(scriptedModulesPath, 'Resources', filename)
  
  def addLandmark(self, name, modelPos=[0,0,0]):

    newLandmark = Landmark(name, modelPos)
    self.addLandmarkToTable(newLandmark)

    self.landmarks.append(newLandmark)
    self.updateLandmarkDisplay(newLandmark)

  def addLandmarkToTable(self, landmark):
    row = self.tableWidget.rowCount
    self.tableWidget.insertRow(row)
    landmark.row = row
    iconLabel = qt.QLabel()
    iconLabel.setAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
    iconLabel.setPixmap(self.notStartedIcon.pixmap(16, 16))
    nameLabel = qt.QLabel(landmark.name)
    button = qt.QPushButton('')
    button.maximumWidth = 40
    button.maximumHeight = 16
    button.enabled = False
    button.clicked.connect(lambda state, x=landmark: self.updateLandmark(x))
    self.tableWidget.setCellWidget(row, 0, iconLabel)
    self.tableWidget.setCellWidget(row, 1, nameLabel)
    self.tableWidget.setCellWidget(row, 2, button)

  def updateLandmarksDisplay(self):
    
    for landmark in self.landmarks:
      self.updateLandmarkDisplay(landmark)

  def updateLandmarkDisplay(self, landmark):
    button = self.tableWidget.cellWidget(landmark.row, 2)
    iconLabel = self.tableWidget.cellWidget(landmark.row, 0)

    if landmark.state == LandmarkState.NOT_STARTED:
      button.enabled = False
      button.text = ''
      iconLabel.setPixmap(self.notStartedIcon.pixmap(16, 16))

    if landmark.state == LandmarkState.IN_PROGRESS:
      button.enabled = True
      button.text = 'Skip'
      iconLabel.setPixmap(self.startedIcon.pixmap(16, 16))

    if landmark.state == LandmarkState.DONE:
      button.enabled = True
      button.text = 'Redo'
      iconLabel.setPixmap(self.doneIcon.pixmap(16, 16))

    if landmark.state == LandmarkState.SKIPPED:
      button.enabled = True
      button.text = 'Add'
      iconLabel.setPixmap(self.SkippedIcon.pixmap(16, 16))
  
  def startNextLandmark(self):
    for landmark in self.landmarks:
      if landmark.state == LandmarkState.NOT_STARTED:
        self.startLandmark(landmark)
        break
    self.updateLandmarksDisplay()
  
  def startLandmark(self, landmark):
    if self.currentLandmark is not None:
      #cancel current landmark if not done
      if self.currentLandmark.state == LandmarkState.IN_PROGRESS:
        self.currentLandmark.state = LandmarkState.NOT_STARTED

    landmark.state = LandmarkState.IN_PROGRESS
    self.currentLandmark = landmark
    self.updateLandmarksDisplay()
  
  def collectLandmarkPosition(self):
    pos = [10,10,10]
    if self.currentLandmark is not None:
      self.currentLandmark.state = LandmarkState.DONE
      self.currentLandmark.trackerPosition = pos
      self.currentLandmark = None
      self.startNextLandmark()
  
  def updateLandmark(self, landmark):
    if landmark.state == LandmarkState.IN_PROGRESS:
      landmark.state = LandmarkState.SKIPPED
      self.currentLandmark = None
      self.startNextLandmark()
      return
    elif landmark.state == LandmarkState.DONE:
      landmark.state = LandmarkState.IN_PROGRESS
      self.startLandmark(landmark)
      return
    elif landmark.state == LandmarkState.SKIPPED:
      landmark.state = LandmarkState.IN_PROGRESS
      self.startLandmark(landmark)
