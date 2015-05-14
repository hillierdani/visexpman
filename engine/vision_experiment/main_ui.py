import copy
import time
import numpy
import os.path
import itertools
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph
import pyqtgraph.console

from visexpman.engine.generic import stringop,utils,gui,signal,fileop,introspect
from visexpman.engine.vision_experiment import gui_engine, experiment
TOOLBAR_ICON_SIZE = 35

def get_icon(name):
    return QtGui.QIcon(os.path.join(fileop.visexpman_package_path(),'data', 'icons', '{0}.png'.format(name)))
    
class StimulusTree(pyqtgraph.TreeWidget):
    def __init__(self,parent, root):
        self.parent=parent
        self.root=root
        pyqtgraph.TreeWidget.__init__(self,parent)
        self.setColumnCount(1)
        self.setHeaderLabels(QtCore.QStringList(['']))#, 'Date Modified']))
        self.setMaximumWidth(350)
        self.populate()
        self.itemDoubleClicked.connect(self.stimulus_selected)
        self.itemSelectionChanged.connect(self.get_selected_stimulus)
#        self.timer=QtCore.QTimer()
#        self.timer.start(3000)#ms
#        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self._populate)
        
    def populate(self):
        files = fileop.find_files_and_folders(self.root)[1]
        files = [f for f in files if fileop.file_extension(f) =='py']
        experiment_configs = []
        for f in files:
            try:
                confnames = experiment.parse_stimulation_file(f).keys()
                experiment_configs.extend(map(os.path.join, [f]*len(confnames), confnames))
            except:
                pass#Ignoring py files with error
        #Clear tree view
        self.blockSignals(True)
        self.clear()
        #Populate with files and stimulus classes
        branches = [list(e.replace(self.root, '')[1:].split(os.sep)) for e in experiment_configs]
        added_items = {}
        for branch in branches:
            for level in range(len(branch)):
                if not added_items.has_key(level):
                    added_items[level] = []
                widgets = [w for w in added_items[level] if str(w.text(0)) == branch[level]]
                if len(widgets)==0:
                    newwidget=QtGui.QTreeWidgetItem([branch[level]])
                    if level==0:
                        self.addTopLevelItem(newwidget)
                    else:
                        try:
                            upper_widget = [w for w in added_items[level-1] if str(w.text(0)) == branch[level-1]][0]
                        except:
                            import pdb
                            pdb.set_trace()
                        upper_widget.addChild(newwidget)
                    added_items[level].append(newwidget)
        self.blockSignals(False)
        
    def stimulus_selected(self,selected_widget):
        if self._is_experiment_class(selected_widget):
            filename, classname = self.filename_from_widget(selected_widget)
            self.parent.to_engine.put({'function': 'open_stimulus_file', 'args':[filename, classname]})
            
    def select_stimulus(self, filename_classname):
        '''
        Selects stimulus class in file/class tree and expands the tree
        '''
        filename_classname = filename_classname.replace(self.root, '').split(os.sep)[1:]
        widget_ref = None
        for tli in self.topLevelItems():
            if str(tli.text(0)) == filename_classname[0]:
                widget_ref = tli
                widget_ref.setExpanded(True)
                for level in range(1, len(filename_classname)):
                    child_found=False
                    for childi in range(widget_ref.childCount()):
                        if widget_ref.child(childi) is None:
                            continue
                        if widget_ref.child(childi).text(0) == filename_classname[level]:
                            widget_ref.setExpanded(True)
                            widget_ref = widget_ref.child(childi)
                            child_found=True
                    if not child_found:
                        return
        if widget_ref is not None:
            self.setItemSelected(widget_ref, True)
        
    def get_selected_stimulus(self):
        selected_widget = self.selectedItems()
        if len(selected_widget)==0:
            self._give_not_stimulus_selected_warning()
            return
        else:
            selected_widget = selected_widget[0]
            if self._is_experiment_class(selected_widget):
                filename, classname = self.filename_from_widget(selected_widget)
                self.setHeaderLabels(QtCore.QStringList([classname]))
                self.parent.to_engine.put({'data': filename+os.sep+classname, 'path': 'stimulusbrowser/Selected experiment class', 'name': 'Selected experiment class'})
        
    def _is_experiment_class(self, widget):
        return not(widget.parent() is None or str(widget.parent().text(0))[-3:] != '.py')
        
    def filename_from_widget(self, widget, give_warning=True):
        if not self._is_experiment_class(widget) and give_warning:
            self._give_not_stimulus_selected_warning()
            return
        next_in_chain = widget
        items = []
        while True:
            if next_in_chain is not None and hasattr(next_in_chain, 'text'):
                items.append(str(next_in_chain.text(0)))
                next_in_chain = next_in_chain.parent()
            else:
                break
        classname = str(widget.text(0))
        items.reverse()
        filename = os.path.join(self.root, os.sep.join(items[:-1]))
        return filename, classname
        
    def _give_not_stimulus_selected_warning(self):
        QtGui.QMessageBox.question(self, 'Warning', 'No stimulus class selected. Please select one', QtGui.QMessageBox.Ok)
        

