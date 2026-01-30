import os.path

from enum import Enum

import qt
import slicer
import vtk

from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)
from slicer.util import VTKObservationMixin

import OpenNavUtils


class LandmarkManager(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Landmark Manager"
        self.parent.categories = ["OpenNav.Utilities"]
        self.parent.dependencies = ["Markups"]
        self.parent.contributors = ["David Allemang (Kitware Inc.)", "Sam Horvath (Kitware, Inc.)"]
        self.parent.helpText = ""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = ""


class LandmarkManagerWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setup(self):
        super().setup()

        # Load widget from .ui file (created by Qt Designer)
        self.uiWidget = slicer.util.loadUI(self.resourcePath("UI/LandmarkManager.ui"))
        self.layout.addWidget(self.uiWidget)
        self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    def enter(self):
        pass


class LandmarkManagerLogic(VTKObservationMixin, ScriptedLoadableModuleLogic):
    ALL_LANDMARKS = [
        "Inion",
        "Left tragus",
        "Left outer canthus",
        "Left inner canthus",
        "Nasion",
        "Acanthion",
        "Right inner canthus",
        "Right outer canthus",
        "Right tragus",
    ]
    LANDMARKS_NEEDED = 3

    requiredLandmarks: list[str] = OpenNavUtils.parameterProperty("REQUIRED_LANDMARKS", default=ALL_LANDMARKS)

    landmarkIndexes: dict[str, int] = OpenNavUtils.parameterProperty("LANDMARK_INDEXES", factory=dict)

    landmarks = OpenNavUtils.nodeReferenceProperty("PLANNING_LANDMARKS", default=None)

    def __init__(self):
        super().__init__()

        self.rebuildMaps()

    def resourcePath(self, filename):
        scriptedModulesPath = os.path.dirname(slicer.util.modulePath("LandmarkManager"))
        return os.path.join(scriptedModulesPath, "Resources", filename)

    def reconnect(self):
        self.removeObservers()

        if self.landmarks:
            for event in [
                slicer.vtkMRMLMarkupsNode.PointAddedEvent,
                slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
                slicer.vtkMRMLMarkupsNode.PointRemovedEvent,
            ]:
                self.addObserver(self.landmarks, event, self.rebuildMaps)

    @property
    def positions(self):
        data = {}
        for name, idx in self.landmarkIndexes.items():
            point = [0, 0, 0]
            self.landmarks.GetNthControlPointPositionWorld(idx, point)
            data[name] = point

        return data

    def rebuildMaps(self, sender=None, event=None):
        landmarks = self.landmarks
        indexes = {}

        if landmarks is not None:
            for idx in range(landmarks.GetNumberOfControlPoints()):
                label = landmarks.GetNthControlPointLabel(idx)
                status = landmarks.GetNthControlPointPositionStatus(idx)

                if status == landmarks.PositionDefined:
                    indexes[label] = idx

        self.landmarkIndexes = indexes

    def setupPlanningLandmarksNode(self):
        if not self.landmarks:
            node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode",
                "PLANNING_LANDMARKS",
            )
            node.CreateDefaultDisplayNodes()

            self.landmarks = node
        display = self.landmarks.GetDisplayNode()
        display.SetUseGlyphScale(False)
        display.SetGlyphSize(6)  # 4mm
        display.SetColor(90 / 255.0, 194 / 255.0, 201 / 255.0)
        display.SetSelectedColor(90 / 255.0, 194 / 255.0, 201 / 255.0)
        self.rebuildMaps()
        self.reconnect()

    def clearPlanningLandmarks(self):
        slicer.mrmlScene.RemoveNode(self.landmarks)


