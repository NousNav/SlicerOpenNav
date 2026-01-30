import functools

import qt
import slicer


# Reserved QObject names
statusLabelName = "StatusLabel"
patientNameLabelName = "PatientNameLabel"
applicationTitleLabelName = "ApplicationTitleLabel"


def setMainPanelVisible(visible):
    modulePanel = slicer.util.findChild(slicer.util.mainWindow(), "PanelDockWidget")
    modulePanel.visible = visible


def setSidePanelVisible(visible):
    sidePanel = slicer.util.findChild(slicer.util.mainWindow(), "SidePanelDockWidget")
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


def setupNavigationToolBar(name):
    """Add toolbar with navigation menu buttons.

    Return a tuple of the form ``(toolBar, pointerButton, pointerButtonAction, layoutButton, layoutButtonAction)``
    """
    toolBar = qt.QToolBar(f"{name}NavigationBottomToolBar")
    toolBar.setObjectName(f"{name}NavigationBottomToolBar")
    addCssClass(toolBar, "bottom-toolbar")
    toolBar.movable = False
    slicer.util.mainWindow().addToolBar(qt.Qt.BottomToolBarArea, toolBar)

    spacer = qt.QWidget()
    policy = spacer.sizePolicy
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    spacer.setSizePolicy(policy)
    spacer.name = f"{name}LeftNavigationBottomToolbarSpacer"
    addCssClass(spacer, "bottom-toolbar__spacer")
    toolBar.addWidget(spacer)

    pointerButton = qt.QPushButton("Pointer Preferences")
    pointerButton.name = "PointerButton"
    addCssClass(pointerButton, ["bottom-toolbar__button", "bottom-toolbar__advance-button"])
    pointerButtonAction = toolBar.addWidget(pointerButton)

    spacer = qt.QWidget()
    policy = spacer.sizePolicy
    policy.setHorizontalPolicy(qt.QSizePolicy.Fixed)
    spacer.setSizePolicy(policy)
    spacer.minimumWidth = 200
    spacer.name = f"{name}CenterNavigationBottomToolbarSpacer"
    addCssClass(spacer, "bottom-toolbar__spacer")
    toolBar.addWidget(spacer)

    layoutButton = qt.QPushButton("Layouts")
    layoutButton.name = "LayoutButton"
    addCssClass(layoutButton, ["bottom-toolbar__button", "bottom-toolbar__advance-button"])
    layoutButtonAction = toolBar.addWidget(layoutButton)

    spacer = qt.QWidget()
    policy = spacer.sizePolicy
    policy.setHorizontalPolicy(qt.QSizePolicy.Expanding)
    spacer.setSizePolicy(policy)
    spacer.name = f"{name}RightNavigationBottomToolbarSpacer"
    addCssClass(spacer, "bottom-toolbar__spacer")
    toolBar.addWidget(spacer)

    # Default
    addCssClass(toolBar, "bottom-toolbar--color-light")

    return (toolBar, pointerButton, pointerButtonAction, layoutButton, layoutButtonAction)


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
    with open(styleSheetFilePath) as fh:
        styleSheet = fh.read()
        for widget in widgets:
            widget.styleSheet = styleSheet


def getWidgetFromSlicer(objectName):
    """Get widget from Slicer main window by its object name.

    Return None if the widget is not found.
    """
    children = slicer.util.findChildren(slicer.util.mainWindow(), objectName)

    if len(children) == 0:
        return None

    return children[0]