class ToolBar(QtGui.QToolBar):
    '''
    Toolbar holding the following shortcuts:
    -experiment start, stop, snap, live start, exit
    '''
    def __init__(self, parent):
        self.parent=parent
        QtGui.QToolBar.__init__(self, 'Toolbar', parent)
        self.add_buttons()
        self.setIconSize(QtCore.QSize(TOOLBAR_ICON_SIZE, TOOLBAR_ICON_SIZE))
        self.setFloatable(False)
        self.setMovable(False)
        
    def add_buttons(self):
        icon_folder = os.path.join(fileop.visexpman_package_path(),'data', 'icons')
        for button in ['start_experiment', 'stop', 'refresh_stimulus_files', 'find_cells', 'previous_roi', 'next_roi', 'delete_roi', 'add_roi', 'save_rois', 'delete_all_rois', 'exit']:
            a = QtGui.QAction(get_icon(button), stringop.to_title(button), self)
            a.triggered.connect(getattr(self.parent, button+'_action'))
            self.addAction(a)
            
    def hideEvent(self,e):
        self.setVisible(True)
        
class Progressbar(QtGui.QWidget):
    def __init__(self, maxtime, name = '', autoclose = False):
        self.maxtime = maxtime
        self.autoclose = autoclose
        QtGui.QWidget.__init__(self)
        self.setWindowTitle(name)
        self.progressbar = QtGui.QProgressBar(self)
        self.progressbar.setRange(0, maxtime)
        self.progressbar.setMinimumWidth(300)
        self.progressbar.setMinimumHeight(50)
        self.t0=time.time()
        self.timer=QtCore.QTimer()
        self.timer.start(200)#ms
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.update)
        
    def update(self):
        now=time.time()
        dt=now-self.t0
        if dt>self.maxtime:
            dt = self.maxtime
            self.timer.stop()
            if self.autoclose:
                self.close()
        self.progressbar.setValue(dt)

class RoiShift(gui.ArrowButtons):
    def __init__(self,parent):
        gui.ArrowButtons.__init__(self, 'Shift Rois', parent)
        
    def arrow_clicked(self, direction):
        h=0
        v=0
        if direction == 'left':
            h -= 1
        elif direction == 'right':
            h += 1
        elif direction == 'down':
            v -= 1
        elif direction == 'up':
            v += 1
        self.parent.parent.to_engine.put({'function': 'roi_shift', 'args':[h,v]})
        
class PythonConsole(pyqtgraph.console.ConsoleWidget):
    def __init__(self, parent):
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':parent.parent, 'utils':utils, 'fileop': fileop, 'signal':signal, 'numpy': numpy}, text = 'self: MainUI, numpy, utils, fileop, signal')
        
class Image(gui.Image):
    def __init__(self, parent, roi_diameter=3):
        gui.Image.__init__(self, parent, roi_diameter)
        self.setFixedWidth(parent.machine_config.GUI['SIZE']['col']/2)
        self.setFixedHeight(parent.machine_config.GUI['SIZE']['col']/2)
        self.plot.setLabels(left='um', bottom='um')
        self.connect(self, QtCore.SIGNAL('roi_mouse_selected'), parent.roi_mouse_selected)
            
