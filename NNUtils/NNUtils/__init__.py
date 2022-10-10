import os, functools
import qt
import slicer
import vtk
import numpy as np

from .parameter_node import (  # noqa: F401
  parameterProperty,
  nodeReferenceProperty,
)


def isLinearTransformNodeIdentity(transformNode):
  identity = vtk.vtkTransform()
  matrix = vtk.vtkMatrix4x4()
  transformNode.GetMatrixTransformToParent(matrix)
  return slicer.vtkAddonMathUtilities.MatrixAreEqual(matrix, identity.GetMatrix())


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


#
# Widgets
#

def setMainPanelVisible(visible):
  modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'PanelDockWidget')
  modulePanel.visible = visible


def setSidePanelVisible(visible):
  sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
  sidePanel.visible = visible


def addCssClass(widget, class_):
  # Retrieve list of classes
  classes = set(widget.property("cssClass") if widget.property("cssClass") else [])
  # Append given class or list of classes depending on the type of the `class_` parameter
  classes |= set([class_] if isinstance(class_, str) else class_)
  widget.setProperty("cssClass", list(classes))


def removeCssClass(widget, class_):
  # Retrieve list of classes
  classes = set(widget.property("cssClass") if widget.property("cssClass") else [])
  # Remove class or list of classes
  classes -= set([class_] if isinstance(class_, str) else class_)
  widget.setProperty("cssClass", list(classes))


def setCssClass(widget, class_):
  # Remove duplicates if any
  classes = set([class_] if isinstance(class_, str) else class_)
  widget.setProperty("cssClass", list(classes))


def setupWorkflowToolBar(name, backButtonText=None, advanceButtonText=None):
  """Add toolbar with a back and advance buttons.

  If no text is specified, the button texts are respectively set to ``Back ({name})``
  and ``Advance ({name})``.

  Return a tuple of the form ``(toolBar, backButton, backButtonAction, advanceButton, advanceButtonAction)``
  """
  toolBar = qt.QToolBar(f"{name}BottomToolBar")
  toolBar.setObjectName(f"{name}BottomToolBar")
  addCssClass(toolBar, "bottom-toolbar")
  toolBar.movable = False
  slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, toolBar)

  backButton = qt.QPushButton(f"Back ({name})" if backButtonText is None else backButtonText)
  backButton.name = f"{name}BackButton"
  addCssClass(backButton, ["bottom-toolbar__button", "bottom-toolbar__back-button"])
  backButtonAction = toolBar.addWidget(backButton)

  spacer = qt.QWidget()
  policy = spacer.sizePolicy
  policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
  spacer.setSizePolicy(policy)
  spacer.name = f"{name}BottomToolbarSpacer"
  addCssClass(spacer, "bottom-toolbar__spacer")
  toolBar.addWidget(spacer)

  advanceButton = qt.QPushButton(f"Advance ({name})" if advanceButtonText is None else advanceButtonText)
  advanceButton.name = f"{name}AdvanceButton"
  addCssClass(advanceButton, ["bottom-toolbar__button", "bottom-toolbar__advance-button"])
  advanceButtonAction = toolBar.addWidget(advanceButton)
  toolBar.visible = False

  # Default
  addCssClass(toolBar, "bottom-toolbar--color-light")

  return (toolBar, backButton, backButtonAction, advanceButton, advanceButtonAction)


def backButton(text="", visible=True, enabled=True):
  """Decorator for enabling/disabling the `back` button and updating its text
  and visibility.

  By default, `visible` and `enabled` properties are set to `True`.
  """
  def inner(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwds):
      self.backButton.text = text
      self.backButtonAction.enabled = enabled
      self.backButtonAction.visible = visible
      return func(self, *args, **kwds)
    return wrapper
  return inner


