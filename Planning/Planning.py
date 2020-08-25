import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap

#
# Home
#

class Planning(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Home" 
    self.parent.categories = [""]
    self.parent.dependencies = ["Data", "SubjectHierarchy", "DICOM"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"] 
    self.parent.helpText = """
This is the Home module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

  
class PlanningWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)


  def nextPlanningStep(self):
    self.ui.PlanningWidget.setCurrentIndex( self.ui.PlanningWidget.currentIndex + 1)

  def previousPlanningStep(self):
    self.ui.PlanningWidget.setCurrentIndex( self.ui.PlanningWidget.currentIndex - 1)

  def createNextPlanningButton(self):
    btn = qt.QPushButton("Next Step")
    btn.clicked.connect(self.nextPlanningStep)
    return btn

  def createPreviousPlanningButton(self):
    btn = qt.QPushButton("Previous Step")
    btn.clicked.connect(self.previousPlanningStep)
    return btn

  def createPlanningStepWidget(self, prevOn, nextOn):
     w = qt.QWidget()
     l = qt.QGridLayout()
     w.setLayout(l)
     if prevOn:
       l.addWidget(self.createPreviousPlanningButton(), 0, 0 )
     if nextOn:
       l.addWidget(self.createNextPlanningButton(), 0, 1 )
     return w

   
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Planning.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    
    #Create logic class
    self.logic = PlanningLogic()   

    #Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())
    
    ###Stacked widgtes navigation changes
    self.CurrentPlanningIndex = -1
    self.ui.PlanningWidget.currentChanged.connect( self.onPlanningChanged )

    ####Planning

    #Step 1: Data Loading
    self.ui.PlanningStep1.layout().addWidget( qt.QLabel("Step 1: Load Data") )
    self.dicomButton = qt.QPushButton('Show DICOM Browser')
    self.ui.PlanningStep1.layout().addWidget(self.dicomButton)
    self.ui.PlanningStep1.layout().addStretch(1)
    self.ui.PlanningStep1.layout().addWidget( self.createPlanningStepWidget(False, True) )


    #Volume Rendering
    self.ui.PlanningStep2.layout().addWidget( qt.QLabel("Step 2: Adjust Volume Rendering") )
    self.renderFrame = qt.QWidget()
    renderLayout = qt.QVBoxLayout()
    self.renderFrame.setLayout( renderLayout )

    self.volumerenderWidget = slicer.modules.volumerendering.createNewWidgetRepresentation()
    #self.presets = slicer.qSlicerVolumeRenderingPresetComboBox(self.renderFrame)
    self.presets = slicer.util.findChild( self.volumerenderWidget, "PresetComboBox" )
    self.presets.setParent( None )
    renderLayout.addWidget(self.presets)
    self.ui.PlanningStep2.layout().addWidget(self.renderFrame)

    self.renderFrameAdvanced = ctk.ctkCollapsibleGroupBox(self.ui.PlanningStep2)
    self.renderFrameAdvanced.name = "AdvancedVolume"
    self.renderFrameAdvanced.title = "Advanced"
    self.renderFrameAdvanced.setChecked( False )
    self.renderFrameAdvanced.setLayout(qt.QVBoxLayout())
    self.renderFrameAdvanced.layout().addWidget(self.volumerenderWidget)
    self.ui.PlanningStep2.layout().addWidget(self.renderFrameAdvanced)
    
    self.ui.PlanningStep2.layout().addStretch(1)
    self.ui.PlanningStep2.layout().addWidget( self.createPlanningStepWidget(True, True) )

    
    #Segmentation
    self.ui.PlanningStep3.layout().addWidget( qt.QLabel("Step 3: Create Segmentation") )
    self.segmentationWidget = slicer.modules.nnsegmentation.createNewWidgetRepresentation()
    self.ui.PlanningStep3.layout().addWidget(self.segmentationWidget)
    self.ui.PlanningStep3.layout().addStretch(1)
    self.ui.PlanningStep3.layout().addWidget( self.createPlanningStepWidget(True, False) )
    
    slicer.app.connect("startupCompleted()", self.setupDICOMBrowser)


  def setupDICOMBrowser(self):
    #Make sure that the DICOM widget exists
    slicer.modules.dicom.widgetRepresentation()
    self.dicomButton.setCheckable(True)
    self.dicomButton.toggled.connect(self.toggleDICOMBrowser)
    
    #For some reason, the browser is instantiated as not hidden. Close
    #so that the 'isHidden' check works as required
    slicer.modules.DICOMWidget.browserWidget.close()
  
  def toggleDICOMBrowser(self, checked):
    if checked:  
      slicer.modules.DICOMWidget.onOpenBrowserWidget()
      self.dicomButton = qt.QPushButton('Hide DICOM Browser') 
    else:
      slicer.modules.DICOMWidget.browserWidget.close()
      self.dicomButton = qt.QPushButton('Show DICOM Browser') 

  #TODO
  def onPlanningChanged(self, tabIndex):
    if tabIndex == self.CurrentPlanningIndex:
      return
    #Enter New Tab
    #Update Current Tab
    self.CurrentPlanningIndex = tabIndex



class PlanningLogic(ScriptedLoadableModuleLogic):
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


class PlanningTest(ScriptedLoadableModuleTest):
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
    self.test_Planning1()

  def test_Planning1(self):
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
    
    logic = PlanningLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class PlanningFileWriter(object):
  def __init__(self, parent):
    pass

