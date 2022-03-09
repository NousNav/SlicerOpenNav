import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import NNUtils
from LandmarkManager import Landmarks
import RegistrationUtils.Tools as Tools


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

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Registration.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    self.AlignmentSideWidget = slicer.util.loadUI(self.resourcePath('UI/AlignmentSideWidget.ui'))
    self.AlignmentSideWidgetui = slicer.util.childWidgetVariables(self.AlignmentSideWidget)
    self.LandmarkSideWidget = slicer.util.loadUI(self.resourcePath('UI/LandmarkSideWidget.ui'))
    self.LandmarkSideWidgetui = slicer.util.childWidgetVariables(self.LandmarkSideWidget)

    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelWidget')
    sidePanel.layout().addWidget(self.AlignmentSideWidget)
    sidePanel.layout().addWidget(self.LandmarkSideWidget)
    self.AlignmentSideWidget.visible = False
    self.LandmarkSideWidget.visible = False

    #Create logic class
    self.logic = RegistrationLogic()

    #Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    #Bottom toolbar
    self.bottomToolBar = qt.QToolBar("RegistrationBottomToolBar")
    self.bottomToolBar.setObjectName("RegistrationBottomToolBar")
    self.bottomToolBar.movable = False
    slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, self.bottomToolBar)
    self.backButtonReg = qt.QPushButton("Back (reg)")
    self.backButtonReg.name = 'RegistrationBackButton'
    self.backButtonAction = self.bottomToolBar.addWidget(self.backButtonReg)
    spacer = qt.QWidget()
    policy = spacer.sizePolicy
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    spacer.setSizePolicy(policy)
    spacer.name = "RegistrationBottomToolbarSpacer"
    self.bottomToolBar.addWidget(spacer)
    self.advanceButtonReg = qt.QPushButton("Advance (reg)")
    self.advanceButtonReg.name = 'RegistrationAdvanceButton'
    self.advanceButtonAction = self.bottomToolBar.addWidget(self.advanceButtonReg)
    self.bottomToolBar.visible = False

    # Registration Tab Bar
    self.registrationTabBar = qt.QTabBar()
    self.registrationTabBar.setObjectName("RegistrationTabBar")
    self.prepRegistrationTabIndex = self.registrationTabBar.addTab("Patient prep")
    self.trackingTabIndex = self.registrationTabBar.addTab("Tracking devices")
    self.cameraTabIndex = self.registrationTabBar.addTab("Camera")
    self.calibrateRegistrationTabIndex = self.registrationTabBar.addTab("Calibrate")
    self.registerPatientTabIndex = self.registrationTabBar.addTab("Register patient")
    self.registrationTabBar.visible = False
    secondaryTabWidget = slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryCenteredWidget')
    secondaryTabWidgetUI = slicer.util.childWidgetVariables(secondaryTabWidget)
    secondaryTabWidgetUI.CenterArea.layout().addWidget(self.registrationTabBar)

    self.registrationTabBar.currentChanged.connect(self.onTabChanged)

    import OptiTrack
    self.optitrack = OptiTrack.OptiTrackLogic()

    self.preloadPictures()
    self.setupToolTables()
    self.setupLandmarkTables()
    self.setupPivotCalibration()

    self.cameraTimer = None
    self.pivotLogic = slicer.vtkSlicerPivotCalibrationLogic()

    self.advanceButtonReg.enabled = False

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
    if self.cameraTimer:
      self.cameraTimer.stop()

  def exit(self):
    self.landmarks.showLandmarks = False
    self.landmarks.updateLandmarksDisplay()
    # self.goToFourUpLayout()
    print('hide')

  def enter(self):

    #Hides other toolbars
    slicer.util.findChild(slicer.util.mainWindow(), 'BottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'NavigationBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'PlanningBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'PlanningTabBar').visible = False

    #Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True
    self.registrationTabBar.visible = True

    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    self.applyStyle([sidePanel, modulePanel], 'PanelLight.qss')

    self.registrationTabBar.setCurrentIndex(self.prepRegistrationTabIndex)
    self.onTabChanged(self.prepRegistrationTabIndex)

    qt.QTimer.singleShot(1000, self.startOptiTrack)

  def startOptiTrack(self):
    if not self.optitrack.isRunning:
      #launch selector
      self.hardwareSelector = slicer.util.loadUI(self.resourcePath('UI/HardwareDialog.ui'))
      self.selectorUI = slicer.util.childWidgetVariables(self.hardwareSelector)
      self.hardwareSelector.accepted.connect(self.launchOptiTrack)
      self.hardwareSelector.open()
    else:
        self.advanceButtonReg.enabled = True

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
      self.advanceButtonReg.enabled = True
      print('enable advance')

  def onTabChanged(self, index):

    self.tools.showToolMarkers = False
    self.tools.updateToolsDisplay()

    self.landmarks.showLandmarks = False
    self.landmarks.updateLandmarksDisplay()

    if self.cameraTimer:
      self.cameraTimer.stop()

    if index == self.prepRegistrationTabIndex:
      self.registrationStep1()

    if index == self.trackingTabIndex:
      self.registrationStep2()

    if index == self.cameraTabIndex:
      self.registrationStep4()

    if index == self.calibrateRegistrationTabIndex:
      self.registrationStep5()

    if index == self.registerPatientTabIndex:
      self.registrationStep7()
      
  def registrationStep1(self):

    #set the layout and display an image
    self.goToPictureLayout(self.pictures['RegistrationStep1.png'])

    #set the button labels
    self.backButtonReg.text = ''
    self.advanceButtonReg.text = 'Setup NousNav'
    self.backButtonAction.visible = False
    self.advanceButtonAction.visible = True

    #set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)

    self.advanceButtonReg.clicked.connect(lambda:self.registrationTabBar.setCurrentIndex(self.trackingTabIndex))

    #set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep1)

  def registrationStep2(self):

    #set the layout and display an image
    self.goToPictureLayout(self.pictures['RegistrationStep2.png'])

    #set the button labels
    self.backButtonReg.text = 'Back'
    self.advanceButtonReg.text = 'Press when done'
    self.backButtonAction.visible = True
    self.advanceButtonAction.visible = True

    #set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)
    self.backButtonReg.clicked.connect(lambda:self.registrationTabBar.setCurrentIndex(self.prepRegistrationTabIndex))
    self.advanceButtonReg.clicked.connect(lambda: self.registrationStep3())

    #set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep2)

  def registrationStep3(self):

    #update toolbar needed for untabbed step
    self.registrationTabBar.setCurrentIndex(self.trackingTabIndex)

    #set the layout and display an image
    self.goToPictureLayout(self.pictures['RegistrationStep3.jpg'])

    #set the button labels
    self.backButtonReg.text = 'Back'
    self.advanceButtonReg.text = 'Press when done'
    self.backButtonAction.visible = True
    self.advanceButtonAction.visible = True

    #set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)
    self.backButtonReg.clicked.connect(lambda:self.registrationStep2())
    self.advanceButtonReg.clicked.connect(lambda:self.registrationTabBar.setCurrentIndex(self.cameraTabIndex))

    #set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep3)

  def registrationStep4(self):

    #set the layout and display an image
    self.goToRegistrationCameraViewLayout()
    self.AlignmentSideWidget.visible = True
    self.LandmarkSideWidget.visible = False

    self.tools.showToolMarkers = True

    self.cameraTimer = qt.QTimer()
    self.cameraTimer.timeout.connect(self.tools.checkTools)
    self.cameraTimer.start(100)

    qt.QTimer.singleShot(1000, lambda: NNUtils.centerCam())

    #set the button labels
    self.backButtonReg.text = 'Back'
    self.advanceButtonReg.text = 'Press when done'
    self.backButtonAction.visible = True
    self.advanceButtonAction.visible = True

    #set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)
    self.backButtonReg.clicked.connect(lambda:self.registrationStep3())
    self.advanceButtonReg.clicked.connect(lambda:self.registrationTabBar.setCurrentIndex(self.calibrateRegistrationTabIndex))

    #set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep4)

  def registrationStep5(self):

    #set the layout and display an image
    self.goToPictureLayout(self.pictures['RegistrationStep5.png'], True)
    self.AlignmentSideWidget.visible = True
    self.LandmarkSideWidget.visible = False

    self.cameraTimer = qt.QTimer()
    self.cameraTimer.timeout.connect(self.tools.checkTools)
    self.cameraTimer.start(100)

    #set the button labels
    self.backButtonReg.text = 'Back'
    self.advanceButtonReg.text = 'Press when done'
    self.backButtonAction.visible = True
    self.advanceButtonAction.visible = True

    #set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)
    self.disconnectAll(self.ui.PivotCalibrationButton)
    self.backButtonReg.clicked.connect(lambda:self.registrationTabBar.setCurrentIndex(self.cameraTabIndex))
    self.advanceButtonReg.clicked.connect(lambda: self.registrationStep6())
    self.ui.PivotCalibrationButton.clicked.connect(self.onPivotCalibrationButton)

    #set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep5)

  def onPivotCalibrationButton(self):
    #setup pivot cal
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
    #create output transform
    try:
      tipToPointer = slicer.util.getNode('TipToPointer')
    except:
      tipToPointer = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', 'TipToPointer')
    properties = {}
    properties['show'] = False
    createModelsLogic = slicer.modules.createmodels.logic()
    self.needleModel = createModelsLogic.CreateNeedle(80.0, 1.0, 2.5, False)
    self.needleModel.GetDisplayNode().SetColor(255,255,0)
    self.needleModel.GetDisplayNode().SetVisibility(False)
    self.needleModel.SetAndObserveTransformNodeID(tipToPointer.GetID())

  def registrationStep6(self):
    # set the layout and display an image
    self.goToPictureLayout(self.pictures['RegistrationStep6.png'], True)

    # set the button labels
    self.backButtonReg.text = 'Back'
    self.advanceButtonReg.text = 'Press when done'
    self.backButtonAction.visible = True
    self.advanceButtonAction.visible = True

    # set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)
    self.disconnectAll(self.ui.SpinCalibrationButton)
    self.advanceButtonReg.clicked.connect(
        lambda: self.registrationTabBar.setCurrentIndex(self.registerPatientTabIndex))
    self.ui.SpinCalibrationButton.clicked.connect(self.onSpinCalibrationButton)

    # set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep6)

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
  
  def registrationStep7(self):
    #set the layout and display an image
    self.goToRegistrationCameraViewLayout()
    self.AlignmentSideWidget.visible = False
    self.LandmarkSideWidget.visible = True

    self.landmarks.advanceButtonReg = self.advanceButtonReg
    self.landmarks.showLandmarks = True
    self.landmarks.updateLandmarksDisplay()
    NNUtils.centerCam()

    #set the button labels
    self.backButtonReg.text = 'Recalibrate'
    self.landmarks.updateAdvanceButton()
    self.backButtonAction.visible = True
    self.advanceButtonAction.visible = True

    #set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)
    self.disconnectAll(self.ui.CollectButton)
    self.backButtonReg.clicked.connect(lambda:self.registrationTabBar.setCurrentIndex(self.calibrateRegistrationTabIndex))
    self.ui.CollectButton.clicked.connect(self.onCollectButton)
    self.advanceButtonReg.clicked.connect(lambda: self.registrationStep8())

    #set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep7)
    self.landmarks.startNextLandmark()

  def registrationStep8(self):
    #set the layout and display an image
    try:
      masterNode = slicer.modules.PlanningWidget.logic.getMasterVolume()
    except:
      masterNode = None
      print('No master volume node is loaded')
    self.goToFourUpLayout(masterNode)

    self.AlignmentSideWidget.visible = False
    self.LandmarkSideWidget.visible = False

    self.landmarks.showLandmarks = False
    self.landmarks.updateLandmarksDisplay()
    NNUtils.centerCam()

    self.fidicialOnlyRegistration()

    #set the button labels
    self.backButtonReg.text = 'Start over'
    self.advanceButtonReg.text = 'Accept'
    self.backButtonAction.visible = True
    self.advanceButtonAction.visible = True

    #set the button actions
    self.disconnectAll(self.advanceButtonReg)
    self.disconnectAll(self.backButtonReg)
    self.disconnectAll(self.ui.CollectButton)
    self.backButtonReg.clicked.connect(lambda: self.registrationStep6())
    self.advanceButtonReg.clicked.connect(lambda: self.openNextModule())

    self.advanceButtonReg.enabled = True

    #set the frame in stacked widget
    self.ui.RegistrationWidget.setCurrentWidget(self.ui.RegistrationStep8)

  def openNextModule(self):
    home = slicer.modules.HomeWidget
    home.primaryTabBar.setCurrentIndex(home.navigationTabIndex)

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
      self.transformNode = slicer.util.getNode('Registration Transform')
    except:
      self.transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode")
      self.transformNode.SetName("Registration Transform")

    #Create your fiducial wizard node and set the input parameters
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

    slicer.modules.PlanningWidget.logic.skin_segmentation.SetDisplayVisibility(True)
    slicer.modules.PlanningWidget.logic.skin_segmentation.GetDisplayNode().SetVisibility2D(False)

  def onCollectButton(self):
    print('Attempt collection')
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

  def setupToolTables(self):
    self.tools = Tools(self.AlignmentSideWidgetui.SeenTableWidget, self.AlignmentSideWidgetui.UnseenTableWidget, self.moduleName)
    node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Pointer')
    node.AddFiducial(0,0,0, 'Pointer')
    node.GetDisplayNode().SetGlyphScale(13)
    node2 = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Reference Frame')
    node2.AddFiducial(0,0,0, 'Reference Frame')
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
    self.landmarks.advanceButtonReg = self.advanceButtonReg

  def disconnectAll(self, widget):
    try: widget.clicked.disconnect()
    except Exception: pass

  def preloadPictures(self):
    pictureNames = [
      'RegistrationStep1.png'
      , 'RegistrationStep2.png'
      , 'RegistrationStep3.jpg'
      , 'RegistrationStep4.png'
      , 'RegistrationStep5.png'
      , 'RegistrationStep6.png'
      ]
    self.pictures = {}
    properties = {}
    properties['show'] = False
    properties['singleFile'] = True
    for image in pictureNames:
      imageNode = slicer.util.loadVolume(self.resourcePath('Images/' + image), properties)
      imageNode.hidden = True
      self.pictures[image] = imageNode

  def goToFourUpLayout(self, node=None):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    NNUtils.setSliceWidgetSlidersVisible(True)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(False)
    NNUtils.setSliceViewBackgroundColor('#000000')
    slicer.util.setSliceViewerLayers(foreground=node, background=None, label=None, fit=True)

  def goToRegistrationCameraViewLayout(self):

    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    NNUtils.setSliceWidgetSlidersVisible(False)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(True)

  def goToPictureLayout(self, image = None, sidePanelVisible = False):
    if image is not None:
      slicer.util.setSliceViewerLayers(foreground=image, background=None, label=None, fit=True)
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    NNUtils.setSliceWidgetSlidersVisible(False)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(sidePanelVisible)
    NNUtils.setSliceViewBackgroundColor('#434343')

  def applyApplicationStyle(self):
    # Style
    self.applyStyle([slicer.app], 'Home.qss')

  def applyStyle(self, widgets, styleSheetName):
    stylesheetfile = self.resourcePath(styleSheetName)
    with open(stylesheetfile,"r") as fh:
      style = fh.read()
      for widget in widgets:
        widget.styleSheet = style


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
