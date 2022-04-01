import slicer

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
    self.parent.dependencies = ["CameraNavigation", "Tools"]
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

  def enter(self):
    # Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = False

    # Styling
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    for widget in [modulePanel, sidePanel]:
      NNUtils.setCssClass(widget, "widget--color-light")
      NNUtils.polish(widget)

    planningLogic = slicer.modules.PlanningWidget.logic

    try:
      masterNode = planningLogic.master_volume
    except:
      masterNode = None
      print('No master volume node loaded')

    if planningLogic.seed_segmentation:
      planningLogic.seed_segmentation.SetDisplayVisibility(True)

    if planningLogic.skin_segmentation:
      planningLogic.skin_segmentation.SetDisplayVisibility(True)

    if planningLogic.trajectory_markup:
      planningLogic.trajectory_markup.SetDisplayVisibility(True)

    try:
      needleModel = slicer.util.getNode('PointerModel')
      needleModel.GetDisplayNode().SetVisibility(True)
      needleModel.GetDisplayNode().SetVisibility2D(True)
    except:
      pass

    NNUtils.goToNavigationLayout(volumeNode=masterNode)

    tools = slicer.modules.RegistrationWidget.tools
    tools.setToolsStatusCheckEnabled(True)

  def exit(self):
    # Hide current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = False

    planningLogic = slicer.modules.PlanningWidget.logic

    planningLogic.setPlanningNodesVisibility(skinSegmentation=False, seedSegmentation=False, trajectory=False)
    try:
      needleModel = slicer.util.getNode('PointerModel')
      needleModel.GetDisplayNode().SetVisibility(False)
      needleModel.GetDisplayNode().SetVisibility2D(False)
    except:
      pass

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
