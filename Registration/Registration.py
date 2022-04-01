import qt
import slicer
import vtk

from slicer.ScriptedLoadableModule import (
  ScriptedLoadableModule,
  ScriptedLoadableModuleLogic,
  ScriptedLoadableModuleWidget,
)

import NNUtils
import Home

from LandmarkManager import Landmarks
from RegistrationUtils import Tools


class Registration(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NousNav Registration"
    self.parent.categories = [""]
    self.parent.dependencies = ["Tracking", "PivotCalibration"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the Registration main module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class RegistrationWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    super().__init__(parent)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Registration.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    self.workflow = Home.Workflow(
      'registration',
      nested=(
        Home.Workflow("patient-prep", setup=self.registrationStepPatientPrep, widget=self.ui.RegistrationStepPatientPrep),
        Home.Workflow("tracking-prep", setup=self.registrationStepTrackingPrep, widget=self.ui.RegistrationStepTrackingPrep),
        Home.Workflow("pointer-prep", setup=self.registrationStepPointerPrep, widget=self.ui.RegistrationStepPointerPrep),
        Home.Workflow("align-camera", setup=self.registrationStepAlignCamera, widget=self.ui.RegistrationStepAlignCamera),
        Home.Workflow("pivot-calibration", setup=self.registrationStepPivotCalibration, widget=self.ui.RegistrationStepPivotCalibration),
        Home.Workflow("spin-calibration", setup=self.registrationStepSpinCalibration, widget=self.ui.RegistrationStepSpinCalibration),
        Home.Workflow("landmark-registration", setup=self.registrationStepLandmarkRegistration, widget=self.ui.RegistrationStepLandmarkRegistration),
        Home.Workflow(
          "verify-registration",
          setup=self.registrationStepVerifyRegistration,
          widget=self.ui.RegistrationStepVerifyRegistration,
          teardown=self.registrationStepAcceptRegistration,
          ),
      ),
      setup=self.enter,
      teardown=self.exit,
    )

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.AlignmentSideWidget = slicer.util.loadUI(self.resourcePath('UI/AlignmentSideWidget.ui'))
    self.AlignmentSideWidgetui = slicer.util.childWidgetVariables(self.AlignmentSideWidget)
    self.LandmarkSideWidget = slicer.util.loadUI(self.resourcePath('UI/LandmarkSideWidget.ui'))
    self.LandmarkSideWidgetui = slicer.util.childWidgetVariables(self.LandmarkSideWidget)

    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelWidget')
    sidePanel.layout().addWidget(self.AlignmentSideWidget)
    sidePanel.layout().addWidget(self.LandmarkSideWidget)
    self.AlignmentSideWidget.visible = False
    self.LandmarkSideWidget.visible = False

    # Create logic class
    self.logic = RegistrationLogic()

    # Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    # Bottom toolbar
    (
      self.bottomToolBar,
      self.backButton,
      self.backButtonAction,
      self.advanceButton,
      self.advanceButtonAction,
    ) = NNUtils.setupWorkflowToolBar("Registration")

    # Registration Tab Bar
    self.registrationTabBar = qt.QTabBar()
    self.registrationTabBar.setObjectName("RegistrationTabBar")
    NNUtils.addCssClass(self.registrationTabBar, "secondary-tabbar")
    self.registrationTabBar.visible = False
    secondaryTabWidget = slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryCenteredWidget')
    secondaryTabWidgetUI = slicer.util.childWidgetVariables(secondaryTabWidget)
    secondaryTabWidgetUI.CenterArea.layout().addWidget(self.registrationTabBar)

    def addSecondaryTab(name, text=None):
      tabIndex = self.registrationTabBar.addTab(text)
      self.registrationTabBar.setTabData(tabIndex, name)

    addSecondaryTab("patient-prep", "Patient prep")
    addSecondaryTab("tracking-prep", "Tracking devices")
    addSecondaryTab("align-camera", "Camera")
    addSecondaryTab("pivot-calibration", "Calibrate")
    addSecondaryTab("landmark-registration", "Register patient")

    import OptiTrack
    self.optitrack = OptiTrack.OptiTrackLogic()

    self.preloadPictures()
    self.setupToolTables()
    self.setupLandmarkTables()
    self.setupPivotCalibration()

    self.cameraTimer = qt.QTimer()
    self.cameraTimer.interval = 100
    self.cameraTimer.timeout.connect(self.tools.checkTools)

    self.pivotLogic = slicer.vtkSlicerPivotCalibrationLogic()

    self.advanceButton.enabled = False

    self.beep = None
    try:
      self.beep = qt.QSoundEffect()
      self.beep.setSource(qt.QUrl("file:"+self.resourcePath('Data/beep.wav')))
    except AttributeError:
      slicer.util.warningDisplay(
        'Sound playback not supported on this platform. Audio feedback is disabled.',
        'Sound playback error',
      )

  def cleanup(self):
    self.optitrack.shutdown()
    self.setTrackingStatusCheckEnabled(False)

  def exit(self):
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.registrationTabBar.visible = False
    self.bottomToolBar.visible = False

    self.landmarks.showLandmarks = False
    self.landmarks.updateLandmarksDisplay()

  def enter(self):
    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True
    self.registrationTabBar.visible = True

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    for widget in [modulePanel, sidePanel]:
      NNUtils.setCssClass(widget, "widget--color-light")
      NNUtils.polish(widget)

    qt.QTimer.singleShot(1000, self.startOptiTrack)

  def startOptiTrack(self):
    if not self.optitrack.isRunning:
      # launch selector
      self.hardwareSelector = slicer.util.loadUI(self.resourcePath('UI/HardwareDialog.ui'))
      self.selectorUI = slicer.util.childWidgetVariables(self.hardwareSelector)
      self.hardwareSelector.accepted.connect(self.launchOptiTrack)
      self.hardwareSelector.open()
    else:
        self.advanceButton.enabled = True

  def launchOptiTrack(self):

    filename =  ''

    if self.selectorUI.KitwareRadioButton.checked:
      filename = 'MotiveProfile-2021-10-22.xml'

    if self.selectorUI.BWHRadioButton.checked:
      filename = 'NousNav-BWH-Hardware.xml'

    test = qt.QMessageBox(qt.QMessageBox.Information, "Starting", "Starting tracker", qt.QMessageBox.NoButton)
    test.setStandardButtons(0)
    test.show()
    slicer.app.processEvents()
    test.deleteLater()
    self.optitrack.start(self.optitrack.getPlusLauncherPath(), self.resourcePath('PLUSHead.xml.in'), self.resourcePath(filename))
    test.hide()

    if not self.optitrack.isRunning:
      qt.QMessageBox.warning(slicer.util.mainWindow(), "Tracker not connected", "Tracker not connected")
    else:
      self.advanceButton.enabled = True
      print('enable advance')

  def setTrackingStatusCheckEnabled(self, enabled):
    """Check the status of the tracking tool every 100ms and
    update the table summarizing the status of each tools.

    See :func:`RegistrationUtils.Tools.checkTools`
    and :func:`RegistrationUtils.Tools.updateToolsDisplay()`.
    """
    if enabled:
      # If timer is already started, it will stop and restart it.
      self.cameraTimer.start()
    else:
      self.cameraTimer.stop()

  def stepSetup(self):
    self.tools.showToolMarkers = False
    self.tools.updateToolsDisplay()

    self.landmarks.showLandmarks = False
    self.landmarks.updateLandmarksDisplay()

    self.setTrackingStatusCheckEnabled(False)

  @NNUtils.backButton(text="Return to Planning")
  @NNUtils.advanceButton(text="Setup NousNav")
  def registrationStepPatientPrep(self):

    self.stepSetup()

    # set the layout and display an image
    NNUtils.goToPictureLayout(self.pictures["RegistrationStepPatientPrep.png"])

  @NNUtils.backButton(text="Back")
  @NNUtils.advanceButton(text="Press when done")
  def registrationStepTrackingPrep(self):

    self.stepSetup()

    # set the layout and display an image
    NNUtils.goToPictureLayout(self.pictures["RegistrationStepTrackingPrep.png"])

  @NNUtils.backButton(text="Back")
  @NNUtils.advanceButton(text="Press when done")
  def registrationStepPointerPrep(self):

    self.stepSetup()

    # set the layout and display an image
    NNUtils.goToPictureLayout(self.pictures["RegistrationStepPointerPrep.jpg"])

  @NNUtils.backButton(text="Back")
  @NNUtils.advanceButton(text="Press when done")
  def registrationStepAlignCamera(self):

    self.stepSetup()

    # set the layout and display an image
    NNUtils.goToRegistrationCameraViewLayout()
    self.AlignmentSideWidget.visible = True
    self.LandmarkSideWidget.visible = False

    self.tools.showToolMarkers = True

    self.setTrackingStatusCheckEnabled(True)

    qt.QTimer.singleShot(1000, lambda: NNUtils.centerCam())

  @NNUtils.backButton(text="Back")
  @NNUtils.advanceButton(text="Press when done")
  def registrationStepPivotCalibration(self):

    self.stepSetup()

    # set the layout and display an image
    NNUtils.goToPictureLayout(self.pictures["RegistrationStepPivotCalibration.png"], sidePanelVisible=True)
    self.AlignmentSideWidget.visible = True
    self.LandmarkSideWidget.visible = False

    self.setTrackingStatusCheckEnabled(True)

    self.ui.RMSLabel.text = ''
    self.ui.PivotCalibrationButton.text = 'Start Pivot Calibration'

    # set the button actions
    self.disconnectAll(self.ui.PivotCalibrationButton)
    self.ui.PivotCalibrationButton.clicked.connect(self.onPivotCalibrationButton)

  def onPivotCalibrationButton(self):
    # setup pivot cal
    try:
      pointerToHeadFrame = slicer.util.getNode('PointerToHeadFrame')
      self.pivotLogic.SetAndObserveTransformNode(pointerToHeadFrame)
      tipToPointer = slicer.util.getNode('TipToPointer')
      tipToPointer.SetAndObserveTransformNodeID(pointerToHeadFrame.GetID())
      print('Starting pre-record period')
      self.ui.PivotCalibrationButton.text = 'Pivot calibration in progress'
      qt.QTimer.singleShot(5000, self.startPivotCalibration)
    except:
      pass

  def startPivotCalibration(self):
    self.pivotLogic.SetRecordingState(True)
    print('Start recording')
    qt.QTimer.singleShot(5000, self.endPivotCalibration)

  def endPivotCalibration(self):
    outputMatrix = vtk.vtkMatrix4x4()
    tipToPointer = slicer.util.getNode('TipToPointer')
    tipToPointer.GetMatrixTransformToParent(outputMatrix)
    self.pivotLogic.SetToolTipToToolMatrix(outputMatrix)
    self.pivotLogic.SetRecordingState(False)
    print('End recording')
    self.ui.PivotCalibrationButton.text = 'Pivot calibration complete'
    self.pivotLogic.ComputePivotCalibration()
    self.pivotLogic.GetToolTipToToolMatrix(outputMatrix)
    tipToPointer.SetMatrixTransformToParent(outputMatrix)

    RMSE = self.pivotLogic.GetPivotRMSE()
    self.pivotLogic.ClearToolToReferenceMatrices()

    self.ui.RMSLabel.text = 'RMS Error: ' + str(RMSE)

    if self.beep:
      self.beep.play()

  def setupPivotCalibration(self):
    # create output transform
    try:
      tipToPointer = slicer.util.getNode('TipToPointer')
    except:
      tipToPointer = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', 'TipToPointer')
      tipToPointer.SaveWithSceneOff()
    properties = {}
    properties['show'] = False
    createModelsLogic = slicer.modules.createmodels.logic()
    self.needleModel = createModelsLogic.CreateNeedle(80.0, 1.0, 2.5, False)
    self.needleModel.SetName('PointerModel')
    self.needleModel.GetDisplayNode().SetColor(255,255,0)
    self.needleModel.GetDisplayNode().SetVisibility(False)
    self.needleModel.SetAndObserveTransformNodeID(tipToPointer.GetID())
    self.needleModel.SaveWithSceneOff()

  @NNUtils.backButton(text="Back")
  @NNUtils.advanceButton(text="Press when done")
  def registrationStepSpinCalibration(self):

    self.stepSetup()

    # set the layout and display an image
    NNUtils.goToPictureLayout(self.pictures["RegistrationStepSpinCalibration.png"], sidePanelVisible=True)
    self.AlignmentSideWidget.visible = True
    self.LandmarkSideWidget.visible = False

    self.setTrackingStatusCheckEnabled(True)

    self.ui.RMSLabelSpin.text = ''
    self.ui.SpinCalibrationButton.text = 'Start Spin Calibration'

    # set the button actions
    self.disconnectAll(self.ui.SpinCalibrationButton)
    self.ui.SpinCalibrationButton.clicked.connect(self.onSpinCalibrationButton)

  def onSpinCalibrationButton(self):
    # setup spin cal
    try:
      pointerToHeadFrame = slicer.util.getNode('PointerToHeadFrame')
      self.pivotLogic.SetAndObserveTransformNode(pointerToHeadFrame)
      tipToPointer = slicer.util.getNode('TipToPointer')
      tipToPointer.SetAndObserveTransformNodeID(pointerToHeadFrame.GetID())
      print('Starting pre-record period')
      self.ui.SpinCalibrationButton.text = 'Spin calibration in progress'
      qt.QTimer.singleShot(5000, self.startSpinCalibration)
    except:
      pass

  def startSpinCalibration(self):
    self.pivotLogic.SetRecordingState(True)
    print('Start recording')
    qt.QTimer.singleShot(5000, self.endSpinCalibration)

  def endSpinCalibration(self):
    outputMatrix = vtk.vtkMatrix4x4()
    tipToPointer = slicer.util.getNode('TipToPointer')
    tipToPointer.GetMatrixTransformToParent(outputMatrix)
    self.pivotLogic.SetToolTipToToolMatrix(outputMatrix)
    self.pivotLogic.SetRecordingState(False)
    print('End recording')
    self.ui.SpinCalibrationButton.text = 'Spin calibration complete'
    self.pivotLogic.ComputeSpinCalibration()
    self.pivotLogic.GetToolTipToToolMatrix(outputMatrix)
    tipToPointer.SetMatrixTransformToParent(outputMatrix)

    RMSE = self.pivotLogic.GetSpinRMSE()
    self.pivotLogic.ClearToolToReferenceMatrices()

    self.ui.RMSLabelSpin.text = 'RMS Error: ' + str(RMSE)

    if self.beep:
      self.beep.play()

  @NNUtils.backButton(text="Recalibrate")
  @NNUtils.advanceButton(text="")
  def registrationStepLandmarkRegistration(self):
    # Set the layout and display an image
    NNUtils.goToRegistrationCameraViewLayout()
    self.AlignmentSideWidget.visible = False
    self.LandmarkSideWidget.visible = True

    self.landmarks.advanceButton = self.advanceButton
    self.landmarks.showLandmarks = True
    self.landmarks.updateLandmarksDisplay()
    NNUtils.centerCam()

    # set the button labels
    self.landmarks.updateAdvanceButton()

    # set the button actions
    self.disconnectAll(self.ui.CollectButton)
    self.ui.CollectButton.clicked.connect(self.onCollectButton)

    # set the frame in stacked widget
    self.landmarks.startNextLandmark()

  @NNUtils.backButton(text="Start over")
  @NNUtils.advanceButton(text="Accept", enabled=False)
  def registrationStepVerifyRegistration(self):
    # set the layout and display an image
    try:
      masterNode = slicer.modules.PlanningWidget.logic.master_volume
    except:
      masterNode = None
      print('No master volume node is loaded')
    NNUtils.goToNavigationLayout(volumeNode=masterNode, mainPanelVisible=True)

    self.AlignmentSideWidget.visible = False
    self.LandmarkSideWidget.visible = False

    self.landmarks.showLandmarks = False
    self.landmarks.updateLandmarksDisplay()
    NNUtils.centerCam()

    self.fidicialOnlyRegistration()

    # set the button actions
    self.disconnectAll(self.ui.CollectButton)

    self.setRestartRegistrationButtonEnabled(True)

  def setRestartRegistrationButtonEnabled(self, enabled):
    self.disconnectAll(self.backButton)
    self.advanceButton.enabled = True
    if enabled:
      self.backButton.clicked.connect(self.restartRegistration)
    else:
      self.backButton.clicked.connect(self.workflow.gotoPrev)

  def registrationStepAcceptRegistration(self):
    self.setRestartRegistrationButtonEnabled(False)
    self.needleModel.GetDisplayNode().SetVisibility(False)
    self.needleModel.GetDisplayNode().SetVisibility2D(False)

    planningLogic = slicer.modules.PlanningWidget.logic

    planningLogic.setPlanningNodesVisibility(skinSegmentation=False, seedSegmentation=False, trajectory=False)

  def restartRegistration(self):
    print('Restarting')
    self.workflow.gotoByName(("nn", "registration", "landmark-registration"))

  def fidicialOnlyRegistration(self):
    try:
      pointerToHeadFrame = slicer.util.getNode('PointerToHeadFrame')
    except:
      print('Nodes missing, tracker not connected!!!')
      pointerToHeadFrame = None

    fromMarkupsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'From')
    toMarkupsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'To')
    defs = slicer.modules.PlanningWidget.landmarkLogic
    for name, position in defs.positions.items():
      toMarkupsNode.AddFiducial(position[0], position[1], position[2] )
      pos = self.landmarks.getTrackerPosition(name)
      fromMarkupsNode.AddFiducial(pos[0], pos[1], pos[2])

    # Create transform node to hold the computed registration result
    try:
      self.transformNode = slicer.util.getNode('HeadFrameToImage')
    except:
      self.transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode")
      self.transformNode.SetName("HeadFrameToImage")
      self.transformNode.SaveWithSceneOff()

    # Create your fiducial wizard node and set the input parameters
    fiducialRegNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLFiducialRegistrationWizardNode', 'Registration')

    fiducialRegNode.SetAndObserveFromFiducialListNodeId(fromMarkupsNode.GetID())
    fiducialRegNode.SetAndObserveToFiducialListNodeId(toMarkupsNode.GetID())
    fiducialRegNode.SetOutputTransformNodeId(self.transformNode.GetID())
    fiducialRegNode.SetRegistrationModeToSimilarity()

    fromMarkupsNode.SetAndObserveTransformNodeID(self.transformNode.GetID())
    self.needleModel.GetDisplayNode().SetVisibility(True)
    self.needleModel.GetDisplayNode().SetVisibility2D(True)
    self.needleModel.GetDisplayNode().SetSliceIntersectionThickness(6)
    if pointerToHeadFrame:
      pointerToHeadFrame.SetAndObserveTransformNodeID(self.transformNode.GetID())

    slicer.mrmlScene.RemoveNode(fromMarkupsNode)
    slicer.mrmlScene.RemoveNode(toMarkupsNode)

    planningLogic = slicer.modules.PlanningWidget.logic

    if planningLogic.skin_segmentation:
      planningLogic.skin_segmentation.SetDisplayVisibility(True)
      planningLogic.skin_segmentation.GetDisplayNode().SetVisibility2D(False)

  def onCollectButton(self):
    print('Attempt collection')

    print('Unobserve registration transform')
    try:
      pointerToHeadFrame = slicer.util.getNode('PointerToHeadFrame')
      pointerToHeadFrame.SetAndObserveTransformNodeID(None)
    except:
      print("Warning!! Tracker not connected")

    try:
      tipToPointer = slicer.util.getNode('TipToPointer')
      samplePoint = [0,0,0]
      outputPoint = [0,0,0]
      transform = vtk.vtkGeneralTransform()
      slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(tipToPointer, None, transform)
      transform.TransformPoint(samplePoint, outputPoint)
      # print(outputPoint)
      self.landmarks.collectLandmarkPosition(outputPoint)
      if self.beep:
        self.beep.play()
    except:
      print('Could not get tip node')

    print('Reobserve registration transform')
    try:
      pointerToHeadFrame = slicer.util.getNode('PointerToHeadFrame')
      transformNode = slicer.util.getNode('HeadFrameToImage')
      pointerToHeadFrame.SetAndObserveTransformNodeID(transformNode.GetID())
    except:
      print("No previous registration")

  def setupToolTables(self):
    self.tools = Tools(self.AlignmentSideWidgetui.SeenTableWidget, self.AlignmentSideWidgetui.UnseenTableWidget, self.moduleName)
    node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Pointer')
    node.AddFiducial(0,0,0, 'Pointer')
    node.SaveWithSceneOff()
    node.GetDisplayNode().SetGlyphScale(13)
    node2 = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Reference Frame')
    node2.AddFiducial(0,0,0, 'Reference Frame')
    node2.SaveWithSceneOff()
    node2.GetDisplayNode().SetGlyphScale(13)

    self.tools.addTool('PointerToTracker', 'Pointer', node)
    self.optitrack.setTools(['PointerToHeadFrame'])
    self.optitrack.setTools(['PointerToTracker'])

    self.tools.addTool('HeadFrameToTracker', 'Reference Frame', node2)
    self.optitrack.setTools(['HeadFrameToTracker'])
    self.tools.optitrack = self.optitrack

  def setupLandmarkTables(self):
    self.landmarks = Landmarks(self.LandmarkSideWidgetui.LandmarkTableWidget, self.moduleName)
    # self.landmarks.addLandmark('Inion', [-1.912, 112.455, -151.242])
    # self.landmarks.addLandmark('Left tragus', [-73.714, 189.367, -162.215])
    self.landmarks.addLandmark('Left outer canthus', [-46.945, 256.678, -150.139])
    # self.landmarks.addLandmark('Left inner canthus', [-15.406, 265.77, -153.487])
    # self.landmarks.addLandmark('Nasion',[-1.990, 281.283, -142.598])
    self.landmarks.addLandmark('Acanthion', [-2.846, 278.845, -193.982])
    # self.landmarks.addLandmark('Right inner canthus', [16.526, 264.199, -155.210])
    self.landmarks.addLandmark('Right outer canthus', [46.786, 252.705, -149.633])
    # self.landmarks.addLandmark('Right tragus', [65.648, 189.888, -163.348])
    self.landmarks.advanceButton = self.advanceButton

  def disconnectAll(self, widget):
    try: widget.clicked.disconnect()
    except Exception: pass

  def preloadPictures(self):
    pictureNames = [
      "RegistrationStepPatientPrep.png",
      "RegistrationStepTrackingPrep.png",
      "RegistrationStepPointerPrep.jpg",
      "RegistrationStepAlignCamera.png",
      "RegistrationStepPivotCalibration.png",
      "RegistrationStepSpinCalibration.png",
      ]
    self.pictures = {}
    properties = {}
    properties['show'] = False
    properties['singleFile'] = True
    for image in pictureNames:
      imageNode = slicer.util.loadVolume(self.resourcePath('Images/' + image), properties)
      imageNode.SaveWithSceneOff()
      imageNode.hidden = True
      self.pictures[image] = imageNode


class RegistrationLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    pass
