import ctk
import logging
import os.path
import qt
import slicer
import slicer.modules
import slicer.util
import vtk

from slicer.ScriptedLoadableModule import *

import NNUtils


class Patients(ScriptedLoadableModule):
  def __init__(self, parent):
    super().__init__(parent)

    self.parent.title = "NousNav Patients"
    self.parent.categories = [""]
    self.parent.dependencies = []
    self.parent.contributors = [
      "David Allemang (Kitware Inc.)",
      "Sam Horvath (Kitware Inc.)",
    ]
    self.parent.helpText = "This is the Patients module for the NousNav application. "
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = ""


class PatientsWidget(ScriptedLoadableModuleWidget):
  def __init__(self, parent):
    super().__init__(parent)
    self.VolumeNodeTag = None

  def setup(self):
    super().setup()

    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Patients.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    self.logic = PatientsLogic()

    # Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    # Bottom toolbar
    (
      self.bottomToolBar,
      self.backButton,
      self.backButtonAction,
      self.advanceButton,
      self.advanceButtonAction,
    ) = NNUtils.setupWorkflowToolBar(
      "Patients", backButtonText="Back", advanceButtonText="Go To Planning"
    )

    # Default
    self.backButton.visible = False
    self.advanceButtonAction.enabled = False

    # Make sure DICOM widget exists
    slicer.app.connect("startupCompleted()", self.setupDICOMBrowser)

  def enter(self):
    # Hides other toolbars
    slicer.util.findChild(slicer.util.mainWindow(), 'PlanningBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'PlanningTabBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationTabBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'NavigationBottomToolBar').visible = False

    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    NNUtils.applyStyle([sidePanel, modulePanel], self.resourcePath("PanelDark.qss"))

    # Begin listening for new volumes
    if self.VolumeNodeTag is None:
      self.VolumeNodeTag = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)

    self.goToFourUpLayout()

  def goToFourUpLayout(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    NNUtils.setSliceWidgetSlidersVisible(True)
    NNUtils.setMainPanelVisible(True)
    NNUtils.setSidePanelVisible(False)

  def exit(self):
    pass

  def onClose(self, o, e):
    pass

  def cleanup(self):
    pass

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

  def processIncomingVolumeNode(self, node):
    if node.GetDisplayNode() is None:
      node.CreateDefaultDisplayNodes()
    node.GetDisplayNode().SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
    self.advanceButtonAction.enabled = True

    displayNode = node.GetDisplayNode()
    range = node.GetImageData().GetScalarRange()
    if range[1] - range[0] < 4000:
      displayNode.SetAutoWindowLevel(True)
    else:
      displayNode.SetAutoWindowLevel(False)
      displayNode.SetLevel(50)
      displayNode.SetWindow(100)
    slicer.modules.HomeWidget.setup3DView()
    slicer.modules.HomeWidget.setupSliceViewers()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, calldata):
    node = calldata
    if isinstance(node, slicer.vtkMRMLVolumeNode):
      # Call processing using a timer instead of calling it directly
      # to allow the volume loading to fully complete.
      # TODO: no event for volume loading done?
      qt.QTimer.singleShot(1000, lambda: self.processIncomingVolumeNode(node))


class PatientsLogic(ScriptedLoadableModuleLogic):

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
