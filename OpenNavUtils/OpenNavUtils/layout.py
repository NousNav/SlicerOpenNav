import numpy as np
import vtk

import qt
import slicer

from .widgets import setMainPanelVisible, setSidePanelVisible


def initializeNavigationLayouts():
    """This function was designed to be called once from Home module."""

    # Add the layout
    registerSixUpNavigationLayout()
    registerTwoUpNavigationLayout()

    # Switch to navigation layout forces the creation of views
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(getSixUpNavigationLayoutID())

    # Reset to four-up layout
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)


def setupSliceViewers(visible=False):
    for name in slicer.app.layoutManager().sliceViewNames():
        sliceWidget = slicer.app.layoutManager().sliceWidget(name)
        setupSliceViewer(sliceWidget, visible)


def setupSliceViewer(sliceWidget, visible=False):
    controller = sliceWidget.sliceController()
    controller.setStyleSheet("background-color: #000000")
    controller.sliceViewLabel = ""
    setSliceControllerButtonsVisible(sliceWidget, visible)


def setup3DView(visible=False):
    layoutManager = slicer.app.layoutManager()
    controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
    controller.setBlackBackground()
    controller.set3DAxisVisible(False)
    controller.set3DAxisLabelVisible(False)
    controller.setOrientationMarkerType(3)  # Axis marker
    controller.setStyleSheet("background-color: #000000")

    threeDWidget = layoutManager.threeDWidget(0)
    threeDWidget.mrmlViewNode().SetBoxVisible(False)
    horizontalSpacer = qt.QSpacerItem(0, 0, qt.QSizePolicy.Expanding, qt.QSizePolicy.Minimum)
    threeDWidget.layout().insertSpacerItem(0, horizontalSpacer)

    setSliceControllerComponentVisible(slicer.util.findChild(controller, "MaximizeViewButton"), True)
    setSliceControllerComponentVisible(slicer.util.findChild(controller, "PinButton"), visible)
    setSliceControllerComponentVisible(slicer.util.findChild(controller, "ViewLabel"), False)
    setSliceControllerComponentVisible(slicer.util.findChild(controller, "CenterButton_Header"), visible)


def setSliceControllerButtonsVisible(sliceWidget, visible):
    slicer.util.findChild(sliceWidget, "SliceOffsetSlider").spinBoxVisible = False
    setSliceControllerComponentVisible(slicer.util.findChild(sliceWidget, "PinButton"), visible)
    setSliceControllerComponentVisible(slicer.util.findChild(sliceWidget, "ViewLabel"), False)
    setSliceControllerComponentVisible(slicer.util.findChild(sliceWidget, "FitToWindowToolButton"), visible)
    setSliceControllerComponentVisible(slicer.util.findChild(sliceWidget, "MaximizeViewButton"), True)
    setSliceControllerComponentVisible(slicer.util.findChild(sliceWidget, "MoreButton"), visible)


def setSliceControllerComponentVisible(component, visible):
    component.visible = visible
    component.setStyleSheet("background-color: #5ac2c9")


def showSliceOrientationLabels(visible):
    for name in slicer.app.layoutManager().sliceViewNames():
        sliceWidget = slicer.app.layoutManager().sliceWidget(name)
        if sliceWidget.sliceOrientation == "Axial" or sliceWidget.sliceOrientation == "Coronal":
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


def goToNavigationLayout(volumeNode=None, layout="SixUp", mainPanelVisible=False, sidePanelVisible=False):
    # Switching to FourUpLayout is a workaround to ensure
    # the layout the NavigationLayout is properly displayed
    # with all view properly sized.
    goToFourUpLayout()

    layoutManager = slicer.app.layoutManager()
    if layout == "TwoUp":
        layoutManager.setLayout(getTwoUpNavigationLayoutID())
    elif layout == "SixUp":
        layoutManager.setLayout(getSixUpNavigationLayoutID())
    else:
        layoutManager.setLayout(getSixUpNavigationLayoutID())
    setMainPanelVisible(mainPanelVisible)
    setSidePanelVisible(sidePanelVisible)
    setSliceViewBackgroundColor("#000000")
    slicer.util.setSliceViewerLayers(foreground=None, background=volumeNode, label=None, fit=True)
    setupSliceViewers()

    try:
        tipToPointer = slicer.util.getNode("POINTER_CALIBRATION")
        activateReslicing(tipToPointer)

    except:
        print("Cannot find pointer node")

    showSliceOrientationAxes(True)
    showSliceOrientationLabels(False)
    slicer.app.layoutManager().activeThreeDRenderer().ResetCamera()


