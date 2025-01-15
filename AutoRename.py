# Function: IDA script plugin, auto rename for all (Functions, Names) symbols
# Author: Crifan Li
# Update: 20250115

import re
import os
import json

import os
from datetime import datetime,timedelta
from datetime import time  as datetimeTime
# import time
import codecs
import copy

import logging

import idc
import idaapi
import idautils
import ida_nalt
import ida_segment
import ida_name
import ida_bytes
import ida_funcs

################################################################################
# Document
################################################################################

# IDA Python API:
#   https://www.hex-rays.com/products/ida/support/idapython_docs/index.html
#
#   idc
#     https://hex-rays.com//products/ida/support/idapython_docs/idc.html
#   ida_name
#     https://hex-rays.com/products/ida/support/idapython_docs/ida_name.html

################################################################################
# Config & Settings & Const
################################################################################

logUsePrint = True
logUseLogging = False
# logUsePrint = False
# logUseLogging = True # Note: current will 1 log output 7 log -> maybe IDA bug, so temp not using logging

logLevel = logging.INFO
# logLevel = logging.DEBUG # for debug

# from selector string to find (ObjC Class) id type
isGenerateIdType = True
# isGenerateIdType = False

# isFailForUnsupportInstruction = False
isFailForUnsupportInstruction = True

# export result to json file
# isExportResult = False
isExportResult = True

if isExportResult:
  outputFolder = None
  # outputFolder = "/Users/crifan/dev/dev_root/crifan/github/AutoRename/debug"

SINGLE_INSTRUCTION_SIZE = 4 # bytes
# for rename, the max number of instruction to support
# MAX_INSTRUCTION_NUM = 6
MAX_INSTRUCTION_NUM = 8
MAX_INSTRUCTION_SIZE = MAX_INSTRUCTION_NUM * SINGLE_INSTRUCTION_SIZE

################################################################################
# Util Function
################################################################################

# Update: 20250115
class CommonUtil:

  CURRENT_LIB_FILENAME = "crifanLogging"

  LOG_FORMAT_FILE = "%(asctime)s %(filename)s:%(lineno)-4d %(levelname)-7s %(message)s"
  # https://docs.python.org/3/library/time.html#time.strftime
  LOG_FORMAT_FILE_DATETIME = "%Y/%m/%d %H:%M:%S"
  LOG_LEVEL_FILE = logging.DEBUG
  LOG_FORMAT_CONSOLE = "%(asctime)s %(filename)s:%(lineno)-4d %(levelname)-7s %(message)s"
  LOG_FORMAT_CONSOLE_DATETIME = "%Y%m%d %H:%M:%S"
  LOG_LEVEL_CONSOLE = logging.INFO
  # LOG_LEVEL_CONSOLE = logging.DEBUG

  def loggingInit(filename = None,
                  fileLogLevel = LOG_LEVEL_FILE,
                  fileLogFormat = LOG_FORMAT_FILE,
                  fileLogDateFormat = LOG_FORMAT_FILE_DATETIME,
                  enableConsole = True,
                  consoleLogLevel = LOG_LEVEL_CONSOLE,
                  consoleLogFormat = LOG_FORMAT_CONSOLE,
                  consoleLogDateFormat = LOG_FORMAT_CONSOLE_DATETIME,
                  ):
      """
      init logging for both log to file and console

      :param filename: input log file name
          if not passed, use current lib filename
      :return: none
      """
      logFilename = ""
      if filename:
          logFilename = filename
      else:
          # logFilename = __file__ + ".log"
          # '/Users/crifan/dev/dev_root/xxx/crifanLogging.py.log'
          logFilename = CommonUtil.CURRENT_LIB_FILENAME + ".log"

      # logging.basicConfig(
      #                 level    = fileLogLevel,
      #                 format   = fileLogFormat,
      #                 datefmt  = fileLogDateFormat,
      #                 filename = logFilename,
      #                 encoding = "utf-8",
      #                 filemode = 'w')

      # rootLogger = logging.getLogger()
      rootLogger = logging.getLogger("")
      rootLogger.setLevel(fileLogLevel)
      fileHandler = logging.FileHandler(
          filename=logFilename,
          mode='w',
          encoding="utf-8")
      fileHandler.setLevel(fileLogLevel)
      fileFormatter = logging.Formatter(
          fmt=fileLogFormat,
          datefmt=fileLogDateFormat
      )
      fileHandler.setFormatter(fileFormatter)
      rootLogger.addHandler(fileHandler)

      if enableConsole :
          # define a Handler which writes INFO messages or higher to the sys.stderr
          console = logging.StreamHandler()
          console.setLevel(consoleLogLevel)
          # set a format which is simpler for console use
          consoleFormatter = logging.Formatter(
              fmt=consoleLogFormat,
              datefmt=consoleLogDateFormat)
          # tell the handler to use this format
          console.setFormatter(consoleFormatter)
          rootLogger.addHandler(console)

  def log_print(formatStr, *paraTuple):
    if paraTuple:
      print(formatStr % paraTuple)
    else:
      print(formatStr)

  def logInfo(formatStr, *paraTuple):
    if logUsePrint:
      if logLevel <= logging.INFO:
        CommonUtil.log_print(formatStr, *paraTuple)

    if logUseLogging:
      logging.info(formatStr, *paraTuple)

  def logDebug(formatStr, *paraTuple):
    if logUsePrint:
      if logLevel <= logging.DEBUG:
        CommonUtil.log_print(formatStr, *paraTuple)
    
    if logUseLogging:
      logging.debug(formatStr, *paraTuple)

  def logMainStr(mainStr):
    mainDelimiter = "="*40
    # print("%s %s %s" % (mainDelimiter, mainStr, mainDelimiter))
    CommonUtil.logInfo("%s %s %s", mainDelimiter, mainStr, mainDelimiter)

  def logSubStr(subStr):
    subDelimiter = "-"*30
    # print("%s %s %s" % (subDelimiter, subStr, subDelimiter))
    CommonUtil.logDebug("%s %s %s", subDelimiter, subStr, subDelimiter)
    # CommonUtil.logInfo("%s %s %s", subDelimiter, subStr, subDelimiter)

  def logSubSubStr(subStr):
    subsubDelimiter = "-"*20
    # print("%s %s %s" % (subsubDelimiter, subStr, subsubDelimiter))
    CommonUtil.logDebug("%s %s %s", subsubDelimiter, subStr, subsubDelimiter)
    # CommonUtil.logInfo("%s %s %s", subsubDelimiter, subStr, subsubDelimiter)

  def datetimeToStr(inputDatetime, format="%Y%m%d_%H%M%S"):
      """Convert datetime to string

      Args:
          inputDatetime (datetime): datetime value
      Returns:
          str
      Raises:
      Examples:
          datetime.datetime(2020, 4, 21, 15, 44, 13, 2000) -> '20200421_154413'
      """
      datetimeStr = inputDatetime.strftime(format=format)
      # print("inputDatetime=%s -> datetimeStr=%s" % (inputDatetime, datetimeStr)) # 2020-04-21 15:08:59.787623
      return datetimeStr

  def getCurDatetimeStr(outputFormat="%Y%m%d_%H%M%S"):
      """
      get current datetime then format to string

      eg:
          20171111_220722

      :param outputFormat: datetime output format
      :return: current datetime formatted string
      """
      curDatetime = datetime.now() # 2017-11-11 22:07:22.705101
      # curDatetimeStr = curDatetime.strftime(format=outputFormat) #'20171111_220722'
      curDatetimeStr = CommonUtil.datetimeToStr(curDatetime, format=outputFormat)
      return curDatetimeStr

  def loadTextFromFile(fullFilename, fileEncoding="utf-8"):
    """load file text content from file"""
    with codecs.open(fullFilename, 'r', encoding=fileEncoding) as fp:
      allText = fp.read()
      # logging.debug("Complete load text from %s", fullFilename)
      return allText

  def saveJsonToFile(fullFilename, jsonValue, indent=2, fileEncoding="utf-8"):
      """
          save json dict into file
          for non-ascii string, output encoded string, without \\u xxxx
      """
      with codecs.open(fullFilename, 'w', encoding=fileEncoding) as jsonFp:
          json.dump(jsonValue, jsonFp, indent=indent, ensure_ascii=False)
          # logging.debug("Complete save json %s", fullFilename)

  def listSubfolderFiles(subfolder, isIncludeFolder=True, isRecursive=False):
    """os.listdir recursively

    Args:
        subfolder (str): sub folder path
        isIncludeFolder (bool): whether is include folder. Default is True. If True, result contain folder
        isRecursive (bool): whether is recursive, means contain sub folder. Default is False
    Returns:
        list of str
    Raises:
    """
    allSubItemList = []
    curSubItemList = os.listdir(path=subfolder)
    print("len(curSubItemList)=%d, curSubItemList=%s" % (len(curSubItemList), curSubItemList))
    for curSubItem in curSubItemList:
      print("curSubItem=%s" % curSubItem)
      curSubItemFullPath = os.path.join(subfolder, curSubItem)
      print("curSubItemFullPath=%s" % curSubItemFullPath)
      if os.path.isfile(curSubItemFullPath):
        print("is file for: %s" % curSubItemFullPath)
        allSubItemList.append(curSubItemFullPath)
      else:
        print("NOT file for: %s" % curSubItemFullPath)
        if isIncludeFolder:
          if os.path.isdir(curSubItemFullPath):
            subSubItemList = CommonUtil.listSubfolderFiles(curSubItemFullPath, isIncludeFolder, isRecursive)
            allSubItemList.extend(subSubItemList)

    if isIncludeFolder:
      allSubItemList.append(subfolder)

    return allSubItemList

  def createFolder(folderFullPath):
    """
      create folder, even if already existed
      Note: for Python 3.2+
    """
    os.makedirs(folderFullPath, exist_ok=True)

# Update: 20250115
class ARMUtil:
  ArmSpecialRegNameList = [
    "SB",
    "TR",
    "XR",
    "IP",
    "IP0",
    "IP1",
    "PR",
    "SP",
    "FP",
    "LR",
    "PC",
  ]

  PrologueEpilogueRegList = [
    "X19",
    "X20",
    "X21",
    "X22",
    "X23",
    "X24",
    "X25",
    "X26",
    "X27",
    "X28",
    "X29",
    "X30",

    "D8",
    "D9",
  ]

