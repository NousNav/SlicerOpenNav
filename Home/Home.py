import os
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
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
    self.parent.dependencies = ["Planning", "Registration", "Navigation"]
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
    self.planningWidget = slicer.modules.planning.createNewWidgetRepresentation()
    self.ui.PlanningTab.layout().addWidget( self.planningWidget )

    self.registrationWidget = slicer.modules.registration.createNewWidgetRepresentation()
    self.ui.RegistrationTab.layout().addWidget( self.registrationWidget )

    self.navigationWidget = slicer.modules.navigation.createNewWidgetRepresentation()
    self.ui.NavigationTab.layout().addWidget(self.navigationWidget)

    self.advanceButton.clicked.connect(lambda: self.primaryTabBar.setCurrentIndex(self.planningTabIndex))
    self.backButton.clicked.connect(lambda: slicer.util.selectModule('Home'))

    self.primaryTabBar.setCurrentIndex(self.patientsTabIndex)
    self.onPrimaryTabChanged(self.patientsTabIndex)

    # Apply style
    self.applyApplicationStyle()

    # self.ui.TreeView.setMRMLScene(slicer.mrmlScene)
    # self.ui.TreeView.nodeTypes = ('vtkMRMLSegmentationNode', 'vtkMRMLVolumeNode')

    # Make sure DICOM widget exists
    slicer.app.connect("startupCompleted()", self.setupDICOMBrowser)

    # Begin listening for new volumes
    self.VolumeNodeTag = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent,
            self.onNodeAdded)

  def setupDICOMBrowser(self):
    # Make sure that the DICOM widget exists
    slicer.modules.dicom.widgetRepresentation()
    self.ui.DICOMToggleButton.toggled.connect(self.toggleDICOMBrowser)
    self.ui.ImportDICOMButton.clicked.connect(self.onDICOMImport)
    self.ui.LoadDataButton.clicked.connect(slicer.util.openAddDataDialog)

    # For some reason, the browser is instantiated as not hidden. Close
    # so that the 'isHidden' check works as required
    slicer.modules.DICOMWidget.browserWidget.close()
    slicer.modules.DICOMWidget.browserWidget.closed.connect(self.resetDICOMToggle)

  def onDICOMImport(self):
    slicer.modules.DICOMWidget.browserWidget.dicomBrowser.openImportDialog()
    self.ui.DICOMToggleButton.checked = qt.Qt.Checked

  def resetDICOMToggle(self):
    self.ui.DICOMToggleButton.checked = qt.Qt.Unchecked
    slicer.util.selectModule('Home')

  def toggleDICOMBrowser(self, show):
    if show:
      slicer.modules.DICOMWidget.onOpenBrowserWidget()
    else:
      slicer.modules.DICOMWidget.browserWidget.close()

  def applyApplicationStyle(self):
    # Style
    self.applyStyle([slicer.app], 'Home.qss')

  def applyStyle(self, widgets, styleSheetName):
    stylesheetfile = self.resourcePath(styleSheetName)
    with open(stylesheetfile,"r") as fh:
      style = fh.read()
      for widget in widgets:
        widget.styleSheet = style

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

    # Bottom toolbar
    self.bottomToolBar = qt.QToolBar("BottomToolBar")
    self.bottomToolBar.setObjectName("BottomToolBar")
    self.bottomToolBar.movable = False
    slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, self.bottomToolBar)
    self.backButton = qt.QPushButton("Back")
    self.backButton.name = 'BackButton'
    self.backButton.visible = False
    self.bottomToolBar.addWidget(self.backButton)
    spacer = qt.QWidget()
    policy = spacer.sizePolicy
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    spacer.setSizePolicy(policy)
    self.bottomToolBar.addWidget(spacer)
    self.advanceButton = qt.QPushButton("Go To Planning")
    self.advanceButton.name = 'AdvanceButton'
    self.advanceButton.enabled = False
    self.bottomToolBar.addWidget(self.advanceButton)

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
      self.enter()
      self.goToFourUpLayout()

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

  def enter(self):

    # Hides other toolbars
    slicer.util.findChild(slicer.util.mainWindow(), 'BottomToolBar').visible = True
    slicer.util.findChild(slicer.util.mainWindow(), 'PlanningBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'PlanningTabBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationTabBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'NavigationBottomToolBar').visible = False

    # Show current
    self.bottomToolBar.visible = True
    self.secondaryToolBar.visible = False

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    self.applyStyle([sidePanel, modulePanel], 'PanelDark.qss')

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
      slicer.util.findChild(slicer.util.mainWindow(), 'BottomToolBar')
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

  def goToFourUpLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    NNUtils.setSliceWidgetSlidersVisible(True)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(False)

  def goToRedSliceLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    NNUtils.setSliceWidgetSlidersVisible(True)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(False)

  def goToPictureLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    NNUtils.setSliceWidgetSlidersVisible(False)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(False)

  def goToRegistrationCameraViewLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    NNUtils.setSliceWidgetSlidersVisible(False)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(True)

  def go3DViewLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    NNUtils.setSliceWidgetSlidersVisible(True)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(True)

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

  def processIncomingVolumeNode(self, node):
    if node.GetDisplayNode() is None:
      node.CreateDefaultDisplayNodes()
    node.GetDisplayNode().SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
    self.advanceButton.enabled = True

    displayNode = node.GetDisplayNode()
    range = node.GetImageData().GetScalarRange()
    if range[1] - range[0] < 4000:
      displayNode.SetAutoWindowLevel(True)
    else:
      displayNode.SetAutoWindowLevel(False)
      displayNode.SetLevel(50)
      displayNode.SetWindow(100)
    self.setup3DView()
    self.setupSliceViewers()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, calldata):
    node = calldata
    if isinstance(node, slicer.vtkMRMLVolumeNode):
      # Call processing using a timer instead of calling it directly
      # to allow the volume loading to fully complete.
      # TODO: no event for volume loading done?
      qt.QTimer.singleShot(1000, lambda: self.processIncomingVolumeNode(node))

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

  def loadDICOM(self, dicomData):

    print("Loading DICOM from command line")
    # dicomDataDir = "c:/my/folder/with/dicom-files"  # input folder with DICOM files
    loadedNodeIDs = []  # this list will contain the list of all loaded node IDs

    from DICOMLib import DICOMUtils
    with DICOMUtils.TemporaryDICOMDatabase() as db:
      self.importDicom(dicomData, db)
      patientUIDs = db.patients()
      for patientUID in patientUIDs:
        loadedNodeIDs.extend(DICOMUtils.loadPatientByUID(patientUID))

  def importDicom(self, dicomDataItem, dicomDatabase=None, copyFiles=False):
    """ Import DICOM files from folder into Slicer database
    """
    try:
      indexer = ctk.ctkDICOMIndexer()
      assert indexer is not None
      if dicomDatabase is None:
        dicomDatabase = slicer.dicomDatabase
      if os.path.isdir(dicomDataItem):
        indexer.addDirectory(dicomDatabase, dicomDataItem, copyFiles)
        indexer.waitForImportFinished()
      elif os.path.isfile(dicomDataItem):
        indexer.addFile(dicomDatabase, dicomDataItem, copyFiles)
        indexer.waitForImportFinished()
      else:
        print('Item type is not recognized')
    except Exception:
      import traceback
      traceback.print_exc()
      logging.error('Failed to import DICOM folder/file ' + dicomDataItem)
      return False
    return True
