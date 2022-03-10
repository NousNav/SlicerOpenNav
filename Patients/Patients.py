import ctk
import logging
import os.path
import slicer
import slicer.modules
import slicer.util

from slicer.ScriptedLoadableModule import *


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

  def setup(self):
    super().setup()

    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Patients.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    self.logic = PatientsLogic()

  def enter(self):
    pass

  def exit(self):
    pass


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