# Update: 20250115
class IDAUtil:
  # IDA Python API:
  #   https://www.hex-rays.com/products/ida/support/idapython_docs/index.html
  #
  #   idc
  #     https://hex-rays.com//products/ida/support/idapython_docs/idc.html
  #   ida_name
  #     https://hex-rays.com/products/ida/support/idapython_docs/ida_name.html


  IdaReservedStr = [
    "class",
    "id",
    "const",
    "char",
    "void",
    "return",
    "private",
    "namespace",
    "catch",
    "do",
    "while",
    "new",
    "default",
    "for",
  ]

  # for rename
  funcNameP_X29X30_STP = r"_(?P<stpName>X29X30ToSPOff[^_]+)"
  funcNameP_X29X30_LDP = r"_(?P<ldpName>SPOff[^_]+ToX29X30)"

  #-------------------------------------------------------------------------------
  # iOS Util Function
  #-------------------------------------------------------------------------------

  def ida_getFunctionComment(idaAddr, repeatable=False):
    """
    Get function comment
    """
    # funcStruct = ida_funcs.get_func(idaAddr)
    # print("[0x%X] -> funcStruct=%s" % (idaAddr, funcStruct))
    # curFuncCmt = ida_funcs.get_func_cmt(funcStruct, repeatable)
    curFuncCmt = idc.get_func_cmt(idaAddr, repeatable)
    # print("[0x%X] -> curFuncCmt=%s" % (idaAddr, curFuncCmt))
    return curFuncCmt

  def ida_setFunctionComment(idaAddr, newComment, repeatable=False):
    """
    Set function comment
    """
    setCmtRet = idc.set_func_cmt(idaAddr, newComment, repeatable)
    # print("[0x%X] -> setCmtRet=%s" % (idaAddr, setCmtRet))
    return setCmtRet

  def ida_setComment(idaAddr, commentStr, repeatable=False):
    """
    Set comment for ida address
    """
    isSetCmtOk = ida_bytes.set_cmt(idaAddr, commentStr, repeatable)
    # print("set_cmt: [0x%X] commentStr=%s -> isSetCmtOk=%s" % (idaAddr, commentStr, isSetCmtOk))
    return isSetCmtOk

  # setCmtAddr = 0xF35794
  # # # setCmtAddr = 0xF35798
  # # commentStr = "-[WamEventBotJourney is_ui_surface_set], -[WamEventCallUserJourney is_ui_surface_set], -[WamEventGroupJourney is_ui_surface_set], -[WamEventIncallParticipantPickerShown is_ui_surface_set], -[WamEventSelectParticipantFromPicker is_ui_surface_set]"
  # # # commentStr = ""
  # # # ida_setComment(setCmtAddr, commentStr)
  # # newFuncCmt = commentStr
  # # oldFuncCmt = ida_getFunctionComment(setCmtAddr)
  # # print("oldFuncCmt=%s" % oldFuncCmt)
  # # if oldFuncCmt:
  # #   newFuncCmt = "%s\n%s" % (oldFuncCmt, newFuncCmt)
  # # print("newFuncCmt=%s" % newFuncCmt)
  # # setCmdRet = ida_setFunctionComment(setCmtAddr, newFuncCmt)
  # setCmdRet = ida_setFunctionComment(setCmtAddr, "")
  # print("setCmdRet=%s" % setCmdRet)
  # ssssss

  def ida_getXrefsToList(idaAddr):
    """
    get XrefsTo info dict list from ida address
    eg:
      0x139CFBF -> [{'type': 1, 'typeName': 'Data_Offset', 'isCode': 0, 'from': 26301800, 'to': 20565951}]
    """
    xrefToInfoDictList = []
    refToGenerator = idautils.XrefsTo(idaAddr)
    # print("refToGenerator=%s" % refToGenerator)
    for eachXrefTo in refToGenerator:
      # print("eachXrefTo=%s" % eachXrefTo)
      xrefType = eachXrefTo.type
      # print("xrefType=%s" % xrefType)
      xrefTypeName = idautils.XrefTypeName(xrefType)
      # print("xrefTypeName=%s" % xrefTypeName)
      xrefIsCode = eachXrefTo.iscode
      # print("xrefIsCode=%s" % xrefIsCode)
      xrefFrom = eachXrefTo.frm
      # print("xrefFrom=0x%X" % xrefFrom)
      xrefTo = eachXrefTo.to
      # print("xrefTo=0x%X" % xrefTo)
      curXrefToInfoDict = {
        "type": xrefType,
        "typeName": xrefTypeName,
        "isCode": xrefIsCode,
        "from": xrefFrom,
        "to": xrefTo,
      }
      xrefToInfoDictList.append(curXrefToInfoDict)
    # print("idaAddr=0x%X -> xrefToInfoDictList=%s" % (idaAddr, xrefToInfoDictList))
    return xrefToInfoDictList

  def findClassFromSelector(selectorStr):
    """
    find ObjC Class name (and function name) from selector string
    eg:
      "setCellsEligibleForExpansion:" -> [{'objcClassName': 'WAAccordionTableView', 'objcFuncName': '-[WAAccordionTableView setCellsEligibleForExpansion:]'}]
    """
    foundItemList = []

    # idaSelStr = re.sub(":", "_", selectorStr)
    # idaSelStr = "sel_%s" % idaSelStr
    idaSelStr = "sel_%s" % selectorStr
    CommonUtil.logDebug("idaSelStr=%s", idaSelStr)
    # idaAddr = ida_name.get_name_ea(idaSelStr)
    idaAddr = idc.get_name_ea_simple(idaSelStr)
    CommonUtil.logDebug("idaAddr=0x%X", idaAddr)

    # realAddr = 0x139CFA1
    # foundObjcMethname = idc.get_name(realAddr)
    # logDebug("realAddr=0x%X -> foundObjcMethname=%s" % (realAddr, foundObjcMethname))

    # refToGenerator = idautils.XrefsTo(idaAddr)
    # logDebug("refToGenerator=%s" % refToGenerator)
    # for eachXrefTo in refToGenerator:
    xrefToInfoDictList = IDAUtil.ida_getXrefsToList(idaAddr)
    CommonUtil.logDebug("xrefToInfoDictList=%s", xrefToInfoDictList)
    for eachXrefToInfoDict in xrefToInfoDictList:
      CommonUtil.logDebug("eachXrefToInfoDict=%s" % eachXrefToInfoDict)
      xrefFrom = eachXrefToInfoDict["from"]
      CommonUtil.logDebug("xrefFrom=%s" % xrefFrom)

      CommonUtil.logDebug("--- Xref From [0x%X] ---" % xrefFrom)
      xrefFromName = idc.get_name(xrefFrom)
      CommonUtil.logDebug("xrefFromName=%s" % xrefFromName)
      # xrefFromType = idc.get_type(xrefFrom)
      # logDebug("xrefFromType=%s" % xrefFromType)
      # xrefFromTinfo = idc.get_tinfo(xrefFrom)
      # logDebug("xrefFromTinfo=%s" % xrefFromTinfo)
      xrefFromSegName = idc.get_segm_name(xrefFrom)
      CommonUtil.logDebug("xrefFromSegName=%s" % xrefFromSegName)
      xrefFromItemSize = idc.get_item_size(xrefFrom)
      CommonUtil.logDebug("xrefFromItemSize=%s" % xrefFromItemSize)

      # (1) __objc_const:000000000183B5F8  __objc2_meth <sel_setCellsEligibleForExpansion_, aV240816_3, \ ;-[WAAccordionTableView setCellsEligibleForExpansion:] ...
      #     __objc_const:000000000183B5F8  __WAAccordionTableView_setCellsEligibleForExpansion__>
      # isValidObjcSegment = xrefFromSegName == "__objc_const"
      # (2) __objc_data:00000000019C8F18                 __objc2_meth <sel_initWithDependencyInversion_, a240816_5, \ ; -[WAContext initWithDependencyInversion:] ...
      #     __objc_data:00000000019C8F18                               __WAContext_initWithDependencyInversion__>
      isValidObjcSegment = (xrefFromSegName == "__objc_const") or (xrefFromSegName == "__objc_data")
      CommonUtil.logDebug("isValidObjcSegment=%s" % isValidObjcSegment)
      Objc2MethSize = 24
      isObjcMethodSize = xrefFromItemSize == Objc2MethSize
      CommonUtil.logDebug("isObjcMethodSize=%s" % isObjcMethodSize)
      isObjcConstMeth = isValidObjcSegment and isObjcMethodSize
      CommonUtil.logDebug("isObjcConstMeth=%s" % isObjcConstMeth)

      if isObjcConstMeth:
        # methodSignatureAddr = xrefFrom + 0x8
        # logDebug("methodSignatureAddr=0x%X" % methodSignatureAddr)
        # isRepeatable = False
        # xrefFromCmt = ida_bytes.get_cmt(xrefFrom, isRepeatable)
        # logDebug("xrefFromCmt=%s" % xrefFromCmt)
        # methodSignatureCmt = ida_bytes.get_cmt(methodSignatureAddr, isRepeatable)
        # logDebug("methodSignatureCmt=%s" % methodSignatureCmt)

        methodImplementAddr = xrefFrom + 0x10
        CommonUtil.logDebug("methodImplementAddr=0x%X" % methodImplementAddr)
        methodImplementValueAddr = ida_bytes.get_qword(methodImplementAddr)
        CommonUtil.logDebug("methodImplementValueAddr=0x%X" % methodImplementValueAddr)
        objcMethodName = None
        methodImplementValueName = idc.get_name(methodImplementValueAddr)
        CommonUtil.logDebug("methodImplementValueName=%s" % methodImplementValueName)
        if methodImplementValueName:
          objcMethodName = methodImplementValueName
        else:
          methodImplementValueFuncName = idc.get_func_name(methodImplementValueAddr)
          CommonUtil.logDebug("methodImplementValueFuncName=%s" % methodImplementValueFuncName)
          objcMethodName = methodImplementValueFuncName
        
        if objcMethodName:
          isObjcFuncName, isClass, foundClassName, foundSelectorStr = IDAUtil.isObjcFunctionName(objcMethodName)
          CommonUtil.logDebug("objcMethodName=%s -> isObjcFuncName=%s, isClass=%s, foundClassName=%s, selectorStr=%s" % (objcMethodName, isObjcFuncName, isClass, foundClassName, foundSelectorStr))
          if isObjcFuncName:
            if selectorStr == foundSelectorStr:
              className = foundClassName
              # break
              curItemDict = {
                "objcClassName": className,
                "objcFuncName": objcMethodName,
              }
              foundItemList.append(curItemDict)
              CommonUtil.logDebug("foundItemList=%s" % foundItemList)

    CommonUtil.logDebug("selectorStr=%s -> foundItemList=%s" % (selectorStr, foundItemList))
    return foundItemList

  # # # selectorStr = "setCellsEligibleForExpansion:"
  # # # selectorStr = "setCenter:"
  # # # selectorStr = "sameDeviceCheckRequestURLWithOfflineExposures:offlineMetrics:pushToken:tokenReadError:"
  # # # selectorStr = "initWithDependencyInversion:" # -[WAContext initWithDependencyInversion:]
  # # # selectorStr = "getChannel" # total 736
  # # # # -[WamEventAutoupdateSetupAction getChannel]
  # # # # -[WamEventAvatarBloksLaunch getChannel]
  # selectorStr = "setQuery:"
  # # -[FMStatement setQuery:]
  # # -[FMResultSet setQuery:]
  # foundItemList = findClassFromSelector(selectorStr)
  # print("selectorStr=%s -> foundItemList: %s, count=%d" % (selectorStr, foundItemList, len(foundItemList)))
  # sssss

  ################################################################################
  # IDA Util Function
  ################################################################################

  #-------------------- need call IDA api --------------------

  def ida_getInfo():
    """
    get IDA info
    """
    info = idaapi.get_inf_structure()
    # print("info=%s" % info)
    return info

  def ida_printInfo(info):
    """
    print IDA info
    """
    version = info.version
    print("version=%s" % version)
    is64Bit = info.is_64bit()
    print("is64Bit=%s" % is64Bit)
    procName = info.procname
    print("procName=%s" % procName)
    entryPoint = info.start_ea
    print("entryPoint=0x%X" % entryPoint)
    baseAddr = info.baseaddr
    print("baseAddr=0x%X" % baseAddr)

  def ida_printAllImports():
    """
    print all imports lib and functions inside lib"""
    nimps = ida_nalt.get_import_module_qty()
    print("Found %d import(s)..." % nimps)
    for i in range(nimps):
      name = ida_nalt.get_import_module_name(i)
      if not name:
        print("Failed to get import module name for [%d] %s" % (i, name))
        name = "<unnamed>"
      else:
        print("[%d] %s" % (i, name))

      def imp_cb(ea, name, ordinal):
          if not name:
              print("%08x: ordinal #%d" % (ea, ordinal))
          else:
              print("%08x: %s (ordinal #%d)" % (ea, name, ordinal))
          # True -> Continue enumeration
          # False -> Stop enumeration
          return True
      ida_nalt.enum_import_names(i, imp_cb)

  def ida_printSegment(curSeg):
    """
    print segment info
      Note: in IDA, segment == section
    """
    segName = curSeg.name
    # print("type(segName)=%s" % type(segName))
    segSelector = curSeg.sel
    segStartAddr = curSeg.start_ea
    segEndAddr = curSeg.end_ea
    print("Segment: [0x%X-0x%X] name=%s, selector=%s : seg=%s" % (segStartAddr, segEndAddr, segName, segSelector, curSeg))

  def ida_getSegmentList():
    """
    get segment list
    """
    segList = []
    segNum = ida_segment.get_segm_qty()
    for segIdx in range(segNum):
      curSeg = ida_segment.getnseg(segIdx)
      # print("curSeg=%s" % curSeg)
      segList.append(curSeg)
      # ida_printSegment(curSeg)
    return segList

  def ida_testGetSegment():
    """
    test get segment info
    """
    # textSeg = ida_segment.get_segm_by_name("__TEXT")
    # dataSeg = ida_segment.get_segm_by_name("__DATA")

    # ida_getSegmentList()

    # NAME___TEXT = "21"
    # NAME___TEXT = 21
    # NAME___TEXT = "__TEXT,__text"
    # NAME___TEXT = "__TEXT:__text"
    # NAME___TEXT = ".text"

    """
      __TEXT,__text
      __TEXT,__stubs
      __TEXT,__stub_helper
      __TEXT,__objc_stubs
      __TEXT,__const
      __TEXT,__objc_methname
      __TEXT,__cstring
      __TEXT,__swift5_typeref
      __TEXT,__swift5_protos
      __TEXT,__swift5_proto
      __TEXT,__swift5_types
      __TEXT,__objc_classname
      __TEXT,__objc_methtype
      __TEXT,__gcc_except_tab
      __TEXT,__ustring
      __TEXT,__unwind_info
      __TEXT,__eh_frame
      __TEXT,__oslogstring

      __DATA,__got
      __DATA,__la_symbol_ptr
      __DATA,__mod_init_func
      __DATA,__const
      __DATA,__cfstring
      __DATA,__objc_classlist
      __DATA,__objc_catlist
      __DATA,__objc_protolist
      __DATA,__objc_imageinfo
      __DATA,__objc_const
      __DATA,__objc_selrefs
      __DATA,__objc_protorefs
      __DATA,__objc_classrefs
      __DATA,__objc_superrefs
      __DATA,__objc_ivar
      __DATA,__objc_data
      __DATA,__data
      __DATA,__objc_stublist
      __DATA,__swift_hooks
      __DATA,__swift51_hooks
      __DATA,__s_async_hook
      __DATA,__swift56_hooks
      __DATA,__thread_vars
      __DATA,__thread_bss
      __DATA,__bss
      __DATA,__common
    """

    # __TEXT,__text
    NAME___text = "__text"
    textSeg = ida_segment.get_segm_by_name(NAME___text)
    print("textSeg: %s -> %s" % (NAME___text, textSeg))
    IDAUtil.ida_printSegment(textSeg)

    # __TEXT,__objc_methname
    NAME___objc_methname = "__objc_methname"
    objcMethNameSeg = ida_segment.get_segm_by_name(NAME___objc_methname)
    print("objcMethNameSeg: %s -> %s" % (NAME___objc_methname, objcMethNameSeg))
    IDAUtil.ida_printSegment(objcMethNameSeg)

    # __DATA,__got
    NAME___got = "__got"
    gotSeg = ida_segment.get_segm_by_name(NAME___got)
    print("gotSeg: %s -> %s" % (NAME___got, gotSeg))
    IDAUtil.ida_printSegment(gotSeg)

    # __DATA,__data
    # NAME___DATA = "22"
    # NAME___DATA = 22
    NAME___DATA = "__data"
    dataSeg = ida_segment.get_segm_by_name(NAME___DATA)
    print("dataSeg: %s -> %s" % (NAME___DATA, dataSeg))
    IDAUtil.ida_printSegment(dataSeg)

    # exist two one: __TEXT,__const / __DATA,__const
    NAME___const = "__const"
    constSeg = ida_segment.get_segm_by_name(NAME___const)
    print("constSeg: %s -> %s" % (NAME___const, constSeg))
    IDAUtil.ida_printSegment(constSeg)

  def ida_getDemangledName(origSymbolName):
    """
    use IDA to get demangled name for original symbol name
    """
    retName = origSymbolName
    # demangledName = idc.demangle_name(origSymbolName, idc.get_inf_attr(idc.INF_SHORT_DN))
    # https://hex-rays.com/products/ida/support/ida74_idapython_no_bc695_porting_guide.shtml
    demangledName = idc.demangle_name(origSymbolName, idc.get_inf_attr(idc.INF_SHORT_DEMNAMES))
    if demangledName:
      retName = demangledName

    # do extra post process:
    # remove/replace invalid char for non-objc function name
    isNotObjcFuncName = not IDAUtil.isObjcFunctionName(retName)
    # print("isNotObjcFuncName=%s" % isNotObjcFuncName)
    if isNotObjcFuncName:
      retName = retName.replace("?", "")
      retName = retName.replace(" ", "_")
      retName = retName.replace("*", "_")
    # print("origSymbolName=%s -> retName=%s" % (origSymbolName, retName))
    return retName

  def ida_getFunctionEndAddr(funcAddr):
    """
    get function end address
      Example:
        0x1023A2534 -> 0x1023A2540
    """
    funcAddrEnd = idc.get_func_attr(funcAddr, attr=idc.FUNCATTR_END)
    return funcAddrEnd

  def ida_getFunctionSize(funcAddr):
    """
    get function size
      Example:
        0x1023A2534 -> 12
    """
    funcAddrEnd = idc.get_func_attr(funcAddr, attr=idc.FUNCATTR_END)
    funcAddStart = idc.get_func_attr(funcAddr, attr=idc.FUNCATTR_START)
    funcSize = funcAddrEnd - funcAddStart
    return funcSize

  def ida_getFunctionName(funcAddr):
    """
    get function name
      Exmaple:
        0x1023A2534 -> "sub_1023A2534"
        0xF9D260 -> "objc_msgSend$initWithKeyValueStore_namespace_binaryCoders_X22toX0_X23toX2_X24toX4_EF8C"
    """
    funcName = idc.get_func_name(funcAddr)
    return funcName

  def ida_getName(curAddr):
    """
    get name
      Exmaple:
        0xF9D260 -> "_objc_msgSend$initWithKeyValueStore:namespace:binaryCoders:"
    """
    addrName = idc.get_name(curAddr)
    return addrName

  def ida_getDisasmStr(funcAddr):
    """
    get disasmemble string
      Exmaple:
        0x1023A2534 -> "MOV X5, X0"
    """
    # method 1: generate_disasm_line
    # disasmLine_forceCode = idc.generate_disasm_line(funcAddr, idc.GENDSM_FORCE_CODE)
    # print("disasmLine_forceCode: type=%s, val=%s" % (type(disasmLine_forceCode), disasmLine_forceCode))
    # disasmLine_multiLine = idc.generate_disasm_line(funcAddr, idc.GENDSM_MULTI_LINE)
    # print("disasmLine_multiLine: type=%s, val=%s" % (type(disasmLine_multiLine), disasmLine_multiLine))

    # method 2: GetDisasm
    disasmLine = idc.GetDisasm(funcAddr)
    # print("disasmLine: type=%s, val=%s" % (type(disasmLine), disasmLine))

    # post process
    # print("disasmLine=%s" % disasmLine)
    # "MOV             X4, X21" -> "MOV X4, X21"
    disasmLine = re.sub("\s+", " ", disasmLine)
    # print("disasmLine=%s" % disasmLine)
    return disasmLine

  def ida_getFunctionAddrList():
    """
    get function address list
    """
    functionIterator = idautils.Functions()
    functionAddrList = []
    for curFuncAddr in functionIterator:
      functionAddrList.append(curFuncAddr)
    return functionAddrList

  def ida_rename(curAddr, newName, retryName=None):
    """
    rename <curAddr> to <newName>. if fail, retry with with <retryName> if not None
      Example:
        0x3B4E28, "X2toX21_X1toX20_X0toX19_4E28", "X2toX21_X1toX20_X0toX19_3B4E28" -> True, "X2toX21_X1toX20_X0toX19_4E28"
    """
    # print("curAddr=0x%X, newName=%s, retryName=%s" % (curAddr, newName, retryName))
    isRenameOk = False
    renamedName = None

    isOk = idc.set_name(curAddr, newName)
    # print("isOk=%s for [0x%X] -> %s" % (isOk, curAddr, newName))
    if isOk == 1:
      isRenameOk = True
      renamedName = newName
    else:
      if retryName:
        isOk = idc.set_name(curAddr, retryName)
        # print("isOk=%s for [0x%X] -> %s" % (isOk, curAddr, retryName))
        if isOk == 1:
          isRenameOk = True
          renamedName = retryName

    # print("isRenameOk=%s, renamedName=%s" % (isRenameOk, renamedName))
    return (isRenameOk, renamedName)

  def ida_getCurrentFolder():
    """
    get current folder for IDA current opened binary file
      Example:
        -> /Users/crifan/dev/dev_root/iosReverse/WhatsApp/ipa/Payload/WhatsApp.app
        -> /Users/crifan/dev/dev_root/iosReverse/WhatsApp/ipa/Payload/WhatsApp.app/Frameworks/SharedModules.framework
    """
    curFolder = None
    inputFileFullPath = ida_nalt.get_input_file_path()
    # print("inputFileFullPath=%s" % inputFileFullPath)
    if inputFileFullPath.startswith("/var/containers/Bundle/Application"):
      # inputFileFullPath=/var/containers/Bundle/Application/2BE964D4-8DF0-4858-A06D-66CA8741ACDC/WhatsApp.app/WhatsApp
      # -> maybe IDA bug -> after debug settings, output iOS device path, but later no authority to write exported file to it
      # so need to avoid this case, change to output to PC side (Mac) current folder
      curFolder = "."
    else:
      curFolder = os.path.dirname(inputFileFullPath)
    # print("curFolder=%s" % curFolder)

    # debugInputPath = ida_nalt.dbg_get_input_path()
    # print("debugInputPath=%s" % debugInputPath)

    curFolder = os.path.abspath(curFolder)
    # print("curFolder=%s" % curFolder)
    # here work:
    # . -> /Users/crifan/dev/dev_root/iosReverse/WhatsApp/ipa/Payload/WhatsApp.app
    return curFolder

  def isDefaultTypeForObjcMsgSendFunction(funcAddr):
    """
    check is objc_msgSend$xxx function's default type "id(void *, const char *, ...)" or not
    eg:
      0xF3EF8C -> True
        note: funcType=id(void *, const char *, __int64, __int64, ...)
    """
    isDefType = False
    funcType = idc.get_type(funcAddr)
    CommonUtil.logDebug("[0x%X] -> funcType=%s", funcAddr, funcType)
    if funcType:
      defaultTypeMatch = re.search("\.\.\.\)$", funcType)
      CommonUtil.logDebug("defaultTypeMatch=%s", defaultTypeMatch)
      isDefType = bool(defaultTypeMatch)
      CommonUtil.logDebug("isDefType=%s", isDefType)
    return isDefType

  #-------------------- not need call IDA api --------------------

  def isObjcFunctionName(funcName):
    """
    check is ObjC function name or not
    eg:
      "+[WAAvatarStringsActions editAvatar]" -> True, True, "WAAvatarStringsActions", "editAvatar"
      "-[ParentGroupInfoViewController initWithParentGroupChatSession:userContext:recentlyLinkedGroupJIDs:]" -> True, False, "ParentGroupInfoViewController", "initWithParentGroupChatSession:userContext:recentlyLinkedGroupJIDs:"
      "-[OKEvolveSegmentationVC proCard]_116" -> True, False, "OKEvolveSegmentationVC", "proCard"
      "-[WAAvatarStickerUpSellSupplementaryView .cxx_destruct]" -> True, False, "WAAvatarStickerUpSellSupplementaryView", ".cxx_destruct"
      "sub_10004C6D8" -> False, False, None, None
      "protocol witness for RawRepresentable.init(rawValue:) in conformance UIFont.FontWeight" -> False, False, None, None
    """
    isObjcFuncName = False
    isClass = False
    className = None
    selectorStr = None

    objcFuncMatch = re.match("^(?P<classChar>[\-\+])\[(?P<className>\w+) (?P<selectorStr>[\w\.\:]+)\]\w*$", funcName)
    # print("objcFuncMatch=%s" % objcFuncMatch)
    if objcFuncMatch:
      isObjcFuncName = True
      classChar = objcFuncMatch.group("classChar")
      # print("classChar=%s" % classChar)
      if classChar == "+":
        isClass = True
      className = objcFuncMatch.group("className")
      # print("className=%s" % className)
      selectorStr = objcFuncMatch.group("selectorStr")
      # print("selectorStr=%s" % selectorStr)

    # print("funcName=%s -> isObjcFuncName=%s, isClass=%s, className=%s, selectorStr=%s" % (funcName, isObjcFuncName, isClass, className, selectorStr))
    return isObjcFuncName, isClass, className, selectorStr

  def isObjcMsgSendFuncName(funcName):
    """
    check function name is _objc_msgSend$xxx or not
    eg:
      "_objc_msgSend$arrayByAddingObjectsFromArray:" -> True, "arrayByAddingObjectsFromArray:"
      "_objc_msgSend$addObject:_AB00" -> True, "addObject:_AB00"
      "objc_msgSend$initWithKeyValueStore_namespace_binaryCoders_X22toX0_X23toX2_X24toX4" -> True, "initWithKeyValueStore_namespace_binaryCoders_X22toX0_X23toX2_X24toX4"
    """
    isOjbcMsgSend = False
    selectorStr = None
    # _objc_msgSend$arrangedSubviews
    # _objc_msgSend$arrayByAddingObjectsFromArray:
    # _objc_msgSend$arrangeFromView:toView:progress:forwardDirection:
    # objcMsgSendMatch = re.match("^_*objc_msgSend\$(?P<selectorStr>[\w\:]+¸)$", funcName)
    # objcMsgSendMatch = re.match("^_*objc_msgSend\$(?P<selectorStr>[\w\:]+)(?P<renamedAddrSuffix>_[A-Za-z0-9]+)?$", funcName)
    objcMsgSendMatch = re.match("^_*objc_msgSend\$(?P<selectorStr>[\w\:]+)$", funcName)
    # print("objcMsgSendMatch=%s" % objcMsgSendMatch)
    if objcMsgSendMatch:
      selectorStr = objcMsgSendMatch.group("selectorStr")
      # print("selectorStr=%s" % selectorStr)
      isOjbcMsgSend = True
    # print("isOjbcMsgSend=%s, selectorStr=%s" % (isOjbcMsgSend, selectorStr))
    return isOjbcMsgSend, selectorStr

  def isFuncName_TypeMetadataAccessorForAppDelegate(funcName):
    """
    check function name is 'type metadata accessor for AppDelegate_N' or not
    eg:
      type metadata accessor for AppDelegate_5
    """
    isTypeMetadataAccessorForAppDelegate = re.match("type metadata accessor for AppDelegate", funcName)
    return isTypeMetadataAccessorForAppDelegate

  def isFuncName_STP(funcName):
    """
    check function name is contain STP, eg '_X29X30ToSPOffxxx' or not
    eg:
      "ZdlPv_X29X30ToSPOff0xFFFFFFFFFFFFFFF0Val_xxxx_0274" -> True, Match Object
    """
    isStp = False
    stpMatch = None
    stpMatch = re.search(IDAUtil.funcNameP_X29X30_STP, funcName)
    if stpMatch:
      isStp = True
    CommonUtil.logDebug("funcName=%s -> isStp=%s, stpMatch=%s", funcName, isStp, stpMatch)
    return isStp, stpMatch

  def isFuncName_LDP(funcName):
    """
    check function name is contain LDP, eg '_SPOffxxxToX29X30' or not
    eg:
      "ZdlPv_xxx_SPOff0x10ValToX29X30_0274" -> True, Match Object
    """
    isLdp = False
    ldpMatch = None
    ldpMatch = re.search(IDAUtil.funcNameP_X29X30_LDP, funcName)
    if ldpMatch:
      isLdp = True
    CommonUtil.logDebug("funcName=%s -> isLdp=%s, ldpMatch=%s", funcName, isLdp, ldpMatch)
    return isLdp, ldpMatch

  def isFuncName_STP_LDP(funcName):
    """
    check function name is 'ZdlPv_X29X30ToSPOff0xFFFFFFFFFFFFFFF0Val_SPToX29_PageAddr0xFA8000ToX8_X8Add0x760ToX8_X8Add0x8ToX1_BranchTonullsub_248_SPOff0x10ValToX29X30_0274' (which contain '_X29X30ToSPOffxxx', '_SPOffxxxToX29X30') or not
    eg:
      "ZdlPv_X29X30ToSPOff0xFFFFFFFFFFFFFFF0Val_SPToX29_PageAddr0xFA8000ToX8_X8Add0x760ToX8_X8Add0x8ToX1_BranchTonullsub_248_SPOff0x10ValToX29X30_0274" -> is match
    """
    # funcNameP_stp = re.search(IDAUtil.funcNameP_X29X30_STP, funcName)
    # isFuncName_stp = bool(funcNameP_stp)
    # funcNameP_ldp = re.search(IDAUtil.funcNameP_X29X30_LDP, funcName)
    # isFuncName_ldp = bool(funcNameP_ldp)
    isFuncName_stp, stpMatch = IDAUtil.isFuncName_STP(funcName)
    isFuncName_ldp, ldpMatch = IDAUtil.isFuncName_LDP(funcName)
    isFuncName_stp_ldp = isFuncName_stp or isFuncName_ldp
    CommonUtil.logDebug("isFuncName_stp_ldp=%s, isFuncName_stp=%s, isFuncName_ldp=%s", isFuncName_stp_ldp, isFuncName_stp, isFuncName_ldp)
    return isFuncName_stp_ldp

  def isFuncName_sub(funcName):
    """
    check is default sub_XXX function or not from name
    eg:
      sub_F332C0 -> True, "F332C0"
    """
    isSub = False
    addressStr = None
    # subMatch = re.match("^sub_[0-9A-Za-z]+$", funcName)
    subMatch = re.match("^sub_(?P<addressStr>[0-9A-Fa-f]+)$", funcName)
    # print("subMatch=%s" % subMatch)
    if subMatch:
      isSub = True
      addressStr = subMatch.group("addressStr")
    return isSub, addressStr

  def isFuncName_nullsub(funcName):
    """
    check is default nullsub_XXX function or not from name
    eg:
      nullsub_58 -> True, "58"
    """
    isNullsub = False
    suffixStr = None
    nullsubMatch = re.match("^nullsub_(?P<suffixStr>\w+)$", funcName)
    # print("nullsubMatch=%s" % nullsubMatch)
    if nullsubMatch:
      isNullsub = True
      suffixStr = nullsubMatch.group("suffixStr")
    return isNullsub, suffixStr

  def isReservedPrefix_locType(funcName):
    """
    check is reserved prefix loc_XXX / locret_XXX name or not
    eg:
      loc_100007A2C -> True, "100007A2C"
      locret_16A0 -> True, "16A0"
    """
    isLoc = False
    addressStr = None
    # locMatch = re.match("^loc_(?P<addressStr>[0-9A-Fa-f]+)$", funcName)
    locMatch = re.match("^loc(ret)?_(?P<addressStr>[0-9A-F]+)$", funcName)
    # print("locMatch=%s" % locMatch)
    if locMatch:
      isLoc = True
      addressStr = locMatch.group("addressStr")
    return isLoc, addressStr

  def isDefaultSubFunction(curAddr):
    """
    check is default sub_XXX function or not from address
    """
    isDefSubFunc = False
    curFuncName = IDAUtil.ida_getFunctionName(curAddr)
    # print("curFuncName=%s" % curFuncName)
    if curFuncName:
      isDefSubFunc, subAddStr = IDAUtil.isFuncName_sub(curFuncName)
    return isDefSubFunc, curFuncName

  def isObjcMsgSendFunction(curAddr):
    """
    check is default sub_XXX function or not from address
    """
    isObjcMsgSend = False
    curFuncName  = IDAUtil.ida_getFunctionName(curAddr)
    # print("curFuncName=%s" % curFuncName)
    if curFuncName:
      isObjcMsgSend, selectorStr = IDAUtil.isObjcMsgSendFuncName(curFuncName)
    return isObjcMsgSend, selectorStr

  def isFunc_TypeMetadataAccessorForAppDelegate(curAddr):
    """
    check is function type_metadata_accessor_for_AppDelegate or not from address
    """
    curFuncName = IDAUtil.ida_getFunctionName(curAddr)
    isTypeMetadataAccessorForAppDelegate = IDAUtil.isFuncName_TypeMetadataAccessorForAppDelegate(curFuncName)
    return isTypeMetadataAccessorForAppDelegate

  def isPrologueEpilogueReg(regName):
    """
    Check is Prologue/Epilogue register
    eg:
      "X28" -> True
      "D8" -> True
    """
    # print("regName=%s" % regName)
    regNameUpper = regName.upper()
    # print("regNameUpper=%s" % regNameUpper)
    isPrlgEplg = regNameUpper in ARMUtil.PrologueEpilogueRegList
    # print("isPrlgEplg=%s" % isPrlgEplg)
    return isPrlgEplg

  def isPrologueEpilogueOperand(curOperand):
    """
    Check is Prologue/Epilogue Operand
    eg:
      <Operand: op=X28,type=1,val=0x9D> -> True
    """
    isPrlgEplgOp = False
    opIsReg = curOperand.isReg()
    # print("opIsReg=%s" % opIsReg)
    if opIsReg:
      regName = curOperand.operand
      # print("regName=%s" % regName)
      isPrlgEplgOp = IDAUtil.isPrologueEpilogueReg(regName)

    # print("isPrlgEplgOp=%s" % isPrlgEplgOp)
    return isPrlgEplgOp

  def isAllPrologueStp(instructionList):
    """
    Check is all STP instruction of prologue
    eg:
      STP X28, X27, [SP,#arg_70]
    """
    isAllPrlgStp = True
    for eachInst in instructionList:
      # print("eachInst=%s" % eachInst)
      isStp = eachInst.isStp()
      if isStp:
        # check operand register match or not
        curOperands = eachInst.operands
        # print("curOperands=%s" % curOperands)
        operandNum = len(curOperands)
        # print("operandNum=%s" % operandNum)
        if operandNum == 3:
          operand1 = curOperands[0]
          operand2 = curOperands[1]
          # print("operand1=%s, operand2=%s" % (operand1, operand2))
    
          # # for debug
          # operand3 = curOperands[2]
          # print("operand3=%s" % operand3)
    
          op1IsPrlgEplg = IDAUtil.isPrologueEpilogueOperand(operand1)
          op2IsPrlgEplg = IDAUtil.isPrologueEpilogueOperand(operand2)
          # print("op1IsPrlgEplg=%s, op2IsPrlgEplg=%s" % (op1IsPrlgEplg, op2IsPrlgEplg))
          isAllPrlgStp = op1IsPrlgEplg and op2IsPrlgEplg
        else:
          isAllPrlgStp = False  
      else:
        isAllPrlgStp = False
        break

    # print("isAllPrlgStp=%s" % isAllPrlgStp)
    return isAllPrlgStp

  def isRenamedFunctionName(funcName):
    """
    check is has renamed function name or not
    eg:
      "getMap_recordNumber_SFI_recordValue_B6400" -> True,"B6400"
      "_objc_msgSend$_fileNameUrlForProvider_fileName_withExtension_private__DD20" -> True,"_DD20"
      "_objc_msgSend$_fileWriteOptions" -> False,""
    """
    isRenamed = False
    addrSuffix = ""

    isSubFunc, addressStr = IDAUtil.isFuncName_sub(funcName)
    print("isSubFunc=%s, addressStr=%s" % (isSubFunc, addressStr))

    if not isSubFunc:
      addrSuffixMatch = re.search(".+(?P<addrSuffix>_[A-Z0-9]{4,20})$", funcName)
      # print("addrSuffixMatch=%s" % addrSuffixMatch)
      isRenamed = bool(addrSuffixMatch)
      # print("isRenamed=%s" % isRenamed)
      if addrSuffixMatch:
        addrSuffix = addrSuffixMatch.group("addrSuffix")
        # print("addrSuffix=%s" % addrSuffix)

    return isRenamed, addrSuffix

  def removeFuncNameAddressSuffixIfExist(funcName):
    """
    remove address suffix if exist
    eg:
      "_objc_msgSend$initWithKeyValueStore:namespace:error:_D280" -> "_objc_msgSend$initWithKeyValueStore:namespace:error:"
      "objc_msgSend$copyItemAtPath_toPath_error_X22toX0_X24toX2_X25toX3_EFB4" -> "objc_msgSend$copyItemAtPath_toPath_error_X22toX0_X24toX2_X25toX3"
    """
    funcNameNoAddrSuffix = re.sub("_[A-Z0-9]{4,20}$", "", funcName)
    # print("funcName=%s -> funcNameNoAddrSuffix=%s" % (funcName, funcNameNoAddrSuffix))
    return funcNameNoAddrSuffix