def advanceButton(text="", visible=True, enabled=True):
  """Decorator for enabling/disabling the `advance` button and updating its text
  and visibility.

  By default, `visible` and `enabled` properties are set to `True`.
  """
  def inner(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwds):
      self.advanceButton.text = text
      self.advanceButtonAction.enabled = enabled
      self.advanceButtonAction.visible = visible
      return func(self, *args, **kwds)
    return wrapper
  return inner


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


def polish(widget):
  """Re-polish widget and all its children.

  This function may be called after setting dynamic properties
  to ensure the application stylesheet is applied.
  """
  for child in slicer.util.findChildren(widget):
    try:
      widget.style().polish(child)
    except ValueError:
      pass


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


def showSliceOrientationLabels(visible):
  for name in slicer.app.layoutManager().sliceViewNames():
    sliceWidget = slicer.app.layoutManager().sliceWidget(name)
    if sliceWidget.sliceOrientation == 'Axial' or sliceWidget.sliceOrientation == 'Coronal':
      view = sliceWidget.sliceView()
      if visible:
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerRight, "L")
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerLeft, "R")
      else:
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerRight, "")
        view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerLeft, "")
      view.cornerAnnotation().SetMaximumFontSize(60)
      view.cornerAnnotation().SetMinimumFontSize(60)
      view.cornerAnnotation().SetNonlinearFontScaleFactor(1)
    else:
      view = sliceWidget.sliceView()
      view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerRight, "")
      view.cornerAnnotation().SetText(vtk.vtkCornerAnnotation.LowerLeft, "")


def showSliceOrientationAxes(visible):
  for name in slicer.app.layoutManager().sliceViewNames():
    sliceWidget = slicer.app.layoutManager().sliceWidget(name)
    controller = sliceWidget.sliceController()
    if visible:
      controller.setOrientationMarkerType(slicer.vtkMRMLAbstractViewNode.OrientationMarkerTypeAxes)
    else:
      controller.setOrientationMarkerType(slicer.vtkMRMLAbstractViewNode.OrientationMarkerTypeNone)


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
    tipToPointer = slicer.util.getNode("POINTER_CALIBRATION")
    activateReslicing(tipToPointer)

  except:
    print('Cannot find pointer node')

  showSliceOrientationAxes(True)
  showSliceOrientationLabels(False)


def showCentralWidget(name):
  slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidgetImageFrame').visible = False
  slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidgetLayoutFrame').visible = False
  slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidgetVideoFrame').visible = False

  if name == 'layout':
    slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidgetLayoutFrame').visible = True

  if name == 'image':
    slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidgetImageFrame').visible = True

  if name == 'video':
    slicer.util.findChild(slicer.util.mainWindow(), 'CentralWidgetVideoFrame').visible = True


def goToFourUpLayout(volumeNode=None, mainPanelVisible=True, sidePanelVisible=False):
  deactivateReslicing()
  showCentralWidget('layout')
  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
  setSliceWidgetSlidersVisible(True)
  setMainPanelVisible(mainPanelVisible)
  setSidePanelVisible(sidePanelVisible)
  setSliceViewBackgroundColor("#000000")
  slicer.util.setSliceViewerLayers(foreground=None, background=volumeNode, label=None, fit=True)

  # reset slice orientations to default
  slicer.app.layoutManager().sliceWidget("Red").sliceOrientation = 'Axial'
  slicer.app.layoutManager().sliceWidget("Green").sliceOrientation = 'Coronal'
  slicer.app.layoutManager().sliceWidget("Yellow").sliceOrientation = 'Sagittal'

  setupSliceViewers()
  showSliceOrientationLabels(True)
  showSliceOrientationAxes(False)


def goToRegistrationCameraViewLayout():
  deactivateReslicing()
  showCentralWidget('layout')
  layoutManager = slicer.app.layoutManager()
  layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
  setSliceWidgetSlidersVisible(False)
  setMainPanelVisible(True)
  setSidePanelVisible(True)


