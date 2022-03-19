#-----------------------------------------------------------------------------
set(MODULE_NAME Home)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/Icons/Gears.png
  Resources/UI/${MODULE_NAME}.ui
  Resources/UI/Settings.ui
  Resources/UI/CenteredWidget.ui
  Resources/${MODULE_NAME}.qss
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
