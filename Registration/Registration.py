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
    self.parent.title = "NousNav Registration"
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


    #Bottom toolbar
    self.bottomToolBar = qt.QToolBar("RegistrationBottomToolBar")
    self.bottomToolBar.setObjectName("RegistrationBottomToolBar")
    self.bottomToolBar.movable = False
    slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, self.bottomToolBar)
    self.backButton = qt.QPushButton("Back (reg)")
    self.backButton.name = 'RegistrationBackButton'
    self.bottomToolBar.addWidget(self.backButton)
    spacer = qt.QWidget()
    policy = spacer.sizePolicy
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    spacer.setSizePolicy(policy)
    self.bottomToolBar.addWidget(spacer)
    self.advanceButton = qt.QPushButton("Advance (reg)")
    self.advanceButton.name = 'RegistrationAdvanceButton'
    self.bottomToolBar.addWidget(self.advanceButton)
    self.bottomToolBar.visible = False

    # Registration Tab Bar
    self.registrationTabBar = qt.QTabBar()
    self.registrationTabBar.setObjectName("RegistrationTabBar")
    self.prepRegistrationTabIndex = self.registrationTabBar.addTab("Patient prep")
    self.trackingTabIndex = self.registrationTabBar.addTab("Tracking devices")
    self.cameraTabIndex = self.registrationTabBar.addTab("Camera")
    self.calibrateRegistrationTabIndex = self.registrationTabBar.addTab("Calibrate")
    self.registerPatientTabIndex = self.registrationTabBar.addTab("Register patient")
    self.registrationTabBar.visible = False
    secondaryTabWidget = slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryCenteredWidget')
    secondaryTabWidgetUI = slicer.util.childWidgetVariables(secondaryTabWidget)
    secondaryTabWidgetUI.CenterArea.layout().addWidget(self.registrationTabBar)

  def enter(self):

    #Hides other toolbars
    slicer.util.findChild(slicer.util.mainWindow(), 'BottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'NavigationBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'NavigationTabBar').visible = False

    #Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = True
    self.bottomToolBar.visible = True
    self.registrationTabBar.visible = True

    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    self.applyStyle([sidePanel, modulePanel], 'PanelLight.qss')

  def applyApplicationStyle(self):
    # Style
    self.applyStyle([slicer.app], 'Home.qss')
    

  def applyStyle(self, widgets, styleSheetName):
    stylesheetfile = self.resourcePath(styleSheetName)
    with open(stylesheetfile,"r") as fh:
      style = fh.read()
      for widget in widgets:
        widget.styleSheet = style


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

