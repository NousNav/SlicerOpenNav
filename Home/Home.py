import qt
import slicer

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

    # Create logic class
    self.logic = HomeLogic()

    # setup scene
    self.setupNodes()

    # Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    # The home module is a place holder for the planning, registration and navigation modules
    self.patientsWidget = slicer.modules.patients.createNewWidgetRepresentation()
    self.ui.PatientsTab.layout().addWidget(self.patientsWidget)

    self.planningWidget = slicer.modules.planning.createNewWidgetRepresentation()
    self.ui.PlanningTab.layout().addWidget(self.planningWidget)

    self.registrationWidget = slicer.modules.registration.createNewWidgetRepresentation()
    self.ui.RegistrationTab.layout().addWidget(self.registrationWidget)

    self.navigationWidget = slicer.modules.navigation.createNewWidgetRepresentation()
    self.ui.NavigationTab.layout().addWidget(self.navigationWidget)

    self.patientsWidget.self().advanceButton.clicked.connect(lambda: self.primaryTabBar.setCurrentIndex(self.planningTabIndex))
    self.patientsWidget.self().backButton.clicked.connect(lambda: slicer.util.selectModule('Home'))

    self.primaryTabBar.setCurrentIndex(self.patientsTabIndex)
    self.onPrimaryTabChanged(self.patientsTabIndex)

    # Apply style
    self.applyApplicationStyle()

    # self.ui.TreeView.setMRMLScene(slicer.mrmlScene)
    # self.ui.TreeView.nodeTypes = ('vtkMRMLSegmentationNode', 'vtkMRMLVolumeNode')

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
    self.patientsTabIndex = self.primaryTabBar.addTab("Patients")
    self.planningTabIndex = self.primaryTabBar.addTab("Planning")
    self.registrationTabIndex = self.primaryTabBar.addTab("Registration")
    self.navigationTabIndex = self.primaryTabBar.addTab("Navigation")
    self.primaryTabWidgetUI.CenterArea.layout().addWidget(self.primaryTabBar)
    self.primaryTabBar.currentChanged.connect(self.onPrimaryTabChanged)

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
    self.settingsUI.CustomUICheckBox.toggled.connect(self.toggleUI)
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
    self.hideSlicerUI()

  def onPrimaryTabChanged(self, index):
    print('Primary tab changed')
    self.registrationWidget.exit()
    self.planningWidget.exit()

    if index == self.patientsTabIndex:
      slicer.util.selectModule('Home')
      self.ui.HomeWidget.setCurrentWidget(self.ui.PatientsTab)
      self.patientsWidget.enter()

    if index == self.planningTabIndex:
      slicer.util.selectModule('Home')
      self.ui.HomeWidget.setCurrentWidget(self.ui.PlanningTab)
      self.planningWidget.enter()

    if index == self.navigationTabIndex:
      slicer.util.selectModule('Home')
      self.ui.HomeWidget.setCurrentWidget(self.ui.NavigationTab)
      self.navigationWidget.enter()

    if index == self.registrationTabIndex:
      self.planningWidget.exit()
      slicer.util.selectModule('Home')
      self.ui.HomeWidget.setCurrentWidget(self.ui.RegistrationTab)
      self.registrationWidget.enter()

  def toggleStyle(self,visible):
    if visible:
      self.applyApplicationStyle()
    else:
      slicer.app.styleSheet = ''

  def toggleUI(self, visible):

    if visible:
      self.hideSlicerUI()
    else:
      self.showSlicerUI()

  def raiseSettings(self, unused):
    self.settingsDialog.exec()

  def hideSlicerUI(self):
    slicer.util.setDataProbeVisible(False)
    slicer.util.setMenuBarsVisible(False, ignore=['MainToolBar', 'ViewToolBar'])
    slicer.util.setModuleHelpSectionVisible(False)
    slicer.util.setModulePanelTitleVisible(False)
    slicer.util.setPythonConsoleVisible(False)
    slicer.util.setApplicationLogoVisible(False)
    slicer.util.setToolbarsVisible(True)
    keepToolbars = [
      slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'PrimaryToolBar'),
      ]
    slicer.util.setToolbarsVisible(False, keepToolbars)

  def showSlicerUI(self):
    slicer.util.setDataProbeVisible(True)
    slicer.util.setMenuBarsVisible(True)
    slicer.util.setModuleHelpSectionVisible(True)
    slicer.util.setModulePanelTitleVisible(True)
    slicer.util.setPythonConsoleVisible(True)
    slicer.util.setToolbarsVisible(True)
    slicer.util.setApplicationLogoVisible(True)

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


class HomeLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  pass
