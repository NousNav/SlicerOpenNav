import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *


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


def setMainPanelVisible(visible):
  modulePanel = slicer.util.findChild(slicer.util.mainWindow(), 'PanelDockWidget')
  modulePanel.visible = visible


def setSidePanelVisible(visible):
  sidePanel = slicer.util.findChild(slicer.util.mainWindow(), 'SidePanelDockWidget')
  sidePanel.visible = visible


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
