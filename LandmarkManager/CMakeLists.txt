#-----------------------------------------------------------------------------
set(MODULE_NAME LandmarkManager)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.svg
  Resources/UI/${MODULE_NAME}.ui
  Resources/Icons/Done.svg
  Resources/Icons/NotStarted.svg
  Resources/Icons/Skipped.svg
  Resources/Icons/Started.svg
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

