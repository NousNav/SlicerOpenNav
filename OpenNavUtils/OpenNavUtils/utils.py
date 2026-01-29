import numpy as np
import vtk

import slicer


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


def createPolyData(X):
  n = X.shape[0]
  points = vtk.vtkPoints()
  points.SetNumberOfPoints(n)
  for i in range(n):
    points.SetPoint(i, X[i, 0], X[i, 1], X[i, 2])
  polyData = vtk.vtkPolyData()
  polyData.SetPoints(points)

  cloudCells = vtk.vtkCellArray()
  cloudCells.InsertNextCell(n)
  for i in range(n):
    cloudCells.InsertCellPoint(i)
  polyData.SetLines(cloudCells)

  return polyData


def centerCam():
  controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
  controller.resetFocalPoint()
