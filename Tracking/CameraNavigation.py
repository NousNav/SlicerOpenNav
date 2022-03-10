import qt
import slicer
from slicer.ScriptedLoadableModule import *
import numpy as np
import NNUtils


class CameraNavigation(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "CameraNavigation"
    self.parent.categories = [""]
    self.parent.dependencies = ["Tools"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """Module for tracking device handling and setup"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """...""" # replace with organization, grant and thanks.


class CameraNavigationWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = CameraNavigationLogic()
    self.toolsLogic = slicer.modules.tools.widgetRepresentation().self().logic

  def updateSliceViews(self, index):
    if self.cameraTool.currentIndex - 1 == index:
      tool = self.toolsLogic.getTool(index)
      pos = tool.getTranslation()
      if self.cameraAlignButton.checked:
        rot = np.linalg.inv(tool.getRotation())
        NNUtils.updateSliceViews(pos, rot)
      else:
        NNUtils.setSliceViewsPosition(pos)

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Track slice view to tool
    self.trackCameraWidget = qt.QWidget(self.parent)
    trackCameraLayout = qt.QHBoxLayout()
    self.trackCameraWidget.setLayout(trackCameraLayout)
    trackCameraLabel = qt.QLabel("Align Slice Views To: ")
    trackCameraLayout.addWidget(trackCameraLabel)

    self.cameraTool = qt.QComboBox()
    self.cameraTool.addItem("None")
    for i in range(self.toolsLogic.getNumberOfTools()):
      self.cameraTool.addItem(self.toolsLogic.getTool(i).getName())

    def indexChanged(index):
      if index == 0:
        NNUtils.resetSliceViews()
        NNUtils.centerOnActiveVolume()

    self.cameraTool.currentIndexChanged.connect(indexChanged)
    trackCameraLayout.addWidget(self.cameraTool)
    self.cameraAlignButton = qt.QPushButton("Orient to Volume")
    self.cameraAlignButton.setCheckable(True)

    def toggleCamera( checked ):
      if checked:
        self.cameraAlignButton.setText("Orient to Tool")
      else:
        self.cameraAlignButton.setText("Orient to Volume")
        NNUtils.resetSliceViews()

    self.cameraAlignButton.toggled.connect(toggleCamera)
    trackCameraLayout.addWidget(self.cameraAlignButton)
    self.layout.addWidget(self.trackCameraWidget)

    for i in range(self.toolsLogic.getNumberOfTools()):
      tool = self.toolsLogic.getTool(i)
      tool.transformNode.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent,
              (lambda index: lambda x, y: self.updateSliceViews(index) )(i) )

    # Compress the layout
    self.layout.addStretch(1)

  def enter(self):
    self.registerWidget.enter()


class CameraNavigationLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)


class CameraNavigationTest(ScriptedLoadableModuleTest):
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
    self.test_CameraNavigation1()

  def test_CameraNavigation1(self):
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

    logic = CameraNavigationLogic()
    self.delayDisplay('Test passed!')
