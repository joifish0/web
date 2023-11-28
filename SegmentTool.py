import logging
import os
import time
import vtk,qt
import numpy as np
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin


#
# SegmentTool
#

class SegmentTool(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SegmentTool"  # TODO: make this more human readable by adding spaces
        self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Guoqi yu"]  # TODO: replace with "Firstname Lastname (Organization)"
       

#
# SegmentToolWidget
#

class SegmentSliceManager:
    def __init__(self, slice_name):
        self.slice_name = slice_name
        self.last_index = -1
        self.current_slice_index=-1
        self.modified_slice_indices = []
        #监听切片改变事件
        sliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNode%s" % self.slice_name)
        sliceNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.OnSliceChanged)
        if 'Red'==self.slice_name:
            self.slice_name_index=0
        elif 'Green'==self.slice_name:
            self.slice_name_index=1
        else:
            self.slice_name_index=2
        #初始化按钮
        layoutManager=slicer.app.layoutManager()
        self.sliceView=layoutManager.sliceWidget(self.slice_name).sliceView()
        self.copyButton=slicer.util.findChild(self.sliceView,'Copy')
        self.copyButton.connect("clicked(bool)",self.OnPast)
        # #添加位置观察者，设置按钮位置
        # layoutManager.layoutLogic().GetLayoutNode().AddObserver(vtk.vtkCommand.ModifiedEvent, self.OnSliceSizeChanged)



    #切换数据时，重新初始化
    def reinit(self):
        self.last_index = -1
        self.current_slice_index=-1
        self.modified_slice_indices = []
        self.copyButton.hide()



    def clear_modified_slices(self):
        self.modified_slice_indices = []
        self.last_index = -1

    def update_last_index(self):
        if self.current_slice_index==-1:
            self.OnSliceChanged()
        self.last_index = self.current_slice_index
        self.modified_slice_indices.append(self.last_index)
        self.copyButton.hide()


    # def OnSliceSizeChanged(self,arg1=None,arg2=None):
    #     self.copyButton.setGeometry(self.sliceView.width -100, self.sliceView.height-40, 90, 30)
    #     print('size:',self.sliceView.width -60, self.sliceView.height-40)



    #粘贴功能实现
    def OnPast(self):
        segmentationNode = slicer.SegmentEditorEffects.scriptedEffect.parameterSetNode().GetSegmentationNode()
        volumeNode = slicer.SegmentEditorEffects.scriptedEffect.parameterSetNode().GetSourceVolumeNode()
        seg = slicer.util.getNode("SegmentEditor")
        segmentID = seg.GetSelectedSegmentID()
        segmentArray = slicer.util.arrayFromSegmentBinaryLabelmap(segmentationNode, segmentID, volumeNode)
        ##segmentArray[-1,:,:]#为红色第一层
        #shape=segmentArray.shape[self.slice_name_index]
        if 'Red'==self.slice_name:
            segmentArrayCopyFrom=segmentArray[self.last_index,:,:]
            segmentArray[self.current_slice_index,:,:]=segmentArrayCopyFrom
            #print('从红色第',self.last_index,'层，沾入第',self.current_slice_index)
        elif 'Green'==self.slice_name:
            segmentArrayCopyFrom=segmentArray[:,self.last_index,:]
            segmentArray[:,self.current_slice_index,:]=segmentArrayCopyFrom
        else:
            segmentArrayCopyFrom=segmentArray[:,:,self.last_index]
            segmentArray[:,:,self.current_slice_index]=segmentArrayCopyFrom
        vtk_data = vtk.util.numpy_support.numpy_to_vtk(segmentArray.ravel(), 1, vtk.VTK_SHORT)
        selectedSegmentLabelmap = slicer.SegmentEditorEffects.scriptedEffect.selectedSegmentLabelmap()
        emptyLabelmap = slicer.vtkOrientedImageData()
        emptyLabelmap.ShallowCopy(selectedSegmentLabelmap)
        emptyLabelmap.CopyDirections(selectedSegmentLabelmap)
        emptyLabelmap.GetPointData().SetScalars(vtk_data)
        slicer.SegmentEditorEffects.scriptedEffect.modifySelectedSegmentByLabelmap(emptyLabelmap,
                                                                slicer.qSlicerSegmentEditorAbstractEffect.ModificationModeAdd)
        self.update_last_index()

    
    def OnSliceChanged(self,caler=None,event=None):
        # 获取当前切片索引
        try:
            widget = slicer.app.layoutManager().sliceWidget(self.slice_name)
            logic = widget.sliceLogic()
            self.current_slice_index=logic.GetSliceIndexFromOffset(logic.GetSliceOffset(),slicer.SegmentEditorEffects.scriptedEffect.parameterSetNode().GetSourceVolumeNode())-1

            # 根据当前切片索引是否存在于modifiedSliceIndices中显示或隐藏粘贴按钮
            if self.last_index != -1:
                if self.current_slice_index in self.modified_slice_indices:
                    # 隐藏粘贴按钮
                    self.copyButton.hide()
                else:
                    # 显示粘贴按钮
                    self.copyButton.show()
        except:
            print('数据未初始化')





class SegmentToolWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/SegmentTool.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)
        uiWidget.setMRMLScene(slicer.mrmlScene)


        #初始化切片控制
        self.redSliceManager = SegmentSliceManager('Red')
        self.greenSliceManager = SegmentSliceManager('Green')
        self.yellowSliceManager = SegmentSliceManager('Yellow')

        #初始化修改事件及保存时间
        self.saveTime=time.time()
        self.modifiedTime=self.saveTime



        #默认设置
        #设置默认布局
        slicer.app.layoutManager().setLayout(0)

        self.ui.TwoNoEditing.connect("clicked(bool)",self.OnNoEditing)
        self.ui.TwoDraw.connect("clicked(bool)",self.OnDraw)
        self.ui.TwoErase.connect("clicked(bool)",self.OnErase)
        self.ui.TwoUndo.connect("clicked(bool)",self.OnUndo)
        self.ui.TwoRedo.connect("clicked(bool)",self.OnRedo)


        self.ui.Save.connect("clicked(bool)",self.OnSave)
        self.ui.Last.connect("clicked(bool)",self.OnLast)
        self.ui.Next.connect("clicked(bool)",self.OnNext)

        self.ui.NoEditing.connect("clicked(bool)",self.OnNoEditing)
        self.ui.Draw.connect("clicked(bool)",self.OnDraw)
        self.ui.Paint.connect("clicked(bool)",self.OnPaint)
        self.ui.Erase.connect("clicked(bool)",self.OnErase)
        self.ui.LevelTracing.connect("clicked(bool)",self.OnLevelTracing)
        self.ui.FillBetweenSlice.connect("clicked(bool)",self.OnFillBetweenSlice)
        self.ui.Undo.connect("clicked(bool)",self.OnUndo)
        self.ui.Redo.connect("clicked(bool)",self.OnRedo)
        self.ui.BrushSlider.connect("valueChanged(double)",self.SetBrush)
        self.ui.ShowThreeD.connect("clicked(bool)",self.OnShowThreeD)
        self.ui.effectWidget.setVisible(0)


        #布局下拉菜单
        menuSelection = qt.QMenu(self.ui.Layout)
        FourUpAction = qt.QAction()
        GreenSliceOnlyAction = qt.QAction()
        RedSliceOnlyAction = qt.QAction()
        YellowSliceOnlyAction = qt.QAction()
        FourUpAction.setText("田字显示 Four-Up")
        GreenSliceOnlyAction.setText("Green slice only")
        RedSliceOnlyAction.setText("Red slice only")
        YellowSliceOnlyAction.setText("Yellow slice only")

        menuSelection.addAction(FourUpAction)
        menuSelection.addAction(GreenSliceOnlyAction)
        menuSelection.addAction(YellowSliceOnlyAction)
        menuSelection.addAction(RedSliceOnlyAction)
        #设置布局对应的索引
        FourUpAction.setObjectName(3)
        RedSliceOnlyAction.setObjectName(6)
        YellowSliceOnlyAction.setObjectName(7)
        GreenSliceOnlyAction.setObjectName(8)

        self.ui.Layout.setMenu(menuSelection)
        #设置下拉菜单的弹出方式
        self.ui.Layout.setPopupMode(qt.QToolButton.MenuButtonPopup)
        # self.ui.Layout.setToolButtonStyle(qt.Qt.ToolButtonTextBesideIcon)
        # self.ui.Layout.setDefaultAction(FourUpAction)
        

        FourUpAction.connect("triggered(bool)",lambda:self.SetLayout(FourUpAction))
        GreenSliceOnlyAction.connect("triggered(bool)",lambda:self.SetLayout(GreenSliceOnlyAction))
        RedSliceOnlyAction.connect("triggered(bool)",lambda:self.SetLayout(RedSliceOnlyAction))
        YellowSliceOnlyAction.connect("triggered(bool)",lambda:self.SetLayout(YellowSliceOnlyAction))
        
        self.ui.Crossing.connect("clicked(bool)",self.SetCrossing)
        self.ui.SliceIntersect.connect("clicked(bool)",self.SetSliceIntersect)

        #设置按钮图标
        iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')
        NoEditingPath = os.path.join(iconsPath,"NullEffect.png")
        DrawPath = os.path.join(iconsPath,"Draw.png")
        PaintPath = os.path.join(iconsPath,"Paint.png")
        ErasePath = os.path.join(iconsPath,"Erase.png")
        LevelTracingPath = os.path.join(iconsPath,"LevelTracing.png")
        FillBetweenSlicePath = os.path.join(iconsPath,"FillBetweenSlices.png")
        RedoPath = os.path.join(iconsPath,"Redo.png")
        UndoPath = os.path.join(iconsPath,"Undo.png")
        FourUpPath = os.path.join(iconsPath,"FourUp.png")
        GreenSliceOnlyPath = os.path.join(iconsPath,"GreenSliceOnly.png")
        RedSliceOnlyPath = os.path.join(iconsPath,"RedSliceOnly.png")
        YellowSliceOnlyPath = os.path.join(iconsPath,"YellowSliceOnly.png")
        CrossingPath = os.path.join(iconsPath,"Crossing.png")
        SliceIntesectPath = os.path.join(iconsPath,"SliceIntesect.png")
        SavePath = os.path.join(iconsPath,"Save.png")
        LayoutPath = os.path.join(iconsPath,"Layout.png")


        self.ui.NoEditing.setIcon(qt.QIcon(NoEditingPath))
        self.ui.Draw.setIcon(qt.QIcon(DrawPath))
        self.ui.Paint.setIcon(qt.QIcon(PaintPath))
        self.ui.Erase.setIcon(qt.QIcon(ErasePath))
        self.ui.LevelTracing.setIcon(qt.QIcon(LevelTracingPath))
        self.ui.FillBetweenSlice.setIcon(qt.QIcon(FillBetweenSlicePath))
        self.ui.Redo.setIcon(qt.QIcon(RedoPath))
        self.ui.Undo.setIcon(qt.QIcon(UndoPath))

        self.ui.Crossing.setIcon(qt.QIcon(CrossingPath))
        self.ui.SliceIntersect.setIcon(qt.QIcon(SliceIntesectPath))
        FourUpAction.setIcon(qt.QIcon(FourUpPath))
        GreenSliceOnlyAction.setIcon(qt.QIcon(GreenSliceOnlyPath))
        RedSliceOnlyAction.setIcon(qt.QIcon(RedSliceOnlyPath))
        YellowSliceOnlyAction.setIcon(qt.QIcon(YellowSliceOnlyPath))
        self.ui.TwoNoEditing.setIcon(qt.QIcon(NoEditingPath))
        self.ui.TwoDraw.setIcon(qt.QIcon(DrawPath))
        self.ui.TwoErase.setIcon(qt.QIcon(ErasePath))
        self.ui.TwoUndo.setIcon(qt.QIcon(UndoPath))
        self.ui.TwoRedo.setIcon(qt.QIcon(RedoPath))
        self.ui.Save.setIcon(qt.QIcon(SavePath))
        self.ui.Layout.setIcon(qt.QIcon(LayoutPath))
    

        



    def OnSegmentModified(self,sliceName):
        print(sliceName)
        if 'Red'==sliceName:
            self.redSliceManager.update_last_index()
        elif 'Green'==sliceName:
            self.greenSliceManager.update_last_index()
        else:
            self.yellowSliceManager.update_last_index()
        self.modifiedTime=time.time()




    def initSegment(self):
        self.masterVolumeNode = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLScalarVolumeNode')
        slicer.modules.segmenteditor.widgetRepresentation()
        slicer.modules.segmenteditor.widgetRepresentation().self().enter()
        self.segmentationNode = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLSegmentationNode')
        #self.segmentationNode.CreateDefaultDisplayNodes()
        self.segmentEditorWidget = slicer.modules.segmenteditor.widgetRepresentation().self().editor
        if len(slicer.util.getNodesByClass("vtkMRMLSegmentEditorNode")) > 0:
            self.segmentEditorNode = slicer.util.getNodesByClass("vtkMRMLSegmentEditorNode")[0]
        else:
            self.segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode')
        self.segmentEditorWidget.setMRMLSegmentEditorNode(self.segmentEditorNode)
        self.segmentEditorWidget.setSegmentationNode(self.segmentationNode)
        self.segmentEditorWidget.setSourceVolumeNode(self.masterVolumeNode)
        # 添加分段并选中
        self.segmentId = self.segmentationNode.GetSegmentation().AddEmptySegment("Segmentation")
        self.segmentEditorWidget.setCurrentSegmentID(self.segmentId)

    #鼠标
    def OnNoEditing(self):
        self.segmentEditorWidget.setActiveEffectByName(None)
        self.ui.effectWidget.setVisible(0)
    
    #画笔
    def OnDraw(self):
        self.segmentEditorWidget.setActiveEffectByName("Draw")
        self.ui.effectWidget.setVisible(0)
    
    #涂抹
    def OnPaint(self):       
        self.segmentEditorWidget.setActiveEffectByName("Paint")
        effect = self.segmentEditorWidget.activeEffect()
        value = self.ui.BrushSlider.value
        effect.setParameter("BrushRelativeDiameter",value)
        self.ui.effectWidget.setVisible(1)

    #橡皮
    def OnErase(self):
        self.segmentEditorWidget.setActiveEffectByName("Erase")
        effect = self.segmentEditorWidget.activeEffect()
        value = self.ui.BrushSlider.value
        effect.setParameter("BrushRelativeDiameter",value)
        self.ui.effectWidget.setVisible(1)

   
    #自动描边标注
    def OnLevelTracing(self):
        self.segmentEditorWidget.setActiveEffectByName("Level tracing")
        self.ui.effectWidget.setVisible(0)

    #切片填充
    def OnFillBetweenSlice(self):
        self.ui.effectWidget.setVisible(0)
        self.segmentEditorWidget.setActiveEffectByName("Fill between slices")
        effect = self.segmentEditorWidget.activeEffect()
        effect.self().onPreview()
        effect.self().onApply()
        self.ui.NoEditing.click()

    #设置涂抹和橡皮的笔刷大小
    def SetBrush(self,value):
        effect = self.segmentEditorWidget.activeEffect()
        effect.setParameter("BrushRelativeDiameter",value)  

    #撤销
    def OnUndo(self):
        self.segmentEditorWidget.undo()

    #重做
    def OnRedo(self):
        self.segmentEditorWidget.redo()

    #show 3D
    def OnShowThreeD(self):
        if self.ui.ShowThreeD.checked:
            self.segmentationNode.CreateClosedSurfaceRepresentation()
        else:
            self.segmentationNode.RemoveClosedSurfaceRepresentation()

    #保存
    def OnSave(self):
        message = qt.QMessageBox(qt.QMessageBox.Information,'确认',"是否保存本页                  ",qt.QMessageBox.Ok|qt.QMessageBox.Cancel)
        message.button(qt.QMessageBox().Ok).setText('是')
        message.button(qt.QMessageBox().Cancel).setText('否')
        message.setWindowIcon(slicer.util.mainWindow().windowIcon)
        c= message.exec()
        if c == qt.QMessageBox.Ok:
            slicer.modules.datalist.widgetRepresentation().self().DataSave()
            return
            
    #上一个
    def OnLast(self):
        
        DataListSelf = slicer.modules.datalist.widgetRepresentation().self()
        #若数据已保存，则直接跳转，否则弹窗
        if self.saveTime!=self.modifiedTime:
            message = qt.QMessageBox(qt.QMessageBox.Information,"确认","数据已修改，是否保存本页",qt.QMessageBox.NoButton)
            saveButton = message.addButton("保存并打开上一个",qt.QMessageBox().AcceptRole)
            openButton = message.addButton("不保存，打开上一个",qt.QMessageBox().AcceptRole)
            cancelButton = message.addButton("取消",qt.QMessageBox().RejectRole)
            message.setWindowIcon(slicer.util.mainWindow().windowIcon)
            message.exec()
            if message.clickedButton() == saveButton:
                DataListSelf.DataSave()
                DataListSelf.CurrentDataIndex = DataListSelf.CurrentDataIndex -1
                DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex,0)
                DataListSelf.DataLoad()
            elif message.clickedButton() == openButton:
                print("不保存，并打开另一个")
                DataListSelf.CurrentDataIndex = DataListSelf.CurrentDataIndex -1
                DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex,0)
                DataListSelf.DataLoad()
            elif message.clickedButton() == cancelButton:
                DataListSelf.CurrentDataIndex=DataListSelf.PreDataIndex
                DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex, 0)
        else:
            DataListSelf.CurrentDataIndex = DataListSelf.CurrentDataIndex -1
            DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex,0)
            DataListSelf.DataLoad()

    #下一个
    def OnNext(self):
        DataListSelf = slicer.modules.datalist.widgetRepresentation().self()
        #若数据已保存，则直接跳转，否则弹窗
        if self.saveTime!=self.modifiedTime:
            message = qt.QMessageBox(qt.QMessageBox.Information,"确认","是否保存本页",qt.QMessageBox.NoButton)
            saveButton = message.addButton("保存并打开下一个",qt.QMessageBox().AcceptRole)
            openButton = message.addButton("不保存，打开下一个",qt.QMessageBox().AcceptRole)
            cancelButton = message.addButton("取消",qt.QMessageBox().RejectRole)
            message.setWindowIcon(slicer.util.mainWindow().windowIcon)
            message.exec()
            if message.clickedButton() == saveButton:
                DataListSelf.DataSave()
                DataListSelf.CurrentDataIndex = DataListSelf.CurrentDataIndex +1
                DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex,0)

                DataListSelf.DataLoad()
            elif message.clickedButton() == openButton:
                print("不保存，并打开另一个")
                DataListSelf.CurrentDataIndex = DataListSelf.CurrentDataIndex +1
                DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex,0)

                DataListSelf.DataLoad()
            elif message.clickedButton() == cancelButton:
                DataListSelf.CurrentDataIndex=DataListSelf.PreDataIndex
                DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex, 0)
        else:
            DataListSelf.CurrentDataIndex = DataListSelf.CurrentDataIndex +1
            DataListSelf.ui.tableWidget.setCurrentCell(DataListSelf.CurrentDataIndex,0)
            DataListSelf.DataLoad()
        

    def OnDataLoaded(self):
        self.ui.NoEditing.click()
        self.redSliceManager.reinit()
        self.greenSliceManager.reinit()
        self.yellowSliceManager.reinit()
        self.ui.ShowThreeD.setChecked(0)
        self.ui.Crossing.setChecked(0)
        self.ui.SliceIntersect.setChecked(0)


    #根据布局索引设置布局
    def SetLayout(self,action):
        slicer.app.layoutManager().setLayout(int(action.objectName))
    
    #设置十字准线的显示和隐藏
    def SetCrossing(self):
        crosshairNode = slicer.util.getNode("Crosshair")
        if self.ui.Crossing.checked:
            crosshairNode.SetCrosshairMode(1)
        else:
            crosshairNode.SetCrosshairMode(0)


    #设置切片相交的显示和隐藏
    def SetSliceIntersect(self):
        appLogic = slicer.app.applicationLogic()
        if self.ui.SliceIntersect.checked:
            appLogic.SetIntersectingSlicesEnabled(slicer.vtkMRMLApplicationLogic.IntersectingSlicesVisibility,1)        
        else:
            appLogic.SetIntersectingSlicesEnabled(slicer.vtkMRMLApplicationLogic.IntersectingSlicesVisibility,0)

  
    def IsRedoUndo(self):
        segmentation_node = slicer.util.getSegmentationNode()
        # 检查是否有可重做的操作
        if segmentation_node.GetSegmentation().GetNumberOfUndoRedoItems() < 0:
            self.ui.Redo.setEnable(False)
        else:
            self.ui.Redo.SetEnabled(True)