def goToPictureLayout(image=None, sidePanelVisible=False):
  deactivateReslicing()
  showCentralWidget('image')
  centralImageLabel = slicer.util.findChild(slicer.util.mainWindow(), 'CentralImageLabel')
  centralImageLabel.pixmap = image
  setMainPanelVisible(True)
  setSidePanelVisible(sidePanelVisible)
  showSliceOrientationLabels(False)
  showSliceOrientationAxes(False)


# Usage example:
# NNUtils.goToVideoLayout(self.resourcePath('Videos/example.html'))
def goToVideoLayout(videoURL, sidePanelVisible=False):
  deactivateReslicing()
  showCentralWidget('video')
  centralVideoWidget = slicer.util.findChild(slicer.util.mainWindow(), 'CentralVideoWidget')
  centralVideoWidget.setUrl('file:///' + videoURL.replace('\\', '/'))
  setMainPanelVisible(True)
  setSidePanelVisible(sidePanelVisible)


def activateReslicing(driverNode):
  driver = slicer.modules.volumereslicedriver.logic()

  def _activate(sliceViewNodeID, mode):
    sliceViewNode = slicer.util.getNode(sliceViewNodeID)
    driver.SetModeForSlice(mode, sliceViewNode)
    driver.SetDriverForSlice(driverNode.GetID(), sliceViewNode)

  _activate("vtkMRMLSliceNodeBlue", driver.MODE_INPLANE)
  _activate("vtkMRMLSliceNodeOrange", driver.MODE_INPLANE90)

  blueSliceViewNode = slicer.util.getNode("vtkMRMLSliceNodeBlue")
  driver.SetRotationForSlice(-45.0, blueSliceViewNode)
  observeTransformForSliceJump(driverNode)


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

  driverNode = slicer.mrmlScene.GetFirstNodeByName("POINTER_CALIBRATION")
  if driverNode:
    removeObserveTransformForSliceJump(driverNode)


def observeTransformForSliceJump(driverNode):
  observerTag = driverNode.AddObserver(slicer.vtkMRMLLinearTransformNode.TransformModifiedEvent, jumpAxisAlignedSlices)
  driverNode.SetAttribute('JumpObserverTag', str(observerTag))


def removeObserveTransformForSliceJump(driverNode):
  observerTag = driverNode.GetAttribute('JumpObserverTag')
  if observerTag:
    driverNode.RemoveObserver(int(observerTag))


def jumpAxisAlignedSlices(driverNode,eventid):

  def _getTranslation(driverNode):
    mat = vtk.vtkMatrix4x4()
    driverNode.GetMatrixTransformToWorld(mat)
    npmat = np.zeros(3)
    for i in range(3):
      npmat[i] = mat.GetElement(i,3)
    return npmat
  
  def _jump(sliceViewNodeID, driverNode):
    sliceViewNode = slicer.util.getNode(sliceViewNodeID)
    pos = _getTranslation(driverNode)
    sliceViewNode.JumpSliceByOffsetting(pos[0], pos[1], pos[2])

  _jump("vtkMRMLSliceNodeRed", driverNode)
  _jump("vtkMRMLSliceNodeYellow", driverNode)
  _jump("vtkMRMLSliceNodeGreen", driverNode)


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


def _autoSaveDirectory():
  userPath = os.path.expanduser('~')
  return os.path.join(userPath, 'NousNav', 'AutoSave')


def _autoSaveDataDirectory():
  return os.path.join(_autoSaveDirectory(), 'Data')


def _autoSaveFilePath():
  return os.path.join(_autoSaveDirectory(), 'AutoSave.mrml')


def _deleteAutoSave():
  if os.path.exists(_autoSaveDirectory()):
    import shutil
    shutil.rmtree(_autoSaveDirectory())


def _ensureAutoSaveDirectoriesExist():
  # Create all directories in tree recursively
  os.makedirs(_autoSaveDataDirectory())