def showCentralWidget(name):
    slicer.util.findChild(slicer.util.mainWindow(), "CentralWidgetImageFrame").visible = False
    slicer.util.findChild(slicer.util.mainWindow(), "CentralWidgetLayoutFrame").visible = False
    slicer.util.findChild(slicer.util.mainWindow(), "CentralWidgetVideoFrame").visible = False

    if name == "layout":
        slicer.util.findChild(slicer.util.mainWindow(), "CentralWidgetLayoutFrame").visible = True

    if name == "image":
        slicer.util.findChild(slicer.util.mainWindow(), "CentralWidgetImageFrame").visible = True

    if name == "video":
        slicer.util.findChild(slicer.util.mainWindow(), "CentralWidgetVideoFrame").visible = True


def goToFourUpLayout(volumeNode=None, mainPanelVisible=True, sidePanelVisible=False):
    deactivateReslicing()
    showCentralWidget("layout")
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    setSliceWidgetSlidersVisible(True)
    setMainPanelVisible(mainPanelVisible)
    setSidePanelVisible(sidePanelVisible)
    setSliceViewBackgroundColor("#000000")
    slicer.util.setSliceViewerLayers(foreground=None, background=volumeNode, label=None, fit=True)
    slicer.app.layoutManager().activeThreeDRenderer().ResetCamera()

    # reset slice orientations to default
    slicer.app.layoutManager().sliceWidget("Red").sliceOrientation = "Axial"
    slicer.app.layoutManager().sliceWidget("Green").sliceOrientation = "Coronal"
    slicer.app.layoutManager().sliceWidget("Yellow").sliceOrientation = "Sagittal"

    setupSliceViewers()
    showSliceOrientationLabels(True)
    showSliceOrientationAxes(False)


def goToRegistrationCameraViewLayout():
    deactivateReslicing()
    showCentralWidget("layout")
    layoutManager = slicer.app.layoutManager()
    layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    setSliceWidgetSlidersVisible(False)
    setMainPanelVisible(True)
    setSidePanelVisible(True)


def goToPictureLayout(image=None, sidePanelVisible=False):
    deactivateReslicing()
    showCentralWidget("image")
    centralImageLabel = slicer.util.findChild(slicer.util.mainWindow(), "CentralImageLabel")
    centralImageLabel.pixmap = image
    setMainPanelVisible(True)
    setSidePanelVisible(sidePanelVisible)
    showSliceOrientationLabels(False)
    showSliceOrientationAxes(False)


# Usage example:
# NNUtils.goToVideoLayout(self.resourcePath('Videos/example.html'))
def goToVideoLayout(videoURL, sidePanelVisible=False):
    deactivateReslicing()
    showCentralWidget("video")
    centralVideoWidget = slicer.util.findChild(slicer.util.mainWindow(), "CentralVideoWidget")
    centralVideoWidget.setUrl("file:///" + videoURL.replace("\\", "/"))
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
    driverNode.SetAttribute("JumpObserverTag", str(observerTag))


def removeObserveTransformForSliceJump(driverNode):
    observerTag = driverNode.GetAttribute("JumpObserverTag")
    if observerTag:
        driverNode.RemoveObserver(int(observerTag))


