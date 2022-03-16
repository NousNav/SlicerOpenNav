from collections import OrderedDict
import qt
import slicer
import typing

from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import NNUtils


class Home(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NousNav Home"
    self.parent.categories = [""]
    self.parent.dependencies = ["Patients", "Planning", "Registration", "Navigation"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the Home module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class HomeWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Home.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    # Remove uneeded UI elements, add toolbars
    self.modifyWindowUI()

    innerTabBar = qt.QTabBar()
    self.secondaryTabWidgetUI.CenterArea.layout().addWidget(innerTabBar)

    patients = slicer.modules.patients.createNewWidgetRepresentation()
    planning = slicer.modules.planning.createNewWidgetRepresentation()
    registration = slicer.modules.registration.createNewWidgetRepresentation()
    navigation = slicer.modules.navigation.createNewWidgetRepresentation()

    info = Workflow(
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

    # Apply style
    self.applyApplicationStyle()

  def applyApplicationStyle(self):
    NNUtils.applyStyle([slicer.app], self.resourcePath("Home.qss"))

  def setupNodes(self):
    # Set up the layout / 3D View
    self.setup3DView()
    self.setupSliceViewers()

  def onClose(self, unusedOne, unusedTwo):
    pass

  def cleanup(self):
    pass

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
    nousNavLabel = qt.QLabel('NousNav')
    nousNavLabel.setObjectName("NousNavLabel")
    self.primaryToolBar.addWidget(nousNavLabel)
    self.primaryToolBar.addWidget(self.primaryTabWidget)

    # Settings dialog
    gearIcon = qt.QIcon(self.resourcePath('Icons/Gears.png'))
    self.settingsAction = self.primaryToolBar.addAction(gearIcon, "")
    self.settingsDialog = slicer.util.loadUI(self.resourcePath('UI/Settings.ui'))
    self.settingsUI = slicer.util.childWidgetVariables(self.settingsDialog)
    self.settingsUI.CustomUICheckBox.toggled.connect(self.setCustomUIVisible)
    self.settingsUI.CustomStyleCheckBox.toggled.connect(self.toggleStyle)
    self.settingsAction.triggered.connect(self.raiseSettings)

    # Tabs for secondary toolbars - navigation and registration
    self.secondaryTabWidget = slicer.util.loadUI(self.resourcePath('UI/CenteredWidget.ui'))
    self.secondaryTabWidget.setObjectName("SecondaryCenteredWidget")
    self.secondaryTabWidgetUI = slicer.util.childWidgetVariables(self.secondaryTabWidget)
    self.secondaryToolBar.addWidget(self.secondaryTabWidget)

    # Side Widget
    dockWidget = qt.QDockWidget(slicer.util.mainWindow())
    dockWidget.name = 'SidePanelDockWidget'
    self.SidePanelWidget = qt.QWidget(dockWidget)
    self.SidePanelWidget.setLayout(qt.QVBoxLayout())
    self.SidePanelWidget.name = 'SidePanelWidget'
    dockWidget.setWidget(self.SidePanelWidget)
    dockWidget.setFeatures(dockWidget.NoDockWidgetFeatures)
    slicer.util.mainWindow().addDockWidget(qt.Qt.RightDockWidgetArea , dockWidget)

  def toggleStyle(self,visible):
    if visible:
      self.applyApplicationStyle()
    else:
      slicer.app.styleSheet = ''

  def raiseSettings(self, unused):
    self.settingsDialog.exec()

  def setCustomUIVisible(self, visible):
    self.setSlicerUIVisible(not visible)

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

  def setup3DView(self):
    layoutManager = slicer.app.layoutManager()
    controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
    controller.setBlackBackground()
    controller.set3DAxisVisible(False)
    controller.set3DAxisLabelVisible(False)
    controller.setOrientationMarkerType(3)  # Axis marker
    controller.setStyleSheet("background-color: #000000")

    threeDWidget = layoutManager.threeDWidget(0)
    threeDWidget.mrmlViewNode().SetBoxVisible(False)
    threeDWidget.threeDController().visible = False
    horizontalSpacer = qt.QSpacerItem(0, 0, qt.QSizePolicy.Expanding, qt.QSizePolicy.Minimum)
    threeDWidget.layout().insertSpacerItem(0, horizontalSpacer)

  def setupSliceViewers(self):
    for name in slicer.app.layoutManager().sliceViewNames():
        sliceWidget = slicer.app.layoutManager().sliceWidget(name)
        self.setupSliceViewer(sliceWidget)

  def setupSliceViewer(self, sliceWidget):
    controller = sliceWidget.sliceController()
    controller.setStyleSheet("background-color: #000000")
    controller.sliceViewLabel = ''
    slicer.util.findChild(sliceWidget, "PinButton").visible = False
    slicer.util.findChild(sliceWidget, "ViewLabel").visible = False
    slicer.util.findChild(sliceWidget, "FitToWindowToolButton").visible = False
    slicer.util.findChild(sliceWidget, "SliceOffsetSlider").spinBoxVisible = False


class Step:
  def __init__(self, names, setups, teardowns):
    self.names = names
    self.setups = setups
    self.teardowns = teardowns
    self.nextStep = None
    self.prevStep = None

  def __str__(self) -> str:
     return "step({})".format(",".join(self.names))

  @classmethod
  def one(cls, name, setup, teardown):
    return Step((name,), (setup,), (teardown,))

  def concat(self, other):
    cls = type(self)
    return cls(
      self.names + other.names,
      self.setups + other.setups,
      self.teardowns + other.teardowns,
    )

  @classmethod
  def transition(cls, lhs, rhs):
    """Find the actions needed to transition from self to other. Teardown self, then setup other."""
    if not lhs or not rhs:
      if lhs:
        yield from reversed(lhs.teardowns)
      if rhs:
        yield from rhs.setups
      return

    # find the first index i where self.names and other.names differ
    for i, (l, r) in enumerate(zip(lhs.names, rhs.names)):
      if l != r:
        break
    else:
      return # the lhs and rhs are the same; no action needed.

    yield from reversed(lhs.teardowns[i:])  # teardown in reverse order; context is a stack.
    yield from rhs.setups[i:]


class Workflow:
  def __init__(
    self,
    name,
    widget=None,
    setup=None,
    teardown=None,
    nested=(),
    engine=None,
  ):
    self.name = name
    self.widget = widget
    self.setup = setup
    self.teardown = teardown
    self.nested = nested
    self.engine = engine

  def gotoNext(self):
    if self.engine:
      self.engine.gotoNext()

  def gotoPrev(self):
    if self.engine:
      self.engine.gotoPrev()

  def gotoByName(self, name):
    if self.engine:
      self.engine.gotoByName(name)

  def flatten(self, stack):
    if self.widget:
      stack.addWidget(self.widget)

    if not self.nested:
      def setup():
        if self.widget:
          stack.setCurrentWidget(self.widget)
        if self.setup:
          self.setup()

      def teardown():
        if self.teardown:
          self.teardown()

      yield Step.one(self.name, setup, teardown)
    else:

      for nested in self.nested:

        def setup(idx=None):
          if self.widget:
            stack.setCurrentWidget(self.widget)
          if self.setup:
            self.setup()

        def teardown():
          if self.teardown:
            self.teardown()

        if self.engine:
          nested.engine = self.engine

        this = Step.one(self.name, setup, teardown)

        for step in nested.flatten(stack):
          yield this.concat(step)


class HomeLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  _currentName: typing.Tuple[str] = NNUtils.parameterProperty('CURRENT_STEP_NAME', default=None)

  @property
  def current(self) -> Step:
    name = self._currentName
    if name is None:
      return None

    return self.names[tuple(name)]

  @current.setter
  def current(self, value: Step):
    self._currentName = tuple(value.names)

  @property
  def nextStep(self):
    return self.current.nextStep

  @property
  def prevStep(self):
    return self.current.prevStep

  def __init__(self, info: Workflow, stack):
    super().__init__()

    info.engine = self

    self.stack = stack

    self.steps = list(info.flatten(stack))
    self.names = {step.names: step for step in self.steps}

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
    for name, step in self.primarySteps.items():
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
    self.goto(self.steps[0])

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

  def goto(self, dst: Step):
    slicer.util.selectModule('Home')

    if dst is None:
      return

    src = self.current
    if src and (src.names == dst.names):
      return

    print(src, '->', dst)

    # set new current name now to prevent recursion when setting tab index.
    self._currentName = dst.names

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
    actions = Step.transition(src, dst)
    for action in actions:
      if action:
        action()

  def gotoNext(self):
    self.goto(self.nextStep)

  def gotoPrev(self):
    self.goto(self.prevStep)

  def gotoByName(self, name):
    self.goto(self.names[name])
