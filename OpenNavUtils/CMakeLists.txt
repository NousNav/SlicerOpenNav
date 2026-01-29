#-----------------------------------------------------------------------------
set(MODULE_NAME OpenNavUtils)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  OpenNavUtils/__init__.py
  OpenNavUtils/autosave.py
  OpenNavUtils/layout.py
  OpenNavUtils/parameter_node.py
  OpenNavUtils/utils.py
  OpenNavUtils/widgets.py
  OpenNavUtils/workflow.py
  )

set(MODULE_PYTHON_RESOURCES
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )
