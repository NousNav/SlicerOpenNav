import slicer
import vtk

from slicer.ScriptedLoadableModule import (
  ScriptedLoadableModule,
  ScriptedLoadableModuleLogic,
  ScriptedLoadableModuleWidget,
)

import NNUtils
import Home


class Navigation(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "NousNav Navigation"
    self.parent.categories = [""]
    self.parent.dependencies = ["Tools"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """
This is the Navigation main module for the NousNav application
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.


class NavigationWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    super().__init__(parent)

    self.workflow = Home.Workflow(
      'navigation',
      widget=self.parent,
      setup=self.enter,
      teardown=self.exit,
      validate=self.validate
    )

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Create logic class
    self.logic = NavigationLogic()

    # Bottom toolbar
    (
      self.bottomToolBar,
      self.backButton,
      self.backButtonAction,
      self.advanceButton,
      self.advanceButtonAction,
    ) = NNUtils.setupWorkflowToolBar("Navigation")

  def validate(self):
    
    registrationNode = slicer.modules.RegistrationWidget.logic.registration_transform
    if not registrationNode:
      return 'Registration not complete'
   
    identity = vtk.vtkTransform()
    if slicer.vtkAddonMathUtilities.MatrixAreEqual(registrationNode.GetMatrixTransformToParent(), identity.GetMatrix()):
      return 'Registration not complete'

    if not slicer.modules.RegistrationWidget.logic.registration_passed:
      return 'Please redo registration to improve results'
  
  def enter(self):
    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = False

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    centralPanel = slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidget')
    for widget in [modulePanel, sidePanel, centralPanel]:
      NNUtils.setCssClass(widget, "widget--color-light")
      NNUtils.polish(widget)

    planningLogic = slicer.modules.PlanningWidget.logic

    try:
      masterNode = planningLogic.master_volume
    except:
      masterNode = None
      print('No master volume node loaded')

    planningLogic.setPlanningNodesVisibility(skinSegmentation=True, seedSegmentation=False, targetSegmentation=True, trajectory=True, landmarks=False)
    try:
      planningLogic.skin_segmentation.GetDisplayNode().SetOpacity3D(0.5)
      planningLogic.target_segmentation.GetDisplayNode().SetOpacity3D(0.3)
    except:
      pass

    if slicer.modules.RegistrationWidget.logic.needle_model:
      slicer.modules.RegistrationWidget.logic.needle_model.GetDisplayNode().SetVisibility(True)
      slicer.modules.RegistrationWidget.logic.needle_model.GetDisplayNode().SetVisibility2D(True)

    NNUtils.goToNavigationLayout(volumeNode=masterNode)

    tools = slicer.modules.RegistrationWidget.tools
    tools.setToolsStatusCheckEnabled(True)
    slicer.modules.RegistrationWidget.startOptiTrack()

  def exit(self):
    # Hide current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = False

    planningLogic = slicer.modules.PlanningWidget.logic

    planningLogic.setPlanningNodesVisibility(skinSegmentation=False, seedSegmentation=False, targetSegmentation=False, trajectory=False)
    planningLogic.resetDefaultNodeAppearance()
    
    if slicer.modules.RegistrationWidget.logic.needle_model:
      slicer.modules.RegistrationWidget.logic.needle_model.GetDisplayNode().SetVisibility(False)
      slicer.modules.RegistrationWidget.logic.needle_model.GetDisplayNode().SetVisibility2D(False)

    tools = slicer.modules.RegistrationWidget.tools
    tools.setToolsStatusCheckEnabled(False)

  def disconnectAll(self, widget):
    try: widget.clicked.disconnect()
    except Exception: pass


class NavigationLogic(ScriptedLoadableModuleLogic):
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