class PlanningLandmarkTableManager(VTKObservationMixin):
    @property
    def advanceButton(self):
        return self._advanceButton

    @advanceButton.setter
    def advanceButton(self, value):
        self._advanceButton = value
        self.updateAdvanceButton()

    def __init__(self, logic, table, icons):
        super().__init__()

        self._advanceButton = None

        self.logic = logic
        self.table = table
        self.icons = icons

        self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        self.selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")

        self._initTable()

    def updateAdvanceButton(self):
        if not self.advanceButton:
            return

        collectedCount = len(self.logic.landmarkIndexes)
        requiredCount = self.logic.LANDMARKS_NEEDED
        remainingCount = requiredCount - collectedCount
        remainingCount = 0 if remainingCount < 0 else remainingCount

        if remainingCount:
            unit = "landmark" if remainingCount == 1 else "landmarks"
            self.advanceButton.text = f"Place {remainingCount} more {unit}"
            self.advanceButton.enabled = False
        else:
            self.advanceButton.text = "Press to continue"
            self.advanceButton.enabled = True

    def _initTable(self):
        self.table.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, qt.QHeaderView.ResizeToContents)

        self.table.clear()

        self.table.setFrameStyle(qt.QFrame.NoFrame)

        for row, name in enumerate(self.logic.requiredLandmarks):
            self.table.insertRow(row)

            iconLabel = qt.QLabel()
            iconLabel.setAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
            self.table.setCellWidget(row, 0, iconLabel)

            nameLabel = qt.QLabel(name)
            nameLabel.setAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
            nameLabel.setStyleSheet("QLabel{font-size: 18px;}")
            self.table.setCellWidget(row, 1, nameLabel)

            button = qt.QPushButton("")
            button.minimumWidth = 80
            button.maximumHeight = 32
            button.enabled = True
            button.clicked.connect(lambda state, name=name, row=row: self.onButtonClick(name, row))
            self.table.setCellWidget(row, 2, button)

        self.updateLandmarksDisplay()

    def reconnect(self):
        self.removeObservers()
        if self.logic.landmarks:
            for event in [
                slicer.vtkMRMLMarkupsNode.PointAddedEvent,
                slicer.vtkMRMLMarkupsNode.PointModifiedEvent,
                slicer.vtkMRMLMarkupsNode.PointRemovedEvent,
            ]:
                self.addObserver(self.logic.landmarks, event, self.onPointsChanged)

    def updateLandmarkDisplay(self, name, row):
        iconLabel = self.table.cellWidget(row, 0)
        nameLabel = self.table.cellWidget(row, 1)
        button = self.table.cellWidget(row, 2)

        if name in self.logic.landmarkIndexes:  # position is defined
            iconLabel.setPixmap(self.icons["Done"].pixmap(32, 32))
            nameLabel.text = name
            button.text = "Remove"
        else:
            iconLabel.setPixmap(self.icons["NotStarted"].pixmap(32, 32))
            nameLabel.text = name
            button.text = "Place"

    def updateLandmarksDisplay(self):
        for row, name in enumerate(self.logic.requiredLandmarks):
            self.updateLandmarkDisplay(name, row)

    def onPointsChanged(self, sender=None, event=None):
        self.updateLandmarksDisplay()
        self.updateAdvanceButton()

    def onButtonClick(self, name, row):
        if name in self.logic.landmarkIndexes:
            # position is defined, so remove point
            # triggers onPointsChanged
            self.logic.landmarks.RemoveNthControlPoint(self.logic.landmarkIndexes[name])
        else:
            # position is not defined, so add point
            # once user defs point, triggers onPointsChanged
            self.selectionNode.SetActivePlaceNodeID(self.logic.landmarks.GetID())
            self.selectionNode.SetActivePlaceNodeClassName(self.logic.landmarks.GetClassName())
            self.interactionNode.SetCurrentInteractionMode(self.interactionNode.Place)
            self.logic.landmarks.SetMarkupLabelFormat(name)  # names next markup even if cursor moves between views


class LandmarkState(Enum):
    # From Registration/RegistrationUtils/Landmarks.py
    NOT_STARTED = 0
    IN_PROGRESS = 1
    DONE = 2
    SKIPPED = 3


class Landmark:
    # From Registration/RegistrationUtils/Landmarks.py
    def __init__(self, name, modelPos=[0, 0, 0]):
        self.name = name
        self.row = -1
        self.index = -1
        self.state = LandmarkState.NOT_STARTED
        self.modelPosition = modelPos
        self.imagePosition = None
        self.trackerPosition = None
        self.ignore = False


