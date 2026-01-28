#-----------------------------------------------------------------------------
set(MODULE_NAME OpenNavUtils)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  OpenNavUtils/__init__.py
  OpenNavUtils/parameter_node.py
  )

set(MODULE_PYTHON_RESOURCES
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