def jumpAxisAlignedSlices(driverNode, eventid):
    def _getTranslation(driverNode):
        mat = vtk.vtkMatrix4x4()
        driverNode.GetMatrixTransformToWorld(mat)
        npmat = np.zeros(3)
        for i in range(3):
            npmat[i] = mat.GetElement(i, 3)
        return npmat

    def _jump(sliceViewNodeID, driverNode):
        sliceViewNode = slicer.util.getNode(sliceViewNodeID)
        pos = _getTranslation(driverNode)
        sliceViewNode.JumpSliceByOffsetting(pos[0], pos[1], pos[2])

    _jump("vtkMRMLSliceNodeRed", driverNode)
    _jump("vtkMRMLSliceNodeYellow", driverNode)
    _jump("vtkMRMLSliceNodeGreen", driverNode)


def getSixUpNavigationLayoutID():
    threeDWithReformatCustomLayoutId = 503
    return threeDWithReformatCustomLayoutId


def registerSixUpNavigationLayout():
    customLayout = (
        '<layout type="vertical">'
        " <item>"
        '  <layout type="horizontal">'
        "   <item>"
        '    <view class="vtkMRMLSliceNode" singletontag="Blue">'
        '     <property name="orientation" action="default">Axial</property>'
        '     <property name="viewlabel" action="default">R</property>'
        '     <property name="viewcolor" action="default">#F34A33</property>'
        "    </view>"
        "   </item>"
        "   <item>"
        '    <view class="vtkMRMLSliceNode" singletontag="Orange">'
        '     <property name="orientation" action="default">Axial</property>'
        '     <property name="viewlabel" action="default">R</property>'
        '     <property name="viewcolor" action="default">#FFA500</property>'
        "    </view>"
        "   </item>"
        "   <item>"
        '    <view class="vtkMRMLViewNode" singletontag="1">'
        '     <property name="viewlabel" action="default">1</property>'
        "    </view>"
        "   </item>"
        "  </layout>"
        " </item>"
        " <item>"
        '  <layout type="horizontal">'
        "   <item>"
        '    <view class="vtkMRMLSliceNode" singletontag="Red">'
        '     <property name="orientation" action="default">Axial</property>'
        '     <property name="viewlabel" action="default">R</property>'
        '     <property name="viewcolor" action="default">#0000FF</property>'
        "    </view>"
        "   </item>"
        "   <item>"
        '    <view class="vtkMRMLSliceNode" singletontag="Green">'
        '     <property name="orientation" action="default">Coronal</property>'
        '     <property name="viewlabel" action="default">G</property>'
        '     <property name="viewcolor" action="default">#6EB04B</property>'
        "    </view>"
        "   </item>"
        "   <item>"
        '    <view class="vtkMRMLSliceNode" singletontag="Yellow">'
        '     <property name="orientation" action="default">Sagittal</property>'
        '     <property name="viewlabel" action="default">Y</property>'
        '     <property name="viewcolor" action="default">#EDD54C</property>'
        "    </view>"
        "   </item>"
        "  </layout>"
        " </item>"
        "</layout>"
    )
    layoutNode = slicer.app.layoutManager().layoutLogic().GetLayoutNode()
    layoutNode.AddLayoutDescription(getSixUpNavigationLayoutID(), customLayout)


def getTwoUpNavigationLayoutID():
    reformatCustomLayoutId = 504
    return reformatCustomLayoutId


def registerTwoUpNavigationLayout():
    customLayout = (
        '  <layout type="horizontal">'
        "   <item>"
        '    <view class="vtkMRMLSliceNode" singletontag="Blue">'
        '     <property name="orientation" action="default">Axial</property>'
        '     <property name="viewlabel" action="default">R</property>'
        '     <property name="viewcolor" action="default">#F34A33</property>'
        "    </view>"
        "   </item>"
        "   <item>"
        '    <view class="vtkMRMLSliceNode" singletontag="Orange">'
        '     <property name="orientation" action="default">Axial</property>'
        '     <property name="viewlabel" action="default">R</property>'
        '     <property name="viewcolor" action="default">#FFA500</property>'
        "    </view>"
        "   </item>"
        "  </layout>"
    )
    layoutNode = slicer.app.layoutManager().layoutLogic().GetLayoutNode()
    layoutNode.AddLayoutDescription(getTwoUpNavigationLayoutID(), customLayout)
