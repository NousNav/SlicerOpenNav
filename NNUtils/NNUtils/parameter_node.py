import json
import typing

import slicer

from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic


def get_logic_node(instance: ScriptedLoadableModuleLogic):
  return instance.getParameterNode()


MISSING = object()

FactoryType = typing.Callable[[], typing.Any]
DumpsType = typing.Callable[[typing.Any], str]
LoadsType = typing.Callable[[str], typing.Any]


def parameterProperty(
  name,
  get_node=get_logic_node,
  dumps: DumpsType = json.dumps,
  loads: LoadsType = json.loads,
  factory: FactoryType = MISSING,
  default: typing.Any = MISSING,
):
  """
  Create a property which stores data in a parameter node (vtkMRMLScriptedModuleNode).
  Intended to be used in module logic classes (ScriptedLoadableModuleLogic subclasses).

  Since a parameter node is a string mapping, values must be converted to/from str; by
  default this is done using json.

  >>> class SampleLogic(ScriptedLoadableModuleLogic)
  ...   data = parameterProperty("EXTRA_DATA")
  ...
  >>> logic = SampleLogic()
  >>> logic.data = [2, 3]
  >>> logic.data
  [2, 3]

  Note that, since values are only stored on assignment, inline modifications will not persist

  >>> logic.data = [2, 3]
  >>> logic.data.append(4)
  >>> logic.data
  [2, 3]

  Use a temporary variable and re-assign the value to persist changes

  >>> data = logic.data
  >>> data.append(4)
  >>> logic.data = data
  >>> logic.data
  [2, 3, 4]

  :param name: The parameter name (key) used for storage.
  :param get_node: Gets a parameter node from the instance. Default behavior calls
  getParameterNode on the instance.
  :param dumps: Convert a value to a string.
  :param loads: Convert a string to a value.
  :param factory: Create a default value if the property does not exist in the parameter
  node. The result is immediately stored in the node. Mutually exclusive with default.
  :param default: A default value, used if the property does not exist in the parameter
  node. A copy is immediately stored in the node. Mutually exclusive with factory.
  """

  if sum((factory is not MISSING, default is not MISSING)) > 1:
    raise ValueError(
      "More than one default option was provided. factory and default are mutually "
      "exclusive."
    )

  def fget(self):
    params = get_node(self)
    string = params.GetParameter(name)

    if string:
      return loads(string)
    elif factory is not MISSING:
      value = factory()
      string = dumps(value)
      params.SetParameter(name, string)
      return value
    elif default is not MISSING:
      value = default
      string = dumps(value)
      params.SetParameter(name, string)

      # create a copy of the value to prevent mutating the default.
      return loads(string)

    raise KeyError("Parameter node {!r} has no parameter {!r}".format(params, name))

  def fset(self, value):
    params = get_node(self)
    string = dumps(value)
    params.SetParameter(name, string)

  return property(fget, fset)


def nodeReferenceProperty(
  reference_role,
  get_node=get_logic_node,
  factory: FactoryType = MISSING,
  default: typing.Any = MISSING,
  class_: str = MISSING,
):
  """
  Create a property which stores a node reference in a parameter node (vtkMRMLScriptedModuleNode).
  Intended to be used in module logic classes (ScriptedLoadableModuleLogic subclasses).

  >>> class SampleLogic(ScriptedLoadableModuleLogic)
  ...   node = nodeReferenceProperty("SEGMENTATION")
  ...
  >>> logic = SampleLogic()
  >>> logic.node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
  >>> logic.node
  (MRMLCorePython.vtkMRMLSegmentationNode)0x7fd88d59d1c8

  :param reference_role: The reference role (key) used for storage.
  :param get_node: Gets a parameter node from the instance. Default behavior calls
  getParameterNode on the instance.
  :param factory: Create a default value if the property does not exist in the parameter
  node. The result is immediately stored in the node. Mutually exclusive with default
  and class_.
  :param default: A default value, used if the property does not exist in the parameter
  node. A reference to this value is immediately stored in the node. Mutually exclusive
  with factory and class_.
  :param class_: A MRML class, used if the property does not exist in the parameter node.
  A node of this type is created and immediately stored in the node. Mutually exclusive
  with factory and default. See slicer.mrmlScene.AddNewNodeByClass
  """

  if sum((factory is not MISSING, default is not MISSING, class_ is not MISSING)) > 1:
    raise ValueError(
      "More than one default option was provided. factory, default, and class_ are "
      "mutually exclusive."
    )

  def fget(self):
    params = get_node(self)
    node = params.GetNodeReference(reference_role)

    if node:
      return node
    elif factory is not MISSING:
      node = factory()
      if node is None:
        nodeID = None
      else:
        nodeID = node.GetID()
      params.SetNodeReferenceID(reference_role, nodeID)
      return node
    elif default is not MISSING:
      node = default
      if node is None:
        nodeID = None
      else:
        nodeID = node.GetID()
      params.SetNodeReferenceID(reference_role, nodeID)
      return node
    elif class_ is not MISSING:
      node = slicer.mrmlScene.AddNewNodeByClass(class_)
      if node is None:
        nodeID = None
      else:
        nodeID = node.GetID()
      params.SetNodeReferenceID(reference_role, nodeID)
      return node

    raise KeyError(
      "Parameter node {!r} has no reference role {!r}".format(
        params, reference_role
      )
    )

  def fset(self, node):
    params = get_node(self)
    params.SetNodeReferenceID(reference_role, node.GetID())

  return property(fget, fset)
