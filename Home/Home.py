import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
import textwrap

class Home(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Home" 
    self.parent.categories = [""]
    self.parent.dependencies = ["Planning", "Registration", "Navigation", "VolumeRendering"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"] 
    self.parent.helpText = """
This is the Home module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap
from slicer.util import VTKObservationMixin


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

    
    #Remove uneeded UI elements
    self.modifyWindowUI()

    #Create logic class
    self.logic = HomeLogic()   

    #setup scene
    self.setupNodes()

    #Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())


    #The home module is a place holder for the planning, registration and navigation modules
    self.planningWidget = slicer.modules.planning.createNewWidgetRepresentation()
    self.ui.PlanningTab.layout().addWidget( self.planningWidget )

    self.registrationWidget = slicer.modules.registration.createNewWidgetRepresentation()
    self.ui.RegistrationTab.layout().addWidget( self.registrationWidget )

    self.navigationWidget = slicer.modules.navigation.createNewWidgetRepresentation()
    self.ui.NavigationTab.layout().addWidget(self.navigationWidget)


    #Begin listening for new volumes
    self.VolumeNodeTag = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent, 
            self.onNodeAdded)

    #Apply style
    #self.applyStyle()

  def applyStyle(self):
    # Style
    stylesheetfile = self.resourcePath('Home.qss')
    with open(stylesheetfile,"r") as fh:
      slicer.app.styleSheet = fh.read()

  def setupNodes(self):
    #Set up the layout / 3D View
    self.setup3DView()
    self.setupSliceViewers()

  def showAdvancedEffects(self, show):    
    for effect in self.effectsToHide:
      widget = slicer.util.findChild(self.segWidget, effect)
      widget.visible = show

  def onClose(self, unusedOne, unusedTwo):
    pass
  
  def cleanup(self):
    pass
        
  def modifyWindowUI(self):
    slicer.util.setModuleHelpSectionVisible(False)

    slicer.util.mainWindow().moduleSelector().modulesMenu().removeModule('Annotations', False)
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeModule('Markups', False)
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeModule('Transforms', False)
    #slicer.util.mainWindow().moduleSelector().modulesMenu().removeModule('Data', False)
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeModule('SegmentEditor', False)

    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Informatics')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Registration')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Segmentation')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Quantification')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Diffusion')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Converters')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Utilities')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Developer Tools')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Legacy')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('IGT')
    slicer.util.mainWindow().moduleSelector().modulesMenu().removeCategory('Filtering')
    #slicer.util.mainWindow().moduleSelector().modulesMenu().allModulesCategoryVisible= False


    slicer.util.setDataProbeVisible(False)
    #slicer.util.setMenuBarsVisible(False, ignore=['MainToolBar', 'ViewToolBar'])
    slicer.util.setModuleHelpSectionVisible(False)
    slicer.util.setModulePanelTitleVisible(False)
    slicer.util.setPythonConsoleVisible(False)
    slicer.util.setToolbarsVisible(True)
    mainToolBar = slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar')
    keepToolbars = [
      slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'ViewToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'ModuleSelectorToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'MouseModeToolBar')
      ]
    slicer.util.setToolbarsVisible(False, keepToolbars)
    
    hideToolBar = qt.QToolBar("HideToolBar")
    hideToolBar.name = "hideToolBar"
    slicer.util.mainWindow().insertToolBar(mainToolBar, hideToolBar)
    def toggleHide():
        panel = slicer.util.findChild(slicer.util.mainWindow(), "PanelDockWidget")
        if self.hideAction.isChecked():
            panel.hide()
        else:
            panel.show()

    logo =qt.QPixmap(self.resourcePath('Icons/Home.png') )
    logoIcon = qt.QIcon(logo)
    self.hideAction = hideToolBar.addAction(logoIcon, "")
    self.hideAction.setObjectName("HideToolBar")
    self.hideAction.setCheckable( True )
    self.hideAction.toggled.connect( toggleHide )
    
    

    central = slicer.util.findChild(slicer.util.mainWindow(), name='CentralWidget')
    central.setStyleSheet("background-color: #464449")


  def setLabelMapVolumeDefaults(self):
    defaultNode = slicer.vtkMRMLVolumeArchetypeStorageNode()
    defaultNode.SetDefaultWriteFileExtension('nii.gz')
    slicer.mrmlScene.AddDefaultNode(defaultNode)

  def setTablesDefaults(self):
    defaultNode = slicer.vtkMRMLTableStorageNode()
    defaultNode.SetDefaultWriteFileExtension('csv')
    slicer.mrmlScene.AddDefaultNode(defaultNode)    
  
  def setup3DView(self):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
    controller.setBlackBackground()
    controller.set3DAxisVisible(False)
    controller.set3DAxisLabelVisible(False)
    controller.setOrientationMarkerType(3)  #Axis marker
    #controller.setStyleSheet("background-color: #222222")    

  def setup2DViewForNode(self, node):
    layoutManager = slicer.app.layoutManager()
    sliceColor = self.getSliceViewFor2DNode(node)
    if sliceColor == 'Red':
      layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    elif sliceColor == 'Green':
      layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpGreenSliceView)
    elif sliceColor == 'Yellow':
      layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpYellowSliceView)
  
  
  def getSliceViewFor2DNode(self, node):    
    ijk2ras = vtk.vtkMatrix4x4()
    node.GetIJKToRASMatrix(ijk2ras)
    scanOrder = slicer.vtkMRMLVolumeNode.ComputeScanOrderFromIJKToRAS(ijk2ras)
    if scanOrder == 'IS' or scanOrder == 'SI':
      return 'Red'
    elif scanOrder == 'PA' or scanOrder == 'AP':
      return 'Green'
    elif scanOrder == 'LR' or scanOrder == 'RL':
      return 'Yellow'

  def imageIs2D(self, node):
    data = node.GetImageData()
    dimension = data.GetDimensions()
    return (min(dimension) == 1)

  def hasStringInName(self,text, node):
    name = node.GetName()
    hasText = name.lower().find(text) != -1
    return hasText
  
  def determineImageType(self, node):
    dimension = 3
    modality = 'None'

    if self.imageIs2D(node):
      dimension = 2

    #use subject hierarchy to get modality - most reliable
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    node_item = shNode.GetItemByDataNode(node)
    sh_modality = shNode.GetItemAttribute(node_item, 'DICOM.Modality')

    #Then, check modality in MRML Node    
    mrml_modality = node.GetAttribute('DICOM.Modality')
    

    #Could not find modality
    return dimension, modality
  
  def processIncomingVolumeNode(self, node):
   
    dimension, modality = self.determineImageType(node)    

    if node.GetDisplayNode() is None:
      node.CreateDefaultDisplayNodes()
    
    

    if self.sceneDataIs2DOnly():
      self.setup2DViewForNode(node)     
    else:
      self.setup3DView()

    # Copy over modality tag for all images
    if modality != '':
      node.SetAttribute('DICOM.Modality', modality)

    #Display CT image
    self.displayCTImage(node)
  

  def sceneDataIs2DOnly(self):
    volumesList = slicer.util.getNodesByClass('vtkMRMLVolumeNode')
    slicePlane = None

    for volume in volumesList:
      is2D = self.imageIs2D(volume)
      if is2D:
        #check if all 2D images are in same plane
        if not slicePlane:
          slicePlane = self.getSliceViewFor2DNode(volume)
        else:
          if self.getSliceViewFor2DNode(volume) != slicePlane:
            return False  #multiple 2D images in different slice planes exist
      else:
        return False
    
    #No 3D images found
    return True
  
  
  def displayCTImage(self, node):
    self.setup3DView()
    node.GetDisplayNode().SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
    volumeComboBox = slicer.util.findChild(self.planningWidget.self().volumerenderWidget, "VolumeNodeComboBox")
    volumeComboBox.setCurrentNode( node )
    volRenLogic = slicer.modules.volumerendering.logic()
    displayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(node)
    displayNode.SetVisibility(True)
    displayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName('CT-Bones'))
    controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
    controller.resetFocalPoint() 

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onNodeAdded(self, caller, event, calldata):
    node = calldata
    if isinstance(node, slicer.vtkMRMLVolumeNode):
      # Call processing using a timer instead of calling it directly
      # to allow the volume loading to fully complete.
      #TODO: no event for volume loading done?
      qt.QTimer.singleShot(1000, lambda: self.processIncomingVolumeNode(node))

  def setupSliceViewers(self):
    for name in slicer.app.layoutManager().sliceViewNames():
        sliceWidget = slicer.app.layoutManager().sliceWidget(name)
        self.setupSliceViewer(sliceWidget)

  def setupSliceViewer(self, sliceWidget):
    controller = sliceWidget.sliceController()
    controller.setOrientationMarkerType(3)  #Axis marker
    controller.setRulerType(1)  #Thin ruler
    controller.setRulerColor(0) #White ruler
    controller.setStyleSheet("background-color: #464449")
    controller.sliceViewLabel = ''

  def showSlicePlaneIn3D(self, sliceColor):
    sliceWidget = slicer.app.layoutManager().sliceWidget(sliceColor)
    controller = sliceWidget.sliceController()
    sliceNode = controller.mrmlSliceNode()
    sliceNode.SetSliceVisible(True)
    controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
    controller.resetFocalPoint()
  
  def loadDICOM(self, dicomData):

    print("Loading DICOM from command line")
    #dicomDataDir = "c:/my/folder/with/dicom-files"  # input folder with DICOM files
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
    except Exception as e:
      import traceback
      traceback.print_exc()
      logging.error('Failed to import DICOM folder/file ' + dicomDataItem)
      return False
    return True
  

class HomeLogic(ScriptedLoadableModuleLogic):
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


class HomeTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  
  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Home1()

  def test_Home1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    
    logic = HomeLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class HomeFileWriter(object):
  def __init__(self, parent):
    pass

