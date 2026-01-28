from datetime import datetime
import logging
import os.path
import pathlib
import time

import ctk
import qt
import slicer
import slicer.modules
import slicer.util
import vtk

from slicer.ScriptedLoadableModule import (
  ScriptedLoadableModule,
  ScriptedLoadableModuleWidget,
  ScriptedLoadableModuleLogic,
)

import Home
import OpenNavUtils


class Patients(ScriptedLoadableModule):
  def __init__(self, parent):
    super().__init__(parent)

    self.parent.title = "OpenNav Patients"
    self.parent.categories = [""]
    self.parent.dependencies = []
    self.parent.contributors = [
      "David Allemang (Kitware Inc.)",
      "Sam Horvath (Kitware Inc.)",
    ]
    self.parent.helpText = "This is the Patients module for the OpenNav application. "
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = ""

    # Make sure DICOM widget exists
    slicer.app.connect("startupCompleted()", self.createDICOMWidget)

  def createDICOMWidget(self):
    """Create the DICOM widget if it does not already exist.

    .. warning::

        This function is expected to be called only once and it will log an error
        message and return otherwise.
    """

    if hasattr(slicer.modules, "DICOMWidget"):
      logging.error("error: DICOMWidget is already instantiated: PatientsWidget.createDICOMWidget() should be called only once.")
      return

    slicer.modules.dicom.widgetRepresentation()
    # For some reason, the browser is instantiated as not hidden. Close
    # so that the 'isHidden' check works as required
    slicer.modules.DICOMWidget.browserWidget.close()


