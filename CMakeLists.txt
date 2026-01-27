cmake_minimum_required(VERSION 3.20.6...3.22.6 FATAL_ERROR)

project(SlicerOpenNav)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/SlicerOpenNav")
set(EXTENSION_CONTRIBUTORS "Sam Horvath (Kitware Inc.)")
set(EXTENSION_DESCRIPTION "Open source tools for surgical navigation")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/SlicerOpenNav.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/SlicerOpenNav/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

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
add_subdirectory(NNUtils)
add_subdirectory(OptiTrack)
add_subdirectory(Patients)
add_subdirectory(Planning)
add_subdirectory(SlicerCustomAppUtilities)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
