#-----------------------------------------------------------------------------
set(MODULE_NAME Registration)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  RegistrationUtils/__init__.py
  RegistrationUtils/Tools.py
  RegistrationUtils/Trace.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui
  Resources/UI/HardwareDialog.ui
  Resources/UI/AlignmentSideWidget.ui
  Resources/Images/RegistrationStepPatientPrep.png
  Resources/Images/RegistrationStepTrackingPrep.png
  Resources/Images/RegistrationStepPointerPrep.jpg
  Resources/Images/RegistrationStepAlignCamera.png
  Resources/Data/manny.vtk
  Resources/Data/beep.wav
  Resources/Videos/pivot.html
  Resources/Videos/Pivot.webm
  Resources/Videos/spin.html
  Resources/Videos/Spin.webm
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