class Debug(QtGui.QTabWidget):
    def __init__(self,parent):
        self.parent=parent
        QtGui.QTabWidget.__init__(self,parent)
        self.log = gui.TextOut(self)
        self.console = PythonConsole(self)
        self.addTab(self.log, 'Log')
        self.addTab(self.console, 'Console')
        self.setTabPosition(self.South)
        
class DataFileBrowser(gui.FileTree):
    def __init__(self,parent, root, extensions):
        gui.FileTree.__init__(self,parent, root, extensions)
        self.doubleClicked.connect(self.file_selected)
        self.setToolTip('Double click on file to open')
        
    def file_selected(self,index):
        filename = str(index.model().filePath(index))
        #Make compatible filename with win and linux systems
        filename = filename.replace('/', os.sep)
        filename = list(filename)
        filename[0] = filename[0].lower()
        filename = ''.join(filename)
        if os.path.isdir(filename): return#Double click on folder is ignored
        ext = fileop.file_extension(filename)
        if ext == 'hdf5':
            function = 'open_datafile'
            self.parent.to_engine.put({'function': 'keep_rois', 'args':[self.parent.analysis_helper.keep_rois.input.checkState()==2]})
            self.parent.analysis_helper.keep_rois.input.setCheckState(0)
        else:
            raise NotImplementedError(filename)
        self.parent.to_engine.put({'function': function, 'args':[filename]})

class TraceParameterPlots(QtGui.QWidget):
    def __init__(self, distributions):
        QtGui.QWidget.__init__(self)
        self.setWindowIcon(get_icon('main_ui'))
        self.distributions = distributions
        self.setWindowTitle('Parameter distributions')
        self.tab = QtGui.QTabWidget(self)
        self.plots = {}
        for par1,par2 in itertools.combinations(['rise', 'fall', 'drop', 'amplitude'],2):
            self.plots['{0}@{1}'.format(par1,par2)] = gui.Plot(self)
        for k in self.plots.keys():
            self.tab.addTab(self.plots[k], k)
        self.tab.setTabPosition(self.tab.South)
        self.nstd = gui.LabeledInput(self, 'n = ')
        self.nstd.input.setFixedWidth(50)
        self.nstd.input.setText('1')
        self.scale = QtGui.QPushButton('Scale to mean +/- n * std' ,parent=self)
        self.axis2scale = gui.LabeledComboBox(self, 'axis to scale',['both', 'x', 'y'])
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.tab,0,0,3,4)
        self.layout.addWidget(self.nstd,4,0,1,1)
        self.layout.addWidget(self.axis2scale,4,1,1,1)
        self.layout.addWidget(self.scale,4,2,1,1)
        self.setLayout(self.layout)
        self.setGeometry(10,10,700,400)
        self.update_plots()
        self.connect(self.scale, QtCore.SIGNAL('clicked()'), self.rescale)
        self.connect(self.axis2scale.input, QtCore.SIGNAL('currentChanged(int)'), self.rescale)
        
    def _plotname2distributionname(self,plotname):
        if self.distributions.has_key(plotname):
                ki=plotname
        else:
            ki = plotname.split('@')
            ki.reverse()
            ki = '@'.join(ki)
        return ki
        
    def update_plots(self):
        for k in self.plots.keys():
            ki=self._plotname2distributionname(k)
            self.plots[k].plot.setLabels(bottom=ki.split('@')[0], left =ki.split('@')[1])
            x=self.distributions[ki][0]
            y=self.distributions[ki][1]
            self.plots[k].update_curve(x, y, pen=None, plotparams = {'symbol' : 'o', 'symbolSize': 8, 'symbolBrush' : (0, 0, 0)})
        
    def rescale(self):
        plotname = self.plots.keys()[self.tab.currentIndex()]
        plot = self.plots[plotname]
        try:
            n = float(self.nstd.input.text())
        except:
            return
        x=self.distributions[self._plotname2distributionname(plotname)][0]
        y=self.distributions[self._plotname2distributionname(plotname)][1]
        axis2scale = str(self.axis2scale.input.currentText())
        if axis2scale == 'x' or axis2scale == 'both':
            mu,std = (x.mean(), n*x.std())
            plot.plot.setXRange(mu-std, mu+std)
        if axis2scale == 'y' or axis2scale == 'both':
            mu,std = (y.mean(), n*y.std())
            plot.plot.setYRange(mu-std, mu+std)

