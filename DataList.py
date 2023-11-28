import logging
import os
import csv
import time
import vtk,qt

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin


#
# DataList
#

class DataList(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "DataList"  # TODO: make this more human readable by adding spaces
        self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Guqing Yu"]  # TODO: replace with "Firstname Lastname (Organization)"
       



class DataListWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

    def __init__(self, parent=None):

        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False





    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/DataList.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)
        uiWidget.setMRMLScene(slicer.mrmlScene)
        self.InitArguments()

        self.ui.tableWidget.cellClicked.connect(self.DataSelect)
        self.ui.tableWidget.setShowGrid(False)#隐藏表格
        self.ui.tableWidget.horizontalHeader().setSectionResizeMode(qt.QHeaderView.Stretch)#自适应宽
        # 3D视图测试数据
        self.mainWindowInit()
        self.initList()



    def InitArguments(self):
        self.DataType=None
        self.DataSetName=None
        self.FirstPath=None
        self.configFilsPath=None
        self.FirstID=None
        self.CurrentDataIndex = None
        self.PreDataIndex = None
        self.DataID = None

        self.IDs=[]
        self.FielPaths=[]

        settings = qt.QSettings("MyCompany", "MyApp")
        keys=settings.allKeys()
        allArguement=[]
        for key in keys:
            allArguement.append(settings.value(key))
        
        if '-n' in keys:
            self.DataSetName=settings.value('-n')

        if '-t' in keys:
            self.DataType=settings.value('-t')

        if '-i' in keys:
            self.FirstID=settings.value('-i')

        if '-p' in keys:
            self.FirstPath=settings.value('-p')

        if '-f' in keys:
            self.configFilsPath=settings.value('-f')
            self.read_config_file(self.configFilsPath)
        
        self.DataListNameLabel = slicer.util.mainWindow().findChild(qt.QLabel,"DataListName")
        self.DataListNameLabel.setText(self.DataSetName)
        self.DataIDLabel = slicer.util.mainWindow().findChild(qt.QLabel,"DataID")
        self.DataIDLabel.setText(self.FirstID)
        
        



    def read_config_file(self,file_path):
        if not os.path.exists(file_path):
            print(f"File '{file_path}' does not exist.")
            return []
        if file_path.endswith(".txt"):
            with open(file_path, 'r') as file:
                for line in file:
                    line = line.strip()  # 去除行尾的换行符和空格
                    data=line.split(',')
                    self.IDs.append(data[0])
                    self.FielPaths.append(data[1])
        else:
            # 打开 CSV 文件
            # 尝试使用 UTF-8 编码读取 CSV 文件
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    for row in reader:
                        # 处理每一行数据
                        self.IDs.append(row[0])
                        self.FielPaths.append(row[1])

            # 如果 UTF-8 解码失败，则尝试使用 GBK 编码
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='gbk') as file:
                    reader = csv.reader(file)
                    for row in reader:
                        # 处理每一行数据
                        self.IDs.append(row[0])
                        self.FielPaths.append(row[1])

        if self.FirstID:
            self.PreDataIndex = self.IDs.index(self.FirstID)
            self.CurrentDataIndex = self.IDs.index(self.FirstID)




    def mainWindowInit(self):
        # 隐藏工具栏等窗口
        slicer.util.setToolbarsVisible(0)
        slicer.util.setMenuBarsVisible(0)
        slicer.util.setPythonConsoleVisible(1)
        slicer.util.setStatusBarVisible(0)
        pane=slicer.util.findChild(slicer.util.mainWindow(),'PanelDockWidget')
        pane.hide()
        # 重建模块
        widget_Module=slicer.util.findChild(slicer.util.mainWindow(),'widget_Module')
        # 创建垂直布局管理器
        layout = qt.QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        # 将子窗口添加到布局中
        layout.addWidget(slicer.modules.segmenttool.widgetRepresentation().self().ui.widget_segment)
        # 将布局设置为父窗口的布局
        widget_Module.setLayout(layout)

        widget_PatientList=slicer.util.findChild(slicer.util.mainWindow(),'widget_PatientList')
        # 创建垂直布局管理器
        layout = qt.QVBoxLayout()
        layout.setContentsMargins(0,0,10,0)
        # 将子窗口添加到布局中
        layout.addWidget(self.ui.widget_list)
        # 将布局设置为父窗口的布局
        widget_PatientList.setLayout(layout)
        pane=slicer.util.findChild(slicer.util.mainWindow(),'PanelDockWidget')
        pane.hide()




    def initList(self):

        segmentTool = slicer.modules.segmenttool.widgetRepresentation().self()
        if self.DataType == '2d':#加载2D数据
            self.initTwoDList()
            self.DataLoad()
        elif self.DataType == "3d":#加载3D数据
            self.initThreeDList()   
            self.DataLoad()         
        elif self.DataType == "video":#加载视频
            segmentTool.ui.stackedWidget.setCurrentIndex(0)
            widget_PatientList=slicer.util.findChild(slicer.util.mainWindow(),'widget_PatientList')
            widget_PatientList.hide()
            self.IDs.append(self.FirstID)
            self.FielPaths.append(self.FirstPath)
            self.CurrentDataIndex=0
            self.initTwoDList()
            self.DataLoad()
        else:
            print('请输入正确参数')
        
    def initTwoDList(self):
        slicer.app.layoutManager().setLayout(6)      
        segmentTool = slicer.modules.segmenttool.widgetRepresentation().self()
        segmentTool.ui.stackedWidget.setCurrentIndex(0)
        self.ui.tableWidget.setRowCount(len(self.IDs))
        self.ui.tableWidget.setColumnCount(1)
        for i in range(len(self.IDs)):
            item_name = qt.QTableWidgetItem(str(self.IDs[i]))
            self.ui.tableWidget.setItem(i, 0, item_name)
        self.ui.tableWidget.setCurrentCell(self.CurrentDataIndex, 0)




    def initThreeDList(self):
        slicer.app.layoutManager().setLayout(0) 
        segmentTool = slicer.modules.segmenttool.widgetRepresentation().self()
        segmentTool.ui.stackedWidget.setCurrentIndex(1) 
        self.ui.tableWidget.setRowCount(len(self.IDs))
        self.ui.tableWidget.setColumnCount(1)
        for i in range(len(self.IDs)):
            item_name = qt.QTableWidgetItem(str(self.IDs[i]))
            self.ui.tableWidget.setItem(i, 0, item_name)
        self.ui.tableWidget.setCurrentCell(self.CurrentDataIndex, 0)


    def DataSelect(self,item=None):
        self.PreDataIndex = self.CurrentDataIndex
        segmentTool = slicer.modules.segmenttool.widgetRepresentation().self()
        
        if segmentTool.modifiedTime!=segmentTool.saveTime:
            message = qt.QMessageBox(qt.QMessageBox.Information,"确认","数据已修改，是否保存本页",qt.QMessageBox.NoButton)
            saveButton = message.addButton("保存并打开另一个",qt.QMessageBox().AcceptRole)
            openButton = message.addButton("不保存，打开另一个",qt.QMessageBox().AcceptRole)
            cancelButton = message.addButton("取消",qt.QMessageBox().RejectRole)
            message.exec()
            if message.clickedButton() == saveButton:
                print("保存并打开另一个")
                self.DataSave()
                self.CurrentDataIndex = self.ui.tableWidget.currentRow()
                self.DataLoad()
            elif message.clickedButton() == openButton:
                print("不保存，并打开另一个")
                self.CurrentDataIndex = self.ui.tableWidget.currentRow()
                self.DataLoad()
            elif message.clickedButton() == cancelButton:
                self.ui.tableWidget.setCurrentCell(self.PreDataIndex, 0)
        else:
            self.CurrentDataIndex = self.ui.tableWidget.currentRow()
            self.DataLoad()
        
        
        
    def getSavePath(self):
        path=self.FielPaths[self.CurrentDataIndex]
        # path=os.path.normpath(path)
        # path=path.replace('\\','/')
        file_name, file_extension = os.path.splitext(path)
        if self.DataType=='3d' and not (path.endswith('.nii')):
            if file_name[-1]=="/":
                file_name=file_name[0:-1]
            if file_name[-2:]=="//":
                file_name=file_name[0:-2]
            while file_name.endswith("\\"):
                file_name=file_name[0:-1]
            return file_name+'___mask.nii'
        return file_name+'___mask.nii'
        
    def DataSave(self):        
        # 获取当前的Segmentation节点
        segmentation_node = slicer.modules.segmenttool.widgetRepresentation().self().segmentationNode
        volumeNode=slicer.modules.segmenttool.widgetRepresentation().self().masterVolumeNode
        # 构建保存路径
        save_file_path = self.getSavePath()

        # Create a labelmap volume node from the segmentation
        labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(segmentation_node, labelmap_node,volumeNode)

        # 将Labelmap节点保存为NIfTI文件
        slicer.util.saveNode(labelmap_node, save_file_path)
        segmentTool = slicer.modules.segmenttool.widgetRepresentation().self()
        segmentTool.saveTime=time.time()
        segmentTool.modifiedTime=segmentTool.saveTime
    
    def DataLoad(self):
        #上一个及下一个可见性修改
        if self.CurrentDataIndex ==0:
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Last.setEnabled(False)
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Next.setEnabled(True)
        elif self.CurrentDataIndex == self.ui.tableWidget.rowCount-1:
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Next.setEnabled(False)
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Last.setEnabled(True)
        else:
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Next.setEnabled(True)
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Last.setEnabled(True)

        if self.CurrentDataIndex == self.ui.tableWidget.rowCount-1==0:
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Next.setEnabled(False)
            slicer.modules.segmenttool.widgetRepresentation().self().ui.Last.setEnabled(False)         

        #清空当前数据
        slicer.mrmlScene.Clear()
        #设置布局
        if self.DataType=='3d':
            slicer.app.layoutManager().setLayout(0)
            

        #加载数据
        if os.path.isdir(self.FielPaths[self.CurrentDataIndex]):
            dicomDataDir = self.FielPaths[self.CurrentDataIndex]
            loadedNodeIDs = []  
            from DICOMLib import DICOMUtils
            with DICOMUtils.TemporaryDICOMDatabase() as db:
                DICOMUtils.importDicom(dicomDataDir, db)
                patientUIDs = db.patients()
                for patientUID in patientUIDs:
                    loadedNodeIDs.extend(DICOMUtils.loadPatientByUID(patientUID))
        elif self.FielPaths[self.CurrentDataIndex].endswith('.png'):
            slicer.util.loadVolume(self.FielPaths[self.CurrentDataIndex])
        elif self.FielPaths[self.CurrentDataIndex].endswith('.nii'):
            slicer.util.loadVolume(self.FielPaths[self.CurrentDataIndex])
        #初始化分段
        segmentTool = slicer.modules.segmenttool.widgetRepresentation().self()
        segmentTool.initSegment()
        #判断mask是否存在
        mask_path = self.getSavePath()
        if os.path.exists(mask_path):
            #移除所有分段
            segmentTool.segmentationNode.GetSegmentation().RemoveAllSegments()
            labelmap_node = slicer.util.loadLabelVolume(mask_path)
            # 加载Segment到Segmentation节点
            slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(labelmap_node, segmentTool.segmentationNode)
            segmentTool.segmentId=segmentTool.segmentationNode.GetSegmentation().GetSegmentIdBySegmentName('1')
            segmentTool.segmentEditorWidget.setCurrentSegmentID(segmentTool.segmentId)
            slicer.mrmlScene.RemoveNode(labelmap_node)

        #更新id
        self.DataID=self.IDs[self.CurrentDataIndex]
        self.DataIDLabel.setText(self.DataID)
        #先前id
        self.PreDataIndex=self.CurrentDataIndex
        segmentTool.OnDataLoaded()
        #更新修改时间
        segmentTool.saveTime=time.time()
        segmentTool.modifiedTime=segmentTool.saveTime
            
    
    def loadTwoD(self,filePath):
        slicer.util.loadVolume(filePath)