class PatientsWidget(ScriptedLoadableModuleWidget):
  def __init__(self, parent):
    super().__init__(parent)
    self.VolumeNodeTag = None

    self.workflow = Home.Workflow(
      'patients',
      widget=self.parent,
      setup=self.enter,
      teardown=self.exit,
    )

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
    ) = OpenNavUtils.setupWorkflowToolBar("Patients")

    OpenNavUtils.addCssClass(self.bottomToolBar, "bottom-toolbar--color-dark")

    # Default
    self.advanceButtonAction.enabled = False

    self.setupCaseDialog()

    self.ui.DICOMToggleButton.clicked.connect(self.toggleDICOMBrowser)
    self.ui.ImportDICOMButton.clicked.connect(PatientsWidget.onDICOMImport)

    

    self.ui.planButton.toggled.connect(self.onPlanButtonToggled)
    self.ui.PatientListButton.clicked.connect(self.launchPatientListDialog)
    self.ui.dicomPathButton.clicked.connect(self.onDicomPathButtonClicked)

  def onPlanButtonToggled(self,checked):
    if checked:
      self.loadCaseFromPanel()
    else:
      self.closePlan()
    self.updateGUIFromPatientState()

  def onDicomPathButtonClicked(self):
    dicomBrowser = slicer.modules.DICOMWidget.browserWidget.dicomBrowser
    dicomBrowser.selectDatabaseDirectory()
  
  
  @OpenNavUtils.backButton(text="Back", visible=False)
  @OpenNavUtils.advanceButton(text="Go To Planning")
  def enter(self):
    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = True

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    centralPanel = slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidget')
    for widget in [modulePanel, sidePanel, centralPanel]:
      OpenNavUtils.setCssClass(widget, "widget--color-dark")
      OpenNavUtils.polish(widget)

    # Begin listening for new volumes
    if self.VolumeNodeTag is None:
      self.VolumeNodeTag = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent, self.onNodeAdded)

    # Passing the special value "keep-current" ensure the layer is not modified
    # See https://slicer.readthedocs.io/en/latest/developer_guide/slicer.html#slicer.util.setSliceViewerLayers
    OpenNavUtils.goToFourUpLayout(volumeNode='keep-current')
    self.updateCasesList()
    self.updateGUIFromPatientState()

  def exit(self):
    # Hide current
    self.bottomToolBar.visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False

    PatientsWidget.setDICOMBrowserVisible(False)
  
  def updateGUIFromPatientState(self):
    master_volume = slicer.modules.PlanningWidget.logic.master_volume
    self.ui.DICOMToggleButton.enabled = not master_volume
    self.ui.PatientListButton.enabled = not master_volume
    
    self.ui.planButton.enabled = (not master_volume and len(self.ui.CasesTableWidget.selectedItems()) != 0) or master_volume
    self.patientListDialogUI.OpenButton.enabled = len(self.patientListDialogUI.CasesTableWidgetDialog.selectedItems()) != 0
    self.patientListDialogUI.RemoveButton.enabled = len(self.patientListDialogUI.CasesTableWidgetDialog.selectedItems()) != 0

    slicer.modules.HomeWidget.patientNameLabel.text = 'Patient: ' + str(slicer.modules.PlanningWidget.logic.case_name)

    if master_volume:
      self.ui.planButton.text = 'Close Current Patient'
    else:
      self.ui.planButton.text = 'Open Patient'
    
    if hasattr(slicer.modules, "DICOMWidget"):
      if master_volume:
        PatientsWidget.setDICOMBrowserVisible(False)
      self.ui.ImportDICOMButton.visible = not slicer.modules.DICOMWidget.browserWidget.isHidden()
      self.ui.dicomPathButton.visible = not slicer.modules.DICOMWidget.browserWidget.isHidden()
      if slicer.modules.DICOMWidget.browserWidget.isHidden():
         self.ui.DICOMToggleButton.text = 'Add Patient From DICOM'
      else:
         self.ui.DICOMToggleButton.text = 'Close DICOM Database'
    else:
      self.ui.ImportDICOMButton.visible = False
      self.ui.dicomPathButton.visible = False

  def onClose(self, o, e):
    pass

  def cleanup(self):
    pass

  def setupCaseDialog(self):
    self.caseDialog = slicer.util.loadUI(self.resourcePath('UI/CaseNameDialog.ui'))
    self.caseDialog.setWindowFlags(qt.Qt.CustomizeWindowHint)
    self.caseDialogUI = slicer.util.childWidgetVariables(self.caseDialog)
    self.caseDialog.accepted.connect(self.startNewCase)
    self.ui.CasesTableWidget.itemSelectionChanged.connect(self.updateGUIFromPatientState)
    self.patientListDialog = slicer.util.loadUI(self.resourcePath('UI/PatientListDialog.ui'))
    self.patientListDialogUI = slicer.util.childWidgetVariables(self.patientListDialog)
    self.patientListDialogUI.CasesTableWidgetDialog.itemSelectionChanged.connect(self.updateGUIFromPatientState)
    self.patientListDialogUI.OpenButton.clicked.connect(self.loadCaseFromList)
    self.patientListDialogUI.RemoveButton.clicked.connect(self.removeCaseFromList)
    self.patientListDialogUI.CasesTableWidgetDialog.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.ResizeToContents)
    self.patientListDialogUI.CasesTableWidgetDialog.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)
    self.ui.CasesTableWidget.horizontalHeader().setSectionResizeMode(1, qt.QHeaderView.ResizeToContents)
    self.ui.CasesTableWidget.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)


  def startNewCase(self):
    print('start a new case')
    slicer.modules.PlanningWidget.logic.case_name = self.caseDialogUI.CaseNameLineEdit.text
    slicer.modules.HomeWidget.logic.autoSavePlan()
    self.updateCasesList()
    self.updateGUIFromPatientState()
  
  def launchPatientListDialog(self):
    self.patientListDialog.exec()
    self.updateGUIFromPatientState()
  
  def launchCaseNameDialog(self):
    self.caseDialogUI.CaseNameLineEdit.text = OpenNavUtils.slugify(slicer.modules.PlanningWidget.logic.master_volume.GetName())
    self.caseDialog.exec()

  def updateCasesList(self):
    print("Updating table")
    cases = OpenNavUtils.listAvailablePlans()
    self.ui.CasesTableWidget.clearContents()
    recentRowCount = len(cases) if len(cases) < 5 else 5
    self.ui.CasesTableWidget.setRowCount(recentRowCount)
    self.patientListDialogUI.CasesTableWidgetDialog.clearContents()
    self.patientListDialogUI.CasesTableWidgetDialog.setRowCount(len(cases))
    for i, (case, date) in enumerate(cases):
      if i < 5:    # add to shortcuts
        item_name_panel = qt.QTableWidgetItem(case)
        item_date_panel = qt.QTableWidgetItem(datetime.fromtimestamp(date).strftime("%b %d %H:%M %Y"))
        self.ui.CasesTableWidget.setItem(i, 0, item_name_panel)
        self.ui.CasesTableWidget.setItem(i, 1, item_date_panel)
      item_name_list = qt.QTableWidgetItem(case)
      item_date_list = qt.QTableWidgetItem(datetime.fromtimestamp(date).strftime("%b %d %H:%M %Y"))
      self.patientListDialogUI.CasesTableWidgetDialog.setItem(i, 0, item_name_list)
      self.patientListDialogUI.CasesTableWidgetDialog.setItem(i, 1, item_date_list)
  
  def loadCaseFromPanel(self):
    currentRow = self.ui.CasesTableWidget.currentRow()
    caseItem = self.ui.CasesTableWidget.item(currentRow, 0)
    caseName = caseItem.text()
    self.loadCase(caseName)

  def loadCaseFromList(self):
     currentRow = self.patientListDialogUI.CasesTableWidgetDialog.currentRow()
     caseItem = self.patientListDialogUI.CasesTableWidgetDialog.item(currentRow, 0)
     caseName = caseItem.text()
     self.loadCase(caseName)

  def removeCaseFromList(self):
    currentRow = self.patientListDialogUI.CasesTableWidgetDialog.currentRow()
    caseItem = self.patientListDialogUI.CasesTableWidgetDialog.item(currentRow, 0)
    caseName = caseItem.text()
    OpenNavUtils.deleteAutoSave(caseName)
    self.updateCasesList()
  
  def loadCase(self, caseName):
    master_volume = slicer.modules.PlanningWidget.logic.master_volume
    if master_volume:
      return  # already loaded
    print('load a case: ' + caseName)
    slicer.modules.PlanningWidget.logic.case_name = caseName
    OpenNavUtils.loadAutoSave(slicer.modules.PlanningWidget.logic.case_name)
    slicer.modules.PlanningWidget.logic.case_name = caseName
    self.updateGUIFromPatientState()
    
  def closePlan(self):
    slicer.modules.PlanningWidget.logic.clearPlanningData()
    slicer.modules.RegistrationWidget.logic.clearRegistrationData()
    slicer.modules.PlanningWidget.landmarkLogic.clearPlanningLandmarks()
    slicer.modules.RegistrationWidget.landmarks.clearTrackerLandmarks()
    self.updateGUIFromPatientState()
   
  @staticmethod
  def onDICOMImport():

    # ... then open the DICOM import dialog
    dicomBrowser = slicer.modules.DICOMWidget.browserWidget.dicomBrowser
    dicomBrowser.openImportDialog()

  def toggleDICOMBrowser(self):
    PatientsWidget.setDICOMBrowserVisible(slicer.modules.DICOMWidget.browserWidget.isHidden())
    self.updateGUIFromPatientState()

  @staticmethod
  def setDICOMBrowserVisible(visible):
    if visible:
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
    self.updateGUIFromPatientState()
    if not slicer.modules.PlanningWidget.logic.case_name:
      self.launchCaseNameDialog()

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, calldata):
    node = calldata
    if isinstance(node, slicer.vtkMRMLVolumeNode):
      # Call processing using a timer instead of calling it directly
      # to allow the volume loading to fully complete.
      # TODO: no event for volume loading done?
      qt.QTimer.singleShot(500, lambda: self.processIncomingVolumeNode(node))

  def onLoadPlanButtonClicked(self):
    default_dir = qt.QStandardPaths.writableLocation(qt.QStandardPaths.DocumentsLocation)

    dialog = qt.QFileDialog()
    plan_path = dialog.getOpenFileName(
      slicer.util.mainWindow(),
      'Open OpenNav Plan',
      default_dir,
      '*.mrb',
    )
    if not plan_path:
      return

    plan_path = pathlib.Path(plan_path)
    if plan_path.suffix != '.mrb':
      plan_path = plan_path.with_suffix('.mrb')

    print(f'loading plan: {plan_path}')

    slicer.util.loadScene(str(plan_path))
    slicer.app.layoutManager().activeThreeDRenderer().ResetCamera()


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