class AnalysisHelper(QtGui.QWidget):
    def __init__(self, parent):
        self.parent = parent
        QtGui.QWidget.__init__(self, parent)
        self.show_rois = gui.LabeledCheckBox(self, 'Show/hide rois')
        self.show_rois.input.setCheckState(2)
        self.keep_rois = gui.LabeledCheckBox(self, 'Keep rois')
        self.keep_rois.setToolTip('Check this it before opening next file and rois will be kept as a reference set and will be used for the next file')
        self.show_repetitions = gui.LabeledCheckBox(self, 'Show Repetitions')
        self.show_repetitions.input.setCheckState(2)
        self.find_repetitions = QtGui.QPushButton('Find repetitions' ,parent=self)
        self.show_trace_parameter_distribution = QtGui.QPushButton('Trace parameters' ,parent=self)
        self.roi_adjust = RoiShift(self)
        self.trace_parameters = QtGui.QLabel('', self)
#        self.trace_parameters.setFont(QtGui.QFont('Arial', 10))
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_rois,0,0,1,1)
        self.layout.addWidget(self.keep_rois,1,0,1,1)
        self.layout.addWidget(self.roi_adjust,0,1,2,2)
        self.layout.addWidget(self.trace_parameters,0,2,2,1)
        self.layout.addWidget(self.show_repetitions,0,3,1,1)
        self.layout.addWidget(self.find_repetitions,1,3,1,1)
        self.layout.addWidget(self.show_trace_parameter_distribution,2,3,1,1)
        self.setLayout(self.layout)
        self.setFixedHeight(140)
        self.setFixedWidth(550)
        self.connect(self.find_repetitions, QtCore.SIGNAL('clicked()'), self.find_repetitions_clicked)
        self.connect(self.show_trace_parameter_distribution, QtCore.SIGNAL('clicked()'), self.show_trace_parameter_distribution_clicked)
        
    def find_repetitions_clicked(self):
        self.parent.to_engine.put({'function': 'find_repetitions', 'args':[]})
        
    def show_trace_parameter_distribution_clicked(self):
        self.parent.to_engine.put({'function': 'display_trace_parameter_distribution', 'args':[]})

class MainUI(Qt.QMainWindow):
    def __init__(self, context):
        if QtCore.QCoreApplication.instance() is None:
            qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        self.setWindowIcon(get_icon('main_ui'))
        if os.path.exists('C:\\Users'):
            import ctypes
            myappid = 'visexpman main user interface' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        for c in ['machine_config', 'user_interface_name', 'socket_queues', 'warning', 'logger']:
            setattr(self,c,context[c])
        self._init_variables()
        self._start_engine()
        self.resize(self.machine_config.GUI['SIZE']['col'], self.machine_config.GUI['SIZE']['row'])
        self._set_window_title()
        #Set up toobar
        self.toolbar = ToolBar(self)
        self.addToolBar(self.toolbar)
        #Add dockable widgets
        self.debug = Debug(self)