# Update: 20250115
class OperandType:
  # Operand Type
  # old doc: 
  #   https://hex-rays.com/products/ida/support/idapython_docs/idc.html#idc.get_operand_value
  # new doc: 
  #   https://cpp.docs.hex-rays.com/group__o__.html
  #   https://docs.hex-rays.com/developer-guide/idc/idc-api-reference/alphabetical-list-of-idc-functions/276
  o_void     = 0        # No Operand                           ----------
  o_reg      = 1        # General Register (al,ax,es,ds...)    reg
  o_mem      = 2        # Direct Memory Reference  (DATA)      addr
  o_phrase   = 3        # Memory Ref [Base Reg + Index Reg]    phrase
  o_displ    = 4        # Memory Reg [Base Reg + Index Reg + Displacement] phrase+addr
  o_imm      = 5        # Immediate Value                      value
  o_far      = 6        # Immediate Far Address  (CODE)        addr
  o_near     = 7        # Immediate Near Address (CODE)        addr
  o_idpspec0 = 8        # Processor specific type
  o_idpspec1 = 9        # Processor specific type
  o_idpspec2 = 10       # Processor specific type
  o_idpspec3 = 11       # Processor specific type
  o_idpspec4 = 12       # Processor specific type
  o_idpspec5 = 13       # Processor specific type
                        # There can be more processor specific types

  # x86
  o_trreg  =       o_idpspec0      # trace register
  o_dbreg  =       o_idpspec1      # debug register
  o_crreg  =       o_idpspec2      # control register
  o_fpreg  =       o_idpspec3      # floating point register
  o_mmxreg  =      o_idpspec4      # mmx register
  o_xmmreg  =      o_idpspec5      # xmm register

  # arm
  o_reglist  =     o_idpspec1      # Register list (for LDM/STM)
  o_creglist  =    o_idpspec2      # Coprocessor register list (for CDP)
  o_creg  =        o_idpspec3      # Coprocessor register (for LDC/STC)
  o_fpreglist  =   o_idpspec4      # Floating point register list
  o_text  =        o_idpspec5      # Arbitrary text stored in the operand
  o_cond  =        o_idpspec5 + 1  # ARM condition as an operand

  # ppc
  o_spr  =         o_idpspec0      # Special purpose register
  o_twofpr  =      o_idpspec1      # Two FPRs
  o_shmbme  =      o_idpspec2      # SH & MB & ME
  o_crf  =         o_idpspec3      # crfield      x.reg
  o_crb  =         o_idpspec4      # crbit        x.reg
  o_dcr  =         o_idpspec5      # Device control register

