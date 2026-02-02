# Re-export all public symbols for backward compatibility
#
# This module has been split into several submodules:
#   - workflow.py: Step and Workflow classes
#   - widgets.py: CSS utilities, toolbar setup, decorators
#   - layout.py: Layout management, slice viewers, reslicing
#   - autosave.py: Case/plan saving and loading
#   - utils.py: Transform utilities, volume helpers, etc.
#   - parameter_node.py: Parameter node property descriptors (DEPRECATED)

# DEPRECATED: parameterProperty and nodeReferenceProperty are deprecated.
# Use slicer.parameterNodeWrapper instead.
# See https://slicer.readthedocs.io/en/latest/developer_guide/parameter_nodes/overview.html
from .parameter_node import (  # noqa: F401
    parameterProperty,
    nodeReferenceProperty,
)

from .workflow import (  # noqa: F401
    Step,
    Workflow,
)

from .widgets import (  # noqa: F401
    statusLabelName,
    patientNameLabelName,
    applicationTitleLabelName,
    setMainPanelVisible,
    setSidePanelVisible,
    addCssClass,
    removeCssClass,
    setCssClass,
    setupWorkflowToolBar,
    setupNavigationToolBar,
    backButton,
    advanceButton,
    polish,
    applyStyle,
    getWidgetFromSlicer,
)

from .layout import (  # noqa: F401
    initializeNavigationLayouts,
    setupSliceViewers,
    setupSliceViewer,
    setup3DView,
    setSliceControllerButtonsVisible,
    setSliceControllerComponentVisible,
    showSliceOrientationLabels,
    showSliceOrientationAxes,
    setSliceWidgetOffsetSliderVisible,
    setSliceWidgetSlidersVisible,
    setSliceViewBackgroundColor,
    goToNavigationLayout,
    showCentralWidget,
    goToFourUpLayout,
    goToRegistrationCameraViewLayout,
    goToPictureLayout,
    goToVideoLayout,
    activateReslicing,
    deactivateReslicing,
    observeTransformForSliceJump,
    removeObserveTransformForSliceJump,
    jumpAxisAlignedSlices,
    getSixUpNavigationLayoutID,
    registerSixUpNavigationLayout,
    getTwoUpNavigationLayoutID,
    registerTwoUpNavigationLayout,
)

from .autosave import (  # noqa: F401
    deleteAutoSave,
    slugify,
    autoSavePlan,
    loadAutoSave,
    checkAutoSave,
    savePlan,
    listAvailablePlans,
    saveScreenShotViewersOnly,
    saveScreenShot,
    openCasesDirectoryInExplorer,
)

from .utils import (  # noqa: F401
    isLinearTransformNodeIdentity,
    getModality,
    getActiveVolume,
    centerOnActiveVolume,
    center3DView,
    createPolyData,
    centerCam,
)