def _listNodesToSave(incremental=False):
  storableNodes = slicer.util.getNodesByClass('vtkMRMLStorableNode')
  saveableNodes = [node for node in storableNodes if (node.GetSaveWithScene() and not node.GetHideFromEditors())]
  saveableToOwnFileNodes = [node for node in saveableNodes if slicer.app.coreIOManager().fileWriterFileType(node) != 'NoFile']
  modifiedNodes = [node for node in saveableToOwnFileNodes if node.GetModifiedSinceRead()]
  
  if incremental:
    nodes = modifiedNodes
  else:
    nodes = saveableToOwnFileNodes

  return nodes


def _fileIsInDataDirectory(filename):
  try:
    commonfilepathpath = os.path.commonpath([_autoSaveDataDirectory(),os.path.abspath(filename)])
  except ValueError:  # Value errors can occur in the worst cases of non-matching paths
    return False

  return os.path.normpath(_autoSaveDataDirectory()) == os.path.normpath(commonfilepathpath)


def _slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    import unicodedata
    import re
    
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value)
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def _createAutoSaveFilePath(node):
  snode = node.GetStorageNode()
  possiblePath = os.path.join(_autoSaveDataDirectory(), _slugify(node.GetName()) + '.' + snode.GetDefaultWriteFileExtension())
  return slicer.mrmlScene.CreateUniqueFileName(possiblePath, '.'+snode.GetDefaultWriteFileExtension())


def _ensureStorageNodeAndFileNameExist(node):
  snode = node.GetStorageNode()
  if not snode:
    node.AddDefaultStorageNode()
    snode = node.GetStorageNode()

  filename = snode.GetFileName()

  if not filename or filename == '':
    filename = _createAutoSaveFilePath(node)
  else:
    if not _fileIsInDataDirectory(filename):
      filename = _createAutoSaveFilePath(node)
    
  print('Autosave storage node filename: ' + filename)
  snode.SetFileName(filename)


def _autoSaveNode(node):
  snode = node.GetStorageNode()
  filename = snode.GetFileName()
  slicer.util.saveNode(node, filename)


def _autoSaveNodes(nodes):
  for node in nodes:
    _ensureStorageNodeAndFileNameExist(node)
    _autoSaveNode(node)


def autoSavePlan():
  # construct autosave path
  
  incremental = os.path.exists(_autoSaveDirectory())
  if incremental:
    print('Autosave incremental save')
  else:
    print('Autosave first save')
    _ensureAutoSaveDirectoriesExist()
  
  nodes = _listNodesToSave(incremental=incremental)
  
  autoSaveDialog = qt.QMessageBox(qt.QMessageBox.NoIcon, "Auto-saving", "Auto-saving", qt.QMessageBox.NoButton)
  autoSaveDialog.setStandardButtons(0)
  if not incremental:
    autoSaveDialog.show()
  slicer.app.processEvents()
  autoSaveDialog.deleteLater()
  slicer.mrmlScene.SetRootDirectory(_autoSaveDirectory())
  _autoSaveNodes(nodes)
  slicer.util.saveScene(_autoSaveFilePath())
  autoSaveDialog.hide()

  
def checkAutoSave():
  # construct autosave path
  print('Checking for autosave')
  import os
  if os.path.exists(_autoSaveDirectory()):
    print('Autosave found')
    reloadAutoSaveDialog = qt.QMessageBox(qt.QMessageBox.Information, "Reload autosave?",
      "An autosave has been found, would you like to reload it?", qt.QMessageBox.Yes | qt.QMessageBox.Discard)
    reloadAutoSaveDialog.open()
    ret = reloadAutoSaveDialog.exec()
    if ret == qt.QMessageBox.Yes:
      print('reloading autosave')
      slicer.util.loadScene(str(_autoSaveFilePath()))
    else:
      print('Skip loading autosave, discarding old autosave')
      _deleteAutoSave()