# Update: 20250115
class Operand:
  # addStr = "add"
  # addStr = "Add"
  offStr = "Off" # Offset=Index
  # valStr = "val"
  valStr = "Val"

  def __init__(self, operand, type, value):
    self.operand = operand
    self.type = type
    self.value = value

    # for o_displ / o_phrase
    self.baseReg = None
    self.indexReg = None
    # for o_displ
    self.displacement = None
    self.displ_addr = None

    self._postInit()
  
  def _postInit(self):
    # print("")
    CommonUtil.logDebug("_postInit: self.operand=%s", self.operand)
    if self.isDispl():
      # o_displ    = 4        # Memory Reg [Base Reg + Index Reg + Displacement] phrase+addr
      # [SP,#arg_18]
      # [X20,#0x50]
      # print("self.operand=%s" % self.operand)
      # displMatch = re.search("\[(?P<baseReg>\w+),(?P<displacement>#[\w\-\.]+)\]", self.operand)
      # [X9]
      # displMatch = re.search("\[(?P<baseReg>\w+)(,(?P<displacement>#[\w\-\.]+))?\]", self.operand)
      # curOperand=[SP,#-0x10+var_s0]!
      displMatch = re.search("\[(?P<baseReg>\w+)(,(?P<displacement>#[\w\-\.\+]+))?\]!?", self.operand)
      CommonUtil.logDebug("displMatch=%s", displMatch)
      if displMatch:
        self.baseReg = displMatch.group("baseReg")
        CommonUtil.logDebug("self.baseReg=%s", self.baseReg)
        self.displacement = displMatch.group("displacement")
        CommonUtil.logDebug("self.displacement=%s", self.displacement)

      if not displMatch:
        # LDP X29, X30, [SP+var_s0],#0x10
        # curOperand=[SP+var_s0],#0x10
        displMatch = re.search("\[(?P<baseReg>\w+)\+(?P<displacement>\w+)\],#(?P<displ_addr>)", self.operand)
        CommonUtil.logDebug("displMatch=%s", displMatch)

        if displMatch:
          self.baseReg = displMatch.group("baseReg")
          CommonUtil.logDebug("self.baseReg=%s", self.baseReg)
          self.displacement = displMatch.group("displacement")
          CommonUtil.logDebug("self.displacement=%s", self.displacement)
          self.displ_addr = displMatch.group("displ_addr")
          CommonUtil.logDebug("self.displ_addr=%s", self.displ_addr)

    elif self.isPhrase():
      # o_phrase   = 3        # Memory Ref [Base Reg + Index Reg]    phrase
      # [X19,X8]
      # print("self.operand=%s" % self.operand)
      phraseMatch = re.search("\[(?P<baseReg>\w+),(?P<indexReg>\w+)\]", self.operand)
      # print("phraseMatch=%s" % phraseMatch)
      if phraseMatch:
        self.baseReg = phraseMatch.group("baseReg")
        # print("self.baseReg=%s" % self.baseReg)
        self.indexReg = phraseMatch.group("indexReg")
        # print("self.indexReg=%s" % self.indexReg)

  def __str__(self):
    valStr = ""
    if self.value <= 0:
      valStr = "%s" % self.value
    else:
      valStr = "0x%X" % self.value
    # curOpStr = "<Operand: op=%s,type=%d,val=%s>" % (self.operand, self.type, valStr)
    # curOpStr = "<Operand: op=%s,type=%d,val=%s, baseReg=%s,indexReg=%s,displ=%s>" % (self.operand, self.type, valStr, self.baseReg, self.indexReg, self.displacement)
    extraInfo = ""
    if self.isDispl():
      extraInfo = ",bsReg=%s,idxReg=%s,displ=%s" % (self.baseReg, self.indexReg, self.displacement)
    elif self.isPhrase():
      extraInfo = ",bsReg=%s,idxReg=%s" % (self.baseReg, self.indexReg)
    curOpStr = "<Operand: op=%s,type=%d,val=%s%s>" % (self.operand, self.type, valStr, extraInfo)
    # print("curOpStr=%s" % curOpStr)
    return curOpStr

  @staticmethod
  def listToStr(operandList):
    # operandStrList = []
    # for curOperand in operandList:
    #   if curOperand:
    #     curOperandStr = "%s" % curOperand
    #   else:
    #     curOperandStr = ""
    #   # print("curOperandStr=%s" % curOperandStr)
    #   operandStrList.append(curOperandStr)
    operandStrList = [str(eachOperand) for eachOperand in operandList]
    operandListAllStr = ", ".join(operandStrList)
    operandListAllStr = "[%s]" % operandListAllStr
    return operandListAllStr

  def isReg(self):
    return self.type == OperandType.o_reg

  def isImm(self):
    return self.type == OperandType.o_imm

  def isDispl(self):
    return self.type == OperandType.o_displ

  def isPhrase(self):
    return self.type == OperandType.o_phrase

  def isNear(self):
    return self.type == OperandType.o_near

  def isIdpspec0(self):
    #   o_idpspec0 = 8        # Processor specific type
    return self.type == OperandType.o_idpspec0

  def isValid(self):
    isDebug = False

    # isValidOperand = bool(self.operand)
    # print("isValidOperand=%s" % isValidOperand)
    # if isValidOperand:
    isValidOperand = False

    if isDebug:
      print("self.operand=%s" % self.operand)

    if self.operand:
      if self.isImm():
        # #0x20200A2C
        # #0x2020
        # #arg_20
        # isMatchImm = re.match("^#[0-9a-fA-FxX]+$", self.operand)
        # #-3.0
        # isMatchImm = re.match("^#\w+$", self.operand)
        # isMatchImm = re.match("^#[\w\-\.]+$", self.operand)
        # curOperand=#_OBJC_CLASS_$__TtC11XxxxXxxXxxx26ApiInitiateRechargeRequest@PAGEOFF
        isMatchImm = re.match("^#[\w\-\.\$\@]+$", self.operand)
        CommonUtil.logDebug("isMatchImm=%s" % isMatchImm)
        isValidOperand = bool(isMatchImm)
        CommonUtil.logDebug("isValidOperand=%s" % isValidOperand)
      elif self.isReg():
        # X0/X1
        # D8/D4
        # Special: XZR/WZR
        regNameUpper = self.operand.upper()
        # print("regNameUpper=%s" % regNameUpper)
        # isMatchReg = re.match("^[XD]\d+$", regNameUpper)
        # isMatchReg = re.match("^[XDW]\d+$", regNameUpper)
        isMatchReg = re.match("^([XDW]\d+)|(XZR)|(WZR)$", regNameUpper)
        CommonUtil.logDebug("isMatchReg=%s" % isMatchReg)
        isValidOperand = bool(isMatchReg)
        CommonUtil.logDebug("isValidOperand=%s" % isValidOperand)
        if not isValidOperand:
          isValidOperand = regNameUpper in ARMUtil.ArmSpecialRegNameList
      elif self.isDispl():
        # o_displ    = 4        # Memory Reg [Base Reg + Index Reg + Displacement] phrase+addr
        # curOperand=<Operand: op=[SP,#arg_18],type=4,val=0x18>
        # if self.baseReg and (not self.indexReg) and self.displacement:
        # curOperand=<Operand: op=[X9],type=4,val=0x0>
        CommonUtil.logDebug("self.baseReg=%s, self.indexReg=%s, self.displacement=%s" % (self.baseReg, self.indexReg, self.displacement))

        if self.baseReg and (not self.indexReg):
          # Note: self.displacement is None / Not-None
          # TODO: add more type support, like indexReg not None
          isValidOperand = True
      elif self.isPhrase():
        # curOperand=<Operand: op=[X19,X8],type=3,val=0x94>
        CommonUtil.logDebug("self.baseReg=%s, self.indexReg=%s" % (self.baseReg, self.indexReg))
        if self.baseReg and self.indexReg:
          isValidOperand = True
      elif self.isNear():
        # o_near     = 7        # Immediate Near Address (CODE)        addr
        # curOperand=<Operand: op=_objc_copyWeak,type=7,val=0x1024ABBD0>
        CommonUtil.logDebug("self.value=%s" % self.value)

        if self.value:
          # jump to some (non 0) address -> consider is valid
          isValidOperand = True
      elif self.isIdpspec0():
        isValidOperand = True

    # print("isValidOperand=%s" % isValidOperand)

    # isValidType = self.type != OperandType.o_void
    # isValidValue = self.value >= 0
    # isValidAll = isValidOperand and isValidType and isValidValue
    # isValidTypeValue = False
    # if self.isReg() or self.isImm():
    #   isValidTypeValue = self.value >= 0
    # elif self.isIdpspec0():
    #   isValidTypeValue = self.value == -1

    if self.isIdpspec0():
      isValidTypeValue = self.value == -1
    else:
      isValidType = self.type != OperandType.o_void
      isValidValue = self.value >= 0
      isValidTypeValue = isValidType and isValidValue
    isValidAll = isValidOperand and isValidTypeValue

    if isDebug:
      print("Operand isValidAll=%s" % isValidAll)
    return isValidAll

  def isInvalid(self):
    return not self.isValid()
  
  @property
  def immVal(self):
    curImmVal = None
    if self.isImm():
      curImmVal = self.value
      # print("curImmVal=%s" % curImmVal)
    return curImmVal
  
  @property
  def immValHex(self):
    curImmValHex = ""
    if self.immVal != None:
      curImmValHex = "0x%X" % self.immVal
      # print("curImmValHex=%s" % curImmValHex)
    return curImmValHex

  @property
  def regName(self):
    curRegName = None
    if self.isReg():
      curRegName = self.operand
    return curRegName

  @property
  def contentStr(self):
    contentStr = ""
    if self.isReg():
      # print("isReg")
      contentStr = self.regName
    elif self.isImm():
      # print("isImm")
      # if 0 == self.immVal:
      # for 0 <= x < 8, not add 0x prefix, eg: 0x7 -> 7
      if (self.immVal >= 0) and (self.immVal < 8):
        # contentStr = "0"
        contentStr = "%X" % self.immVal
      else:
        contentStr = self.immValHex
    elif self.isIdpspec0():
        contentStr = self.operand
    elif self.isDispl():
        # [SP,#arg_18]
        # print("self.displacement=%s" % self.displacement)
        if self.displacement:
          displacementStr = ""
          if self.value != None:
            if (self.value >= 0) and (self.value < 8):
              displacementStr = "%X" % self.value
            else:
              displacementStr = "0x%X" % self.value
          # print("displacementStr=%s" % displacementStr)
          contentStr = "%s%s%s%s" % (self.baseReg, Operand.offStr, displacementStr, Operand.valStr)
        else:
          contentStr = "%s%s" % (self.baseReg, Operand.valStr)
    elif self.isPhrase():
      # [X19,X8]
      contentStr = "%s%s%s%s" % (self.baseReg, Operand.offStr, self.indexReg, Operand.valStr)

    # remove invalid char
    # <Operand: op=W0,UXTB,type=8,val=-1>
    # W0,UXTB -> W0UXTB
    contentStr = contentStr.replace(",", "")
    # X21,LSL#32
    # X8,ASR#29
    contentStr = contentStr.replace("#", "")

    # TODO: add more case

    # print("contentStr=%s" % contentStr)
    return contentStr

  @property
  def regIdx(self):
    curRegIdx = None
    if self.isReg():
      # TODO: extract reg idx, 
      # eg: X0 -> 0, X4 -> 4
      # note: additonal: D0 -> 0, D8 -> 8 ?
      curRegIdx = 0
    return curRegIdx

