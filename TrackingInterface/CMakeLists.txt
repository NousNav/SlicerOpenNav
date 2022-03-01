#-----------------------------------------------------------------------------
set(MODULE_NAME TrackingInterface)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  TrackingDevices/__init__.py
  TrackingDevices/Interface.py
  TrackingDevices/NDIDevices.py
  TrackingDevices/PLUSOptiTrack.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
