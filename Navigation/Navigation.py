import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import NNUtils


class Navigation(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Nav"
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
    ScriptedLoadableModuleWidget.__init__(self, parent)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer)
    self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Navigation.ui'))
    self.layout.addWidget(self.uiWidget)
    self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    #Create logic class
    self.logic = NavigationLogic()

    #Dark palette does not propogate on its own?
    self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    #Bottom toolbar
    self.bottomToolBar = qt.QToolBar("NavigationBottomToolBar")
    self.bottomToolBar.setObjectName("NavigationBottomToolBar")
    self.bottomToolBar.movable = False
    slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, self.bottomToolBar)
    self.backButton = qt.QPushButton("Back (nav)")
    self.backButton.name = 'NavigationBackButton'
    self.bottomToolBar.addWidget(self.backButton)
    spacer = qt.QWidget()
    policy = spacer.sizePolicy
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    spacer.setSizePolicy(policy)
    spacer.name = "NavigationBottomToolbarSpacer"
    self.bottomToolBar.addWidget(spacer)
    self.advanceButton = qt.QPushButton("Advance (nav)")
    self.advanceButton.name = 'NavigationAdvanceButton'
    self.bottomToolBar.addWidget(self.advanceButton)
    self.bottomToolBar.visible = False

    self.navLayout = NavigationWidget.registerCustomLayouts(slicer.app.layoutManager().layoutLogic())

  def enter(self):

    #Hides other toolbars
    slicer.util.findChild(slicer.util.mainWindow(), 'BottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationBottomToolBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationTabBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'PlanningTabBar').visible = False
    slicer.util.findChild(slicer.util.mainWindow(), 'RegistrationTabBar').visible = False

    #Show current
    slicer.util.findChild(slicer.util.mainWindow(), 'SecondaryToolBar').visible = False
    self.bottomToolBar.visible = False

    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'ModulePanel')
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
    self.applyStyle([sidePanel, modulePanel], 'PanelLight.qss')

    try:
      masterNode = slicer.modules.PlanningWidget.logic.getMasterVolume()
    except:
      masterNode = None
      print('No master volume node loaded')

    slicer.modules.PlanningWidget.logic.seed_segmentation.SetDisplayVisibility(True)
    slicer.modules.PlanningWidget.logic.skin_segmentation.SetDisplayVisibility(True)
    slicer.modules.PlanningWidget.logic.trajectory_markup.SetDisplayVisibility(True)

    self.goToNavLayout(masterNode)

  def applyApplicationStyle(self):
    # Style
    self.applyStyle([slicer.app], 'Home.qss')

  def applyStyle(self, widgets, styleSheetName):
    stylesheetfile = self.resourcePath(styleSheetName)
    with open(stylesheetfile,"r") as fh:
      style = fh.read()
      for widget in widgets:
        widget.styleSheet = style

  def goToNavLayout(self, node=None):
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(self.navLayout)
    # self.toggleAllSliceSlidersVisiblility(False)
    NNUtils.setMainPanelVisible(False)
    NNUtils.setSidePanelVisible(False)
    NNUtils.setSliceViewBackgroundColor('#000000')
    slicer.util.setSliceViewerLayers(foreground=node, background=None, label=None, fit=True)
    self.setupSliceViewers()

    try:
      tipToPointer = slicer.util.getNode('TipToPointer')
      self.setupReslicing(tipToPointer)

    except:
      pass

  def setupReslicing(self, driverNode):

    driver = slicer.modules.volumereslicedriver.logic()
    redView = slicer.util.getNode('vtkMRMLSliceNodeRed')
    yellowView = slicer.util.getNode('vtkMRMLSliceNodeYellow')
    greenView = slicer.util.getNode('vtkMRMLSliceNodeGreen')
    blueView = slicer.util.getNode('vtkMRMLSliceNodeBlue')
    orangeView = slicer.util.getNode('vtkMRMLSliceNodeOrange')
    driver.SetModeForSlice(driver.MODE_AXIAL, redView)
    driver.SetDriverForSlice(driverNode.GetID(), redView)
    driver.SetModeForSlice(driver.MODE_SAGITTAL, yellowView)
    driver.SetDriverForSlice(driverNode.GetID(), yellowView)
    driver.SetModeForSlice(driver.MODE_CORONAL, greenView)
    driver.SetDriverForSlice(driverNode.GetID(), greenView)
    driver.SetModeForSlice(driver.MODE_INPLANE, blueView)
    driver.SetDriverForSlice(driverNode.GetID(), blueView)
    driver.SetRotationForSlice(-45.0, blueView)
    driver.SetModeForSlice(driver.MODE_INPLANE90, orangeView)
    driver.SetDriverForSlice(driverNode.GetID(), orangeView)

  def setupSliceViewers(self):
    for name in slicer.app.layoutManager().sliceViewNames():
        sliceWidget = slicer.app.layoutManager().sliceWidget(name)
        self.setupSliceViewer(sliceWidget)

  def setupSliceViewer(self, sliceWidget):
    controller = sliceWidget.sliceController()
    controller.setStyleSheet("background-color: #000000")
    controller.sliceViewLabel = ''
    slicer.util.findChild(sliceWidget, "PinButton").visible = False
    slicer.util.findChild(sliceWidget, "ViewLabel").visible = False
    slicer.util.findChild(sliceWidget, "FitToWindowToolButton").visible = False
    slicer.util.findChild(sliceWidget, "SliceOffsetSlider").spinBoxVisible = False

  def disconnectAll(self, widget):
    try: widget.clicked.disconnect()
    except Exception: pass

  @staticmethod
  def registerCustomLayouts(layoutLogic):
    customLayout = (
      "<layout type=\"vertical\">"
      " <item>"
      "  <layout type=\"horizontal\">"
      "   <item>"
      "    <view class=\"vtkMRMLSliceNode\" singletontag=\"Blue\">"
      "     <property name=\"orientation\" action=\"default\">Axial</property>"
      "     <property name=\"viewlabel\" action=\"default\">R</property>"
      "     <property name=\"viewcolor\" action=\"default\">#F34A33</property>"
      "    </view>"
      "   </item>"
      "   <item>"
      "    <view class=\"vtkMRMLSliceNode\" singletontag=\"Orange\">"
      "     <property name=\"orientation\" action=\"default\">Axial</property>"
      "     <property name=\"viewlabel\" action=\"default\">R</property>"
      "     <property name=\"viewcolor\" action=\"default\">#FFA500</property>"
      "    </view>"
      "   </item>"
      "   <item>"
      "    <view class=\"vtkMRMLViewNode\" singletontag=\"1\">"
      "     <property name=\"viewlabel\" action=\"default\">1</property>"
      "    </view>"
      "   </item>"
      "  </layout>"
      " </item>"
      " <item>"
      "  <layout type=\"horizontal\">"
      "   <item>"
      "    <view class=\"vtkMRMLSliceNode\" singletontag=\"Red\">"
      "     <property name=\"orientation\" action=\"default\">Axial</property>"
      "     <property name=\"viewlabel\" action=\"default\">R</property>"
      "     <property name=\"viewcolor\" action=\"default\">#0000FF</property>"
      "    </view>"
      "   </item>"
      "   <item>"
      "    <view class=\"vtkMRMLSliceNode\" singletontag=\"Green\">"
      "     <property name=\"orientation\" action=\"default\">Coronal</property>"
      "     <property name=\"viewlabel\" action=\"default\">G</property>"
      "     <property name=\"viewcolor\" action=\"default\">#6EB04B</property>"
      "    </view>"
      "   </item>"
      "   <item>"
      "    <view class=\"vtkMRMLSliceNode\" singletontag=\"Yellow\">"
      "     <property name=\"orientation\" action=\"default\">Sagittal</property>"
      "     <property name=\"viewlabel\" action=\"default\">Y</property>"
      "     <property name=\"viewcolor\" action=\"default\">#EDD54C</property>"
      "    </view>"
      "   </item>"
      "  </layout>"
      " </item>"
      "</layout>")
    threeDWithReformatCustomLayoutId = 503
    layoutLogic.GetLayoutNode().AddLayoutDescription(threeDWithReformatCustomLayoutId, customLayout)
    return threeDWithReformatCustomLayoutId


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