# Update: 20250115
class Instruction:
  branchToStr = "BranchTo"
  # toStr = "to"
  toStr = "To"
  # addStr = "add"
  addStr = "Add"

  def __init__(self, addr, name, operands):
    self.addr = addr
    self.disAsmStr = IDAUtil.ida_getDisasmStr(addr)
    # print("self.disAsmStr=%s" % self.disAsmStr)
    self.name = name
    self.operands = operands

  def __str__(self):
    # operandsAllStr = Operand.listToStr(self.operands)
    # print("operandsAllStr=%s" % operandsAllStr)
    # curInstStr = "<Instruction: addr=0x%X,name=%s,operands=%s>" % (self.addr, self.name, operandsAllStr)
    # curInstStr = "<Instruction: addr=0x%X,disAsmStr=%s>" % (self.addr, self.disAsmStr)
    curInstStr = "<Instruction: 0x%X: %s>" % (self.addr, self.disAsmStr)
    # print("curInstStr=%s" % curInstStr)
    return curInstStr

  @staticmethod
  def listToStr(instList):
    instContentStrList = [str(eachInst) for eachInst in instList]
    instListAllStr = ", ".join(instContentStrList)
    instListAllStr = "[%s]" % instListAllStr
    return instListAllStr

  @staticmethod
  def parse(addr):
    CommonUtil.logDebug("Instruction: parsing 0x%X", addr)
    parsedInst = None

    instName = idc.print_insn_mnem(addr)
    CommonUtil.logDebug("instName=%s", instName)

    curOperandIdx = 0
    curOperandVaild = True
    operandList = []
    while curOperandVaild:
      CommonUtil.logSubSubStr("[%d]" % curOperandIdx)
      curOperand = idc.print_operand(addr, curOperandIdx)
      CommonUtil.logDebug("curOperand=%s", curOperand)
      curOperandType = idc.get_operand_type(addr, curOperandIdx)
      CommonUtil.logDebug("curOperandType=%d", curOperandType)
      curOperandValue = idc.get_operand_value(addr, curOperandIdx)
      CommonUtil.logDebug("curOperandValue=%s=0x%X", curOperandValue, curOperandValue)
      curOperand = Operand(curOperand, curOperandType, curOperandValue)
      CommonUtil.logDebug("curOperand=%s", curOperand)
      if curOperand.isValid():
        operandList.append(curOperand)
      else:
        CommonUtil.logDebug("End of operand for invalid %s", curOperand)
        curOperandVaild = False

      CommonUtil.logDebug("curOperandVaild=%s", curOperandVaild)
      curOperandIdx += 1

    if operandList:
      parsedInst = Instruction(addr=addr, name=instName, operands=operandList)
    CommonUtil.logDebug("parsedInst=%s", parsedInst)
    CommonUtil.logDebug("operandList=%s", Operand.listToStr(operandList))
    return parsedInst

  def isInst(self, instName):
    isMatchInst = False
    if self.name:
      if (instName.lower() == self.name.lower()):
        isMatchInst = True
    return isMatchInst

  @property
  def contentStr(self):
    """
    convert to meaningful string of Instruction real action / content
    """
    contentStr = ""

    # isDebug = False
    # isDebug = True

    CommonUtil.logDebug("----- To contentStr: %s ----- ", self)

    operandNum = len(self.operands)
    CommonUtil.logDebug("operandNum=%s", operandNum)
    
    isPairInst = self.isStp() or self.isLdp()
    CommonUtil.logDebug("isPairInst=%s", isPairInst)
    if not isPairInst:
      if operandNum >= 1:
        dstOperand = self.operands[0]
        CommonUtil.logDebug("dstOperand=%s", dstOperand)
        dstOperandStr = dstOperand.contentStr
        CommonUtil.logDebug("dstOperandStr=%s", dstOperandStr)

      if operandNum >= 2:
        srcOperand = self.operands[1]
        CommonUtil.logDebug("srcOperand=%s", srcOperand)
        srcOperandStr = srcOperand.contentStr
        CommonUtil.logDebug("srcOperandStr=%s", srcOperandStr)
    
    if self.isBl():
      if operandNum == 1:
        # <Instruction: 0xE3C8: BL _swift_getInitializedObjCClass>
        dstOperandOperand = dstOperand.operand
        CommonUtil.logDebug("dstOperandOperand=%s", dstOperandOperand)
        contentStr = "%s%s" % (Instruction.branchToStr, dstOperandOperand)

    if self.isMov() or self.isFmov():
      # MOV X0, X24
      # FMOV D4, #-3.0

      if operandNum == 2:
        contentStr = "%s%s%s" % (srcOperandStr, Instruction.toStr, dstOperandStr)
        # print("contentStr=%s" % contentStr)
      elif operandNum > 2:
        # TODO: add case for operand > 2
        print("TODO: add support operand > 2 of MOV/FMOV")
    elif self.isAdd() or self.isFadd():
      # <Instruction: 0x10235D574: ADD X0, X19, X8; location>
      # # print("is ADD: self=%s" % self)
      # instName = self.name
      # # print("instName=%s" % instName)
      # instOperandList = self.operands
      # # print("instOperandList=%s" % Operand.listToStr(instOperandList))
      if operandNum == 3:
        # <Instruction: 0x10235D574: ADD X0, X19, X8; location>
        # <Instruction: 0xE3C4: ADD X0, X0, #_OBJC_CLASS_$__TtC11XxxxXxxXxxx26ApiInitiateRechargeRequest@PAGEOFF>
        extracOperand = self.operands[2]
        # print("extracOperand=%s" % extracOperand)
        extraOperandStr = extracOperand.contentStr
        # print("extraOperandStr=%s" % extraOperandStr)
        contentStr = "%s%s%s%s%s" % (srcOperandStr, Instruction.addStr, extraOperandStr, Instruction.toStr, dstOperandStr)

      # TODO: add case operand == 2
    elif self.isLdr():
      # LDR X0, [SP,#arg_18];
      if operandNum == 2:
        contentStr = "%s%s%s" % (srcOperandStr, Instruction.toStr, dstOperandStr)
      elif operandNum > 2:
        # TODO: add case for operand > 2
        CommonUtil.logInfo("TODO: add support operand > 2 of LDR")
    elif self.isStr():
      # STR XZR, [X19,X8]
      if operandNum == 2:
        contentStr = "%s%s%s" % (dstOperandStr, Instruction.toStr, srcOperandStr)
      elif operandNum > 2:
        # TODO: add case for operand > 2
        CommonUtil.logInfo("TODO: add support operand > 2 of STR")
    elif self.isStp():
      # <Instruction: 0x10235D6B4: STP X8, X9, [SP,#arg_18]>
      if operandNum == 3:
        srcOperand1 = self.operands[0]
        CommonUtil.logDebug("srcOperand1=%s", srcOperand1)
        srcOperand1Str = srcOperand1.contentStr
        CommonUtil.logDebug("srcOperand1Str=%s", srcOperand1Str)
        srcOperand2 = self.operands[1]
        CommonUtil.logDebug("srcOperand2=%s", srcOperand2)
        srcOperand2Str = srcOperand2.contentStr
        CommonUtil.logDebug("srcOperand2Str=%s", srcOperand2Str)

        dstOperand = self.operands[2]
        CommonUtil.logDebug("dstOperand=%s", dstOperand)
        dstOperandStr = dstOperand.contentStr
        CommonUtil.logDebug("dstOperandStr=%s", dstOperandStr)
        
        contentStr = "%s%s%s%s" % (srcOperand1Str, srcOperand2Str, Instruction.toStr, dstOperandStr)
    elif self.isLdp():
      # <Instruction: 0x10235D988: LDP D0, D1, [X8]>
      # <Instruction: 0x10235D98C: LDP D2, D3, [X8,#0x10]>
      if operandNum == 3:
        dstOperand1 = self.operands[0]
        CommonUtil.logDebug("dstOperand1=%s", dstOperand1)
        dstOperand1Str = dstOperand1.contentStr
        CommonUtil.logDebug("dstOperand1Str=%s", dstOperand1Str)
        dstOperand2 = self.operands[1]
        CommonUtil.logDebug("dstOperand2=%s", dstOperand2)
        dstOperand2Str = dstOperand2.contentStr
        CommonUtil.logDebug("dstOperand2Str=%s", dstOperand2Str)

        srcOperand = self.operands[2]
        CommonUtil.logDebug("srcOperand=%s", srcOperand)
        srcOperandStr = srcOperand.contentStr
        CommonUtil.logDebug("srcOperandStr=%s", srcOperandStr)
        
        contentStr = "%s%s%s%s" % (srcOperandStr, Instruction.toStr, dstOperand1Str, dstOperand2Str)
    elif self.isAdrp():
      if operandNum == 2:
        # <Instruction: 0xE3C0: ADRP X0, #unk_111D000; classType>
        dstOperand1 = self.operands[0]
        CommonUtil.logDebug("dstOperand1=%s", dstOperand1)
        dstOperand1Str = dstOperand1.contentStr
        CommonUtil.logDebug("dstOperand1Str=%s", dstOperand1Str)

        srcOperand = self.operands[1]
        CommonUtil.logDebug("srcOperand=%s", srcOperand)
        srcOperandStr = srcOperand.contentStr
        CommonUtil.logDebug("srcOperandStr=%s", srcOperandStr)

        contentStr = "PageAddr%s%s%s" % (srcOperandStr, Instruction.toStr, dstOperand1Str)

    # TODO: add other Instruction support: SUB/STR/...
    CommonUtil.logDebug("contentStr=%s", contentStr)
    return contentStr

  def isMov(self):
    return self.isInst("MOV")

  def isFmov(self):
    return self.isInst("FMOV")

  def isRet(self):
    return self.isInst("RET")

  def isB(self):
    return self.isInst("B")

  def isBr(self):
    return self.isInst("BR")

  def isBl(self):
    return self.isInst("BL")

  def isBranch(self):
    # TODO: support more: BRAA / ...
    return self.isB() or self.isBr() or self.isBl()

  def isAdd(self):
    return self.isInst("ADD")

  def isFadd(self):
    return self.isInst("FADD")

  def isSub(self):
    return self.isInst("SUB")

  def isStr(self):
    return self.isInst("STR")

  def isStp(self):
    return self.isInst("STP")

  def isLdp(self):
    return self.isInst("LDP")

  def isLdr(self):
    return self.isInst("LDR")

  def isAdrp(self):
    return self.isInst("ADRP")

################################################################################
# Current Project Functions
################################################################################

def isFuncSizeValid(funcSize):
  # note: not include invalid size: 0
  return (funcSize > 0) and (funcSize <= MAX_INSTRUCTION_SIZE)

def isAllMovInst(instructionList):
  """
  Check is all MOV/FMOV instruction
  """
  isAllMov = True
  for eachInst in instructionList:
    isMovLikeInst = eachInst.isMov() or eachInst.isFmov()
    if not isMovLikeInst:
      isAllMov = False
      break
  return isAllMov

