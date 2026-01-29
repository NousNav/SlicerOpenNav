import datetime
import logging
import os
import pathlib
import re
import unicodedata

import qt
import slicer

from .widgets import getWidgetFromSlicer


def _casesDirectory():
  userPath = os.path.expanduser('~')
  return os.path.join(userPath, 'OpenNav', 'Cases')


def _autoSaveDirectory(caseName):
  return os.path.join(_casesDirectory(), caseName)


def _autoSaveDataDirectory(caseName):
  return os.path.join(_autoSaveDirectory(caseName), 'Data')


def _autoSaveFilePath(caseName):
  path = caseName + '.mrml'
  return os.path.join(_autoSaveDirectory(caseName), path)


def deleteAutoSave(caseName):
  if os.path.exists(_autoSaveDirectory(caseName)):
    import shutil
    shutil.rmtree(_autoSaveDirectory(caseName))


def _ensureAutoSaveDirectoriesExist(caseName):
  # Create all directories in tree recursively
  os.makedirs(_autoSaveDataDirectory(caseName))


def _listNodesToSave(incremental=False):
  storableNodes = slicer.util.getNodesByClass('vtkMRMLStorableNode')
  saveableNodes = [node for node in storableNodes if (node.GetSaveWithScene() and not node.GetHideFromEditors())]
  saveableToOwnFileNodes = [node for node in saveableNodes if slicer.app.coreIOManager().fileWriterFileType(node) != 'NoFile']
  modifiedNodes = [node for node in saveableToOwnFileNodes if node.GetModifiedSinceRead()]

  if incremental:
    nodes = modifiedNodes
  else:
    nodes = saveableToOwnFileNodes

  return nodes


def _fileIsInDataDirectory(caseName,filename):
  try:
    commonfilepathpath = os.path.commonpath([_autoSaveDataDirectory(caseName),os.path.abspath(filename)])
  except ValueError:  # Value errors can occur in the worst cases of non-matching paths
    return False

  return os.path.normpath(_autoSaveDataDirectory(caseName)) == os.path.normpath(commonfilepathpath)


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/main/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value)
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def _createAutoSaveFilePath(caseName, node):
  snode = node.GetStorageNode()
  possiblePath = os.path.join(_autoSaveDataDirectory(caseName), slugify(node.GetName()) + '.' + snode.GetDefaultWriteFileExtension())
  return slicer.mrmlScene.CreateUniqueFileName(possiblePath, '.'+snode.GetDefaultWriteFileExtension())


def _ensureStorageNodeAndFileNameExist(caseName, node):
  snode = node.GetStorageNode()
  if not snode:
    node.AddDefaultStorageNode()
    snode = node.GetStorageNode()

  filename = snode.GetFileName()

  if not filename or filename == '':
    filename = _createAutoSaveFilePath(caseName, node)
  else:
    if not _fileIsInDataDirectory(caseName, filename):
      filename = _createAutoSaveFilePath(caseName, node)

  print('Autosave storage node filename: ' + filename)
  snode.SetFileName(filename)


def _autoSaveNode(node):
  snode = node.GetStorageNode()
  filename = snode.GetFileName()
  slicer.util.saveNode(node, filename)


def _autoSaveNodes(caseName, nodes):
  for node in nodes:
    _ensureStorageNodeAndFileNameExist(caseName, node)
    _autoSaveNode(node)


def autoSavePlan(caseName='Default'):

  if not caseName:
    logging.warning('Case is not set. Should only occur when skipping validation')
    return
  # construct autosave path

  savingStatusLabel = getWidgetFromSlicer('SavingStatusLabel')
  if savingStatusLabel:
    savingStatusLabel.setText('Saving...')

  slicer.app.processEvents()

  incremental = os.path.exists(_autoSaveDirectory(caseName))
  if incremental:
    print('Autosave incremental save: ' + caseName)
  else:
    print('Autosave first save: ' + caseName)
    _ensureAutoSaveDirectoriesExist(caseName)

  nodes = _listNodesToSave(incremental=incremental)

  autoSaveDialog = qt.QMessageBox(qt.QMessageBox.NoIcon, "Auto-saving", "Auto-saving", qt.QMessageBox.NoButton)
  autoSaveDialog.setStandardButtons(0)
  if not incremental:
    autoSaveDialog.show()
  slicer.app.processEvents()
  autoSaveDialog.deleteLater()
  slicer.mrmlScene.SetRootDirectory(_autoSaveDirectory(caseName))
  _autoSaveNodes(caseName,nodes)
  slicer.util.saveScene(_autoSaveFilePath(caseName))
  autoSaveDialog.hide()
  if savingStatusLabel:
    savingStatusLabel.setText('')
  slicer.app.processEvents()


