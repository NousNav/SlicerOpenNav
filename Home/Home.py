import typing

from collections import OrderedDict

import ctk
import qt
import slicer

from slicer.ScriptedLoadableModule import (
  ScriptedLoadableModule,
  ScriptedLoadableModuleLogic,
  ScriptedLoadableModuleWidget,
)
from slicer.util import VTKObservationMixin

import OpenNavUtils


class Home(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "OpenNav Home"
    self.parent.categories = [""]
    self.parent.dependencies = ["Patients", "Planning", "Registration", "Navigation"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the Home module for the OpenNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class HomeWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # |----------------------------------------------------------------------------------------------------|
    # |                                                                                                    |
    # | (OpenNavLabel)                     (CenteredWidget)                                                |
    # |                              PrimaryTab1 | ... | PrimaryTabN                            [Settings] |
    # |                                                                                                    |
    # |                                (SecondaryCenteredWidget)                                           |
    # |                         SecondaryTab1  | SecondaryTab2 | ... | SecondaryTabN                       |
    # |----------------------------------------------------------------------------|-----------------------|
    # | (ModulePanel) |                                                            | (SidePanelDockWidget) |
    # |               |                                                            |                       |
    # |               |                (CentralWidgetLayoutFrame)                  |                       |
    # .               .                                                            .                       .
    # .               .                                                            .                       .
    # |               |                                                            |                       |
    # |----------------------------------------------------------------------------------------------------|
    # | [Back Button]                  (<StepName>BottomToolBar)                          [Advance Button] |
    # |----------------------------------------------------------------------------------------------------|

    # Apply style (1st pass)
    self.applyApplicationStyle()

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Home.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    # Remove uneeded UI elements, add toolbars
    self.validateStepsDefault = True
    self.modifyWindowUI()

    # Initialize navigation layout
    OpenNavUtils.initializeNavigationLayouts()

    patients = slicer.modules.patients.createNewWidgetRepresentation()
    planning = slicer.modules.planning.createNewWidgetRepresentation()
    registration = slicer.modules.registration.createNewWidgetRepresentation()
    navigation = slicer.modules.navigation.createNewWidgetRepresentation()

    info = OpenNavUtils.Workflow(
      'nn',
      nested=(
        patients.self().workflow,
        planning.self().workflow,
        registration.self().workflow,
        navigation.self().workflow,
      ),
    )
    # Create logic class
    self.logic = HomeLogic(info, self.ui.HomeWidget)

    # setup scene
    self.setupNodes()

    # Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    self.setCustomUIVisible(True)
    self.setValidateSteps(self.validateStepsDefault)

    # Apply style
    self.applyApplicationStyle()

  def applyApplicationStyle(self):
    OpenNavUtils.applyStyle([slicer.app], self.resourcePath("Home.qss"))

  def setupNodes(self):
    # Set up the layout / 3D View
    OpenNavUtils.setup3DView()
    OpenNavUtils.setupSliceViewers()

  def onClose(self, unusedOne, unusedTwo):
    self.setupNodes()

  def cleanup(self):
    print('Autosave on close')
    OpenNavUtils.autoSavePlan()
    self.logic = None

  def modifyWindowUI(self):

    # Create primary toolbar
    slicer.util.mainWindow().addToolBarBreak()
    self.primaryToolBar = qt.QToolBar("PrimaryToolBar")
    self.primaryToolBar.setObjectName("PrimaryToolBar")
    self.primaryToolBar.movable = False
    slicer.util.mainWindow().addToolBar(self.primaryToolBar)

    # create secondary toolbar
    slicer.util.mainWindow().addToolBarBreak()
    self.secondaryToolBar = qt.QToolBar("SecondaryToolBar")
    self.secondaryToolBar.setObjectName("SecondaryToolBar")
    self.secondaryToolBar.movable = False
    slicer.util.mainWindow().addToolBar(self.secondaryToolBar)

    # Centering widget for primary toolbar
    self.primaryTabWidget = slicer.util.loadUI(self.resourcePath('UI/CenteredWidget.ui'))
    self.primaryTabWidget.setObjectName("PrimaryCenteredWidget")
    self.primaryTabWidgetUI = slicer.util.childWidgetVariables(self.primaryTabWidget)

    # Tabs for primary toolbar
    self.primaryTabBar = qt.QTabBar()
    self.primaryTabBar.setObjectName("PrimaryTabBar")
    self.primaryTabWidgetUI.CenterArea.layout().addWidget(self.primaryTabBar)

    # Assemble primary bar
    openNavLabel = qt.QLabel('OpenNav')
    openNavLabel.setObjectName(OpenNavUtils.applicationTitleLabelName)
    self.primaryToolBar.addWidget(openNavLabel)
    self.patientNameLabel = qt.QLabel('Patient: ')
    self.patientNameLabel.setObjectName(OpenNavUtils.patientNameLabelName)
    self.primaryToolBar.addWidget(self.patientNameLabel)
    self.savingStatusLabel = qt.QLabel()
    self.savingStatusLabel.setObjectName(OpenNavUtils.statusLabelName)
    self.primaryToolBar.addWidget(self.savingStatusLabel)
    self.primaryToolBar.addWidget(self.primaryTabWidget)

    # Mousemode

    mouseModeToolBar = slicer.util.findChild(slicer.util.mainWindow(), 'MouseModeToolBar')
    actionTranslate = mouseModeToolBar.actions()[0]
    actionTranslate.setIcon(qt.QIcon(self.resourcePath('Icons/arrow.svg')))
    actionWindowLevel = mouseModeToolBar.actions()[1]
    actionWindowLevel.setIcon(qt.QIcon(self.resourcePath('Icons/window_level.png')))
    self.primaryToolBar.addAction(actionTranslate)
    self.primaryToolBar.addAction(actionWindowLevel)
    

    # Screenshot
    screenShotIcon = qt.QIcon(self.resourcePath('Icons/ScreenShot.svg'))
    self.screenShotAction = self.primaryToolBar.addAction(screenShotIcon, "")
    self.screenShotAction.triggered.connect(self.takeScreenShot)
    self.screenShotAction.toolTip = 'Take Screenshot'

    # Open cases folder
    folderIcon = qt.QIcon(self.resourcePath('Icons/Folder.svg'))
    self.folderAction = self.primaryToolBar.addAction(folderIcon, "")
    self.folderAction.triggered.connect(OpenNavUtils.openCasesDirectoryInExplorer)
    self.folderAction.toolTip = 'Open cases folder in Windows Explorer.'

    # Settings dialog
    gearIcon = qt.QIcon(self.resourcePath('Icons/Gears.svg'))
    self.settingsAction = self.primaryToolBar.addAction(gearIcon, "")
    self.settingsDialog = slicer.util.loadUI(self.resourcePath('UI/Settings.ui'))
    self.settingsUI = slicer.util.childWidgetVariables(self.settingsDialog)
    self.settingsUI.CustomUICheckBox.toggled.connect(self.setCustomUIVisible)
    self.settingsUI.ValidateCheckBox.checked = self.validateStepsDefault
    self.settingsUI.ValidateCheckBox.toggled.connect(self.setValidateSteps)
    self.settingsUI.RegistrationCheckBox.toggled.connect(self.setRegistrationRequirement)
    self.settingsUI.CustomStyleCheckBox.toggled.connect(self.toggleStyle)
    self.settingsAction.triggered.connect(self.raiseSettings)
    self.settingsAction.toolTip = 'Open advanced settings menu'
    
    # Tabs for secondary toolbars - navigation and registration
    self.secondaryTabWidget = slicer.util.loadUI(self.resourcePath('UI/CenteredWidget.ui'))
    self.secondaryTabWidget.setObjectName("SecondaryCenteredWidget")
    self.secondaryToolBar.addWidget(self.secondaryTabWidget)

    # Side Widget
    dockWidget = qt.QDockWidget(slicer.util.mainWindow())
    dockWidget.name = 'SidePanelDockWidget'
    self.SidePanelWidget = qt.QWidget(dockWidget)
    width = 300
    self.SidePanelWidget.setMinimumWidth(width)
    self.SidePanelWidget.setMaximumWidth(width)
    self.SidePanelWidget.setLayout(qt.QVBoxLayout())
    self.SidePanelWidget.name = 'SidePanelWidget'
    dockWidget.setWidget(self.SidePanelWidget)
    dockWidget.setFeatures(dockWidget.NoDockWidgetFeatures)
    slicer.util.mainWindow().addDockWidget(qt.Qt.RightDockWidgetArea , dockWidget)

    # Create the central image widget
    centralWidget = slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidget')
    centralWidgetImageFrame = qt.QFrame()
    centralWidgetImageFrame.objectName = 'CentralWidgetImageFrame'
    centralWidgetImageFrame.visible = False
    centralWidgetImageFrame.setLayout(qt.QVBoxLayout())
    centralWidget.layout().addWidget(centralWidgetImageFrame)
    centralImageLabel = ctk.ctkThumbnailLabel()
    centralImageLabel.objectName = 'CentralImageLabel'
    centralWidgetImageFrame.layout().addWidget(centralImageLabel)

    # Create the central video widget
    centralWidgetVideoFrame = qt.QFrame()
    centralWidgetVideoFrame.objectName = 'CentralWidgetVideoFrame'
    centralWidgetVideoFrame.visible = False
    centralWidgetVideoFrame.setLayout(qt.QVBoxLayout())
    centralWidget.layout().addWidget(centralWidgetVideoFrame)
    centralVideoWidget = slicer.qSlicerWebWidget()
    centralVideoWidget.objectName = 'CentralVideoWidget'
    centralWidgetVideoFrame.layout().addWidget(centralVideoWidget)

    # Remove left click menu
    pluginHandler = slicer.qSlicerSubjectHierarchyPluginHandler.instance()
    pluginLogic = pluginHandler.pluginLogic()
    pluginLogic.allowedViewContextMenuActionNames = ["NothingAllowed"]

    # Block invisible segment dialog
    qt.QSettings().setValue("Segmentations/ConfirmEditHiddenSegment", str(qt.QMessageBox.Yes))
  
  def takeScreenShot(self):
    if slicer.modules.PlanningWidget.logic.case_name:
      OpenNavUtils.saveScreenShot(slicer.modules.PlanningWidget.logic.case_name)
    else:
      OpenNavUtils.saveScreenShot('NonPatientScreenShots')
  
  def toggleStyle(self,visible):
    if visible:
      self.applyApplicationStyle()
    else:
      slicer.app.styleSheet = ''

  def raiseSettings(self, unused):
    self.settingsDialog.exec()

  def setCustomUIVisible(self, visible):
    self.setSlicerUIVisible(not visible)

  def setValidateSteps(self, validate):
    self.logic.validateSteps = validate

  def setRegistrationRequirement(self, required):
    if required:
      slicer.modules.RegistrationWidget.RMSE_REGISTRATION_OK = 3
      slicer.modules.RegistrationWidget.RMSE_INITIAL_REGISTRATION_OK = 3
    else:
      slicer.modules.RegistrationWidget.RMSE_REGISTRATION_OK = 99
      slicer.modules.RegistrationWidget.RMSE_INITIAL_REGISTRATION_OK = 99
      slicer.modules.RegistrationWidget.RMSE_INITIAL_REGISTRATION_CONDITIONAL = 99
  
  def setSlicerUIVisible(self, visible):
    slicer.util.setDataProbeVisible(visible)
    slicer.util.setMenuBarsVisible(visible, ignore=['MainToolBar', 'ViewToolBar'])
    slicer.util.setModuleHelpSectionVisible(visible)
    slicer.util.setModulePanelTitleVisible(visible)
    slicer.util.setPythonConsoleVisible(visible)
    slicer.util.setApplicationLogoVisible(visible)
    keepToolbars = [
      slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'PrimaryToolBar'),
      ]
    keepToolbars.extend(
      [slicer.util.findChild(slicer.util.mainWindow(), f"{name}BottomToolBar") for name in [
        "Patients", "Planning", "Navigation", "Registration"]]
    )
    slicer.util.setToolbarsVisible(visible, keepToolbars)
    if visible:
      slicer.util.mainWindow().setContextMenuPolicy(qt.Qt.DefaultContextMenu)
    else:
      slicer.util.mainWindow().setContextMenuPolicy(qt.Qt.NoContextMenu)

    OpenNavUtils.setupSliceViewers(visible)
    OpenNavUtils.setup3DView(visible)




class HomeLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
  """

  _currentNameCache: typing.Optional[typing.Tuple[str]]
  _currentName: typing.Optional[typing.Tuple[str]] = OpenNavUtils.parameterProperty('CURRENT_STEP_NAME', default=None)

  @property
  def current(self) -> typing.Optional[OpenNavUtils.Step]:
    if self._currentName is None:
      return None

    return self.names[tuple(self._currentName)]

  @current.setter
  def current(self, value: OpenNavUtils.Step):
    names = tuple(value.names)
    self._currentName = names
    self._currentNameCache = names

  @property
  def nextStep(self):
    current = self.current
    if current is None:
      return None
    return current.nextStep

  @property
  def prevStep(self):
    current = self.current
    if current is None:
      return None
    return current.prevStep

  def __init__(self, info: OpenNavUtils.Workflow, stack):
    super().__init__()

    info.engine = self

    self.stack = stack

    self.steps = list(info.flatten(stack))
    self.names = {step.names: step for step in self.steps}
    self.validateSteps = True
    self.autoSaveBlocked = False

    # build doubly-linked list
    for prevStep, nextStep in zip(self.steps[:-1], self.steps[1:]):
      prevStep.nextStep = nextStep
      nextStep.prevStep = prevStep

    # Collect steps
    self.primarySteps = OrderedDict()
    self.secondarySteps = OrderedDict()
    for step in self.steps:
      primaryStepName = step.names[1]
      if primaryStepName not in self.primarySteps.keys():
        self.primarySteps[primaryStepName] = step
        self.secondarySteps[primaryStepName] = OrderedDict()
      if len(step.names) == 3:
        secondaryStepName = step.names[2]
        self.secondarySteps[primaryStepName][secondaryStepName] = step

    # Connect back/advance buttons
    for stepName in self.primarySteps.keys():
      backButton = slicer.util.findChild(slicer.util.mainWindow(), f"{stepName.capitalize()}BackButton")
      backButton.clicked.connect(self.gotoPrev)
      advanceButton = slicer.util.findChild(slicer.util.mainWindow(), f"{stepName.capitalize()}AdvanceButton")
      advanceButton.clicked.connect(self.gotoNext)

    # Setup primary tab bar
    primaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), 'PrimaryTabBar')
    for name in self.primarySteps.keys():
      tabIndex = primaryTabBar.addTab(name.capitalize())
      primaryTabBar.setTabData(tabIndex, name)
    # ... and ensure relevant step is shown if clicked
    primaryTabBar.currentChanged.connect(lambda tabIndex: self.goto(self.primarySteps[primaryTabBar.tabData(tabIndex)]))

    def secondaryTabChanged(steps, tabBar):
      def gotoStep(tabIndex):
        self.goto(steps[tabBar.tabData(tabIndex)])
      return gotoStep

    # Setup secondary tab bars
    for primaryStepName, secondary in self.secondarySteps.items():
      try:
        secondaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), f"{primaryStepName.capitalize()}TabBar")
      except (IndexError, RuntimeError):
        continue
      # ... and ensure relevant step is shown if clicked
      secondaryTabBar.currentChanged.connect(secondaryTabChanged(secondary, secondaryTabBar))

    # Initialize workflow selecting first step
    self._currentNameCache = None
    self.goto(self.steps[0], autoSave=False)

    slicer.app.ioManager().newFileLoaded.connect(self.onNewFileLoaded)

  def __del__(self):
    print(f"Deleting {self}" )

  def onNewFileLoaded(self, params):
    if params.get('fileType', None) == 'SceneFile':
      print('Scene Loaded!')

      self.resyncCurrent()
      slicer.modules.PlanningWidget.logic.reconnect()
      slicer.modules.RegistrationWidget.logic.reconnect()
      slicer.modules.PlanningWidget.landmarkLogic.reconnect()
      slicer.modules.PlanningWidget.tableManager.reconnect()
      slicer.modules.PlanningWidget.tableManager.updateLandmarksDisplay()

  def resyncCurrent(self):
    print('resync')
    self.autoSaveBlocked = True
    dst = self.current
    self._currentName = self._currentNameCache
    self.goto(dst)
    self.autoSaveBlocked = False

  def _forceTabReselect(self):
    """Reset the tab state if validation fails.
    """
    dst = self.current
    primaryStepName = dst.names[1]
    try:
      primaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), 'PrimaryTabBar')
      index = self._lookupPrimaryStepTabIndex(primaryStepName)
      if index is not None:
        print('primary tab index', index)
        primaryTabBar.currentIndex = index
    except (IndexError, RuntimeError):
      pass

    if len(dst.names) == 3:
      secondaryStepName = dst.names[2]
      try:
        secondaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), f"{primaryStepName.capitalize()}TabBar")
        index = self._lookupSecondaryStepTabIndex(primaryStepName, secondaryStepName)
        if index is not None:
          print('secondary tab index', index)
          secondaryTabBar.currentIndex = index
      except (IndexError, RuntimeError):
        pass
  
  def _lookupPrimaryStepTabIndex(self, primaryStepName):
    try:
      primaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), 'PrimaryTabBar')
    except (IndexError, RuntimeError):
      return None

    for tabIndex in range(primaryTabBar.count):
      stepName = primaryTabBar.tabData(tabIndex)
      if stepName == primaryStepName:
        return tabIndex

    return None

  def _lookupSecondaryStepTabIndex(self, primaryStepName, secondaryStepName):
    try:
      secondaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), f'{primaryStepName.capitalize()}TabBar')
    except (IndexError, RuntimeError):
      return None

    for tabIndex in range(secondaryTabBar.count):
      stepName = secondaryTabBar.tabData(tabIndex)
      if stepName == secondaryStepName:
        return tabIndex

    return None

  def goto(self, dst: OpenNavUtils.Step, autoSave=True):
    slicer.util.selectModule('Home')

    if dst is None:
      return

     # Get validation function for the destination
    if self.validateSteps:
      validations = OpenNavUtils.Step.validate(dst)
      for validation in validations:
        if validation:
          errorString = validation()
          if errorString:
            self._forceTabReselect()
            slicer.util.errorDisplay(errorString)
            return
        
    src = self.current
    if src and (src.names == dst.names):
      return

    print(src, '->', dst)  # transitioning from src (source) to dst (destination)

    # set new current now to prevent recursion when setting tab index.
    self.current = dst

    # Update workflowToolBar
    primaryStepName = dst.names[1]
    try:
      primaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), 'PrimaryTabBar')
      index = self._lookupPrimaryStepTabIndex(primaryStepName)
      if index is not None:
        print('primary tab index', index)
        primaryTabBar.currentIndex = index
    except (IndexError, RuntimeError):
      pass

    if len(dst.names) == 3:
      secondaryStepName = dst.names[2]
      try:
        secondaryTabBar = slicer.util.findChild(slicer.util.mainWindow(), f"{primaryStepName.capitalize()}TabBar")
        index = self._lookupSecondaryStepTabIndex(primaryStepName, secondaryStepName)
        if index is not None:
          print('secondary tab index', index)
          secondaryTabBar.currentIndex = index
      except (IndexError, RuntimeError):
        pass

    # Collect and execute actions (including teardown and setup)
    # associated with the current transition.
    actions = OpenNavUtils.Step.transition(src, dst)
    for action in actions:
      if action:
        action()

    # AutoSave at end of goto

    if autoSave and not self.autoSaveBlocked:
      print('Autosave started')
      OpenNavUtils.autoSavePlan()
      print('Autosave completed')
    else:
      print('Autosave blocked')

  def gotoNext(self):
    self.goto(self.nextStep)

  def gotoPrev(self):
    self.goto(self.prevStep)

  def gotoByName(self, name):
    self.goto(self.names[name])


