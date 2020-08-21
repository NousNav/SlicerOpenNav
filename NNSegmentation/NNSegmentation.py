import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
import textwrap

#
# NNSegmentation
#
class NNSegmentation(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NousNav Segmentation" # TODO make this more human readable by adding spaces
    self.parent.categories = [""]
    self.parent.dependencies = ["SegmentEditor"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
This is the segmentation module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

  
#
# NNSegmentationWidget
#

class NNSegmentationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)


    #Create logic class
    self.logic = NNSegmentationLogic()   

    #Segmentation Editor + automated segmentation buttons
    hlayout = qt.QHBoxLayout()
    segWidget = qt.QWidget()
    segWidget.setLayout(hlayout)
    self.segmentationWidget = slicer.modules.segmenteditor.createNewWidgetRepresentation()
    segmentButton = qt.QPushButton("Create Skin Segmentation")
    def segmentActiveVolume():
        nodeID = self.logic.getActiveVolume()
        if(nodeID is not None):
          node = slicer.mrmlScene.GetNodeByID( nodeID )
          modality = self.logic.getModality(node)
          if modality == "CT":
            self.logic.createSkinSegmentationCT( node, self.segmentationWidget)
          else:
            self.logic.createSkinSegmentationMRI( node, self.segmentationWidget )

    segmentButton.clicked.connect( segmentActiveVolume ) 
    hlayout.addWidget(segmentButton)
    
    self.editButton = qt.QPushButton("Edit Segmentation")
    editDialog = qt.QDialog(segWidget)
    editDialogLayout = qt.QVBoxLayout()
    editDialogLayout.addWidget (self.segmentationWidget )
    editCloseButton = qt.QPushButton("Close")
    editCloseButton.setDefault(True)
    editCloseButton.clicked.connect(lambda : editDialogLayout.setVisible(False) )
    editDialogLayout.addWidget(editCloseButton)
    editDialogLayout.stretch(1)
    editDialog.setLayout( editDialogLayout )
    def editSegmentation():
        editDialog.show()
        editDialog.activateWindow()

    editDialog.setWindowFlags(qt.Qt.WindowStaysOnTopHint)
    self.editButton.clicked.connect( editSegmentation )
    editDialogLayout.addWidget( self.editButton )

    hlayout.addWidget(self.editButton)
    
    self.layout.addWidget( segWidget )
      
  def onClose(self, unusedOne, unusedTwo):
    pass

  def cleanup(self):
    pass


  

#
# NNSegmentationLogic
#

class NNSegmentationLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def getModality(self, node):
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    node_item = shNode.GetItemByDataNode(node)
    return shNode.GetItemAttribute(node_item, 'DICOM.Modality')
  
  #workaround to get active volume
  def getActiveVolume(self):
    lm = slicer.app.layoutManager()
    sliceLogic = lm.sliceWidget('Red').sliceLogic()
    compositeNode = sliceLogic.GetSliceCompositeNode()
    return compositeNode.GetBackgroundVolumeID()

  def createSkinSegmentationMRI(self, masterVolumeNode, parentWidget):
    if not masterVolumeNode.IsTypeOf("vtkMRMLScalarVolumeNode"):
        pass
    #TODO implment segmentation steps
    pass

  def createSkinSegmentationCT(self, masterVolumeNode, parentWidget):
    if not masterVolumeNode.IsTypeOf("vtkMRMLScalarVolumeNode"):
        pass

    progress = slicer.util.createProgressDialog(parent=parentWidget, value=0, 
            maximum=10, labelText="Creating Automatic Skin Segmentation")

    # Create segmentation
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    segmentationNode.CreateDefaultDisplayNodes() # only needed for display
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(masterVolumeNode)
    addedSegmentID = segmentationNode.GetSegmentation().AddEmptySegment("skin")
    segmentationNode.GetDisplayNode().SetOpacity(0.4)


    # Create segment editor to get access to effects
    segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
    segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
    segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
    segmentEditorWidget.setSegmentationNode(segmentationNode)
    segmentEditorWidget.setMasterVolumeNode(masterVolumeNode)
    
    progress.setValue(1)
    slicer.app.processEvents()

    # Thresholding
    segmentEditorWidget.setActiveEffectByName("Threshold")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("MinimumThreshold","-150")
    effect.setParameter("MaximumThreshold","10000")
    effect.self().onApply()

    progress.setValue(2)
    slicer.app.processEvents()



    # Find largest component
    slicer.app.processEvents()
    segmentEditorWidget.setActiveEffectByName("Islands")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameterDefault("Operation", "KEEP_LARGEST_ISLAND")
    effect.self().onApply()
    
    progress.setValue(4)
    slicer.app.processEvents()

    # Invert
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "INVERT")
    effect.self().onApply()
    
    progress.setValue(5)
    slicer.app.processEvents()


    #Find largest component
    slicer.app.processEvents()
    segmentEditorWidget.setActiveEffectByName("Islands")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameterDefault("Operation", "KEEP_LARGEST_ISLAND")
    effect.self().onApply()
    
    progress.setValue(7)
    slicer.app.processEvents()

    # Invert
    slicer.app.processEvents()
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "INVERT")
    effect.self().onApply()
    
    progress.setValue(8)
    slicer.app.processEvents()


    slicer.app.processEvents()
    segmentEditorWidget.setActiveEffectByName("Hollow")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("ShellMode","OUTSIDE_SURFACE")
    effect.self().onApply()
    
    progress.setValue(9)
    slicer.app.processEvents()
    
    # Clean up
    segmentEditorWidget = None
    slicer.mrmlScene.RemoveNode(segmentEditorNode)

    # Make segmentation results visible in 3D
    segmentationNode.CreateClosedSurfaceRepresentation()
    
    progress.setValue(10)
    slicer.app.processEvents()

    # Make sure surface mesh cells are consistently oriented
    #surfaceMesh = segmentationNode.GetClosedSurfaceRepresentation(addedSegmentID)
    #normals = vtk.vtkPolyDataNormals()
    #normals.AutoOrientNormalsOn()
    #normals.ConsistencyOn()
    #normals.SetInputData(surfaceMesh)
    #normals.Update()
    #surfaceMesh = normals.GetOutput()


  
  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    pass


class NNSegmentationTest(ScriptedLoadableModuleTest):
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
    self.test_NNSegmentation1()

  def test_NNSegmentation1(self):
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
    
    logic = NNSegmentationLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class NNSegmentationFileWriter(object):
  def __init__(self, parent):
    pass