def loadAutoSave(caseName):
  slicer.util.loadScene(str(_autoSaveFilePath(caseName)))


def checkAutoSave(caseName='Default'):
  # construct autosave path
  print('Checking for autosave')
  import os
  if os.path.exists(_autoSaveDirectory(caseName)):
    print('Autosave found')
    reloadAutoSaveDialog = qt.QMessageBox(qt.QMessageBox.Information, "Reload autosave?",
      "An autosave has been found, would you like to reload it?", qt.QMessageBox.Yes | qt.QMessageBox.Discard)
    ret = reloadAutoSaveDialog.exec()
    if ret == qt.QMessageBox.Yes:
      print('reloading autosave')
      slicer.util.loadScene(str(_autoSaveFilePath(caseName)))
    else:
      print('Skip loading autosave, discarding old autosave')
      deleteAutoSave(caseName)


def savePlan():
  default_dir = qt.QStandardPaths.writableLocation(qt.QStandardPaths.DocumentsLocation)

  dialog = qt.QFileDialog()
  plan_path = dialog.getSaveFileName(
    slicer.util.mainWindow(),
    'Save OpenNav Plan',
    default_dir,
    '*.mrb',
  )
  if not plan_path:
    return

  plan_path = pathlib.Path(plan_path)
  if plan_path.suffix != '.mrb':
    plan_path = plan_path.with_suffix('.mrb')

  print(f'saving plan: {plan_path}')

  slicer.util.saveScene(str(plan_path))


def listAvailablePlans():
  print('Available plans:')

  caseNames = []

  if os.path.exists(_casesDirectory()):
    caseNames = next(os.walk(_casesDirectory()))[1]

  print(caseNames)

  plansWithDates = []
  for case in caseNames:
    if os.path.exists(_autoSaveFilePath(case)):
      mtime = os.path.getmtime(_autoSaveFilePath(case))
      plansWithDates.append((case, mtime))

  plansWithDates.sort(key = lambda x: x[1], reverse=True)

  return plansWithDates


def _screenShotDirectory(caseName):
  return os.path.join(_autoSaveDirectory(caseName), 'ScreenShots')


def _screenShotFilePath(caseName, timestamp):
  formattedTimeStamp = timestamp.strftime('%Y-%m-%d_T%H-%M-%S')
  fileName = 'ScreenShot-' + formattedTimeStamp + '.png'
  return os.path.join(_screenShotDirectory(caseName), fileName)


def _ensureScreenShotDirectoriesExist(caseName):
  # Create all directories in tree recursively
  if not os.path.exists(_screenShotDirectory(caseName)):
    os.makedirs(_screenShotDirectory(caseName))


def saveScreenShotViewersOnly(caseName):
  _ensureScreenShotDirectoriesExist(caseName)
  import ScreenCapture
  cap = ScreenCapture.ScreenCaptureLogic()
  cap.captureImageFromView(None, _screenShotFilePath(caseName, datetime.datetime.now()))
  qt.QMessageBox.information(slicer.util.mainWindow(), 'Screenshot saved!', 'Screenshot saved!')


def saveScreenShot(caseName):
  _ensureScreenShotDirectoriesExist(caseName)
  p = slicer.util.mainWindow().grab()
  p.save(_screenShotFilePath(caseName, datetime.datetime.now()), 'png')
  qt.QMessageBox.information(slicer.util.mainWindow(), 'Screenshot saved!', 'Screenshot saved!')


def openCasesDirectoryInExplorer():
  path = _casesDirectory()
  os.system('explorer.exe ' + path)
