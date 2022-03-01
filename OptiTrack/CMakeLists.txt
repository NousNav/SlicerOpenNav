#-----------------------------------------------------------------------------
set(MODULE_NAME OptiTrack)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/PlusDeviceSet_Server_OptiTrack_Profile.xml.in
  Resources/Reference.xml.in
  Resources/ReplayOptiTrack.xml.in
  Resources/Ellipse.mha
  Resources/Probe.xml
  Resources/Reference.xml
  Resources/Head.xml
  Resources/PLUSHead.xml.in
  Resources/MotiveProfile-2021-06-24.xml
  Resources/MotiveProfile-2021-10-22.xml
  Resources/NousNav-BWH-Hardware.xml
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
