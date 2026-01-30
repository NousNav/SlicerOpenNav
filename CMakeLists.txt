cmake_minimum_required(VERSION 3.20.6...3.22.6 FATAL_ERROR)

project(OpenNav)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/NousNav/SlicerOpenNav")
set(EXTENSION_CONTRIBUTORS "Sam Horvath (Kitware Inc.)")
set(EXTENSION_DESCRIPTION "Complete workflow for image-guided surgical navigation including DICOM import, trajectory planning, tool calibration, patient registration, and real-time instrument tracking")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/NousNav/SlicerOpenNav/refs/heads/main/OpenNav.svg")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/NousNav/SlicerOpenNav/refs/heads/main/Screenshot1.png")
set(EXTENSION_DEPENDS "SlicerOpenIGTLink", "SlicerIGT") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
## NEXT_MODULE
add_subdirectory(Home)
add_subdirectory(Registration)
add_subdirectory(LandmarkManager)
add_subdirectory(Navigation)
add_subdirectory(OpenNavUtils)
add_subdirectory(OptiTrack)
add_subdirectory(Patients)
add_subdirectory(Planning)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