class Landmarks(ScriptedLoadableModuleLogic):
    trackerLandmarks = OpenNavUtils.nodeReferenceProperty("TRACKER_LANDMARKS", default=None)
    # From Registration/RegistrationUtils/Landmarks.py

    def __init__(self, tableWidget, moduleName, collectButton):
        super().__init__()
        self.landmarkStates = []
        self.moduleName = moduleName
        self.tableWidget = tableWidget
        self.currentLandmark = None
        self.collectButton = collectButton
        self.tableWidget.setShowGrid(False)
        self.tableWidget.setFocusPolicy(qt.Qt.NoFocus)
        self.tableWidget.setSelectionMode(qt.QAbstractItemView.NoSelection)
        self.tableWidget.setFrameStyle(qt.QFrame.NoFrame)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.Stretch)
        self.tableWidget.horizontalHeader().setSectionResizeMode(2, qt.QHeaderView.ResizeToContents)

        self.landmarksNeeded = 3
        self.landmarksCollected = 0
        self.landmarksFinished = False
        self.advanceButton = None
        self.model = None

        # TODO: improve method of looking up icons
        self.notStartedIcon = qt.QIcon(self.resourcePath("Icons/NotStarted.svg"))
        self.doneIcon = qt.QIcon(self.resourcePath("Icons/Done.svg"))
        self.SkippedIcon = qt.QIcon(self.resourcePath("Icons/Skipped.svg"))
        self.startedIcon = qt.QIcon(self.resourcePath("Icons/Started.svg"))
        self.landmarksGuidanceNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Landmarks")
        self.landmarksGuidanceNode.GetMarkupsDisplayNode().SetVisibility(False)
        self.landmarksGuidanceNode.GetMarkupsDisplayNode().SetSelectedColor(90 / 255.0, 194 / 255.0, 201 / 255.0)
        self.landmarksGuidanceNode.GetMarkupsDisplayNode().SetColor(72 / 255.0, 72 / 255.0, 72 / 255.0)
        self.landmarksGuidanceNode.GetMarkupsDisplayNode().SetTextScale(0)
        self.landmarksGuidanceNode.GetMarkupsDisplayNode().SetUseGlyphScale(False)
        self.landmarksGuidanceNode.GetMarkupsDisplayNode().SetGlyphSize(6)
        self.landmarksGuidanceNode.SetLocked(True)
        self.landmarksGuidanceNode.SaveWithSceneOff()

        self.landmarksInProgressNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "LandmarkInProgress")
        self.landmarksInProgressNode.GetMarkupsDisplayNode().SetVisibility(False)
        self.landmarksInProgressNode.GetMarkupsDisplayNode().SetSelectedColor(255 / 255.0, 85 / 255.0, 0 / 255.0)
        self.landmarksInProgressNode.GetMarkupsDisplayNode().SetColor(255 / 255.0, 85 / 255.0, 0 / 255.0)
        self.landmarksInProgressNode.GetMarkupsDisplayNode().SetTextScale(0)
        self.landmarksInProgressNode.GetMarkupsDisplayNode().SetUseGlyphScale(False)
        self.landmarksInProgressNode.GetMarkupsDisplayNode().SetGlyphSize(8)
        self.landmarksInProgressNode.SetLocked(True)
        self.landmarksInProgressNode.SaveWithSceneOff()
        self.landmarksInProgressNode.AddControlPoint(0, 0, 0)
        self.showLandmarks = False

    def updateAdvanceButton(self):
        landmarksRemaining = self.landmarksNeeded - self.landmarksCollected
        self.advanceButton.enabled = False
        if landmarksRemaining > 1:
            self.advanceButton.text = "Touch " + str(landmarksRemaining) + " more landmarks"
        elif landmarksRemaining == 1:
            self.advanceButton.text = "Touch 1 more landmark"
        else:
            self.advanceButton.text = "Press to continue"
            self.advanceButton.enabled = True

    def resourcePath(self, filename):
        scriptedModulesPath = os.path.dirname(slicer.util.modulePath(self.moduleName))
        return os.path.join(scriptedModulesPath, "Resources", filename)

    def addLandmark(self, name, modelPos=[0, 0, 0]):
        newLandmark = Landmark(name, modelPos)
        self.addLandmarkToTable(newLandmark)

        self.landmarkStates.append(newLandmark)
        newLandmark.index = self.landmarksGuidanceNode.AddControlPoint(modelPos[0], modelPos[1], modelPos[2])
        self.updateLandmarkDisplay(newLandmark)

    def addLandmarkToTable(self, landmark):
        row = self.tableWidget.rowCount
        self.tableWidget.insertRow(row)
        landmark.row = row
        iconLabel = qt.QLabel()
        iconLabel.setAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
        iconLabel.setPixmap(self.notStartedIcon.pixmap(32, 32))
        nameLabel = qt.QLabel(landmark.name)
        nameLabel.setAlignment(qt.Qt.AlignHCenter | qt.Qt.AlignVCenter)
        nameLabel.setStyleSheet("QLabel{font-size: 18px;}")
        nameLabel.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)
        button = qt.QPushButton("")
        button.enabled = False
        button.clicked.connect(lambda state, x=landmark: self.updateLandmark(x))
        button.minimumWidth = 80
        button.maximumHeight = 32
        # button.setSizePolicy(qt.QSizePolicy.Fixed, qt.QSizePolicy.Fixed)
        self.tableWidget.setCellWidget(row, 0, iconLabel)
        self.tableWidget.setCellWidget(row, 1, nameLabel)
        self.tableWidget.setCellWidget(row, 2, button)

    def transferPlanningLandmarks(self, positions):
        self.tableWidget.rowCount = 0
        self.landmarkStates = []
        self.currentLandmark = None
        self.landmarksGuidanceNode.RemoveAllControlPoints()
        # positions[name] = position
        self.landmarksNeeded = 0
        for name, position in positions.items():
            self.addLandmark(name, position)
            self.landmarksNeeded += 1

    def updateLandmarksDisplay(self):
        self.landmarksCollected = 0
        for landmark in self.landmarkStates:
            self.updateLandmarkDisplay(landmark)
        if self.model:
            self.model.GetDisplayNode().SetVisibility(self.showLandmarks)
        self.landmarksGuidanceNode.GetDisplayNode().SetVisibility(self.showLandmarks)
        self.landmarksInProgressNode.GetDisplayNode().SetVisibility(self.showLandmarks)

        self.landmarksFinished = self.landmarksCollected >= self.landmarksNeeded
        self.collectButton.enabled = not self.landmarksFinished
        if self.showLandmarks:
            self.updateAdvanceButton()

    def setLandmarkInProgressDisplay(self, landmark):
        pos = [0, 0, 0]
        self.landmarksGuidanceNode.GetNthControlPointPositionWorld(landmark.row, pos)
        self.landmarksInProgressNode.SetNthControlPointPositionWorld(0, pos[0], pos[1], pos[2])
        self.landmarksInProgressNode.SetNthControlPointVisibility(0, True)

    def updateLandmarkDisplay(self, landmark):
        button = self.tableWidget.cellWidget(landmark.row, 2)
        iconLabel = self.tableWidget.cellWidget(landmark.row, 0)
        self.landmarksGuidanceNode.SetNthControlPointSelected(landmark.row, False)
        self.landmarksGuidanceNode.SetNthControlPointVisibility(landmark.row, True)
        if landmark.state == LandmarkState.NOT_STARTED:
            button.enabled = True
            button.text = "Select"
            iconLabel.setPixmap(self.notStartedIcon.pixmap(32, 32))

        if landmark.state == LandmarkState.IN_PROGRESS:
            button.enabled = False
            button.text = "(active)"
            iconLabel.setPixmap(self.startedIcon.pixmap(32, 32))
            self.setLandmarkInProgressDisplay(landmark)

        if landmark.state == LandmarkState.DONE:
            button.enabled = True
            button.text = "Redo"
            iconLabel.setPixmap(self.doneIcon.pixmap(32, 32))
            self.landmarksGuidanceNode.SetNthControlPointSelected(landmark.row, True)
            self.landmarksCollected += 1

    def startNextLandmark(self):
        indexList = list(range(0, len(self.landmarkStates)))
        if self.currentLandmark is not None:
            currentIndex = self.landmarkStates.index(self.currentLandmark)
            rotate = currentIndex + 1
            indexList = indexList[rotate:] + indexList[:rotate]

        self.currentLandmark = None
        self.landmarksInProgressNode.SetNthControlPointVisibility(0, False)
        for index in indexList:
            landmark = self.landmarkStates[index]
            if landmark.state == LandmarkState.NOT_STARTED:
                self.startLandmark(landmark)
                break
        self.updateLandmarksDisplay()

    def startLandmark(self, landmark):
        if self.currentLandmark is not None:
            # cancel current landmark if not done
            if self.currentLandmark.state == LandmarkState.IN_PROGRESS:
                self.currentLandmark.state = LandmarkState.NOT_STARTED

        landmark.state = LandmarkState.IN_PROGRESS
        self.currentLandmark = landmark
        self.updateLandmarksDisplay()

    def collectLandmarkPosition(self, pos=[0, 0, 0]):
        if self.currentLandmark is not None:
            print(self.currentLandmark.name)
            self.currentLandmark.state = LandmarkState.DONE
            self.currentLandmark.trackerPosition = pos
            self.syncTrackerNode(self.currentLandmark.name, pos)
            self.startNextLandmark()
        else:
            print("Warning - landmark is none")

    def getTrackerPosition(self, name):
        for landmark in self.landmarkStates:
            if landmark.name == name:
                return landmark.trackerPosition

    def syncTrackerPosition(self, name, pos):
        for landmark in self.landmarkStates:
            if landmark.name == name:
                landmark.trackerPosition = pos
                landmark.state = LandmarkState.DONE
                print("name: " + name + " done")

    def syncTrackerNode(self, name, pos):
        for idx in range(0, self.trackerLandmarks.GetNumberOfControlPoints()):
            node_name = self.trackerLandmarks.GetNthControlPointLabel(idx)
            if node_name == name:
                self.trackerLandmarks.SetNthControlPointPositionWorld(idx, pos[0], pos[1], pos[2])
                return
        self.trackerLandmarks.AddControlPointWorld(vtk.vtkVector3d(pos), name)

    def updateLandmark(self, landmark):
        if landmark.state == LandmarkState.IN_PROGRESS:
            landmark.state = LandmarkState.NOT_STARTED
            self.startNextLandmark()
            self.updateLandmarkDisplay(landmark)
        elif landmark.state == LandmarkState.DONE:
            landmark.state = LandmarkState.IN_PROGRESS
            self.startLandmark(landmark)
        elif landmark.state == LandmarkState.NOT_STARTED:
            landmark.state = LandmarkState.IN_PROGRESS
            self.startLandmark(landmark)

    def clearLandmarks(self):
        for landmark in self.landmarkStates:
            landmark.state = LandmarkState.NOT_STARTED
            landmark.trackerPosition = None

        self.updateLandmarksDisplay()

    def syncLandmarks(self):
        if not self.trackerLandmarks:
            return
        if self.trackerLandmarks.GetNumberOfControlPoints() == 0:
            return

        self.clearLandmarks()

        for idx in range(0, self.trackerLandmarks.GetNumberOfControlPoints()):
            point = [0, 0, 0]
            self.trackerLandmarks.GetNthControlPointPositionWorld(idx, point)
            name = self.trackerLandmarks.GetNthControlPointLabel(idx)
            self.syncTrackerPosition(name, point)

        self.updateLandmarksDisplay()

    def setupTrackerLandmarksNode(self):
        if not self.trackerLandmarks:
            node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode",
                "TRACKER_LANDMARKS",
            )
            node.CreateDefaultDisplayNodes()
            self.trackerLandmarks = node
        self.trackerLandmarks.GetDisplayNode().SetVisibility(False)

    def clearTrackerLandmarks(self):
        slicer.mrmlScene.RemoveNode(self.trackerLandmarks)
