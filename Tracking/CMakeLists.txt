#-----------------------------------------------------------------------------
set(MODULE_NAME Tracking)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  Tools.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/NDITools/8700338.rom
  Resources/NDITools/8700339.rom
  Resources/NDITools/8700340.rom
  Resources/OptiTrack/PlusDeviceSet_Server_OptiTrack_Profile.xml.in
  Resources/OptiTrack/ReplayOptiTrack.xml.in
  Resources/OptiTrack/Ellipse.mha
  Resources/OptiTrack/Probe.xml
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