def checkAllMovThenRet(instructionList):
  isAllMovThenRet = False

  lastInst = instructionList[-1]
  # print("lastInst=%s" % lastInst)
  lastIsRet = lastInst.isRet()
  # print("lastIsRet=%s" % lastIsRet)
  if lastIsRet:
    instListExceptLast = instructionList[:-1]
    # print("instListExceptLast=%s" % instListExceptLast)
    isAllMov = isAllMovInst(instListExceptLast)
    print("isAllMov=%s" % isAllMov)
    isAllMovThenRet = lastIsRet and isAllMov

  # print("isAllMovThenRet=%s" % isAllMovThenRet)
  return isAllMovThenRet

def checkAllMovThenBranch(instructionList):
  isAllMovThenBranch = False

  lastInst = instructionList[-1]
  # print("lastInst=%s" % lastInst)
  lastIsBranch = lastInst.isBranch()
  # print("lastIsBranch=%s" % lastIsBranch)
  if lastIsBranch:
    instListExceptLast = instructionList[:-1]
    # print("instListExceptLast=%s" % instListExceptLast)
    isAllMov = isAllMovInst(instListExceptLast)
    # print("isAllMov=%s" % isAllMov)
    isAllMovThenBranch = lastIsBranch and isAllMov

  # print("isAllMovThenBranch=%s" % isAllMovThenBranch)
  return isAllMovThenBranch

def checkPrologue(instructionList):
  isPrologue = False

  lastInst = instructionList[-1]
  # print("lastInst=%s" % lastInst)
  lastIsRet = lastInst.isRet()
  # print("lastIsRet=%s" % lastIsRet)
  if lastIsRet:
    instListExceptLast = instructionList[:-1]
    # print("instListExceptLast=%s" % instListExceptLast)
    isAllStp = IDAUtil.isAllPrologueStp(instListExceptLast)
    # print("isAllStp=%s" % isAllStp)
    isPrologue = lastIsRet and isAllStp

  # print("isPrologue=%s" % isPrologue)
  return isPrologue

def checkJumpToSwiftGetInitializedObjCClass(instructionList):
  """
  Check whether is jump to _swift_getInitializedObjCClass

  Exmaple:

    __text:000000000000E3B8 FD 7B BF A9                 STP             X29, X30, [SP,#-0x10+var_s0]!
    __text:000000000000E3BC FD 03 00 91                 MOV             X29, SP
    __text:000000000000E3C0 60 88 00 F0                 ADRP            X0, #unk_111D000 ; classType
    __text:000000000000E3C4 00 20 2F 91                 ADD             X0, X0, #_OBJC_CLASS_$__TtC11XxxxXxxXxxx26ApiInitiateRechargeRequest@PAGEOFF
    __text:000000000000E3C8 43 75 32 94                 BL              _swift_getInitializedObjCClass
    __text:000000000000E3CC 01 00 80 D2                 MOV             X1, #0
    __text:000000000000E3D0 FD 7B C1 A8                 LDP             X29, X30, [SP+var_s0],#0x10
    __text:000000000000E3D4 C0 03 5F D6                 RET
  """
  CommonUtil.logDebug("checkJumpToSwiftGetInitializedObjCClass: instructionList=%s", instructionList)

  JumpToSwiftGetInitializedObjCClass_INSTRUCTION_SIZE = 8

  isFuncInstMatch = True # is function instructions match
  mangledClassName = None

  if isFuncInstMatch:
    instNum = len(instructionList)
    CommonUtil.logDebug("instNum=%s", instNum)
    if JumpToSwiftGetInitializedObjCClass_INSTRUCTION_SIZE != instNum:
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst1 = instructionList[0]
    CommonUtil.logDebug("inst1=%s", inst1)
    if not inst1.isStp():
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst2 = instructionList[1]
    CommonUtil.logDebug("inst2=%s", inst2)
    if not inst2.isMov():
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst3 = instructionList[2]
    CommonUtil.logDebug("inst3=%s", inst3)
    if not inst3.isAdrp():
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst4 = instructionList[3]
    CommonUtil.logDebug("inst4=%s", inst4)
    if inst4.isAdd():
      curOperands = inst4.operands
      CommonUtil.logDebug("curOperands=%s", curOperands)
      operandNum = len(curOperands)
      CommonUtil.logDebug("operandNum=%s", operandNum)
      if operandNum == 3:
        operand1 = curOperands[0]
        CommonUtil.logDebug("operand1=%s", operand1)
        operand1Name = operand1.operand
        CommonUtil.logDebug("operand1Name=%s", operand1Name)

        operand2 = curOperands[1]
        CommonUtil.logDebug("operand2=%s", operand2)
        operand2Name = operand2.operand
        CommonUtil.logDebug("operand2Name=%s", operand2Name)
        if operand1Name == operand2Name:
          operand3 = curOperands[2]
          CommonUtil.logDebug("operand3=%s", operand3)
          operand3Operand = operand3.operand
          CommonUtil.logDebug("operand3Operand=%s", operand3Operand)

          # operand3Operand=#_OBJC_CLASS_$__TtC11XxxxXxxXxxx26ApiInitiateRechargeRequest@PAGEOFF
          objcClassMatch = re.search("#_OBJC_CLASS_\$_(?P<mangledClassName>\w+)@PAGEOFF", operand3Operand)
          CommonUtil.logDebug("objcClassMatch=%s", objcClassMatch)
          if objcClassMatch:
            mangledClassName = objcClassMatch.group("mangledClassName")
            CommonUtil.logDebug("mangledClassName=%s", mangledClassName)
          else:
            isFuncInstMatch = False
        else:
          isFuncInstMatch = False
      else:
        isFuncInstMatch = False
    else:
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst5 = instructionList[4]
    CommonUtil.logDebug("inst5=%s", inst5)
    if inst5.isBl():
      # _postInit: self.operand=_swift_getInitializedObjCClass
      curOperands = inst5.operands
      CommonUtil.logDebug("curOperands=%s", curOperands)
      operandNum = len(curOperands)
      CommonUtil.logDebug("operandNum=%s", operandNum)
      if operandNum == 1:
        operand1 = curOperands[0]
        CommonUtil.logDebug("operand1=%s", operand1)
        operand1Operand = operand1.operand
        CommonUtil.logDebug("operand1Operand=%s", operand1Operand)
        # support:
        #   swift_getInitializedObjCClass
        #   _swift_getInitializedObjCClass
        getObjcClassMatch = re.search("swift_getInitializedObjCClass", operand1Operand)
        CommonUtil.logDebug("getObjcClassMatch=%s", getObjcClassMatch)
        if getObjcClassMatch:
          isFuncInstMatch = True
        else:
          isFuncInstMatch = False
      else:
        isFuncInstMatch = False
    else:
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst6 = instructionList[5]
    CommonUtil.logDebug("inst6=%s", inst6)
    if not inst6.isMov():
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst7 = instructionList[6]
    CommonUtil.logDebug("inst7=%s", inst7)
    if not inst7.isLdp():
      isFuncInstMatch = False

  if isFuncInstMatch:
    inst8 = instructionList[7]
    CommonUtil.logDebug("inst8=%s", inst8)
    if not inst8.isRet():
      isFuncInstMatch = False

  CommonUtil.logDebug("isFuncInstMatch=%s, mangledClassName=%s", isFuncInstMatch, mangledClassName)
  return isFuncInstMatch,  mangledClassName

def removeWrongLuminaFunctionComment_AppDelegate(funcAddr):
  """
  remove wrong function comments from Lumina

  Example:
    $s11CryptoTrade11AppDelegateCMa 
    type metadata accessor for AppDelegate
  """
  origFuncComment = IDAUtil.ida_getFunctionComment(funcAddr, repeatable=True)
  CommonUtil.logDebug("origFuncComment=%s", origFuncComment)
  isAppDelegateCommentExisted = "type metadata accessor for AppDelegate" in origFuncComment
  CommonUtil.logDebug("isAppDelegateCommentExisted=%s", isAppDelegateCommentExisted)
  if isAppDelegateCommentExisted:
    newComment = ""
    setCmtRet = IDAUtil.ida_setFunctionComment(funcAddr, newComment, repeatable=True)
    CommonUtil.logDebug("setCmtRet=%s", setCmtRet)
    CommonUtil.logInfo("[0x%X] Clear wrong Lumina's AppDelegate function comment: %s", funcAddr, origFuncComment)

def generateFirstParaName(selectorFirstPart):
  """
  generate first parameter name from selector first part
  eg:
    "arrayByAddingObjectsFromArray" -> "someArray"
    "wa_alignedCenterFromCenter" -> "someCenter"
    "arrangeFromView" -> "someView"
    "postIdentityChangeNotificationForDeviceJIDs" -> "deviceJIDs"
    "addObject" -> "someObject"
    "pickerMode" -> "pickerMode"
    "initWithCapacity" -> "someCapacity"
    "mergePendingJournalIfPossibleForDatabaseAtPath" -> "somePath"
    "setMessages_received" -> "someMessages_received"
  """
  firstParaName = ""
  keywordMatch = re.search("(From|from|Add|add|For|With|At|^set)(?P<keyword>[A-Z][a-z0-9_]+)$", selectorFirstPart)
  # print("keywordMatch=%s" % keywordMatch)
  if keywordMatch:
    keyword = keywordMatch.group("keyword")
    # print("keyword=%s" % keyword)
    firstParaName = "some%s" % keyword

  if not firstParaName:
    firstParaName = selectorFirstPart

  # print("selectorFirstPart=%s -> firstParaName=%s" % (selectorFirstPart, firstParaName))
  return firstParaName

def generateInstContentListStr(instructionList, isFirstDigitAddPrefix=True):
  # print("instructionList=%s, isFirstDigitAddPrefix=%s" % (instructionList, isFirstDigitAddPrefix))
  # print("instructionList=%s, isFirstDigitAddPrefix=%s" % (Instruction.listToStr(instructionList), isFirstDigitAddPrefix))

  instContentStrList = []
  for eachInst in instructionList:
    eachInstContentStr = eachInst.contentStr
    # print("eachInstContentStr=%s" % eachInstContentStr)
    instContentStrList.append(eachInstContentStr)

  allInstContentStr = "_".join(instContentStrList)
  # print("allInstContentStr=%s" % allInstContentStr)

  prefixStr = ""
  if isFirstDigitAddPrefix:
    isFisrtIsDigit = re.match("^\d+", allInstContentStr)
    # print("isFisrtIsDigit=%s" % isFisrtIsDigit)
    if isFisrtIsDigit:
      prefixStr = "func_"

  allInstContentStr = "%s%s" % (prefixStr, allInstContentStr)
  # print("allInstContentStr=%s" % allInstContentStr)

  return allInstContentStr

def generateBranchName(branchInst):
  isSupport = True
  branchFunc = None
  errMsg = ""

  branchInstName = branchInst.name
  # print("branchInstName=%s" % branchInstName)
  branchInstOperands = branchInst.operands
  # print("branchInstOperands=%s" % branchInstOperands)
  targetOperand = branchInstOperands[0]
  # print("targetOperand=%s" % targetOperand)
  # targetOperand=<Operand: op=_objc_msgSend$initWithName_protocolString_,type=7,val=0xF9DDC0>
  # branchFunc = targetOperand.value
  branchFunc = targetOperand.operand
  # print("branchFunc=%s" % branchFunc)
  branchType = targetOperand.type
  # print("branchType=%s" % branchType)
  if branchType == OperandType.o_reg:
    # BR X27
    # branchFunc = "Jump%s" % branchFunc
    branchFunc = "%s%s" % (branchInstName, branchFunc)
  else:
    isDefSubFunc, subAddrStr = IDAUtil.isFuncName_sub(branchFunc)
    # print("isDefSubFunc=%s, subAddrStr=%s" % (isDefSubFunc, subAddrStr))
    isReserved_loc, locAddrStr = IDAUtil.isReservedPrefix_locType(branchFunc)
    # print("isReserved_loc=%s, locAddrStr=%s" % (isReserved_loc, locAddrStr))
    if isDefSubFunc:
      isSupport = False
      branchFunc = None
      defSubFuncName = "sub_%s" % subAddrStr
      errMsg = "Current not support for jump to %s" % defSubFuncName
      # TODO: add branch jump to sub_xxx
    elif isReserved_loc:
      # branchFunc = None
      branchFunc = "JmpLoc%s" % locAddrStr
    else:
      # _calloc_2EA8
      # _objc_msgSend
      # _objc_release
      # _objc_storeStrong_39D0
      # objc_msgSend$initWithName_protocolString_
      # _objc_msgSend$addObject__AB00
      # remove leading _
      branchFunc = re.sub("^_+", "", branchFunc)
      # print("branchFunc=%s" % branchFunc)
      # remove ending _
      branchFunc = re.sub("_+$", "", branchFunc)
      # print("branchFunc=%s" % branchFunc)
      # remove last 4 or allAddr part if exist (previous self manual added)
      branchFunc = re.sub("_+[0-9A-Fa-f]{3,20}$", "", branchFunc)
  # print("isSupport=%s, branchFunc=%s, errMsg=%s" % (isSupport, branchFunc, errMsg))
  return isSupport, branchFunc, errMsg

def checkAndGenerateInstListContentStr(instructionList):
  isSupportAllInst = True
  instListContentStr = ""
  firstUnsupportInst = None

  instContentStrList = []
  for eachInst in instructionList:
    # print("eachInst=%s" % eachInst)
    instContentStr = eachInst.contentStr
    # print("instContentStr=%s" % instContentStr)
    if instContentStr:
      instContentStrList.append(instContentStr)
    else:
      isSupportAllInst = False
      firstUnsupportInst = eachInst
      # print("firstUnsupportInst=%s" % firstUnsupportInst)
      break
  
  if isSupportAllInst:
    instListContentStr = "_".join(instContentStrList)
    # print("instListContentStr=%s" % instListContentStr)
    return isSupportAllInst, instListContentStr
  else:
    return isSupportAllInst, firstUnsupportInst

