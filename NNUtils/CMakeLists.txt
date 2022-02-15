#-----------------------------------------------------------------------------
set(MODULE_NAME NNUtils)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  NNUtils/__init__.py
  NNUtils/parameter_node.py
  )

set(MODULE_PYTHON_RESOURCES
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
