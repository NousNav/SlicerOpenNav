import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import textwrap


class Registration(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Reg"
    self.parent.categories = [""]
    self.parent.dependencies = ["Tracking", "NNICPRegistration"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the Registration main module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class RegistrationWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)


  def nextStep(self):
    self.ui.RegistrationWidget.setCurrentIndex( self.ui.RegistrationWidget.currentIndex + 1)

  def previousStep(self):
    self.ui.RegistrationWidget.setCurrentIndex( self.ui.RegistrationWidget.currentIndex - 1)

  def createNextButton(self):
    btn = qt.QPushButton("Next Step")
    btn.clicked.connect(self.nextStep)
    return btn

  def createPreviousButton(self):
    btn = qt.QPushButton("Previous Step")
    btn.clicked.connect(self.previousStep)
    return btn

  def createStepWidget(self, prevOn, nextOn):
     w = qt.QWidget()
     l = qt.QGridLayout()
     w.setLayout(l)
     if prevOn:
       l.addWidget(self.createPreviousButton(), 0, 0 )
     if nextOn:
       l.addWidget(self.createNextButton(), 0, 1 )
     return w


  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Registration.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    #Create logic class
    self.logic = RegistrationLogic()

    #Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())


    ###Stacked widgets navigation changes
    self.CurrentRegistrationIndex = -1
    self.ui.RegistrationWidget.currentChanged.connect( self.onRegistrationChanged )


    ### Registration
    self.trackerWidget = slicer.modules.tracking.createNewWidgetRepresentation().self()

    #Step 1: Connect Tracker:
    self.ui.RegistrationStep1.layout().addWidget( qt.QLabel("Step 1: Connect Tracker") )
    self.ui.RegistrationStep1.layout().addWidget(self.trackerWidget.connectButton)
    self.ui.RegistrationStep1.layout().addWidget(self.trackerWidget.configurationFrame)
    self.ui.RegistrationStep1.layout().addStretch(1)
    self.ui.RegistrationStep1.layout().addWidget( self.createStepWidget(False, True) )

    #Step 2: Calibrate Tools
    self.ui.RegistrationStep2.layout().addWidget( qt.QLabel("Step 2: Calibrate Non-Sterile Tool") )
    self.ui.RegistrationStep2.layout().addWidget(self.trackerWidget.toolsWidget)
    self.ui.RegistrationStep2.layout().addStretch(1)
    self.ui.RegistrationStep2.layout().addWidget( self.createStepWidget(True, True) )

    #Step 3: Registration
    self.ui.RegistrationStep3.layout().addWidget( qt.QLabel("Step 3: Register Patient to Image") )
    self.ui.RegistrationStep3.layout().addWidget(self.trackerWidget.registerWidget)
    self.ui.RegistrationStep3.layout().addStretch(1)
    self.ui.RegistrationStep3.layout().addWidget( self.createStepWidget(True, True) )

    #Step 4: ICP Registration
    self.ui.RegistrationStep4.layout().addWidget( qt.QLabel("Step 4: Register Patient to Image") )
    self.icpregistrationWidget = slicer.modules.nnicpregistration.createNewWidgetRepresentation()
    self.ui.RegistrationStep4.layout().addWidget(self.icpregistrationWidget)
    self.ui.RegistrationStep4.layout().addStretch(1)
    self.ui.RegistrationStep4.layout().addWidget( self.createStepWidget(True, False) )

  #TODO add enter to neceassary widgets
  def onRegistrationChanged(self, tabIndex):
    if tabIndex == self.CurrentRegistrationIndex:
      return
    #Enter New Tab
    if tabIndex == self.ui.RegistrationWidget.indexOf( self.ui.RegistrationStep3 ):
      self.trackerWidget.registerWidget.enter()
    #Update Current Tab
    self.CurrentRegistrationIndex = tabIndex


class RegistrationLogic(ScriptedLoadableModuleLogic):
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


class RegistrationTest(ScriptedLoadableModuleTest):
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
    self.test_Registration1()

  def test_Registration1(self):
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

    logic = RegistrationLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class RegistrationFileWriter(object):
  def __init__(self, parent):
    pass

