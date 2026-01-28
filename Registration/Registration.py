import math
import re

import qt
import slicer
import vtk

from slicer.ScriptedLoadableModule import (
  ScriptedLoadableModule,
  ScriptedLoadableModuleLogic,
  ScriptedLoadableModuleWidget,
)

import OpenNavUtils
import Home

from LandmarkManager import Landmarks
from RegistrationUtils import Tools, Trace, TracingState
import numpy as np


class Registration(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "OpenNav Registration"
    self.parent.categories = [""]
    self.parent.dependencies = ["PivotCalibration"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the Registration main module for the OpenNav application
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
    self.traceObserver = None

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Registration.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    self.workflow = Home.Workflow(
      'registration',
      nested=(
        Home.Workflow("patient-prep", setup=self.registrationStepPatientPrep,
                      widget=self.ui.RegistrationStepPatientPrep),
        Home.Workflow("tracking-prep", setup=self.registrationStepTrackingPrep,
                      widget=self.ui.RegistrationStepTrackingPrep, validate=self.trackerConnected),
        Home.Workflow("pointer-prep", setup=self.registrationStepPointerPrep,
                      widget=self.ui.RegistrationStepPointerPrep, validate=self.trackerConnected),
        Home.Workflow("align-camera", setup=self.registrationStepAlignCamera,
                      widget=self.ui.RegistrationStepAlignCamera, validate=self.trackerConnected),
        Home.Workflow("pivot-calibration", setup=self.registrationStepPivotCalibration,
                      widget=self.ui.RegistrationStepPivotCalibration,
                      validate=self.trackerConnected),
        Home.Workflow("spin-calibration", setup=self.registrationStepSpinCalibration,
                      widget=self.ui.RegistrationStepSpinCalibration,
                      validate=self.validateSpinCalibration),
        Home.Workflow("landmark-registration", setup=self.registrationStepLandmarkRegistration,
                      widget=self.ui.RegistrationStepLandmarkRegistration,
                      teardown=self.fiducialOnlyRegistration,
                      validate=self.validateLandmarkRegistration),
        Home.Workflow("surface-registration", setup=self.registrationStepSurfaceRegistration,
                      widget=self.ui.RegistrationStepSurfaceRegistration,
                      validate=self.validateSurfaceRegistration,
                      teardown=self.resetDefaultButtonActions),
        Home.Workflow("verify-registration", setup=self.registrationStepVerifyRegistration,
                      validate=self.validateVerifyRegistration,
                      widget=self.ui.RegistrationStepVerifyRegistration,
                      teardown=self.registrationStepAcceptRegistration),
      ),
      setup=self.enter,
      teardown=self.exit,
      validate=self.validate,
    )

    self.RMSE_PIVOT_OK = 0.8
    self.RMSE_SPIN_OK = 1.
    self.RMSE_REGISTRATION_OK = 3.
    self.RMSE_INITIAL_REGISTRATION_OK = 5.
    self.RMSE_INITIAL_REGISTRATION_CONDITIONAL = 15.
    self.EPSILON = 0.00001
    self.optitrack_pending = False

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.AlignmentSideWidget = slicer.util.loadUI(self.resourcePath('UI/AlignmentSideWidget.ui'))
    self.AlignmentSideWidgetui = slicer.util.childWidgetVariables(self.AlignmentSideWidget)

    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelWidget')
    sidePanel.layout().addWidget(self.AlignmentSideWidget)
    self.AlignmentSideWidget.visible = False

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
    ) = OpenNavUtils.setupWorkflowToolBar("Registration")

    # Registration Tab Bar
    self.registrationTabBar = qt.QTabBar()
    self.registrationTabBar.setObjectName("RegistrationTabBar")
    OpenNavUtils.addCssClass(self.registrationTabBar, "secondary-tabbar")
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
    addSecondaryTab("pivot-calibration", "Pivot Calibrate")
    addSecondaryTab("spin-calibration", "Spin Calibrate")
    addSecondaryTab("landmark-registration", "Register patient")
    addSecondaryTab("surface-registration", "Refine registration")
    addSecondaryTab("verify-registration", "Verify registration")

    import OptiTrack
    self.optitrack = OptiTrack.OptiTrackLogic()
    self.optitrack.setExpectedNodes(['PointerToHeadFrame', 'PointerToTracker', 'HeadFrameToTracker'])

    self.preloadPictures()
    self.setupToolTables()
    self.setupLandmarkTables()

    self.pivotLogic = slicer.vtkSlicerPivotCalibrationLogic()
    self.planningLogic = slicer.modules.PlanningWidget.logic

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

    self.fiducialRegWizNode = None
    self.fiducialRegWizNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLFiducialRegistrationWizardNode', 'Registration')

    self.shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+b"), slicer.util.mainWindow())
    self.shortcut.connect("activated()", lambda: print('Shortcut not yet bound'))

    self.messageBox = qt.QMessageBox(qt.QMessageBox.Information, "Calibration", "Acquisition in progress...", qt.QMessageBox.NoButton)
    self.messageBox.setStandardButtons(0)

    self.trace = Trace()
    self.trace.setVisible(False)

  def cleanup(self):
    self.optitrack.shutdown()
    self.tools.setToolsStatusCheckEnabled(False)
    self.planningLogic = None

  def exit(self):
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.registrationTabBar.visible = False
    self.bottomToolBar.visible = False
    self.landmarks.showLandmarks = False
    self.landmarks.model = slicer.modules.PlanningWidget.logic.skin_model
    self.landmarks.updateLandmarksDisplay()
    self.shortcut.disconnect("activated()")
    self.trace.setVisible(False)
    self.resetDefaultButtonActions()

  def enter(self):
    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True
    self.registrationTabBar.visible = True

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    centralPanel = slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidget')
    for widget in [modulePanel, sidePanel, centralPanel]:
      OpenNavUtils.setCssClass(widget, "widget--color-light")
      OpenNavUtils.polish(widget)

    self.logic.updateExtensionModels()
    self.setupPivotCalibration()
    self.logic.setupSurfaceErrorComputation()
    self.landmarks.transferPlanningLandmarks(slicer.modules.PlanningWidget.landmarkLogic.positions)
    self.landmarks.syncLandmarks()

  def validate(self):
    print('Registration main validate called')
    landmarkLogic = slicer.modules.PlanningWidget.landmarkLogic

    if not landmarkLogic.landmarks:
      return 'Planning not complete'
  
    if landmarkLogic.landmarks.GetNumberOfControlPoints() < 3 :
      return 'Planning not complete'

    if self.optitrack_pending:
      return
    self.optitrack_pending = True
    self.startOptiTrack()

  def trackerConnected(self):
    if not (self.optitrack.isRunning or self.optitrack_pending):
      return "OptiTrack not connected"

  def validateSpinCalibration(self):
    if OpenNavUtils.isLinearTransformNodeIdentity(self.logic.pointer_calibration):
      return 'Perform pivot calibration before spin calibration'
    if not self.logic.pivot_calibration_passed:
      return 'Improve pivot calibration before spin calibration'

  def validateLandmarkRegistration(self):
    if not self.logic.pointer_calibration:
      return 'Perform pointer calibration before registering'

    # check if pivot transform is identity
    if OpenNavUtils.isLinearTransformNodeIdentity(self.logic.pointer_calibration):
      return 'Perform pointer pivot calibration before registering'

    # check if pivot and spin calibration is good
    if not self.logic.pivot_calibration_passed:
      return 'Improve pointer pivot calibration before registering'
    if not self.logic.spin_calibration_passed:
      return 'Improve pointer spin calibration before registering'

  def validateSurfaceRegistration(self):
    if not self.logic.pointer_calibration:
      return 'Perform pointer calibration before registering'

    # check if pivot transform is identity
    if OpenNavUtils.isLinearTransformNodeIdentity(self.logic.pointer_calibration):
      return 'Perform pointer calibration before registering'

    # check if pivot and spin calibration is good
    if not self.logic.pivot_calibration_passed:
      return 'Improve pointer pivot calibration before registering'
    if not self.logic.spin_calibration_passed:
      return 'Improve pointer spin calibration before registering'

  def validateVerifyRegistration(self):
    if not self.logic.pointer_calibration:
      return 'Perform pointer calibration before registering'

    # check if pivot transform is identity
    if OpenNavUtils.isLinearTransformNodeIdentity(self.logic.pointer_calibration):
      return 'Perform pointer calibration before registering'

    # check if pivot and spin calibration is good
    if not self.logic.pivot_calibration_passed:
      return 'Improve pointer pivot calibration before registering'
    if not self.logic.spin_calibration_passed:
      return 'Improve pointer spin calibration before registering'

    # check if landmark registration is present and good
    if not self.logic.landmark_registration_transform:
      return 'Landmark registration missing'
    if OpenNavUtils.isLinearTransformNodeIdentity(self.logic.landmark_registration_transform):
      return 'Landmark registration not complete'
    if not self.logic.landmark_registration_passed:
      return 'Please redo landmark registration to improve results'

    # check if surface registration is present and good
    if not self.logic.surface_registration_transform:
      return 'Surface registration missing'
    if OpenNavUtils.isLinearTransformNodeIdentity(self.logic.surface_registration_transform):
      return 'Surface registration not complete'
    if not self.logic.surface_registration_passed:
      return 'Please redo surface tracing to improve results'
  
  def startOptiTrack(self):
    
    if not self.optitrack.isRunning:
      # launch selector
      self.hardwareSelector = slicer.util.loadUI(self.resourcePath('UI/HardwareDialog.ui'))
      self.hardwareSelector.setWindowFlags(qt.Qt.WindowStaysOnTopHint)
      self.selectorUI = slicer.util.childWidgetVariables(self.hardwareSelector)
      self.hardwareSelector.accepted.connect(self.launchOptiTrack)
      self.hardwareSelector.rejected.connect(self.cancelOptiTrack)
      dialog_shortcut = qt.QShortcut(qt.QKeySequence("Ctrl+b"), self.hardwareSelector)
      dialog_shortcut.connect("activated()", self.hardwareSelector.accept)
      self.hardwareSelector.exec()
    else:
      self.advanceButton.enabled = True
      self.logic.reconnect()

  def launchOptiTrack(self):
    motiveFileName =  ''
    plusFileName = ''

    if self.selectorUI.KitwareRadioButton.checked:
      motiveFileName = 'MotiveProfile-2021-10-22.xml'
      plusFileName = 'PLUSHeadKitware.xml.in'

    if self.selectorUI.BWHRadioButton.checked:
      motiveFileName = 'OpenNav-BWH-Hardware_2024-05-08.xml'
      plusFileName = 'PLUSHead.xml.in'

    test = qt.QMessageBox(qt.QMessageBox.Information, "Starting", "Starting tracker", qt.QMessageBox.NoButton)
    test.setStandardButtons(0)
    test.show()
    slicer.app.processEvents()
    test.deleteLater()
    self.optitrack.start(self.optitrack.getPlusLauncherPath(), self.resourcePath(plusFileName), self.resourcePath(motiveFileName))
    test.hide()
    self.optitrack_pending = False

    if not self.optitrack.isRunning:
      qt.QMessageBox.warning(slicer.util.mainWindow(), "Tracker not connected", "Tracker not connected")
      self.advanceButton.enabled = False
    else:
      qt.QTimer.singleShot(10, self.logic.reconnect)

  def cancelOptiTrack(self):
    self.optitrack_pending = False

  def stepSetup(self):
    self.tools.showToolMarkers = False
    self.tools.updateToolsDisplay()

    self.landmarks.showLandmarks = False
    self.landmarks.model = slicer.modules.PlanningWidget.logic.skin_model
    self.landmarks.updateLandmarksDisplay()
    self.trace.setVisible(False)

    self.tools.setToolsStatusCheckEnabled(False)

    self.shortcut.disconnect("activated()")

  @OpenNavUtils.backButton(text="Return to Planning")
  @OpenNavUtils.advanceButton(text="Setup OpenNav")
  def registrationStepPatientPrep(self):
    self.stepSetup()
    self.advanceButton.enabled = self.optitrack.isRunning

    # set the layout and display an image
    OpenNavUtils.goToPictureLayout(self.pictures["RegistrationStepPatientPrep.png"])

    self.shortcut.connect("activated()", self.workflow.gotoNext)

  @OpenNavUtils.backButton(text="Back")
  @OpenNavUtils.advanceButton(text="Press when done")
  def registrationStepTrackingPrep(self):
    self.stepSetup()
    self.advanceButton.enabled = self.optitrack.isRunning

    # set the layout and display an image
    OpenNavUtils.goToPictureLayout(self.pictures["RegistrationStepTrackingPrep.png"])

    self.shortcut.connect("activated()", self.workflow.gotoNext)

  @OpenNavUtils.backButton(text="Back")
  @OpenNavUtils.advanceButton(text="Press when done")
  def registrationStepPointerPrep(self):
    self.stepSetup()
    self.advanceButton.enabled = self.optitrack.isRunning

    # set the layout and display an image
    OpenNavUtils.goToPictureLayout(self.pictures["RegistrationStepPointerPrep.jpg"])

    self.shortcut.connect("activated()", self.workflow.gotoNext)

  @OpenNavUtils.backButton(text="Back")
  @OpenNavUtils.advanceButton(text="Press when done")
  def registrationStepAlignCamera(self):
    self.stepSetup()
    self.advanceButton.enabled = self.optitrack.isRunning

    # set the layout and display an image
    OpenNavUtils.goToPictureLayout(self.pictures["RegistrationStepAlignCamera.png"], sidePanelVisible=True)
    self.AlignmentSideWidget.visible = True

    self.tools.setToolsStatusCheckEnabled(True)

    self.shortcut.connect("activated()", self.workflow.gotoNext)

  @OpenNavUtils.backButton(text="Back")
  @OpenNavUtils.advanceButton(text="Press when done")
  def registrationStepPivotCalibration(self):
    self.stepSetup()

    # set the layout and display an image
    OpenNavUtils.goToVideoLayout(self.resourcePath('Videos/pivot.html'), sidePanelVisible=True)
    self.AlignmentSideWidget.visible = True

    self.tools.setToolsStatusCheckEnabled(True)

    self.ui.PivotCalibrationButton.text = 'Start Pivot Calibration'

    self.advanceButton.enabled = self.logic.pivot_calibration_passed

    if self.logic.pivot_calibration_passed:
      self.ui.PivotCalibrationButton.text = 'Restart Pivot Calibration'
      self.ui.RMSLabelPivot.wordWrap = True
      self.ui.RMSLabelPivot.setStyleSheet("color: rgb(0,170,0)")
      self.ui.RMSLabelPivot.text = "Pivot calibration successful."

    # Set the button/shortcut actions:
    self.disconnectAll(self.ui.PivotCalibrationButton)
    self.ui.PivotCalibrationButton.clicked.connect(self.onPivotCalibrationButton)
    self.shortcut.disconnect("activated()")
    self.shortcut.connect("activated()", self.onPivotCalibrationButton)

  def onPivotCalibrationButton(self):
    # Unbind button/shortcut while calibration is in progress:
    self.ui.PivotCalibrationButton.enabled = False
    self.shortcut.disconnect("activated()")
    self.shortcut.connect("activated()", lambda: print("Pivot calibration already in progress"))

    self.messageBox.show()
    slicer.app.processEvents()

    self.advanceButton.enabled = False
    self.logic.pivot_calibration_passed = False
    self.ui.RMSLabelPivot.text = ""

    # setup pivot cal
    self.pivotLogic = slicer.vtkSlicerPivotCalibrationLogic()
    self.pivotLogic.SetAndObserveTransformNode(self.logic.pointer_to_headframe)
    if not self.logic.pointer_to_headframe:
      self.logic.reconnect()
    self.logic.pointer_calibration.SetAndObserveTransformNodeID(self.logic.pointer_to_headframe.GetID())
    print('Starting pre-record period')
    self.ui.PivotCalibrationButton.text = 'Pivot calibration in progress'
    qt.QTimer.singleShot(3000, self.startPivotCalibration)

  def startPivotCalibration(self):
    self.pivotLogic.SetRecordingState(True)
    print('Start recording')
    qt.QTimer.singleShot(5000, self.endPivotCalibration)

  def endPivotCalibration(self):
    outputMatrix = vtk.vtkMatrix4x4()
    self.logic.pointer_calibration.GetMatrixTransformToParent(outputMatrix)
    self.pivotLogic.SetToolTipToToolMatrix(outputMatrix)
    self.pivotLogic.SetRecordingState(False)
    print('End recording')
    self.ui.PivotCalibrationButton.text = 'Restart Pivot Calibration'
    self.pivotLogic.ComputePivotCalibration()
    self.pivotLogic.GetToolTipToToolMatrix(outputMatrix)
    self.logic.pointer_calibration.SetMatrixTransformToParent(outputMatrix)

    RMSE = self.pivotLogic.GetPivotRMSE()
    RMSE_label = f"{RMSE:1.2f}"
    self.pivotLogic.ClearToolToReferenceMatrices()
    print("Pivot calibration RMSE:" + RMSE_label)

    results = []
    if RMSE < self.EPSILON:
      self.ui.RMSLabelPivot.setStyleSheet("color: rgb(170,0,0)")
      results.clear()
      results.append("Calibration failed. It must be redone before proceeding. "
                     "Instruments were either not in view or the pointer wasn't moved sufficiently.")
    elif RMSE < self.RMSE_PIVOT_OK:
      self.ui.RMSLabelPivot.setStyleSheet("color: rgb(0,170,0)")
      results.append("Results are in the acceptable range to proceed.")
    else:
      self.ui.RMSLabelPivot.setStyleSheet("color: rgb(170,0,0)")
      results.append("Results too poor. Calibration  must be redone before proceeding. "
                     "Instruments were either not in view or the pointer was moved too quickly.")

    self.ui.RMSLabelPivot.wordWrap = True
    self.ui.RMSLabelPivot.text = "\n".join(results)

    self.logic.pivot_calibration_passed = RMSE <= self.RMSE_PIVOT_OK and RMSE > self.EPSILON
    self.advanceButton.enabled = self.logic.pivot_calibration_passed

    # Re-bind button/shortcut:
    self.ui.PivotCalibrationButton.enabled = True
    self.shortcut.disconnect("activated()")
    if self.logic.pivot_calibration_passed:
      self.shortcut.connect("activated()", self.workflow.gotoNext)
    else:
      self.shortcut.connect("activated()", self.onPivotCalibrationButton)

    if self.beep:
      self.beep.play()

    self.messageBox.hide()
 
  def setupPivotCalibration(self):
    # create output transform
    
    self.logic.setupPointerCalibration()
    self.logic.needle_model.SetAndObserveTransformNodeID(self.logic.pointer_calibration.GetID())
    self.logic.odd_extensions.SetAndObserveTransformNodeID(self.logic.pointer_calibration.GetID())
    self.logic.even_extensions.SetAndObserveTransformNodeID(self.logic.pointer_calibration.GetID())

  @OpenNavUtils.backButton(text="Back")
  @OpenNavUtils.advanceButton(text="Press when done")
  def registrationStepSpinCalibration(self):
    self.stepSetup()

    # set the layout and display an image
    OpenNavUtils.goToVideoLayout(self.resourcePath('Videos/spin.html'), sidePanelVisible=True)
    self.AlignmentSideWidget.visible = True

    self.tools.setToolsStatusCheckEnabled(True)

    self.advanceButton.enabled = self.logic.spin_calibration_passed

    if self.logic.spin_calibration_passed:
      self.ui.SpinCalibrationButton.text = 'Restart Spin Calibration'
      self.ui.RMSLabelSpin.wordWrap = True
      self.ui.RMSLabelSpin.setStyleSheet("color: rgb(0,170,0)")
      self.ui.RMSLabelSpin.text = "Spin calibration successful."

    self.ui.SpinCalibrationButton.text = 'Start Spin Calibration'

    # Set the button/shortcut actions:
    self.disconnectAll(self.ui.SpinCalibrationButton)
    self.ui.SpinCalibrationButton.clicked.connect(self.onSpinCalibrationButton)
    self.shortcut.connect("activated()", self.onSpinCalibrationButton)

  def onSpinCalibrationButton(self):
    # Unbind button/shortcut while calibration is in progress:
    self.ui.SpinCalibrationButton.enabled = False
    self.shortcut.disconnect("activated()")
    self.shortcut.connect("activated()", lambda: print("Spin calibration already in progress"))

    self.messageBox.show()
    slicer.app.processEvents()

    self.advanceButton.enabled = False
    self.logic.spin_calibration_passed = False
    self.ui.RMSLabelSpin.text = ""

    # setup spin cal
    self.pivotLogic = slicer.vtkSlicerPivotCalibrationLogic()
    if not self.logic.pointer_to_headframe:
      self.logic.reconnect()
    self.pivotLogic.SetAndObserveTransformNode(self.logic.pointer_to_headframe)
    self.logic.pointer_calibration.SetAndObserveTransformNodeID(self.logic.pointer_to_headframe.GetID())
    print('Starting pre-record period')
    self.ui.SpinCalibrationButton.text = 'Spin calibration in progress'
    qt.QTimer.singleShot(3000, self.startSpinCalibration)

  def startSpinCalibration(self):
    self.pivotLogic.SetRecordingState(True)
    print('Start recording')
    qt.QTimer.singleShot(5000, self.endSpinCalibration)

  def endSpinCalibration(self):
    outputMatrix = vtk.vtkMatrix4x4()
    self.logic.pointer_calibration.GetMatrixTransformToParent(outputMatrix)
    self.pivotLogic.SetToolTipToToolMatrix(outputMatrix)
    self.pivotLogic.SetRecordingState(False)
    print('End recording')
    self.ui.SpinCalibrationButton.text = 'Restart Spin Calibration'
    self.pivotLogic.ComputeSpinCalibration()
    self.pivotLogic.GetToolTipToToolMatrix(outputMatrix)
    self.logic.pointer_calibration.SetMatrixTransformToParent(outputMatrix)

    RMSE = math.degrees(self.pivotLogic.GetSpinRMSE())

    self.pivotLogic.ClearToolToReferenceMatrices()
    RMSE_label = f"{RMSE:1.6f}"
    print("Spin calibration RMSE:" + RMSE_label)

    results = []
    if RMSE < self.EPSILON:
      self.ui.RMSLabelSpin.setStyleSheet("color: rgb(170,0,0)")
      results.clear()
      results.append("Calibration failed. It must be redone before proceeding. "
                     "Instruments were wither not in view or the pointer wasn't rotated sufficiently.")
    elif RMSE < self.RMSE_SPIN_OK:
      self.ui.RMSLabelSpin.setStyleSheet("color: rgb(0,170,0)")
      results.append("Results are in the acceptable range to proceed.")
    else:
      self.ui.RMSLabelSpin.setStyleSheet("color: rgb(170,0,0)")
      results.append("Results too poor. Calibration must be redone before proceeding. "
                     "Instruments were either not in view or the pointer was rotated too quickly.")

    self.ui.RMSLabelSpin.wordWrap = True
    self.ui.RMSLabelSpin.text = "\n".join(results)

    self.logic.spin_calibration_passed = RMSE <= self.RMSE_SPIN_OK and RMSE > self.EPSILON
    self.advanceButton.enabled = self.logic.spin_calibration_passed

    # Re-bind button/shortcut:
    self.ui.SpinCalibrationButton.enabled = True
    self.shortcut.disconnect("activated()")
    if self.logic.spin_calibration_passed:
      self.shortcut.connect("activated()", self.workflow.gotoNext)
    else:
      self.shortcut.connect("activated()", self.onSpinCalibrationButton)

    if self.beep:
      self.beep.play()

    self.messageBox.hide()

  @OpenNavUtils.backButton(text="Recalibrate")
  @OpenNavUtils.advanceButton(text="")
  def registrationStepLandmarkRegistration(self):
    # Set the layout
    OpenNavUtils.goToRegistrationCameraViewLayout()
    self.AlignmentSideWidget.visible = True
    self.planningLogic.setPlanningNodesVisibility(skinModel=False, seedSegmentation=False,
                                             targetSegmentation=False, trajectory=False, landmarks=False)

    # Clear previous registration
    self.logic.clearRegistrationTransform()
    self.landmarks.model = slicer.modules.PlanningWidget.logic.skin_model
    self.landmarks.setupTrackerLandmarksNode()
    self.landmarks.clearLandmarks()
    self.resetTrace()
    self.trace.setVisible(False)

    self.tools.setToolsStatusCheckEnabled(True)

    self.landmarks.advanceButton = self.advanceButton
    
    self.landmarks.showLandmarks = True
    self.landmarks.model = slicer.modules.PlanningWidget.logic.skin_model
    self.landmarks.updateLandmarksDisplay()
    OpenNavUtils.centerCam()

    # set the button labels
    self.landmarks.updateAdvanceButton()

    # set the button actions
    self.disconnectAll(self.ui.CollectButton)
    self.ui.CollectButton.clicked.connect(self.onCollectButton)
    self.disconnectAll(self.backButton)
    self.backButton.clicked.connect(self.restartCalibration)

    # set the frame in stacked widget
    self.landmarks.startNextLandmark()

    self.shortcut.disconnect("activated()")
    self.shortcut.connect("activated()", self.onCollectButton)

  @OpenNavUtils.backButton(text="Restart registration")
  @OpenNavUtils.advanceButton(text="Continue")
  def registrationStepSurfaceRegistration(self):
    # Transform validation is done here because the landmark registration is performed in the teardown (invoked after validate)
    if not self.logic.landmark_registration_transform or \
            OpenNavUtils.isLinearTransformNodeIdentity(self.logic.landmark_registration_transform) or \
            not self.logic.landmark_registration_passed:
      self.workflow.gotoPrev()
      return

    # Set the layout
    OpenNavUtils.goToRegistrationCameraViewLayout()
    self.AlignmentSideWidget.visible = True
    
    self.landmarks.showLandmarks = False
    self.landmarks.model = slicer.modules.PlanningWidget.logic.skin_model
    self.landmarks.updateLandmarksDisplay()
    self.trace.setVisible(True)
    self.addLandmarksToTrace()
    self.planningLogic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=False,
                                             targetSegmentation=False, trajectory=False, landmarks=False)
    OpenNavUtils.centerCam()

    self.advanceButton.enabled = self.logic.surface_registration_passed

    # set the button/shortcut actions
    self.disconnectAll(self.ui.TraceButton)
    self.ui.TraceButton.clicked.connect(self.onTraceButton)
    self.disconnectAll(self.ui.ResetTraceButton)
    self.ui.ResetTraceButton.clicked.connect(self.onResetTraceButton)
    self.disconnectAll(self.backButton)
    self.backButton.clicked.connect(self.restartRegistration)

    self.shortcut.disconnect("activated()")
    self.shortcut.connect("activated()", self.onTraceButton)

  @OpenNavUtils.backButton(text="Restart registration")
  @OpenNavUtils.advanceButton(text="Accept", enabled=False)
  def registrationStepVerifyRegistration(self):
    # Set the layout
    masterNode = slicer.modules.PlanningWidget.logic.master_volume
    OpenNavUtils.goToNavigationLayout(volumeNode=masterNode, mainPanelVisible=True)
    self.tools.setToolsStatusCheckEnabled(True)
    self.AlignmentSideWidget.visible = False
    self.planningLogic.setPlanningNodesVisibility(skinModel=True, seedSegmentation=False,
                                                  targetSegmentation=False, trajectory=False, landmarks=False)
    self.logic.needle_model.GetDisplayNode().SetVisibility(True)
    self.logic.needle_model.GetDisplayNode().SetVisibility2D(True)
    self.trace.setVisible(False)
    OpenNavUtils.centerCam()

    self.advanceButton.enabled = self.logic.landmark_registration_passed and self.logic.surface_registration_passed
    self.ui.GoToTracingButton.enabled = self.logic.landmark_registration_passed

    # set the button/shortcut actions
    self.disconnectAll(self.backButton)
    self.backButton.clicked.connect(self.restartRegistration)
    self.disconnectAll(self.ui.GoToTracingButton)
    self.ui.GoToTracingButton.clicked.connect(self.workflow.gotoPrev)

    self.shortcut.disconnect("activated()")
    if self.logic.surface_registration_passed and self.logic.landmark_registration_passed:
      self.shortcut.connect("activated()", self.workflow.gotoNext)
    elif self.logic.landmark_registration_passed:
      self.shortcut.connect("activated()", self.workflow.gotoPrev)
    else:
      self.shortcut.connect("activated()", self.restartRegistration)

  def addLandmarksToTrace(self):
    if not self.trace.initialized_with_landmarks:
      defs = slicer.modules.PlanningWidget.landmarkLogic
      for _name, position in defs.positions.items():
        self.trace.addPoint(position)
      self.trace.initialized_with_landmarks = True
      self.trace.lastAcquisitionLength = 0

  def resetDefaultButtonActions(self):
    self.disconnectAll(self.backButton)
    self.backButton.clicked.connect(self.workflow.gotoPrev)
    self.disconnectAll(self.advanceButton)
    self.advanceButton.clicked.connect(self.workflow.gotoNext)

  def registrationStepAcceptRegistration(self):
    self.resetDefaultButtonActions()
    self.logic.needle_model.GetDisplayNode().SetVisibility(False)
    self.logic.needle_model.GetDisplayNode().SetVisibility2D(False)
    self.planningLogic.setPlanningNodesVisibility(skinModel=False, seedSegmentation=False,
                                                  targetSegmentation=False, trajectory=False, landmarks=False)

  def restartCalibration(self):
    print('Restarting calibration')
    self.workflow.gotoByName(("nn", "registration", "pivot-calibration"))

  def restartRegistration(self):
    print('Restarting registration')
    self.workflow.gotoByName(("nn", "registration", "landmark-registration"))

  def fiducialOnlyRegistration(self):
    if self.landmarks.landmarksFinished:
      fromMarkupsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'From')
      toMarkupsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'To')
      defs = slicer.modules.PlanningWidget.landmarkLogic
      for name, position in defs.positions.items():
        toMarkupsNode.AddControlPoint(position[0], position[1], position[2] )
        pos = self.landmarks.getTrackerPosition(name)
        fromMarkupsNode.AddControlPoint(pos[0], pos[1], pos[2])

      # Create transform node to hold the computed registration result
      self.logic.setupRegistrationTransform()

      # Set the input parameters
      self.fiducialRegWizNode.SetAndObserveFromFiducialListNodeId(fromMarkupsNode.GetID())
      self.fiducialRegWizNode.SetAndObserveToFiducialListNodeId(toMarkupsNode.GetID())
      self.fiducialRegWizNode.SetOutputTransformNodeId(self.logic.landmark_registration_transform.GetID())
      # TODO, always make sure units are correct in Motive
      self.fiducialRegWizNode.SetRegistrationModeToRigid()

      fromMarkupsNode.SetAndObserveTransformNodeID(self.logic.landmark_registration_transform.GetID())

      if self.logic.pointer_to_headframe:
        self.logic.pointer_to_headframe.SetAndObserveTransformNodeID(self.logic.landmark_registration_transform.GetID())

      slicer.mrmlScene.RemoveNode(fromMarkupsNode)
      slicer.mrmlScene.RemoveNode(toMarkupsNode)

      statusMessage = self.fiducialRegWizNode.GetCalibrationStatusMessage()
      print("Registration output message:" + statusMessage)

      regex = re.compile(r"[0-9]+\.[0-9]+")
      search = regex.search(statusMessage)
      messageText = ""

      if search is not None:
        match = search.group()

        RMSE = float(match)

        # Automatic pass
        if RMSE < self.RMSE_INITIAL_REGISTRATION_OK:
          self.logic.landmark_registration_passed = True
        
        # User can decided to proceed or not
        elif RMSE > self.RMSE_INITIAL_REGISTRATION_OK and RMSE < self.RMSE_INITIAL_REGISTRATION_CONDITIONAL:
          questionText = "Registration is poor (current RMSE: " + str(RMSE) + ", target RMSE: " \
            + str(self.RMSE_INITIAL_REGISTRATION_OK) + "). Would you like to proceed anyway?"
          ret = qt.QMessageBox.question(slicer.util.mainWindow(),'Proceed with registration?' ,questionText, qt.QMessageBox.Yes | qt.QMessageBox.No)
          self.logic.landmark_registration_passed = ret == qt.QMessageBox.Yes
          
          # User chooses to not proceed
          if not self.logic.landmark_registration_passed:
            messageText = "Registration not accepted. Registration must be redone before proceeding. "
        
        # Automatic fail
        else:
           messageText = "Results too poor. Registration must be redone before proceeding. (current RMSE: " + str(RMSE) + ")."
           self.logic.landmark_registration_passed = False
      
      # Error in registration algorithm
      else:
        self.logic.landmark_registration_passed = False
        messageText = "Registration error."

      if not self.logic.landmark_registration_passed:
        qt.QMessageBox.critical(slicer.util.mainWindow(), "Registration failed", messageText)

    self.resetDefaultButtonActions()

  def onCollectButton(self):
    print('Attempt collection')

    print('Unobserve registration transform')

    if self.logic.pointer_to_headframe:
      self.logic.pointer_to_headframe.SetAndObserveTransformNodeID(None)
    else:
      print('Warning:  tracker not connected')
    
    samplePoint = [0,0,0]
    outputPoint = [0,0,0]
    transform = vtk.vtkGeneralTransform()
    slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(self.logic.pointer_calibration, None, transform)
    transform.TransformPoint(samplePoint, outputPoint)
    # print(outputPoint)
    self.landmarks.collectLandmarkPosition(outputPoint)
    if self.landmarks.landmarksFinished:
      print("landmarks finished")
      self.shortcut.disconnect("activated()")
      self.shortcut.connect("activated()", self.workflow.gotoNext)
    if self.beep:
      self.beep.play()
    
    print('Reobserve registration transform')
   
    if self.logic.landmark_registration_transform and self.logic.pointer_to_headframe:
      self.logic.pointer_to_headframe.SetAndObserveTransformNodeID(self.logic.landmark_registration_transform.GetID())
      
  def setupToolTables(self):
    self.logic.setupNeedleModel()
    self.tools = Tools(self.AlignmentSideWidgetui.SeenTableWidget, self.AlignmentSideWidgetui.UnseenTableWidget, self.moduleName)
    node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Pointer')
    node.AddControlPoint(0,0,0, 'Pointer')
    node.SaveWithSceneOff()
    node.GetDisplayNode().SetGlyphScale(13)
    node2 = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'Reference Frame')
    node2.AddControlPoint(0,0,0, 'Reference Frame')
    node2.SaveWithSceneOff()
    node2.GetDisplayNode().SetGlyphScale(13)

    self.tools.addTool('PointerToTracker', 'Pointer', node)
    self.tools.addTool('HeadFrameToTracker', 'Reference Frame', node2)
    self.tools.optitrack = self.optitrack
    
    # Setting this makes sure tool transforms are removed from scene saving
    
  def onTraceButton(self):
    print('Attempt tracing')
    if self.trace.state == TracingState.IN_PROGRESS:
      self.shortcut.disconnect("activated()")
      self.shortcut.connect("activated()", lambda: print("Already stopping trace"))
      self.stopTracing()
    else:
      self.shortcut.disconnect("activated()")
      self.shortcut.connect("activated()", lambda: print("Already starting trace"))
      self.startTracing()

  def onResetTraceButton(self):
    self.resetTrace()
    self.addLandmarksToTrace()
    self.shortcut.disconnect("activated()")
    self.shortcut.connect("activated()", self.onTraceButton)

  def resetTrace(self):
    print('Reset trace')
    self.trace.clearTrace()
    self.ui.TraceButton.text = 'Start collection'
    if self.logic.surface_registration_transform:
      self.logic.surface_registration_transform.SetMatrixTransformToParent(vtk.vtkMatrix4x4())
    self.logic.surface_registration_passed = False

  def startTracing(self):
    print('Start tracing')
    self.trace.state = TracingState.IN_PROGRESS
    self.trace.lastAcquisitionLength = 0
    self.ui.TraceButton.text = 'Stop collection'

    if self.logic.landmark_registration_transform:
      self.logic.landmark_registration_transform.SetAndObserveTransformNodeID(None)
    else:
      print('Warning:  tracker not connected')

    try:
      self.traceObserver = self.logic.pointer_to_headframe.AddObserver(
                                  slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.doTracing)
    except:
        print('Warning:  tracker not connected')
        self.trace.state = TracingState.NOT_STARTED
        self.ui.TraceButton.text = 'Start collection'

    # Re-bind shortcut:
    self.shortcut.disconnect("activated()")
    self.shortcut.connect("activated()", self.onTraceButton)

  def stopTracing(self):
    messageBox = qt.QMessageBox(qt.QMessageBox.Information, "Computing", "Computing registration", qt.QMessageBox.NoButton)
    messageBox.setStandardButtons(0)
    messageBox.show()
    slicer.app.processEvents()
    messageBox.deleteLater()

    print("Stop tracing")
    if self.traceObserver is not None:
      self.logic.pointer_to_headframe.RemoveObserver(self.traceObserver)
      self.traceObserver = None
    else:
      print("[Registration::stopTracing]Was not recording, nothing to do.")

    trace_length = self.trace.traceNode.GetNumberOfControlPoints()
    if self.trace.traceNode is None or trace_length == 0:
      print("[Registration::stopTracing]Not enough points to compute registration.")
      return
    else:
      self.trace.state = TracingState.DONE
      self.ui.TraceButton.text = 'Add more points to trace'

    # Remove correction transform to compute the error without it
    backup = vtk.vtkMatrix4x4()
    identity = vtk.vtkMatrix4x4()
    self.logic.surface_registration_transform.GetMatrixTransformToParent(backup)
    self.logic.surface_registration_transform.SetMatrixTransformToParent(identity)

    # Compute average error on trace without correction
    avg_dist_before, tracing_points = self.computeTraceError()
    print("Average distance trace to skin surface before registration: " + str(avg_dist_before))

    # Re-set the correction transform
    self.logic.surface_registration_transform.SetMatrixTransformToParent(backup)

    transformMatrix = self.logic.runSurfaceRegistration(tracing_points)

    if transformMatrix is not None:
      self.logic.surface_registration_transform.SetMatrixTransformToParent(transformMatrix)
      if self.logic.landmark_registration_transform:
        self.logic.landmark_registration_transform.SetAndObserveTransformNodeID(
          self.logic.surface_registration_transform.GetID())
        self.trace.traceNode.SetAndObserveTransformNodeID(
          self.logic.surface_registration_transform.GetID())
      else:
        print('[Registration::stopTracing]Warning: tracker not connected')
    else:
      print("[Registration::stopTracing]Surface registration failed.")

    # Compute average error on trace with correction
    avg_dist_after, _ = self.computeTraceError()
    print("Average distance trace to skin surface after registration: " + str(avg_dist_after))

    self.logic.surface_registration_passed = (avg_dist_after - avg_dist_before < 0. - self.EPSILON) and \
                                             (avg_dist_after < self.RMSE_REGISTRATION_OK)

    self.advanceButton.enabled = self.logic.surface_registration_passed

    if self.logic.surface_registration_passed:
      self.ui.SurfaceRegMessage.text = ""
      self.workflow.gotoNext()
    else:
      self.logic.surface_registration_transform.SetMatrixTransformToParent(identity)
      self.shortcut.disconnect("activated()")
      print("Surface registration likely failed.")
      self.ui.SurfaceRegMessage.text = "Surface registration failed. Keep acquiring points or start over."
      self.shortcut.connect("activated()", self.onTraceButton)

    messageBox.hide()

  def computeTraceError(self):
    error = 0
    trace_length = self.trace.traceNode.GetNumberOfControlPoints()
    tracing_points = np.zeros((trace_length, 3))
    for i in range(trace_length):
      p = [0.0, 0.0, 0.0]
      self.trace.traceNode.GetNthControlPointPositionWorld(i, p)
      tracing_points[i, :] = p
      closest_point_on_surface = [0., 0., 0.]
      cell_id = vtk.reference(0)
      sub_id = vtk.reference(0)
      dist2 = vtk.reference(0.)
      self.logic.locator.FindClosestPoint(p, closest_point_on_surface, cell_id, sub_id, dist2)
      error += math.sqrt(dist2)
    error /= trace_length
    return error, tracing_points

  def doTracing(self, transformNode=None, unusedArg2=None, unusedArg3=None):
    samplePoint = [0, 0, 0]
    outputPoint = [0, 0, 0]
    transform = vtk.vtkGeneralTransform()
    slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(self.logic.pointer_calibration, None, transform)
    transform.TransformPoint(samplePoint, outputPoint)
    self.trace.addPoint(outputPoint)

  def setupLandmarkTables(self):
    self.landmarks = Landmarks(self.ui.RegistrationWidget.RegistrationStepLandmarkRegistration.LandmarkTableWidget, self.moduleName, self.ui.CollectButton)
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
      ]
    self.pictures = {}
    for image in pictureNames:
      imagePixmap = qt.QPixmap(self.resourcePath('Images/' + image))
      self.pictures[image] = imagePixmap


class RegistrationLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  EXTENSION_SEGMENT_LENGTH_MM = 10

  pointer_calibration = OpenNavUtils.nodeReferenceProperty("POINTER_CALIBRATION", default=None)
  landmark_registration_transform = OpenNavUtils.nodeReferenceProperty("IMAGE_REGISTRATION", default=None)
  surface_registration_transform = OpenNavUtils.nodeReferenceProperty("IMAGE_REGISTRATION_REFINEMENT", default=None)
  pivot_calibration_passed = OpenNavUtils.parameterProperty("PIVOT_CALIBRATION_PASSED", default=False)
  spin_calibration_passed = OpenNavUtils.parameterProperty("SPIN_CALIBRATION_PASSED", default=False)
  landmark_registration_passed = OpenNavUtils.parameterProperty("LANDMARK_REGISTRATION_PASSED", default=False)
  surface_registration_passed = OpenNavUtils.parameterProperty("SURFACE_REGISTRATION_PASSED", default=False)

  # Not a reference property, since we DO NOT want any reference to this saved with the scene
  # This node should only exists when the tracker is running
  pointer_to_headframe = None
  needle_model = None
  locator = None
  odd_extensions = None
  even_extensions = None
  half_seg_transform = None
  full_seg_transform = None

  def clearRegistrationData(self):
    slicer.mrmlScene.RemoveNode(self.pointer_calibration)
    slicer.mrmlScene.RemoveNode(self.landmark_registration_transform)
    slicer.mrmlScene.RemoveNode(self.surface_registration_transform)
    slicer.mrmlScene.RemoveNode(self.odd_extensions)
    slicer.mrmlScene.RemoveNode(self.even_extensions)
    self.odd_extensions = None
    self.even_extensions = None
    self.pivot_calibration_passed = False
    self.spin_calibration_passed = False
    self.landmark_registration_passed = False
    self.surface_registration_passed = False
  
  def setupPointerCalibration(self):
    if not self.pointer_calibration:
      node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLLinearTransformNode",
        "POINTER_CALIBRATION",
      )
      self.pointer_calibration = node

  def setupRegistrationTransform(self):
    if not self.landmark_registration_transform:
      node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLLinearTransformNode",
        "IMAGE_REGISTRATION",
      )
      self.landmark_registration_transform = node
    if not self.surface_registration_transform:
      node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLLinearTransformNode",
        "IMAGE_REGISTRATION_REFINEMENT",
      )
      self.surface_registration_transform = node

  def clearRegistrationTransform(self):
    if self.landmark_registration_transform:
      print('Clearing landmark registration transform to recompute')
      identityMatrix = vtk.vtkMatrix4x4()
      self.landmark_registration_transform.SetMatrixTransformToParent(identityMatrix)
    if self.surface_registration_transform:
      print('Clearing surface registration transform to recompute')
      identityMatrix = vtk.vtkMatrix4x4()
      self.surface_registration_transform.SetMatrixTransformToParent(identityMatrix)
    self.landmark_registration_passed = False
    self.surface_registration_passed = False

  def reconnect(self):
    if not self.pointer_to_headframe:
      self.pointer_to_headframe = slicer.util.getFirstNodeByName('PointerToHeadFrame')
      if not self.pointer_to_headframe:
        print('Pointer node not available yet - creating')
        self.pointer_to_headframe = slicer.mrmlScene.AddNewNodeByClass(
          "vtkMRMLLinearTransformNode",
          "PointerToHeadFrame",
          )
      self.pointer_to_headframe.SaveWithSceneOff()
    
    if self.pointer_calibration and self.pointer_to_headframe:
      self.pointer_calibration.SetAndObserveTransformNodeID(self.pointer_to_headframe.GetID())

    if self.needle_model and self.odd_extensions and self.even_extensions and self.pointer_calibration:
      self.needle_model.SetAndObserveTransformNodeID(self.pointer_calibration.GetID())
      self.odd_extensions.SetAndObserveTransformNodeID(self.pointer_calibration.GetID())
      self.even_extensions.SetAndObserveTransformNodeID(self.pointer_calibration.GetID())

    if self.landmark_registration_transform and self.pointer_to_headframe:
      self.pointer_to_headframe.SetAndObserveTransformNodeID(self.landmark_registration_transform.GetID())

    if self.surface_registration_transform and self.landmark_registration_transform:
      self.landmark_registration_transform.SetAndObserveTransformNodeID(self.surface_registration_transform.GetID())

  def setupNeedleModel(self):
    createModelsLogic = slicer.modules.createmodels.logic()
    self.needle_model = createModelsLogic.CreateNeedle(100.0, 1.0, 2.5, False)
    self.needle_model.GetDisplayNode().SetColor(220, 220, 0)
    self.needle_model.GetDisplayNode().SetVisibility(False)
    self.needle_model.GetDisplayNode().SetSliceIntersectionThickness(6)
    self.needle_model.SetName("NEEDLE_MODEL")
    self.needle_model.SaveWithSceneOff()

  def createExtensionNodes(self):
    if not self.odd_extensions:
      self.odd_extensions = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
      self.odd_extensions.SetName('ODD_EXTENSION_SEGMENTS')
      self.odd_extensions.CreateDefaultDisplayNodes()
      self.odd_extensions.GetDisplayNode().SetVisibility(False)
      self.odd_extensions.GetDisplayNode().SetSliceIntersectionThickness(6)
      self.odd_extensions.GetDisplayNode().SetColor(200, 0, 200)
      self.odd_extensions.SaveWithSceneOff()

    if not self.even_extensions:
      self.even_extensions = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
      self.even_extensions.SetName('EVEN_EXTENSION_SEGMENTS')
      self.even_extensions.CreateDefaultDisplayNodes()
      self.even_extensions.GetDisplayNode().SetVisibility(False)
      self.even_extensions.GetDisplayNode().SetSliceIntersectionThickness(6)
      self.even_extensions.GetDisplayNode().SetColor(0, 200, 200)
      self.even_extensions.SaveWithSceneOff()

    if not self.half_seg_transform:
      self.half_seg_transform = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformNode")
      self.half_seg_transform.SetName("HalfSegTransform")
      self.half_seg_transform.SaveWithSceneOff()
      half_seg_matrix = vtk.vtkMatrix4x4()
      half_seg_matrix.SetElement(2, 3, self.EXTENSION_SEGMENT_LENGTH_MM/2)
      self.half_seg_transform.SetMatrixTransformToParent(half_seg_matrix)

    if not self.full_seg_transform:
      self.full_seg_transform = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformNode")
      self.full_seg_transform.SetName("FullSegTransform")
      self.full_seg_transform.SaveWithSceneOff()
      full_seg_matrix = vtk.vtkMatrix4x4()
      full_seg_matrix.SetElement(2, 3, self.EXTENSION_SEGMENT_LENGTH_MM)
      self.full_seg_transform.SetMatrixTransformToParent(full_seg_matrix)

  def updateExtensionModels(self, length=50):

    self.createExtensionNodes()

    nb_seg = math.ceil(length / self.EXTENSION_SEGMENT_LENGTH_MM)
    # Setup:
    nb_seg_odd = int(nb_seg / 2) + (nb_seg % 2)
    nb_seg_even = int(nb_seg / 2)
    createModelsLogic = slicer.modules.createmodels.logic()

    # Create complete odd_extension model:
    oddAppendFilter = vtk.vtkAppendPolyData()
    for i in range(0,nb_seg_odd):
      part = createModelsLogic.CreateCylinder(self.EXTENSION_SEGMENT_LENGTH_MM, 1.0)
      part.SetAndObserveTransformNodeID(self.half_seg_transform.GetID())
      part.HardenTransform()

      for _ in range(i):
        part.SetAndObserveTransformNodeID(self.full_seg_transform.GetID())
        part.HardenTransform()
        part.SetAndObserveTransformNodeID(self.full_seg_transform.GetID())
        part.HardenTransform()
      oddAppendFilter.AddInputData(part.GetPolyData())
      slicer.mrmlScene.RemoveNode(part)

    oddAppendFilter.Update()
    self.odd_extensions.SetAndObservePolyData(oddAppendFilter.GetOutput())
    self.odd_extensions.Modified()

    # Create complete even_extension model:
    evenAppendFilter = vtk.vtkAppendPolyData()
    for i in range(0,nb_seg_even):
      part = createModelsLogic.CreateCylinder(self.EXTENSION_SEGMENT_LENGTH_MM, 1.0)
      part.SetAndObserveTransformNodeID(self.half_seg_transform.GetID())
      part.HardenTransform()
      part.SetAndObserveTransformNodeID(self.full_seg_transform.GetID())
      part.HardenTransform()
      for _ in range(i):
        part.SetAndObserveTransformNodeID(self.full_seg_transform.GetID())
        part.HardenTransform()
        part.SetAndObserveTransformNodeID(self.full_seg_transform.GetID())
        part.HardenTransform()
      
      evenAppendFilter.AddInputData(part.GetPolyData())
      slicer.mrmlScene.RemoveNode(part)

    evenAppendFilter.Update()
    self.even_extensions.SetAndObservePolyData(evenAppendFilter.GetOutput())
    self.even_extensions.Modified()

    self.reconnect()

  def setupSurfaceErrorComputation(self):
    self.locator = vtk.vtkCellLocator()
    self.locator.SetDataSet(slicer.modules.PlanningWidget.logic.skin_model.GetPolyData())
    self.locator.SetNumberOfCellsPerBucket(1)
    self.locator.BuildLocator()
    self.locator.Update()

  def runSurfaceRegistration(self, tracePoints):
    skin_model_polydata = slicer.modules.PlanningWidget.logic.skin_model.GetPolyData()
    icp = vtk.vtkIterativeClosestPointTransform()
    icp.SetMaximumNumberOfIterations(50)
    icp.SetMaximumNumberOfLandmarks(200)
    icp.SetMeanDistanceModeToAbsoluteValue()
    icp.GetLandmarkTransform().SetModeToRigidBody()
    icp.SetTarget(skin_model_polydata)
    icp.SetSource(OpenNavUtils.createPolyData(tracePoints))
    icp.Update()
    return icp.GetMatrix()
