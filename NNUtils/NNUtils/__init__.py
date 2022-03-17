import qt
import slicer

from .parameter_node import parameterProperty, nodeReferenceProperty  # noqa: F401


#
# MRML
#

def getModality(node):
  shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
  node_item = shNode.GetItemByDataNode(node)
  return shNode.GetItemAttribute(node_item, 'DICOM.Modality')


def getActiveVolume():
  lm = slicer.app.layoutManager()
  sliceLogic = lm.sliceWidget('Red').sliceLogic()
  compositeNode = sliceLogic.GetSliceCompositeNode()
  return compositeNode.GetBackgroundVolumeID()


def centerOnActiveVolume():
  nodeId = getActiveVolume()
  if nodeId is None:
    return
  node = slicer.mrmlScene.GetNodeByID(nodeId)
  # Get volume center
  bounds = [0, 0, 0, 0, 0, 0]
  node.GetRASBounds(bounds)
  nodeCenter = [(bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2, (bounds[4]+bounds[5])/2]
  center3DView(nodeCenter)


def center3DView(center):
  threedView = slicer.app.layoutManager().threeDWidget(0).threeDView()

  # Shift camera to look at the new focal point
  renderWindow = threedView.renderWindow()
  renderer = renderWindow.GetRenderers().GetFirstRenderer()
  camera = renderer.GetActiveCamera()
  oldFocalPoint = camera.GetFocalPoint()
  oldPosition = camera.GetPosition()
  cameraOffset = [center[0]-oldFocalPoint[0],
                  center[1]-oldFocalPoint[1],
                  center[2]-oldFocalPoint[2]]
  camera.SetFocalPoint(center)
  camera.SetPosition(oldPosition[0]+cameraOffset[0],
                     oldPosition[1]+cameraOffset[1],
                     oldPosition[2]+cameraOffset[2])


def updateSliceViews(pos, rot):
  sliceNode = slicer.app.layoutManager().sliceWidget('Yellow').mrmlSliceNode()
  sliceNode.SetSliceToRASByNTP( rot[0, 0], rot[1, 0], rot[2, 0],
                                rot[0, 1], rot[1, 1], rot[2, 1],
                                pos[0], pos[1], pos[2], 0)
  sliceNode.UpdateMatrices()

  sliceNode = slicer.app.layoutManager().sliceWidget('Green').mrmlSliceNode()
  sliceNode.SetSliceToRASByNTP( rot[0, 1], rot[1, 1], rot[2, 1],
                                rot[0, 2], rot[1, 2], rot[2, 2],
                                pos[0], pos[1], pos[2], 0)
  sliceNode.UpdateMatrices()

  sliceNode = slicer.app.layoutManager().sliceWidget('Red').mrmlSliceNode()
  sliceNode.SetSliceToRASByNTP( rot[0, 2], rot[1, 2], rot[2, 2],
                                rot[0, 0], rot[1, 0], rot[1, 0],
                                pos[0], pos[1], pos[2], 0)
  sliceNode.UpdateMatrices()


def resetSliceViews():
  nodeID = getActiveVolume()
  if nodeID is None:
    return
  volumeNode = slicer.mrmlScene.GetNodeByID(nodeID)

  for sliceID in ['Yellow', 'Green', 'Red']:
    sliceNode = slicer.app.layoutManager().sliceWidget(sliceID).mrmlSliceNode()
    sliceNode.RotateToVolumePlane(volumeNode)


def setSliceViewsPosition(pos):
  for sliceID in ['Yellow', 'Green', 'Red']:
    sliceNode = slicer.app.layoutManager().sliceWidget(sliceID).mrmlSliceNode()
    sliceNode.JumpSliceByOffsetting(pos[0], pos[1], pos[2])


#
# Widgets
#

def setMainPanelVisible(visible):
  modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'PanelDockWidget')
  modulePanel.visible = visible


def setSidePanelVisible(visible):
  sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
  sidePanel.visible = visible


def setupWorkflowToolBar(name, backButtonText=None, advanceButtonText=None):
  """Add toolbar with a back and advance buttons.

  If no text is specified, the button texts are respectively set to ``Back ({name})``
  and ``Advance ({name})``.

  Return a tuple of the form ``(toolBar, backButton, backButtonAction, advanceButton, advanceButtonAction)``
  """
  toolBar = qt.QToolBar(f"{name}BottomToolBar")
  toolBar.setObjectName(f"{name}BottomToolBar")
  toolBar.movable = False
  slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, toolBar)

  backButton = qt.QPushButton(f"Back ({name})" if backButtonText is None else backButtonText)
  backButton.name = f"{name}BackButton"
  backButtonAction = toolBar.addWidget(backButton)

  spacer = qt.QWidget()
  policy = spacer.sizePolicy
  policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
  spacer.setSizePolicy(policy)
  spacer.name = f"{name}BottomToolbarSpacer"
  toolBar.addWidget(spacer)

  advanceButton = qt.QPushButton(f"Advance ({name})" if advanceButtonText is None else advanceButtonText)
  advanceButton.name = f"{name}AdvanceButton"
  advanceButtonAction = toolBar.addWidget(advanceButton)
  toolBar.visible = False

  return (toolBar, backButton, backButtonAction, advanceButton, advanceButtonAction)


def setSliceWidgetOffsetSliderVisible(sliceWidget, visible):
  slicer.util.findChild(sliceWidget, "SliceOffsetSlider").visible = visible


def setSliceWidgetSlidersVisible(visible):
  for name in slicer.app.layoutManager().sliceViewNames():
    sliceWidget = slicer.app.layoutManager().sliceWidget(name)
    setSliceWidgetOffsetSliderVisible(sliceWidget, visible)