def getOriginSelector(funcAddr):
  """
  get orginal selector string, for some functoin has renamed, no ":", can not used for later to parse out paramter count and name
  eg:
    0xF3EF8C -> "initWithKeyValueStore:namespace:binaryCoders:"
      note: function name: "objc_msgSend$initWithKeyValueStore_namespace_binaryCoders_X22toX0_X23toX2_X24toX4_EF8C" -> no ":"
  """
  originSelector = None

  funcEndAddr = IDAUtil.ida_getFunctionEndAddr(funcAddr)
  CommonUtil.logDebug("funcEndAddr=0x%X", funcEndAddr)
  lastInstAddr = funcEndAddr - SINGLE_INSTRUCTION_SIZE
  CommonUtil.logDebug("lastInstAddr=0x%X", lastInstAddr)
  lastInst = Instruction.parse(lastInstAddr)
  CommonUtil.logDebug("lastInst=%s", lastInst)
  lastIsBranch = lastInst.isBranch()
  CommonUtil.logDebug("lastIsBranch=%s", lastIsBranch)
  if lastIsBranch:
    branchOperand = lastInst.operands[0]
    CommonUtil.logDebug("branchOperand=%s" % branchOperand)
    branchOprand = branchOperand.operand
    branchValue = branchOperand.value
    CommonUtil.logDebug("branchOprand=%s, branchValue=0x%X", branchOprand, branchValue)
    # targetFuncName = ida_getFunctionName(branchValue)
    targetName = IDAUtil.ida_getName(branchValue)
    # targetName=_objc_msgSend$initWithKeyValueStore:namespace:binaryCoders:
    CommonUtil.logDebug("targetName=%s", targetName)
    if targetName:
      isObjcMsgSend, originSelector = IDAUtil.isObjcMsgSendFuncName(targetName)
      # isObjcMsgSend=True, originSelector=initWithKeyValueStore:namespace:binaryCoders:
      CommonUtil.logDebug("isObjcMsgSend=%s, originSelector=%s", isObjcMsgSend, originSelector)

  CommonUtil.logDebug("originSelector=%s" % originSelector)
  return originSelector

def isIdCurObjType(funcAddr):
  """
  check is objc_msgSend$xxx function type is "xxx(id curObj, xxx" or not
  eg:
    0xFEB124 -> True
      note: id __cdecl(id curObj, const char *setCellsEligibleForExpansion_, id someExpansion)
  """
  isIdCurObj = False
  funcType = idc.get_type(funcAddr)
  CommonUtil.logDebug("[0x%X] -> funcType=%s", funcAddr, funcType)
  if funcType:
    idCurObjMatch = re.search("\(id curObj,", funcType)
    CommonUtil.logDebug("idCurObjMatch=%s", idCurObjMatch)
    isIdCurObj = bool(idCurObjMatch)
    CommonUtil.logDebug("isIdCurObj=%s", isIdCurObj)
  return isIdCurObj

def isNeedProcessFunc(curFuncAddr):
  isNeedProcess = False
  curFuncSize = IDAUtil.ida_getFunctionSize(curFuncAddr)
  # print("curFuncSize=%s" % curFuncSize)
  # if curFuncSize <= MAX_INSTRUCTION_SIZE:
  isValidSize = isFuncSizeValid(curFuncSize)
  CommonUtil.logDebug("isValidSize=%s", isValidSize)
  if isValidSize:
    isDefaultSubFunc, funcName = IDAUtil.isDefaultSubFunction(curFuncAddr)
    CommonUtil.logDebug("isDefaultSubFunc=%s, funcName=%s", isDefaultSubFunc, funcName)
    if isDefaultSubFunc:
      isNeedProcess = True

    if not isNeedProcess:
      isTypeMetadataAccessorForAppDelegate = IDAUtil.isFuncName_TypeMetadataAccessorForAppDelegate(funcName)
      CommonUtil.logDebug("isTypeMetadataAccessorForAppDelegate=%s", isTypeMetadataAccessorForAppDelegate)
      if isTypeMetadataAccessorForAppDelegate:
        isNeedProcess = True

    if not isNeedProcess:
      isFuncName_stp_ldp = IDAUtil.isFuncName_STP_LDP(funcName)
      CommonUtil.logDebug("isFuncName_stp_ldp=%s", isFuncName_stp_ldp)
      if isFuncName_stp_ldp:
        isNeedProcess = True

    if not isNeedProcess:
      isObjcMsgSend, selectorStr = IDAUtil.isObjcMsgSendFunction(curFuncAddr)
      CommonUtil.logDebug("isObjcMsgSend=%s, selectorStr=%s", isObjcMsgSend, selectorStr)
      if isObjcMsgSend:
        hasRenamed, suffixAddr = IDAUtil.isRenamedFunctionName(selectorStr)
        CommonUtil.logDebug("hasRenamed=%s, suffixAddr=%s", hasRenamed, suffixAddr)
        if hasRenamed:
          isDefType = IDAUtil.isDefaultTypeForObjcMsgSendFunction(curFuncAddr)
          CommonUtil.logDebug("isDefType=%s", isDefType)
          if isDefType:
            isNeedProcess = True
          else:
            isIdCurObj = isIdCurObjType(curFuncAddr)
            CommonUtil.logDebug("isIdCurObj=%s", isIdCurObj)
            if isIdCurObj:
              isNeedProcess = True
        else:
          isNeedProcess = True

  CommonUtil.logDebug("isNeedProcess=%s", isNeedProcess)
  return isNeedProcess


################################################################################
# Main
################################################################################

idaVersion = idaapi.IDA_SDK_VERSION

curDateTimeStr = CommonUtil.getCurDatetimeStr()

curBinFilename = ida_nalt.get_root_filename()

if logUseLogging:
  idaLogFilename = "%s_idaRename_%s.log" % (curBinFilename, curDateTimeStr)
  CommonUtil.loggingInit(idaLogFilename, fileLogLevel=logLevel, consoleLogLevel=logLevel)
  CommonUtil.logInfo("idaLogFilename=%s", idaLogFilename)

CommonUtil.logInfo("IDA Version: %s", idaVersion)
CommonUtil.logDebug("curDateTimeStr=%s", curDateTimeStr)
CommonUtil.logInfo("curBinFilename=%s", curBinFilename)

if isExportResult:
  if not outputFolder:
    currentIdaFolder = IDAUtil.ida_getCurrentFolder()
    CommonUtil.logInfo("currentIdaFolder=%s", currentIdaFolder)
    outputFolder = os.path.join(currentIdaFolder, "output", "AutoRenameResult")
    CommonUtil.logInfo("outputFolder=%s", outputFolder)
    CommonUtil.createFolder(outputFolder)

# for debug
# toProcessFuncAddrList = [0x1013916A0] # WhatsApp
# toProcessFuncAddrList = [0xFEB120, 0xFEB140] # SharedModules
# toProcessFuncAddrList = [0xF35794] # SharedModules
# toProcessFuncAddrList = [0xE3B8] # binFile1
# # toProcessFuncAddrList = [0xE3B8, 0x137D4, 0x1D22C] # binFile1
# toProcessFuncAddrList = [0x10001A91C] # binFile2
# toProcessFuncAddrList = [0xB786C] # binFile1
# allFuncAddrList = toProcessFuncAddrList

# normal code
allFuncAddrList = IDAUtil.ida_getFunctionAddrList()


allFuncAddrListNum = len(allFuncAddrList)
CommonUtil.logInfo("allFuncAddrListNum=%d", allFuncAddrListNum)
toProcessFuncAddrList = []
for curNum, eachFuncAddr in enumerate(allFuncAddrList, start=1):
  CommonUtil.logSubStr("[%d] 0x%X" % (curNum, eachFuncAddr))
  isNeedProcess = isNeedProcessFunc(eachFuncAddr)

  # # for debug:
  # isNeedProcess = True

  if isNeedProcess:
    toProcessFuncAddrList.append(eachFuncAddr)

toProcessFuncAddrListNum = len(toProcessFuncAddrList)
CommonUtil.logInfo("toProcessFuncAddrListNum=%d", toProcessFuncAddrListNum)

toRenameNum = 0
renameOmitNum = 0
renameOkNum = 0
renameFailNum = 0

toChangeTypeNum = 0
changeTypeOkNum = 0
changeTypeFailNum = 0

if isExportResult:
  resultDict = {}

  okList = []
  failList = []


def doFunctionRename(funcAddr):
  global isFailForUnsupportInstruction

  isOmitted = False
  omitReason = None
  isRenameOk = False
  renamedResultDict = {}

  allAddrStr = "%X" % funcAddr
  funcAddrStr = "0x%s" % allAddrStr
  CommonUtil.logDebug("allAddrStr=%s", allAddrStr)
  last4AddrStr = allAddrStr[-4:]
  CommonUtil.logDebug("last4AddrStr=%s", last4AddrStr)

  CommonUtil.logDebug("doFunctionRename: [%s]", funcAddrStr)

  funcName = IDAUtil.ida_getFunctionName(funcAddr)
  CommonUtil.logDebug("funcName=%s", funcName)

  # process each instrunction and generate new function name
  funcEndAddr = IDAUtil.ida_getFunctionEndAddr(funcAddr)
  CommonUtil.logDebug("funcEndAddr=0x%X", funcEndAddr)

  funcNameMainPart = None
  newFuncName = None
  retryFuncName = None

  funcNamePrefix = ""

  disAsmInstList = []
  for curFuncAddr in range(funcAddr, funcEndAddr, SINGLE_INSTRUCTION_SIZE):
    CommonUtil.logSubStr("[0x%X]" % curFuncAddr)
    newInst = Instruction.parse(curFuncAddr)
    CommonUtil.logDebug("newInst=%s" % newInst)
    if newInst:
      disAsmInstList.append(newInst)
    else:
      instDisasmStr = IDAUtil.ida_getDisasmStr(curFuncAddr)
      instInfoStr = "[0x%X] %s" % (curFuncAddr, instDisasmStr)
      if isFailForUnsupportInstruction:
        isOmitted = True
        omitReason = "Invalid/Unsupported instruction: %s" % instInfoStr
        return isOmitted, omitReason, isRenameOk, renamedResultDict
      else:
        # just omit for Invalid/Unsupport instruction and continue process
        print("Found Invalid/Unsupported instruction: %s" % instInfoStr)

  instDisasmStrList = Instruction.listToStr(disAsmInstList)
  CommonUtil.logDebug("instDisasmStrList=%s", instDisasmStrList)

  isPrologue = checkPrologue(disAsmInstList)
  CommonUtil.logDebug("isPrologue=%s", isPrologue)
  if isPrologue:
    funcNameMainPart = "prologue"
    newFuncName = "%s_%s" % (funcNameMainPart, allAddrStr)
    retryFuncName = None

  if not newFuncName:
    isFuncName_stp_or_ldp = IDAUtil.isFuncName_STP_LDP(funcName)
    CommonUtil.logDebug("isFuncName_stp_or_ldp=%s", isFuncName_stp_or_ldp)
    if isFuncName_stp_or_ldp:
      funcName_noStp = re.sub(IDAUtil.funcNameP_X29X30_STP, "", funcName)
      CommonUtil.logDebug("funcName_noStp=%s", funcName_noStp)
      funcName_noLdp = re.sub(IDAUtil.funcNameP_X29X30_LDP, "", funcName_noStp)
      CommonUtil.logDebug("funcName_noLdp=%s", funcName_noLdp)

      funcNameMainPart = None
      newFuncName = funcName_noLdp
      CommonUtil.logDebug("newFuncName=%s", newFuncName)
      retryFuncName = None

  if not newFuncName:
    isFuncInstMatch, mangledObjcClassName = checkJumpToSwiftGetInitializedObjCClass(disAsmInstList)
    CommonUtil.logDebug("isFuncInstMatch=%s, mangledObjcClassName=%s", isFuncInstMatch, mangledObjcClassName)
    if isFuncInstMatch:
      shortClassName = mangledObjcClassName
      demangledObjcClassName = IDAUtil.ida_getDemangledName(mangledObjcClassName)
      CommonUtil.logDebug("demangledObjcClassName=%s", demangledObjcClassName)
      demangedClassNameMatch = re.search("((?P<binFilename>\w+)\.)?(?P<shortClassName>\w+)", demangledObjcClassName)
      CommonUtil.logDebug("demangedClassNameMatch=%s", demangedClassNameMatch)
      if demangedClassNameMatch:
        shortClassName = demangedClassNameMatch.group("shortClassName")
      CommonUtil.logDebug("shortClassName=%s", shortClassName)

      funcNameMainPart = None
      curPrefix = "getObjCClass"
      newFuncName = "%s_%s" % (curPrefix, shortClassName)
      CommonUtil.logDebug("newFuncName=%s", newFuncName)
      retryFuncName = None

      removeWrongLuminaFunctionComment_AppDelegate(funcAddr)

  if not newFuncName:
    lastInst = disAsmInstList[-1]
    CommonUtil.logDebug("lastInst=%s" % lastInst)
    lastIsRet = lastInst.isRet()
    CommonUtil.logDebug("lastIsRet=%s" % lastIsRet)
    lastIsBranch = lastInst.isBranch()
    CommonUtil.logDebug("lastIsBranch=%s" % lastIsBranch)
    if lastIsRet:
      funcNamePrefix = ""
    elif lastIsBranch:
      isSupport, branchFunc, errMsg = generateBranchName(lastInst)
      if isSupport:
        funcNamePrefix = branchFunc
      else:
        isOmitted = True
        omitReason = errMsg
        return isOmitted, omitReason, isRenameOk, renamedResultDict

    CommonUtil.logDebug("funcNamePrefix=%s" % funcNamePrefix)

    instListExceptLast = disAsmInstList[0:-1]
    CommonUtil.logDebug("instListExceptLast=%s", Instruction.listToStr(instListExceptLast))

    if instListExceptLast:
      isAllInstSupport, retValue = checkAndGenerateInstListContentStr(instListExceptLast)
      CommonUtil.logDebug("isAllInstSupport=%s, retValue=%s", isAllInstSupport, retValue)

      if isAllInstSupport:
        instContentStr = retValue
        if funcNamePrefix:
          funcNameMainPart = "%s_%s" % (funcNamePrefix, instContentStr)
        else:
          funcNameMainPart = instContentStr
      else:
        firstUnsupportInst = retValue
        isOmitted = True
        omitReason = "Fist unsupported instruction: %s" % firstUnsupportInst
        return isOmitted, omitReason, isRenameOk, renamedResultDict
    else:
      if funcNamePrefix:
        funcNameMainPart = funcNamePrefix
      else:
        isOmitted = True
        omitReason = "Only 1 instrunction: %s" % lastInst
        return isOmitted, omitReason, isRenameOk, renamedResultDict

    CommonUtil.logDebug("funcNameMainPart=%s", funcNameMainPart)
    if funcNameMainPart:
      isFisrtIsDigit = re.match("^\d+", funcNameMainPart)
      CommonUtil.logDebug("isFisrtIsDigit=%s", isFisrtIsDigit)
      if isFisrtIsDigit:
        funcNameMainPart = "func_%s" % funcNameMainPart
    CommonUtil.logDebug("funcNameMainPart=%s", funcNameMainPart)

  if funcNameMainPart:
    newFuncName = "%s_%s" % (funcNameMainPart, last4AddrStr)
    retryFuncName = "%s_%s" % (funcNameMainPart, allAddrStr)


  if newFuncName:

    isRenameOk, renamedName = IDAUtil.ida_rename(funcAddr, newFuncName, retryFuncName)

    # # for debug
    # print("Test to rename: [0x%X] newFuncName=%s, retryFuncName=%s" % (funcAddr, newFuncName, retryFuncName))
    # isRenameOk = True
    # renamedName = newFuncName

    CommonUtil.logDebug("isRenameOk=%s, renamedName=%s", isRenameOk, renamedName)

    renamedResultDict["address"] = funcAddrStr
    renamedResultDict["name"] = {
        "old": funcName,
    }
    if isRenameOk:
      renamedResultDict["name"]["new"] = renamedName
    else:
      renamedResultDict["name"]["new"] = newFuncName
      renamedResultDict["name"]["retry"] = retryFuncName

  CommonUtil.logDebug("isRenameOk=%s, renamedResultDict=%s", isRenameOk, renamedResultDict)
  return isOmitted, omitReason, isRenameOk, renamedResultDict