#        self.debug.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/3)
        
        self._add_dockable_widget('Debug', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.debug)
        self.image = Image(self)
        self._add_dockable_widget('Image', QtCore.Qt.RightDockWidgetArea, QtCore.Qt.RightDockWidgetArea, self.image)
        self.plot = gui.Plot(self)
        self.plot.setMinimumWidth(self.machine_config.GUI['SIZE']['col']/2)
        self.plot.setMaximumWidth(self.image.width())
        self.plot.plot.setLabels(bottom='sec')
        self._add_dockable_widget('Plot', QtCore.Qt.BottomDockWidgetArea, QtCore.Qt.BottomDockWidgetArea, self.plot)
        
        self.stimulusbrowser = StimulusTree(self, fileop.get_user_module_folder(self.machine_config) )
        self.datafilebrowser = DataFileBrowser(self, self.machine_config.EXPERIMENT_DATA_PATH, ['hdf5', 'mat'])
        self.analysis_helper = AnalysisHelper(self)
        self.params = gui.ParameterTable(self, self.params_config)
        self.params.setMaximumWidth(500)
        self.params.params.sigTreeStateChanged.connect(self.parameter_changed)
        
        self.main_tab = QtGui.QTabWidget(self)
        self.main_tab.addTab(self.stimulusbrowser, 'Stimulus Files')
        self.main_tab.addTab(self.params, 'Parameters')
        self.main_tab.addTab(self.datafilebrowser, 'Data Files')
        self.main_tab.addTab(self.analysis_helper, 'Analysis')
        self.main_tab.setCurrentIndex(0)
        self.main_tab.setTabPosition(self.main_tab.South)
        
        self._add_dockable_widget('Main', QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.LeftDockWidgetArea, self.main_tab)
        self._load_all_parameters()
        self.show()
        self.timer=QtCore.QTimer()
        self.timer.start(50)#ms
        self.connect(self.timer, QtCore.SIGNAL('timeout()'), self.check_queue)
        self.connect(self.analysis_helper.show_rois.input, QtCore.SIGNAL('stateChanged(int)'), self.show_rois_changed)
        self.connect(self.analysis_helper.show_repetitions.input, QtCore.SIGNAL('stateChanged(int)'), self.show_repeptitions_changed)
        self.connect(self.main_tab, QtCore.SIGNAL('currentChanged(int)'),  self.tab_changed)
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def check_queue(self):
        while not self.from_engine.empty():
            msg = self.from_engine.get()
            if msg.has_key('printc'):
                self.printc(msg['printc'])
            elif msg.has_key('send_image_data'):
                self.meanimage, self.image_scale, self.tsync, self.timg = msg['send_image_data']
                self.image.remove_all_rois()
                self.image.set_image(self.meanimage, color_channel = 1)
                self.image.set_scale(self.image_scale)
            elif msg.has_key('show_suggested_rois'):
                self.image_w_rois = msg['show_suggested_rois']
                self.image.set_image(self.image_w_rois)
            elif msg.has_key('display_roi_rectangles'):
                self.image.remove_all_rois()
                [self.image.add_roi(r[0],r[1], r[2:], movable=False) for r in msg['display_roi_rectangles']]
                self.printc('Displaying {0} rois'.format(len(msg['display_roi_rectangles'])))
            elif msg.has_key('display_roi_curve'):
                timg, curve, index, tsync = msg['display_roi_curve']
                #Highlight roi
                self.image.highlight_roi(index)
                if isinstance(timg, list) and isinstance(curve, list):
                    self.plot.update_curves(timg, curve,plot_average = True)
                else:
                    #Update plot
                    self.plot.update_curve(timg, curve)
                self.plot.add_linear_region(*list(tsync))
            elif msg.has_key('remove_roi_rectangle'):
                 self.image.remove_roi(*list(msg['remove_roi_rectangle']))
            elif msg.has_key('fix_roi'):
                for r in self.image.rois:
                    r.translatable=False
            elif msg.has_key('ask4confirmation'):
                reply = QtGui.QMessageBox.question(self, 'Confirm following action', msg['ask4confirmation'], QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                self.to_engine.put(reply == QtGui.QMessageBox.Yes)
            elif msg.has_key('notify'):
                QtGui.QMessageBox.question(self, msg['notify']['title'], msg['notify']['msg'], QtGui.QMessageBox.Ok)
            elif msg.has_key('delete_all_rois'):
                self.image.remove_all_rois()
            elif msg.has_key('display_trace_parameters'):
                txt='\n'.join(['{0}: {1}'.format(stringop.to_title(k),'{0}'.format(v)[:4]) for k, v in msg['display_trace_parameters'].items()])
                self.analysis_helper.trace_parameters.setText(txt)
            elif msg.has_key('display_trace_parameter_distributions'):
                self.tpp = TraceParameterPlots(msg['display_trace_parameter_distributions'])
                self.tpp.show()
#                self.pb = Progressbar(10)
#                self.pb.show()
                
    def _init_variables(self):
        self.text = ''
        self.source_name = '{0}' .format(self.user_interface_name)
        imaging_channels = self.machine_config.PMTS.keys()
        imaging_channels.append('both')
        fw1=self.machine_config.FILTERWHEEL[0]['filters'].keys()
        fw1.sort()
        fw2=[] if len(self.machine_config.FILTERWHEEL)==1 else self.machine_config.FILTERWHEEL[1]['filters'].keys()
        fw2.sort()
        self.params_config = [
                {'name': 'Imaging', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Cell name', 'type': 'str', 'value': ''},
                    {'name': 'Scan height', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Scan width', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Pixel size', 'type': 'float', 'value': 1.0, 'siPrefix': True},
                    {'name': 'Pixel size unit', 'type': 'list', 'values': ['pixel/um', 'um/pixel', 'us'], 'value': 'pixel/um'},
                    {'name': 'Imaging channel', 'type': 'list', 'values': imaging_channels, 'value': imaging_channels[0]},
                    ]},
                {'name': 'Stimulus', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Filterwheel 1', 'type': 'list', 'values': fw1, 'value': ''},
                    {'name': 'Filterwheel 2', 'type': 'list', 'values': fw2, 'value': ''},
                    {'name': 'Grey level', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': '%'},
                    {'name': 'Projector on', 'type': 'bool', 'value': False},
                    {'name': 'Bullseye on', 'type': 'bool', 'value': False},
                    {'name': 'Bullseye size', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Bullseye shape', 'type': 'list', 'values': ['bullseye', 'spot', 'L', 'square'], 'value': 'bullseye'},
                    {'name': 'Stimulus center X', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                    {'name': 'Stimulus center Y', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                    ]},
                {'name': 'Analysis', 'type': 'group', 'expanded' : True, 'children': [
                    {'name': 'Baseline lenght', 'type': 'float', 'value': 1.0, 'siPrefix': True, 'suffix': 's'},
                    {'name': 'Background threshold', 'type': 'float', 'value': 10, 'siPrefix': True, 'suffix': '%'},
                    {'name': 'Cell detection', 'type': 'group', 'expanded' : False, 'children': [
                        {'name': 'Minimum cell radius', 'type': 'float', 'value': 2.0, 'siPrefix': True, 'suffix': 'um'},
                        {'name': 'Maximum cell radius', 'type': 'float', 'value': 3.0, 'siPrefix': True, 'suffix': 'um'},
                        {'name': 'Sigma', 'type': 'float', 'value': 1.0},
                        {'name': 'Threshold factor', 'type': 'float', 'value': 1.0}
                        ]
                    },
                    {'name': 'Trace statistics', 'type': 'group', 'expanded' : False, 'children': [
                        {'name': 'Mean of repetitions', 'type': 'bool', 'value': False},
                        {'name': 'Include all files', 'type': 'bool', 'value': False},
                        ]},
                    ]
                    },
                    {'name': 'Electrophysiology', 'type': 'group', 'expanded' : False, 'children': [
                        {'name': 'Electrophysiology channel', 'type': 'list', 'values': ['None', 'CH1', 'CH2'], 'value': 'None'},
                        {'name': 'Electrophysiology sampling rate', 'type': 'list', 'value': 10e3,  'values': [10e3, 1e3]},
                    ]},
                    {'name': 'Advanced', 'type': 'group', 'expanded' : False, 'children': [
                        {'name': 'Scanner', 'type': 'group', 'expanded' : True, 'children': [
                            {'name': 'Analog input sampling rate', 'type': 'float', 'value': 400.0, 'siPrefix': True, 'suffix': 'kHz'},
                            {'name': 'Analog output sampling rate', 'type': 'float', 'value': 400.0, 'siPrefix': True, 'suffix': 'kHz'},
                            {'name': 'Scan center x', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                            {'name': 'Scan center y', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'um'},
                            {'name': 'Stimulus flash duty cycle', 'type': 'float', 'value': 100.0, 'siPrefix': True, 'suffix': '%'},
                            {'name': 'Stimulus flash delay', 'type': 'float', 'value': 0.0, 'siPrefix': True, 'suffix': 'us'},
                            {'name': 'Enable flyback scan', 'type': 'bool', 'value': False},
                            {'name': 'Enable phase characteristics', 'type': 'bool', 'value': False},
                            {'name': 'Scanner position to voltage factor', 'type': 'float', 'value': 0.013},
                        ]},
                    ]}
                    ]
                



                                                                        
                                                                        

#                {'name': 'Basic parameter data types', 'type': 'group', 'children': [
#                {'name': 'Integer', 'type': 'int', 'value': 10},
#                {'name': 'Float', 'type': 'float', 'value': 10.5, 'step': 0.1},
#                {'name': 'String', 'type': 'str', 'value': "hi"},
##                {'name': 'List', 'type': 'list', 'values': [1,2,3], 'value': 2},
##                {'name': 'Named List', 'type': 'list', 'values': {"one": 1, "two": "twosies", "three": [3,3,3]}, 'value': 2},
#                {'name': 'Boolean', 'type': 'bool', 'value': True, 'tip': "This is a checkbox"},
##                {'name': 'Color', 'type': 'color', 'value': "FF0", 'tip': "This is a color button"},
#            ]},
#            {'name': 'Numerical Parameter Options', 'type': 'group', 'children': [
#                {'name': 'Units + SI prefix', 'type': 'float', 'value': 1.2e-6, 'step': 1e-6, 'siPrefix': True, 'suffix': 'V'},
#                {'name': 'Limits (min=7;max=15)', 'type': 'int', 'value': 11, 'limits': (7, 15), 'default': -6},
#                {'name': 'DEC stepping', 'type': 'float', 'value': 1.2e6, 'dec': True, 'step': 1, 'siPrefix': True, 'suffix': 'Hz'},
#        
#    ]}]
        
    def _start_engine(self):
        self.engine = gui_engine.GUIEngine(self.machine_config, self.logger)
        self.to_engine, self.from_engine = self.engine.get_queues()
        self.engine.start()
        
    def _stop_engine(self):
        self.to_engine.put('terminate')
        self.engine.join()
        
    def _set_window_title(self, animal_file=''):
        self.setWindowTitle('{0}{1}' .format(utils.get_window_title(self.machine_config), ' - ' + animal_file if len(animal_file)>0 else ''))
        
    def _write2statusbar(self,txt):
        self.statusbar.showMessage(txt)
        
    def _add_dockable_widget(self, title, position, allowed_areas, widget):
        dock = QtGui.QDockWidget(title, self)
        dock.setAllowedAreas(allowed_areas)
        dock.setWidget(widget)
        self.addDockWidget(position, dock)
        dock.setFeatures(dock.DockWidgetMovable | dock.DockWidgetClosable |dock.DockWidgetFloatable)
        
    def _get_parameter_tree(self):
        nodes = [[children for children in self.params.params.children()]]
        import itertools
        while True:
            nodes.append(list(itertools.chain(*[n.children() for n in nodes[-1]])))
            if len(nodes[-1])==0: break
        nodes = list(itertools.chain(*nodes))
        leafes = [n for n in nodes if len(n.children())==0]
        paths = []
        refs = []
        values = []
        for l in leafes:
            value = l.value()
            name = l.name()
            path = []
            ref= copy.deepcopy(l)
            while True:
                if ref.parent() is None: break
                else: 
                    path.append(ref.name())
                    ref= ref.parent()
            path.append('params')
            path.reverse()
            paths.append(path)
            values.append(value)
            refs.append(l)
        return values, paths, refs

    def _dump_all_parameters(self):#TODO: rename
        values, paths, refs = self._get_parameter_tree()
        for i in range(len(refs)):
            self.to_engine.put({'data': values[i], 'path': '/'.join(paths[i]), 'name': refs[i].name()})
            
    def _load_all_parameters(self):
        values, paths, refs = self._get_parameter_tree()
        paths = ['/'.join(p) for p in paths]
        for item in self.engine.guidata.to_dict():
            mwname = item['path'].split('/')[0]
            if mwname == 'params':
                r = refs[paths.index([p for p in paths if p == item['path']][0])]
                r.setValue(item['value'])
                r.setDefault(item['value'])
            elif mwname == 'stimulusbrowser':
                self.stimulusbrowser.select_stimulus(item['value'])
            else:
                ref = introspect.string2objectreference(self, 'self.'+item['path'].replace('/','.'))
                wname = ref.__class__.__name__.lower()
                if 'checkbox' in wname:
                    ref.setCheckState(2 if item['value'] else 0)
                elif 'qtabwidget' in wname:
                    ref.setCurrentIndex(item['value'])
                
    
    def printc(self, text, logonly = False):
        '''
        text is displayed on console and logged to logfile
        '''
        text = str(text)
        if not logonly:
            self.text  += utils.timestamp2hms(time.time()) + ' '  + text + '\n'
            self.debug.log.update(self.text)
        loglevels = ['warning', 'error']
        loglevel = [l for l in loglevels if l in text.lower()]
        if len(loglevel)>0:
            loglevel = loglevel[0]
            getattr(self.logger, loglevel)(text.replace('{0}: '.format(loglevel.upper()),''), self.source_name)
        else:
            self.logger.info(text, self.source_name)
    
    ############# Actions #############
    def start_experiment_action(self):
        self.to_engine.put({'function': 'start_experiment', 'args':[]})
        
    def stop_action(self):
        pass
        
    def refresh_stimulus_files_action(self):
        self.stimulusbrowser.populate()
        self.printc('Stimulus files and classes are refreshed.')
        
    def find_cells_action(self):
        self.to_engine.put({'function': 'find_cells', 'args':[]})
        
    def previous_roi_action(self):
        self.to_engine.put({'function': 'previous_roi', 'args':[]})

    def next_roi_action(self):
        self.to_engine.put({'function': 'next_roi', 'args':[]})
        
    def delete_roi_action(self):
        self.to_engine.put({'function': 'delete_roi', 'args':[]})
        
    def add_roi_action(self):
        '''
        Adds (all) manually placed roi(s)
        '''
        movable_rois = [r for r in self.image.rois if r.translatable]#Rois manually placed
        if len(movable_rois)>1:
            self.printc('Only one manually placed roi can be added!')
            return
        elif len(movable_rois)==0:
            self.printc('Put roi first on image!')
            return
        roi=movable_rois[0] 
        rectangle = [roi.x(), roi.y(),  roi.size().x(),  roi.size().y()]
        self.to_engine.put({'function': 'add_manual_roi', 'args':[rectangle]})
        
    def save_rois_action(self):
        '''Also exports to mat file'''
        self.to_engine.put({'function': 'save_rois_and_export', 'args':[]})
        
    def delete_all_rois_action(self):
        self.to_engine.put({'function': 'delete_all_rois', 'args':[]})
        
    def exit_action(self):
        if hasattr(self, 'tpp'):
            self.tpp.close()
        self._dump_all_parameters()
        self._stop_engine()
        self.close()
    
    ############# Events #############
    def show_rois_changed(self,state):
        if hasattr(self, 'image_w_rois'):
            im = numpy.copy(self.image_w_rois)
            im[:,:,2] *= state==2
            self.image.set_image(im)
            
    def show_repeptitions_changed(self,state):
        self.to_engine.put({'data': state==2, 'path': 'analysis_helper/show_repetitions/input', 'name': 'show_repetitions'})
        self.to_engine.put({'function': 'display_roi_curve', 'args':[]})
        
    def roi_mouse_selected(self,x,y):
        self.to_engine.put({'function': 'roi_mouse_selected', 'args':[x,y]})
    
    def parameter_changed(self, param, changes):
        self.send_widget_status()
        for change in changes:
            #find out tree
            ref = copy.deepcopy(change[0])
            tree = []
            while True:
                if hasattr(ref, 'name') and callable(getattr(ref, 'name')):
                    tree.append(getattr(ref, 'name')())
                    ref = copy.deepcopy(ref.parent())
                else:
                    break
            tree.reverse()
            self.to_engine.put({'data': change[2], 'path': '/'.join(tree), 'name': change[0].name()})
            
    def tab_changed(self,currentIndex):
        self.to_engine.put({'data': currentIndex, 'path': 'main_tab', 'name': 'Main Tab'})
            
    def send_widget_status(self):
        if hasattr(self, 'tpp'):
            self.to_engine.put({'function': 'update_widget_status', 'args': [{'tpp':self.tpp.isVisible()}]})

    def closeEvent(self, e):
        e.accept()
        self.exit_action()
    
if __name__ == '__main__':
    import visexpman.engine
    context = visexpman.engine.application_init(user = 'zoltan', config = 'CaImagingTestConfig', user_interface_name = 'main_ui', log_sources = ['engine'])
    
    context['logger'].start()
    m = MainUI(context=context)
    visexpman.engine.stop_application(context)
