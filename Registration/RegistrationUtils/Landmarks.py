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
    self.index = -1
    self.state = LandmarkState.NOT_STARTED
    self.modelPosition = modelPos
    self.imagePosition = None
    self.trackerPosition = None
    self.ignore = False
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

    self.landmarksNeeded = 3
    self.landmarksCollected = 0
    self.landmarksFinished = False
    self.advanceButtonReg = None

    # TODO: improve method of looking up icons
    self.notStartedIcon = qt.QIcon(self.resourcePath('Icons/NotStarted.svg'))
    self.doneIcon = qt.QIcon(self.resourcePath('Icons/Done.svg'))
    self.SkippedIcon = qt.QIcon(self.resourcePath('Icons/Skipped.svg'))
    self.startedIcon = qt.QIcon(self.resourcePath('Icons/Started.svg'))
    self.model = slicer.util.loadModel(self.resourcePath('Data/manny.vtk'))
    self.model.GetDisplayNode().SetVisibility(False)
    self.model.GetDisplayNode().SetOpacity(0.5)

    self.landmarksDisplay = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Landmarks')
    self.landmarksDisplay.GetMarkupsDisplayNode().SetVisibility(False)
    self.landmarksDisplay.GetMarkupsDisplayNode().SetSelectedColor(35/255.0,76/255.0,79/255.0)
    self.landmarksDisplay.GetMarkupsDisplayNode().SetColor(72/255.0,72/255.0,72/255.0)
    self.landmarksDisplay.GetMarkupsDisplayNode().SetTextScale(0)
    self.landmarksDisplay.GetMarkupsDisplayNode().SetGlyphScale(7)
    self.landmarksDisplay.SetLocked(True)
    self.showLandmarks = False

 
  
  def updateAdvanceButton(self):
    
    landmarksRemaining = self.landmarksNeeded - self.landmarksCollected
    self.advanceButtonReg.enabled = False
    if landmarksRemaining > 1:
      self.advanceButtonReg.text = 'Touch ' + str(landmarksRemaining) + ' more landmarks' 
    elif landmarksRemaining == 1:
      self.advanceButtonReg.text = 'Touch 1 more landmark'
    else:
      self.advanceButtonReg.text = 'Press to continue'
      self.advanceButtonReg.enabled = True
  
  def resourcePath(self, filename):
    scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(scriptedModulesPath, 'Resources', filename)
  
  def addLandmark(self, name, modelPos=[0,0,0]):

    newLandmark = Landmark(name, modelPos)
    self.addLandmarkToTable(newLandmark)

    self.landmarks.append(newLandmark)
    newLandmark.index = self.landmarksDisplay.AddFiducial(modelPos[0], modelPos[1], modelPos[2])
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
    
    self.landmarksCollected = 0
    for landmark in self.landmarks:
      self.updateLandmarkDisplay(landmark)

    self.model.GetDisplayNode().SetVisibility(self.showLandmarks)
    self.landmarksDisplay.GetDisplayNode().SetVisibility(self.showLandmarks)

    self.landmarksFinished = self.landmarksCollected >= self.landmarksNeeded
    if self.showLandmarks:
      self.updateAdvanceButton()
      

  def updateLandmarkDisplay(self, landmark):
    button = self.tableWidget.cellWidget(landmark.row, 2)
    iconLabel = self.tableWidget.cellWidget(landmark.row, 0)
    self.landmarksDisplay.SetNthControlPointSelected(landmark.row, False)
    if landmark.state == LandmarkState.NOT_STARTED:
      button.enabled = False
      button.text = ''
      iconLabel.setPixmap(self.notStartedIcon.pixmap(16, 16))

    if landmark.state == LandmarkState.IN_PROGRESS:
      button.enabled = True
      button.text = 'Skip'
      iconLabel.setPixmap(self.startedIcon.pixmap(16, 16))
      self.landmarksDisplay.SetNthControlPointSelected(landmark.row, True)

    if landmark.state == LandmarkState.DONE:
      button.enabled = True
      button.text = 'Redo'
      iconLabel.setPixmap(self.doneIcon.pixmap(16, 16))
      self.landmarksCollected += 1

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
  
  def collectLandmarkPosition(self, pos = [0,0,0]):
    if self.currentLandmark is not None:
      self.currentLandmark.state = LandmarkState.DONE
      self.currentLandmark.trackerPosition = pos
      self.currentLandmark = None
      self.startNextLandmark()
      
  
  def getTrackerPosition(self, name):
    for landmark in self.landmarks:
      if landmark.name == name:
        return landmark.trackerPosition
  
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