def setSliceViewBackgroundColor(color):
  for name in slicer.app.layoutManager().sliceViewNames():
    sliceWidget = slicer.app.layoutManager().sliceWidget(name)
    view = sliceWidget.sliceView()
    view.setBackgroundColor(qt.QColor(color))


def centerCam():
  controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
  controller.resetFocalPoint()


def applyStyle(widgets, styleSheetFilePath):
  with open(styleSheetFilePath, "r") as fh:
    styleSheet = fh.read()
    for widget in widgets:
      widget.styleSheet = styleSheet


#
# Layout
#

def initializeNavigationLayout():
  """This function was designed to be called once from Home module.
  """
  
  # Add the layout
  registerNavigationLayout()

  # Switch to navigation layout forces the creation of views
  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(getNavigationLayoutID())

  # Reset to four-up layout
  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)


def setupSliceViewers():
  for name in slicer.app.layoutManager().sliceViewNames():
    sliceWidget = slicer.app.layoutManager().sliceWidget(name)
    setupSliceViewer(sliceWidget)


def setupSliceViewer(sliceWidget):
  controller = sliceWidget.sliceController()
  controller.setStyleSheet("background-color: #000000")
  controller.sliceViewLabel = ""
  slicer.util.findChild(sliceWidget, "PinButton").visible = False
  slicer.util.findChild(sliceWidget, "ViewLabel").visible = False
  slicer.util.findChild(sliceWidget, "FitToWindowToolButton").visible = False
  slicer.util.findChild(sliceWidget, "SliceOffsetSlider").spinBoxVisible = False


def goToNavigationLayout(volumeNode=None, mainPanelVisible=False, sidePanelVisible=False):

  # Switching to FourUpLayout is a workaround to ensure
  # the layout the NavigationLayout is properly displayed
  # with all view properly sized.
  goToFourUpLayout()

  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(getNavigationLayoutID())
  setMainPanelVisible(mainPanelVisible)
  setSidePanelVisible(sidePanelVisible)
  setSliceViewBackgroundColor("#000000")
  slicer.util.setSliceViewerLayers(foreground=None, background=volumeNode, label=None, fit=True)
  setupSliceViewers()

  try:
    tipToPointer = slicer.util.getNode("TipToPointer")
    activateReslicing(tipToPointer)

  except:
    pass


def goToFourUpLayout(volumeNode=None, mainPanelVisible=True, sidePanelVisible=False):
  deactivateReslicing()
  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
  setSliceWidgetSlidersVisible(True)
  setMainPanelVisible(mainPanelVisible)
  setSidePanelVisible(sidePanelVisible)
  setSliceViewBackgroundColor("#000000")
  slicer.util.setSliceViewerLayers(foreground=None, background=volumeNode, label=None, fit=True)


def goToRegistrationCameraViewLayout():
  deactivateReslicing()
  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
  setSliceWidgetSlidersVisible(False)
  setMainPanelVisible(True)
  setSidePanelVisible(True)


def goToPictureLayout(image=None, sidePanelVisible=False):
  deactivateReslicing()
  if image is not None:
    slicer.util.setSliceViewerLayers(foreground=None, background=image, label=None, fit=True)
  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
  setSliceWidgetSlidersVisible(False)
  setMainPanelVisible(True)
  setSidePanelVisible(sidePanelVisible)
  setSliceViewBackgroundColor('#434343')


def activateReslicing(driverNode):
  driver = slicer.modules.volumereslicedriver.logic()

  def _activate(sliceViewNodeID, mode):
    sliceViewNode = slicer.util.getNode(sliceViewNodeID)
    driver.SetModeForSlice(mode, sliceViewNode)
    driver.SetDriverForSlice(driverNode.GetID(), sliceViewNode)

  _activate("vtkMRMLSliceNodeRed", driver.MODE_AXIAL)
  _activate("vtkMRMLSliceNodeYellow", driver.MODE_SAGITTAL)
  _activate("vtkMRMLSliceNodeGreen", driver.MODE_CORONAL)
  _activate("vtkMRMLSliceNodeBlue", driver.MODE_INPLANE)
  _activate("vtkMRMLSliceNodeOrange", driver.MODE_INPLANE90)

  blueSliceViewNode = slicer.util.getNode("vtkMRMLSliceNodeBlue")
  driver.SetRotationForSlice(-45.0, blueSliceViewNode)


def deactivateReslicing():
  driver = slicer.modules.volumereslicedriver.logic()

  def _deactivate(sliceViewNodeID):
    sliceViewNode = slicer.util.getNode(sliceViewNodeID)
    driver.SetModeForSlice(driver.MODE_NONE, sliceViewNode)
    driver.SetDriverForSlice("", sliceViewNode)

  _deactivate("vtkMRMLSliceNodeRed")
  _deactivate("vtkMRMLSliceNodeYellow")
  _deactivate("vtkMRMLSliceNodeGreen")
  _deactivate("vtkMRMLSliceNodeBlue")
  _deactivate("vtkMRMLSliceNodeOrange")

  blueSliceViewNode = slicer.util.getNode("vtkMRMLSliceNodeBlue")
  driver.SetRotationForSlice(0, blueSliceViewNode)


def getNavigationLayoutID():
  threeDWithReformatCustomLayoutId = 503
  return threeDWithReformatCustomLayoutId


def registerNavigationLayout():
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
  layoutNode = slicer.app.layoutManager().layoutLogic().GetLayoutNode()
  layoutNode.AddLayoutDescription(getNavigationLayoutID(), customLayout)