def doFunctionChangeType(funcAddr):
  isOmit = False
  isChangeTypeOk = False
  changeTypeResultDict = {}

  defaultParaObj = "id curObj"

  oldFuncType = None
  newFuncType = None
  paraObj = defaultParaObj
  paraSelector = None
  retType = "id"

  funcAddrStr = "0x%X" % funcAddr

  funcName = IDAUtil.ida_getFunctionName(funcAddr)
  CommonUtil.logDebug("funcName=%s", funcName)
  funcNameNoAddrSuffix = IDAUtil.removeFuncNameAddressSuffixIfExist(funcName)
  CommonUtil.logDebug("funcNameNoAddrSuffix=%s", funcNameNoAddrSuffix)

  # hasRenamed, suffixAddr = isRenamedFunctionName(funcName)
  # logDebug("hasRenamed=%s, suffixAddr=%s", hasRenamed, suffixAddr)
  # if hasRenamed:
  #   addrSuffixP = "%s$" % suffixAddr
  #   logDebug("addrSuffixP=%s", addrSuffixP)
  #   funcNameNoAddrSuffix = re.sub(addrSuffixP, "", funcName)
  # else:
  #   funcNameNoAddrSuffix = funcName
  # logDebug("funcNameNoAddrSuffix=%s", funcNameNoAddrSuffix)

  isObjcMsgSend, selectorStr = IDAUtil.isObjcMsgSendFuncName(funcNameNoAddrSuffix)
  CommonUtil.logDebug("isObjcMsgSend=%s, selectorStr=%s", isObjcMsgSend, selectorStr)
  if isObjcMsgSend:
    originSelector = getOriginSelector(funcAddr)
    CommonUtil.logDebug("originSelector=%s", originSelector)
    if originSelector:
      # originSelectorNoAddrSuffix = IDAUtil.removeFuncNameAddressSuffixIfExist(originSelector)
      # logDebug("originSelectorNoAddrSuffix=%s", originSelectorNoAddrSuffix)
      # selectorStr = originSelectorNoAddrSuffix
      selectorStr = originSelector
      CommonUtil.logDebug("selectorStr=%s", selectorStr)

    selectorStr = IDAUtil.removeFuncNameAddressSuffixIfExist(selectorStr)
    CommonUtil.logDebug("selectorStr=%s", selectorStr)

    if isGenerateIdType:
      classInfoDictList = IDAUtil.findClassFromSelector(selectorStr)
      CommonUtil.logDebug("classInfoDictList=%s", classInfoDictList)
      if classInfoDictList:
        classInfoDictListLen = len(classInfoDictList)
        CommonUtil.logDebug("classInfoDictListLen=%s", classInfoDictListLen)
        if classInfoDictListLen == 1:
          uniqueClassInfoDict = classInfoDictList[0]
          CommonUtil.logDebug("uniqueClassInfoDict=%s", uniqueClassInfoDict)
          objcClassName = uniqueClassInfoDict["objcClassName"]
          CommonUtil.logDebug("objcClassName=%s", objcClassName)
          paraObj = "%s* cur%s" % (objcClassName, objcClassName)
        elif classInfoDictListLen <= 5:
          # => not change type, but: add comment
          # generate comment string
          objcFuncNameList = []
          for eachClassInfoDict in classInfoDictList:
            objcFuncName = eachClassInfoDict["objcFuncName"]
            objcFuncNameList.append(objcFuncName)
          CommonUtil.logDebug("objcFuncNameList=%s", objcFuncNameList)
          newComment = ", ".join(objcFuncNameList)
          CommonUtil.logDebug("newComment=%s", newComment)
          # check comment string exist or not
          oldFuncComment = IDAUtil.ida_getFunctionComment(funcAddr)
          CommonUtil.logDebug("oldFuncComment=%s", oldFuncComment)
          isCommentExisted = newComment in oldFuncComment
          CommonUtil.logDebug("isCommentExisted=%s", isCommentExisted)
          if isCommentExisted:
            CommonUtil.logDebug("Not add duplicated function comment string '%s' for 0x%X", newComment, funcAddr)
          else:
            setCmtRet = IDAUtil.ida_setFunctionComment(funcAddr, newComment)
            CommonUtil.logInfo("[0x%X] AddFuncCmt: %s, function comment: %s", funcAddr, setCmtRet, newComment)
        else:
          # >5, too much, omit it
          CommonUtil.logInfo("Omit for too much class (%d) for selector %s", classInfoDictListLen, selectorStr)

    CommonUtil.logDebug("paraObj=%s", paraObj)

    oldFuncType = idc.get_type(funcAddr)
    # oldFuncType=id(void *, const char *, ...)
    CommonUtil.logDebug("oldFuncType=%s", oldFuncType)

    # note: here function name is mandatory for change type, but actually is useless -> will not change to new name
    notUseNewFuncName = funcNameNoAddrSuffix
    # makesure name is valid
    notUseNewFuncName = re.sub("\W", "_", notUseNewFuncName)
    CommonUtil.logDebug("notUseNewFuncName=%s", notUseNewFuncName)

    newSelectorStr = selectorStr.replace(":", "_")
    CommonUtil.logDebug("newSelectorStr=%s", newSelectorStr)
    paraSelector = "const char * %s" % newSelectorStr
    CommonUtil.logDebug("paraSelector=%s", paraSelector)
    paramNum = selectorStr.count(":")
    CommonUtil.logDebug("paramNum=%s", paramNum)
    newValidParaList = []
    if paramNum == 0:
      newFuncType = "%s %s(%s, %s)" % (retType, notUseNewFuncName, paraObj, paraSelector)
      CommonUtil.logDebug("newFuncType=%s", newFuncType)
    else:
      paraList = selectorStr.split(":")
      CommonUtil.logDebug("paraList=%s", paraList)
      # ['arrayByAddingObjectsFromArray', '']
      # ['arrangeFromView', 'toView', 'progress', 'forwardDirection', '']
      # remove last empty
      lastItem = paraList[-1]
      CommonUtil.logDebug("lastItem=%s" % lastItem)
      if not lastItem:
        paraList.pop(-1)
        CommonUtil.logDebug("paraList=%s" % paraList)
      selectorFirstPart = paraList[0]
      CommonUtil.logDebug("selectorFirstPart=%s" % selectorFirstPart)
      firstParaName = generateFirstParaName(selectorFirstPart)
      CommonUtil.logDebug("firstParaName=%s" % firstParaName)
      newParaList = copy.deepcopy(paraList)
      CommonUtil.logDebug("newParaList=%s" % newParaList)
      newParaList[0] = firstParaName
      CommonUtil.logDebug("newParaList=%s" % newParaList)
      # process system reserved string, eg: class, id, ...
      for eachPara in newParaList:
        CommonUtil.logDebug("eachPara=%s" % eachPara)

        # # for debug
        # eachPara = "class"

        if eachPara in IDAUtil.IdaReservedStr:
          firstChar = eachPara[0]
          CommonUtil.logDebug("firstChar=%s" % firstChar)
          firstCharUpper = firstChar.upper()
          CommonUtil.logDebug("firstCharUpper=%s" % firstCharUpper)
          restChars = eachPara[1:]
          CommonUtil.logDebug("restChars=%s" % restChars)
          validPara = "the%s%s" % (firstCharUpper, restChars)
        else:
          validPara = eachPara

        CommonUtil.logDebug("validPara=%s" % validPara)
        newValidParaList.append(validPara)

    CommonUtil.logDebug("newValidParaList=%s" % newValidParaList)

    newParaTypeNameList = []
    newParaTypeNameList.append(paraObj)
    newParaTypeNameList.append(paraSelector)
    for eachValidPara in newValidParaList:
      eachParaType = "id"
      eachParaStr = "%s %s" % (eachParaType, eachValidPara)
      newParaTypeNameList.append(eachParaStr)
    CommonUtil.logDebug("newParaTypeNameList=%s" % newParaTypeNameList)
    newAllParaStr = ", ".join(newParaTypeNameList)
    CommonUtil.logDebug("newAllParaStr=%s" % newAllParaStr)
    newFuncType = "%s %s(%s)" % (retType, notUseNewFuncName, newAllParaStr)
    CommonUtil.logDebug("newFuncType=%s" % newFuncType)
  else:
    isOmit = True

  if newFuncType:
    # # for debug
    # print("Test to change type: [0x%X] %s -> %s" % (funcAddr, oldFuncType, newFuncType))

    # # for debug: no change type
    # newFuncType = oldFuncType

    setTypeRet = idc.SetType(funcAddr, newFuncType)
    # print("type(setTypeRet)=%s" % type(setTypeRet)) # bool
    CommonUtil.logDebug("setTypeRet=%s" % setTypeRet)

    changeTypeResultDict["address"] = funcAddrStr
    changeTypeResultDict["type"] = {
      "old": oldFuncType,
      "new": newFuncType
    }

    # if setTypeRet == 1:
    if setTypeRet:
      isChangeTypeOk = True
    else:
      isChangeTypeOk = False
      changeTypeResultDict["type"]["setTypeRet"] = setTypeRet

  CommonUtil.logDebug("isOmit=%s, isChangeTypeOk=%s, changeTypeResultDict=%s" % (isOmit, isChangeTypeOk, changeTypeResultDict))
  return isOmit, isChangeTypeOk, changeTypeResultDict

def propcessSingleFunction(funcAddr):
  global toRenameNum, renameOmitNum, renameOkNum, renameFailNum
  global toChangeTypeNum, changeTypeOkNum, changeTypeFailNum
  if isExportResult:
    global okList, failList

    okItemDict = {}
    failItemDict = {}

  funcAddrStr = "0x%X" % funcAddr

  toRenameNum += 1
  isOmitted, omitReason, isRenameOk, renamedResultDict = doFunctionRename(funcAddr)
  CommonUtil.logDebug("isOmitted=%s, omitReason=%s, isRenameOk=%s, renamedResultDict=%s" % (isOmitted, omitReason, isRenameOk, renamedResultDict))
  renameResultStr = ""

  if isOmitted:
    renameOmitNum += 1
    renameResultStr = "Omitted, %s" % omitReason
  else:
    oldFuncName = renamedResultDict["name"]["old"]

    if isRenameOk:
      renameOkNum += 1
      if isExportResult:
        okItemDict |= renamedResultDict

      renamedName = renamedResultDict["name"]["new"]
      renameResultStr = "OK, %s -> %s" % (oldFuncName, renamedName)
    else:
      renameFailNum += 1
      if isExportResult:
        failItemDict |= renamedResultDict

      newName = renamedResultDict["name"]["new"]
      retryName = renamedResultDict["name"]["retry"]
      renameResultStr = "Fail, %s -> %s / %s" % (oldFuncName, newName, retryName)

  print("[%s] Rename: %s" % (funcAddrStr, renameResultStr))

  toChangeTypeNum += 1
  isOmit, isChangeTypeOk, changeTypeResultDict = doFunctionChangeType(funcAddr)
  CommonUtil.logDebug("isOmit=%s, isChangeTypeOk=%s, changeTypeResultDict=%s" % (isOmit, isChangeTypeOk, changeTypeResultDict))

  if not isOmit:
    oldFuncType = changeTypeResultDict["type"]["old"]
    newFuncType = changeTypeResultDict["type"]["new"]
    changeTypeResultStr = ""
    if isChangeTypeOk:
      changeTypeResultStr = "OK"
      changeTypeOkNum += 1
      if isExportResult:
        okItemDict |= changeTypeResultDict
    else:
      changeTypeResultStr = "Fail"
      changeTypeFailNum += 1
      if isExportResult:
        failItemDict |= changeTypeResultDict

    print("[%s] SetType: %s, %s -> %s" % (funcAddrStr, changeTypeResultStr, oldFuncType, newFuncType))

  if isExportResult:
    CommonUtil.logDebug("okItemDict=%s, failItemDict=%s" % (okItemDict, failItemDict))

    if okItemDict:
      okList.append(okItemDict)

    if failItemDict:
      failList.append(failItemDict)

def main():
  global outputFolder

  for curNum, funcAddr in enumerate(toProcessFuncAddrList, start=1):
    funcAddrStr = "0x%X" % funcAddr
    CommonUtil.logMainStr("[%08d/%08d] %s" % (curNum, toProcessFuncAddrListNum, funcAddrStr))

    funcSize = IDAUtil.ida_getFunctionSize(funcAddr)
    CommonUtil.logDebug("funcSize=%s" % funcSize)
    if not isFuncSizeValid(funcSize):
      print("Omit [%s] for invalid function size %d" % (funcAddrStr, funcSize))
      continue

    propcessSingleFunction(funcAddr)

  CommonUtil.logMainStr("Summary Info")
  print("Total Functions num: %d" % len(allFuncAddrList))
  print("To process function num: %d" % toProcessFuncAddrListNum)
  print("  To rename num: %d" % toRenameNum)
  print("    Omit num: %d" % renameOmitNum)
  print("    OK num: %d" % renameOkNum)
  print("    fail num: %d" % renameFailNum)
  print("  To change type num: %d" % toChangeTypeNum)
  print("    OK num: %d" % changeTypeOkNum)
  print("    fail num: %d" % changeTypeFailNum)

  if isExportResult:
    CommonUtil.logMainStr("Export result to file")

    resultDict = {
      "ok": okList,
      "fail": failList,
    }

    outputFilename = "%s_IdaRenamedResult_%s.json" % (curBinFilename, curDateTimeStr)
    CommonUtil.logDebug("outputFilename=%s" % outputFilename)
    outputFullPath = os.path.join(outputFolder, outputFilename)
    CommonUtil.logDebug("outputFullPath=%s" % outputFullPath)

    print("Exporting result to file ...")
    print("  folder: %s" % outputFolder)
    print("  file: %s" % outputFilename)
    CommonUtil.saveJsonToFile(outputFullPath, resultDict)
    print("Exported: %s" % outputFullPath)

main()
