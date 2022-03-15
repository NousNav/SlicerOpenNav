#-----------------------------------------------------------------------------
set(MODULE_NAME Registration)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  RegistrationUtils/__init__.py
  RegistrationUtils/Tools.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui
  Resources/UI/HardwareDialog.ui
  Resources/UI/AlignmentSideWidget.ui
  Resources/UI/LandmarkSideWidget.ui
  Resources/Images/RegistrationStepPatientPrep.png
  Resources/Images/RegistrationStepTrackingPrep.png
  Resources/Images/RegistrationStepPointerPrep.jpg
  Resources/Images/RegistrationStepAlignCamera.png
  Resources/Images/RegistrationStepPivotCalibration.png
  Resources/Images/RegistrationStepSpinCalibration.png
  Resources/Data/manny.vtk
  Resources/Data/beep.wav
  Resources/Icons/Done.svg
  Resources/Icons/NotStarted.svg
  Resources/Icons/NotStarted.png
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
