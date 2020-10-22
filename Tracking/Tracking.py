import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

import TrackingDevices.Interface as TrackingInterface


class Tracking(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Tracking"
    self.parent.categories = [""]
    self.parent.dependencies = ["Tools", "FiducialSelection", "CameraNavigation"]
    self.parent.contributors = ["Samuel Gerber (Kitware Inc.)"]
    self.parent.helpText = """Module for tracking device handling and setup"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """...""" # replace with organization, grant and thanks.


class TrackingWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = TrackingLogic()

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Connect button
    self.connectButton = qt.QPushButton("Start Tracking")
    self.connectButton.setCheckable(True)
    self.layout.addWidget(self.connectButton)
    # Tracking toggle button action
    def toggleTracking(checked):
      if not checked:
        self.connectButton.setText("Start Tracking")
        TrackingInterface.stopTracking()
      else:
        try:
          TrackingInterface.startTracking()
          self.connectButton.setText("Stop Tracking")
        except OSError as err:
          # TODO figure out error message handling
          slicer.util.errorDisplay( str(err) )
    self.connectButton.toggled.connect(toggleTracking)

    self.typeWidget = qt.QWidget()
    typeLayout = qt.QFormLayout(self.typeWidget)
    self.typeSelector = qt.QComboBox()
    self.typeSelector.addItem('NDI')
    self.typeSelector.addItem('OptiTrack')
    self.typeSelector.setCurrentText(slicer.util.settingsValue('NousNav/Tracker', 'OptiTrack'))
    typeLayout.addRow('Tracker type (restart needed for change to take effect):', self.typeSelector)
    self.layout.addWidget(self.typeWidget)
    def textChanged(text):
      qt.QSettings().setValue('NousNav/Tracker', text)
    self.typeSelector.currentTextChanged.connect(textChanged)

    
    # Configuration
    self.toolsWidget = slicer.modules.tools.createNewWidgetRepresentation()
    self.configurationFrame = TrackingInterface.getTrackingDevice().getConfigurationWidget()
    self.configurationFrame.setChecked(False)
    self.layout.addWidget(self.configurationFrame)

    # Setup tool calibrations
    self.layout.addWidget(self.toolsWidget)

    # Track slice view to tool
    self.trackCameraWidget = slicer.modules.cameranavigation.createNewWidgetRepresentation()
    self.cameraFrame = ctk.ctkCollapsibleGroupBox(self.parent)
    cameraLayout = qt.QVBoxLayout(self.cameraFrame)
    self.layout.addWidget(self.cameraFrame)
    self.cameraFrame.name = "Tool Tracking"
    self.cameraFrame.title = "Tool Tracking"
    self.cameraFrame.setChecked(True)
    cameraLayout.addWidget(self.trackCameraWidget)
    self.layout.addWidget(self.cameraFrame)

    # Fiducial registration
    self.fiducialFrame = ctk.ctkCollapsibleGroupBox(self.parent)
    fiducialLayout = qt.QVBoxLayout(self.fiducialFrame)
    self.layout.addWidget(self.fiducialFrame)
    self.fiducialFrame.name = "Register Tracking to Scene"
    self.fiducialFrame.title = "Register Tracking to Scene"
    self.fiducialFrame.setChecked( True )
    self.registerWidget = slicer.modules.fiducialselection.createNewWidgetRepresentation()
    fiducialLayout.addWidget(self.registerWidget)

    # Compress the layout
    self.layout.addStretch(1)

  def enter(self):
    self.registerWidget.enter()
    self.screwGuidance.enter()


class TrackingLogic(ScriptedLoadableModuleLogic):
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

class TrackingTest(ScriptedLoadableModuleTest):
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
    self.test_Tracking1()

  def test_Tracking1(self):
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

    logic = TrackingLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class TrackingFileWriter(object):
  def __init__(self, parent):
    pass
