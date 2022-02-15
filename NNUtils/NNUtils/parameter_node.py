import json

from slicer.ScriptedLoadableModule import ScriptedLoadableModuleLogic


def get_logic_node(instance: ScriptedLoadableModuleLogic):
  return instance.getParameterNode()


def parameterProperty(
  name,
  get_node=get_logic_node,
  dumps=json.dumps,
  loads=json.loads,
  factory=None,
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
  node. The value is immediately stored in the node.
  """

  def fget(self):
    params = get_node(self)
    string = params.GetParameter(name)

    if string:
      return loads(string)
    elif factory is not None:
      value = factory()
      string = dumps(value)
      params.SetParameter(name, string)
      return value

    raise KeyError("Parameter node {!r} has no parameter {!r}".format(params, name))

  def fset(self, value):
    params = get_node(self)
    string = dumps(value)
    params.SetParameter(name, string)

  return property(fget, fset)


def nodeReferenceProperty(
  reference_role,
  get_node=get_logic_node,
  factory=None,
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
  node. The value is immediately stored in the node.
  """

  def fget(self):
    params = get_node(self)
    node = params.GetNodeReference(reference_role)

    if node:
      return node
    elif factory is not None:
      node = factory()
      params.SetNodeReferenceID(reference_role, node.GetID())
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
