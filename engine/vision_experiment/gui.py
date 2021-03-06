import shutil
import time,datetime
import numpy
import re
import Queue
import traceback
import os
import os.path
import webbrowser
import copy
import traceback
import tempfile

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

import pyqtgraph
import pyqtgraph.console

from visexpman.engine.vision_experiment import experiment_data
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.hardware_interface import network_interface
from visexpman.engine.hardware_interface import stage_control
from visexpman.engine import generic
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpA.engine.datadisplay import imaged
from visexpA.engine.datahandlers import matlabfile
from visexpA.engine.datahandlers import hdf5io
from visexpA.engine.datadisplay.plot import Qt4Plot
import visexpA.engine.component_guesser as cg

USERS=['','adrian','daniel','fiona','kamill','stuart','zoltan']
BUTTON_HIGHLIGHT = 'color: red'
ANESTHESIA_HISTORY_UPDATE_PERIOD = 60.0
BRAIN_TILT_HELP = 'Provide tilt degrees in text input box in the following format: vertical axis [degree],horizontal axis [degree]\n\
        Positive directions: horizontal axis: right, vertical axis: outer side (closer to user)'

ENABLE_SCAN_REGION_SERIALIZATION= False




class PythonConsole(pyqtgraph.console.ConsoleWidget):
    def __init__(self, parent, selfw = None):
        if selfw == None:
            selfw = parent.parent
        pyqtgraph.console.ConsoleWidget.__init__(self, namespace={'self':selfw, 'utils':utils,  'numpy': numpy}, text = 'self: main gui widget, numpy, utils, fileop, signal')

class Poller(QtCore.QThread):
    '''
    Generic poller thread that receives commands via queues and executes them. Additionally can access gui
    '''
    #Initializing, loader methods
    def __init__(self, parent):
        self.signal_id_queue = Queue.Queue() #signal parameter is passed to handler
        self.parent = parent
        self.config = self.parent.config
        QtCore.QThread.__init__(self)
        self.abort = False
        self.connect_signals()

    def connect_signals(self):
        self.parent.connect(self, QtCore.SIGNAL('printc'),  self.parent.printc)

    def init_run(self):
        pass

    def printc(self, text):
        self.emit(QtCore.SIGNAL('printc'), text)

    def run(self):
        self.init_run()
        self.last_time = time.time()
        startup_time = self.last_time
        while not self.abort:
            now = time.time()
            elapsed_time = now - self.last_time
            if elapsed_time > self.config.GUI_REFRESH_PERIOD:
                self.last_time = now
                self.periodic()
            self.run_in_all_iterations()
            self.handle_commands()
            self.handle_events()
            time.sleep(1e-1)
        self.close()
        self.printc('poller stopped')

    def run_in_all_iterations(self):
        pass
        
    def close(self):
        pass

    def periodic(self):
        pass

    def handle_commands(self):
        '''
        Handle commands coming via queues (mainly from network thread)
        '''
        pass

    def handle_events(self):
        '''
        Handle mapped signals that are connected to gui widgets
        '''
        if not self.signal_id_queue.empty():
            function_call = self.signal_id_queue.get()
            if hasattr(self, function_call):
                try:
                    getattr(self, function_call)()
                except:
                    self.printc(traceback.format_exc())
            else:
                self.printc('{0} method does not exists'.format(function_call))
        
    def pass_signal(self, signal_id):
        self.signal_id_queue.put(str(signal_id))
        
class FlowmeterControl(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Flowmeter control', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.start_button = QtGui.QPushButton('Start', self)
        self.stop_button = QtGui.QPushButton('Stop', self)
        self.reset_button = QtGui.QPushButton('Reset', self)
        self.status_label = QtGui.QLabel('', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.start_button, 0, 0)
        self.layout.addWidget(self.stop_button, 0, 1)
        self.layout.addWidget(self.reset_button, 0, 2)
        self.layout.addWidget(self.status_label, 0, 3)
        self.setLayout(self.layout)

class AnesthesiaHistoryGroupbox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Anesthesia history', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.history_label = QtGui.QLabel('', self)
        
        date_format = QtCore.QString('yyyy-MM-dd hh:mm')
        self.date = QtGui.QDateTimeEdit(self)
        self.date.setDisplayFormat(date_format)
        self.substance_label = QtGui.QLabel('Substance', self)
        self.substance_combobox = QtGui.QComboBox(self)
        self.substance_combobox.setEditable(True)
        self.substance_combobox.addItems(QtCore.QStringList(['', 'chlorprothixene', 'isofluorane']))
        self.amount_label = QtGui.QLabel('Amount', self)
        self.amount_combobox = QtGui.QComboBox(self)
        self.amount_combobox.setEditable(True)
        self.comment_label = QtGui.QLabel('Comment', self)
        self.comment_combobox = QtGui.QComboBox(self)
        self.comment_combobox.setEditable(True)
        self.add_button = QtGui.QPushButton('Add',  self)
        self.remove_button = QtGui.QPushButton('Remove last', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.history_label, 0, 0, 4, 5)
        self.layout.addWidget(self.date, 5, 0, 1, 1)
        self.layout.addWidget(self.substance_label, 5, 1)
        self.layout.addWidget(self.substance_combobox, 5, 2)
        self.layout.addWidget(self.amount_label, 5, 3)
        self.layout.addWidget(self.amount_combobox, 5, 4)
        self.layout.addWidget(self.comment_label, 6, 0)
        self.layout.addWidget(self.comment_combobox, 6, 1, 1, 2)
        self.layout.addWidget(self.add_button, 6, 3)
        self.layout.addWidget(self.remove_button, 6, 4)
        self.setLayout(self.layout)   
    
class MeasurementDatafileStatusGroupbox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Measurement data file status', parent)
        self.create_widgets()
        self.create_layout()
        
    def create_widgets(self):
        self.process_status_label = QtGui.QLabel('', self)
        self.ids_combobox = QtGui.QComboBox(self)
        self.ids_combobox.setEditable(True)
        self.remove_measurement_button = QtGui.QPushButton('Remove measurement',  self)
        self.set_state_to_button = QtGui.QPushButton('Set state to',  self)
        self.set_to_state_combobox = QtGui.QComboBox(self)
        self.set_to_state_combobox.addItems(QtCore.QStringList(['not processed', 'mesextractor_ready', 'find_cells_ready']))
        self.reset_jobhandler_button = QtGui.QPushButton('Reset jobhandler',  self)
        self.add_id_button = QtGui.QPushButton('Add id',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.ids_combobox, 1, 0)
        self.layout.addWidget(self.remove_measurement_button, 1, 1)
        self.layout.addWidget(self.set_state_to_button, 2, 0)
        self.layout.addWidget(self.set_to_state_combobox, 2, 1)
        self.layout.addWidget(self.reset_jobhandler_button, 0, 1)
        self.layout.addWidget(self.process_status_label, 3, 0, 4, 2)
        self.layout.addWidget(self.add_id_button, 0, 0)
        self.setLayout(self.layout)   

class ExperimentControlGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Experiment control', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        #Stimulation/experiment control related
        self.experiment_name = QtGui.QComboBox(self)
        self.experiment_name.setEditable(True)
        self.experiment_name.addItems(QtCore.QStringList([]))
        self.start_experiment_button = QtGui.QPushButton('Start experiment',  self)
        self.start_experiment_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.stop_experiment_button = QtGui.QPushButton('Stop experiment',  self)
        self.stop_experiment_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.next_depth_button = QtGui.QPushButton('Next',  self)
        self.redo_depth_button = QtGui.QPushButton('Redo',  self)
        self.previous_depth_button = QtGui.QPushButton('Prev',  self)
        self.graceful_stop_experiment_button = QtGui.QPushButton('Graceful stop experiment',  self)
#        self.identify_flourescence_intensity_distribution_button = QtGui.QPushButton('Fluorescence distribution',  self)
        self.objective_positions_label = QtGui.QLabel('Objective range [um]\n start,end,step',  self)
        self.objective_positions_combobox = QtGui.QComboBox(self)
        self.objective_positions_combobox.setEditable(True)
        self.laser_intensities_label = QtGui.QLabel('Laser intensity \n(min, max) [%]',  self)
        self.laser_intensities_combobox = QtGui.QComboBox(self)
        self.laser_intensities_combobox.setEditable(True)
        self.scan_mode = QtGui.QComboBox(self)
        self.scan_mode.addItems(QtCore.QStringList(['xy', 'xz']))

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_name, 0, 0, 1, 2)
        self.layout.addWidget(self.start_experiment_button, 0, 2, 1, 2)
        self.layout.addWidget(self.stop_experiment_button, 0, 4)
        self.layout.addWidget(self.graceful_stop_experiment_button, 0, 5)
        self.layout.addWidget(self.previous_depth_button, 1, 0, 1, 2)
        self.layout.addWidget(self.next_depth_button, 1, 4, 1, 1)
        self.layout.addWidget(self.redo_depth_button, 1, 2, 1, 2)
        self.layout.addWidget(self.scan_mode, 2, 0)
        self.layout.addWidget(self.objective_positions_label, 2, 1)
        self.layout.addWidget(self.objective_positions_combobox, 2, 2, 1, 2)
        self.layout.addWidget(self.laser_intensities_label, 2, 4, 1, 1)
        self.layout.addWidget(self.laser_intensities_combobox, 2, 5, 1, 1)
        self.setLayout(self.layout)        

class AnimalParametersWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])

    def create_widgets(self):
        import datetime
        default_date = QtCore.QDate(datetime.datetime.now().year, 1, 1)
        date_format = QtCore.QString('dd-MM-yyyy')
        ear_punch_items = QtCore.QStringList(['0',  '1',  '2'])                
        self.mouse_birth_date_label = QtGui.QLabel('Mouse birth date',  self)        
        self.mouse_birth_date = QtGui.QDateEdit(self)
        self.mouse_birth_date.setDisplayFormat(date_format)
        self.mouse_birth_date.setDate(default_date)
        self.gcamp_injection_date_label = QtGui.QLabel('GCAMP injection date',  self)
        self.gcamp_injection_date = QtGui.QDateEdit(self)
        self.gcamp_injection_date.setDisplayFormat(date_format)
        self.gcamp_injection_date.setDate(default_date)
        self.ear_punch_l_label = QtGui.QLabel('Ear punch L',  self)
        self.ear_punch_l = QtGui.QComboBox(self)
        self.ear_punch_l.addItems(ear_punch_items)
        self.ear_punch_r_label = QtGui.QLabel('Ear punch R',  self)
        self.ear_punch_r = QtGui.QComboBox(self)                
        self.ear_punch_r.addItems(ear_punch_items)
        self.gender_label = QtGui.QLabel('Gender',  self)
        self.gender = QtGui.QComboBox(self)        
        self.gender.addItems(QtCore.QStringList(['male', 'female']))
        self.id_label = QtGui.QLabel('ID',  self)
        self.id = QtGui.QComboBox(self)
        self.id.setEditable(True)
        self.mouse_strain_label = QtGui.QLabel('Mouse strain',  self)
        self.mouse_strain = QtGui.QComboBox(self)
        self.mouse_strain.addItems(QtCore.QStringList(['chatdtr', 'chat', 'bl6', 'grik4']))
        self.mouse_strain.setEditable(True)
        self.green_labeling_label = QtGui.QLabel('Green labeling',  self)
        self.green_labeling = QtGui.QComboBox(self)
        self.green_labeling.setEditable(True)
        self.green_labeling.addItems(QtCore.QStringList(self.config.GREEN_LABELING))
        self.red_labeling_label = QtGui.QLabel('Red labeling',  self)
        self.red_labeling = QtGui.QComboBox(self)
        self.red_labeling.setEditable(True)
        self.red_labeling.addItems(QtCore.QStringList(['no','yes']))
        self.comments = QtGui.QComboBox(self)
        self.comments.setEditable(True)
        self.comments.setToolTip('Add comment')
        self.imaging_channel_label = QtGui.QLabel('Record red and green channels?',  self)
        self.imaging_channel_checkbox = QtGui.QCheckBox(self)
        self.user_label = QtGui.QLabel('User',  self)
        self.user = QtGui.QComboBox(self)
        self.user.setEditable(True)
        self.user.addItems(QtCore.QStringList(USERS))
        self.new_mouse_file_button = QtGui.QPushButton('Create new mouse file',  self)
        self.anesthesia_history_groupbox = AnesthesiaHistoryGroupbox(self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.id_label, 0, 0)
        self.layout.addWidget(self.id, 0, 1)
        self.layout.addWidget(self.mouse_birth_date_label, 1, 0)
        self.layout.addWidget(self.mouse_birth_date, 2, 0)
        self.layout.addWidget(self.gcamp_injection_date_label, 3, 0)
        self.layout.addWidget(self.gcamp_injection_date, 4, 0)
        self.layout.addWidget(self.ear_punch_l_label, 1, 1)
        self.layout.addWidget(self.ear_punch_l, 2, 1)
        self.layout.addWidget(self.ear_punch_r_label, 3, 1)
        self.layout.addWidget(self.ear_punch_r, 4, 1)
        self.layout.addWidget(self.gender_label, 1, 2)
        self.layout.addWidget(self.gender, 2, 2)
        self.layout.addWidget(self.mouse_strain_label, 3, 2)
        self.layout.addWidget(self.mouse_strain, 4, 2)
        self.layout.addWidget(self.green_labeling_label, 5, 0)
        self.layout.addWidget(self.green_labeling, 5, 1)
        self.layout.addWidget(self.red_labeling_label, 5, 2)
        self.layout.addWidget(self.red_labeling, 5, 3)
        self.layout.addWidget(self.imaging_channel_label, 6, 0, 1, 2)
        self.layout.addWidget(self.imaging_channel_checkbox, 6, 2, 1, 1)
        self.layout.addWidget(self.comments, 7, 0, 1, 3)
        self.layout.addWidget(self.user_label, 8, 0, 1, 1)
        self.layout.addWidget(self.user, 8, 1, 1, 1)
        self.layout.addWidget(self.new_mouse_file_button, 9, 0, 1, 2)
        self.layout.addWidget(self.anesthesia_history_groupbox, 10, 0, 2, 4)
        self.layout.setRowStretch(10, 5)
        self.layout.setColumnStretch(5,10)
        self.setLayout(self.layout)
        
################### Image display #######################
class ImagesWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.OVERVIEW_IMAGE_SIZE['col'], self.config.OVERVIEW_IMAGE_SIZE['row'])
        
    def create_widgets(self):
        self.image_display = []
        for i in range(4):
            self.image_display.append(QtGui.QLabel())
        self.blank_image = 128*numpy.ones((self.config.IMAGE_SIZE['col'], self.config.IMAGE_SIZE['row']), dtype = numpy.uint8)
        for image in self.image_display:
            image.setPixmap(imaged.array_to_qpixmap(self.blank_image))
            
    def clear_image_display(self, index):
        self.image_display[index].setPixmap(imaged.array_to_qpixmap(self.blank_image))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        for i in range(len(self.image_display)):
            self.layout.addWidget(self.image_display[i], i/2, (i%2)*2, 1, 1)
        
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(3, 3)
        self.setLayout(self.layout)
        
class OverviewWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.image_display = QtGui.QLabel()
        blank_image = 128*numpy.ones((self.config.OVERVIEW_IMAGE_SIZE['col'], self.config.OVERVIEW_IMAGE_SIZE['row']), dtype = numpy.uint8)
        self.image_display.setPixmap(imaged.array_to_qpixmap(blank_image))
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.image_display, 0, 0, 1, 1)
        self.layout.setRowStretch(3, 3)
        self.layout.setColumnStretch(3, 3)
        self.setLayout(self.layout)
        
class ScanRegionGroupBox(QtGui.QGroupBox):
    def __init__(self, parent):
        QtGui.QGroupBox.__init__(self, 'Scan regions', parent)
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.select_mouse_file_label = QtGui.QLabel('Select mouse file', self)
        self.select_mouse_file = QtGui.QComboBox(self)
        self.animal_parameters_label = QtGui.QLabel('', self)
        self.get_xy_scan_button = QtGui.QPushButton('XY scan',  self)
        self.get_xy_scan_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.use_saved_scan_settings_label = QtGui.QLabel('Use saved scan settings', self)
        self.use_saved_scan_settings_settings_checkbox = QtGui.QCheckBox(self)
        self.add_button = QtGui.QPushButton('Add scan region',  self)
        self.scan_regions_combobox = QtGui.QComboBox(self)
        self.scan_regions_combobox.setEditable(True)
        self.remove_button = QtGui.QPushButton('Remove',  self)
        self.update_xy_button = QtGui.QPushButton('Update XY',  self)
        self.update_xz_button = QtGui.QPushButton('Update XZ',  self)
        self.update_xyt_button = QtGui.QPushButton('Update XYT',  self)
        self.move_to_button = QtGui.QPushButton('Move to',  self)
        self.region_info = QtGui.QLabel('',  self)
        self.move_to_region_options = {}
        self.move_to_region_options['header_labels'] = [ QtGui.QLabel('Move', self), QtGui.QLabel('Realign', self), QtGui.QLabel('Adjust origin', self)]
        self.move_to_region_options['row_labels'] = [ QtGui.QLabel('Stage', self), QtGui.QLabel('Objective', self)]
        self.move_to_region_options['checkboxes'] = {}
        self.move_to_region_options['checkboxes']['stage_move'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['stage_realign'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['stage_origin_adjust'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_move'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_move'].setEnabled(False)
        self.move_to_region_options['checkboxes']['objective_realign'] = QtGui.QCheckBox(self)
        self.move_to_region_options['checkboxes']['objective_origin_adjust'] = QtGui.QCheckBox(self)
        for k, v in self.move_to_region_options['checkboxes'].items():
#            if 'origin_adjust' not in k and 'objective_move' not in k:
            if 'stage_move' in k:
                v.setCheckState(2)
        self.xz_scan_button = QtGui.QPushButton('XZ scan',  self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.select_mouse_file_label, 0, 0, 1, 1)
        self.layout.addWidget(self.select_mouse_file, 0, 1, 1, 3)
        self.layout.addWidget(self.animal_parameters_label, 1, 0, 1, 4)
        self.layout.addWidget(self.use_saved_scan_settings_label, 3, 4, 1, 1)
        self.layout.addWidget(self.use_saved_scan_settings_settings_checkbox, 4, 4, 1, 1)
        self.layout.addWidget(self.get_xy_scan_button, 3, 3, 1, 1)
        self.layout.addWidget(self.xz_scan_button, 3, 2, 1, 1)
        self.layout.addWidget(self.add_button, 3, 0, 1, 1)
        self.layout.addWidget(self.scan_regions_combobox, 4, 0, 1, 2)
        self.layout.addWidget(self.region_info, 4, 3, 1, 1)
        self.layout.addWidget(self.remove_button, 5, 0, 1, 1)
        self.layout.addWidget(self.update_xy_button, 5, 1, 1, 1)
        self.layout.addWidget(self.update_xz_button, 5, 2, 1, 1)
        self.layout.addWidget(self.update_xyt_button, 5, 3, 1, 1)
        self.layout.addWidget(self.move_to_button, 4, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][0], 6, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][1], 6, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['header_labels'][2], 6, 3, 1, 1)
        self.layout.addWidget(self.move_to_region_options['row_labels'][0], 7, 0, 1, 1)
        self.layout.addWidget(self.move_to_region_options['row_labels'][1], 8, 0, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_move'], 7, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_realign'], 7, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['stage_origin_adjust'], 7, 3, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_move'], 8, 1, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_realign'], 8, 2, 1, 1)
        self.layout.addWidget(self.move_to_region_options['checkboxes']['objective_origin_adjust'], 8, 3, 1, 1)
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)
        
class RoiWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        self.scan_region_name_label = QtGui.QLabel()
        self.roi_info_image_display = QtGui.QLabel()
#        blank_image = 128*numpy.ones((self.config.ROI_INFO_IMAGE_SIZE['col'], self.config.ROI_INFO_IMAGE_SIZE['row']), dtype = numpy.uint8)
#        self.roi_info_image_display.setPixmap(imaged.array_to_qpixmap(blank_image))
        self.roi_plot = Qt4Plot()
        self.roi_plot.setMinimumHeight(230)
        self.select_cell_label = QtGui.QLabel('Select cell',  self)
        self.select_cell_combobox = QtGui.QComboBox(self)
        self.select_cell_combobox.setEditable(False)
        self.next_button = QtGui.QPushButton('>>',  self)
        self.previous_button = QtGui.QPushButton('<<',  self)
        self.accept_cell_button = QtGui.QPushButton('Accept cell',  self)
        self.accept_cell_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.ignore_cell_button = QtGui.QPushButton('Ignore cell',  self)
        self.cell_filter_name_combobox = QtGui.QComboBox(self)
        self.cell_filter_name_combobox.addItems(QtCore.QStringList(['No filter', 'depth', 'id', 'date', 'stimulus']))
        self.cell_filter_combobox = QtGui.QComboBox(self)
        self.show_current_soma_roi_label = QtGui.QLabel('Show current soma roi',  self)
        self.show_current_soma_roi_checkbox = QtGui.QCheckBox(self)
        self.show_current_soma_roi_checkbox.setCheckState(2)
        self.show_selected_soma_rois_label = QtGui.QLabel('Show selected soma rois',  self)
        self.show_selected_soma_rois_checkbox = QtGui.QCheckBox(self)
        self.show_selected_roi_centers_label = QtGui.QLabel('Show selected roi centers',  self)
        self.show_selected_roi_centers_checkbox = QtGui.QCheckBox(self)
        self.show_selected_roi_centers_checkbox.setCheckState(2)
        self.xz_line_length_label = QtGui.QLabel('XZ line length',  self)
        self.xz_line_length_combobox = QtGui.QComboBox(self)
        self.xz_line_length_combobox.setEditable(True)
        self.xz_line_length_combobox.setEditText(str(self.config.XZ_SCAN_CONFIG['LINE_LENGTH']))
        self.cell_merge_distance_label =  QtGui.QLabel('Cell merge distance [um]',  self)
        self.cell_merge_distance_combobox = QtGui.QComboBox(self)
        self.cell_merge_distance_combobox.setEditable(True)
        self.cell_merge_distance_combobox.setEditText(str(self.config.CELL_MERGE_DISTANCE))
        self.cell_group_label =  QtGui.QLabel('Cell group name',  self)
        self.cell_group_combobox = QtGui.QComboBox(self)
        self.cell_group_combobox.setEditable(True)
        self.create_xz_lines_button = QtGui.QPushButton('XZ lines',  self)
        self.create_xz_lines_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.xy_scan_button = QtGui.QPushButton('XY scan',  self)
        self.xy_scan_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.suggested_depth_label = QtGui.QLabel('',  self)
        self.roi_pattern_parameters_label = QtGui.QLabel('ROI pattern parameters: pattern size, distance from center [um]',  self)
        self.roi_pattern_parameters_lineedit = QtGui.QComboBox(self)
        self.roi_pattern_parameters_lineedit.setEditable(True)
        self.roi_pattern_parameters_lineedit.setEditText('{0},{1}'.format(self.config.ROI_PATTERN_SIZE, self.config.ROI_PATTERN_RADIUS))
        self.cell_info = QtGui.QLabel('',  self)

    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        image_height_in_rows = 3
        
        self.layout.addWidget(self.scan_region_name_label, 0, 0, 1, 5)
#        self.layout.addWidget(self.roi_info_image_display, 1, 0, image_height_in_rows, 13)
        self.layout.addWidget(self.roi_plot, 1, 0, image_height_in_rows, 13)
        
        self.layout.addWidget(self.show_current_soma_roi_label, image_height_in_rows + 2, 8)
        self.layout.addWidget(self.show_current_soma_roi_checkbox, image_height_in_rows + 2, 9)
        self.layout.addWidget(self.show_selected_soma_rois_label, image_height_in_rows + 3, 8)
        self.layout.addWidget(self.show_selected_soma_rois_checkbox, image_height_in_rows + 3, 9)
        self.layout.addWidget(self.show_selected_roi_centers_label, image_height_in_rows + 4, 8)
        self.layout.addWidget(self.show_selected_roi_centers_checkbox, image_height_in_rows + 4, 9)
        self.layout.addWidget(self.xy_scan_button, image_height_in_rows + 5, 8)
        
        self.layout.addWidget(self.select_cell_label, image_height_in_rows + 2, 0)
        self.layout.addWidget(self.select_cell_combobox, image_height_in_rows + 2, 1, 1, 3)        

        self.layout.addWidget(self.previous_button, image_height_in_rows + 2, 4)
        self.layout.addWidget(self.accept_cell_button, image_height_in_rows + 2, 5)
        self.layout.addWidget(self.ignore_cell_button, image_height_in_rows + 2, 6)
        self.layout.addWidget(self.next_button, image_height_in_rows + 2, 7)
        
        self.layout.addWidget(self.cell_filter_name_combobox, image_height_in_rows + 3, 0, 1, 1)
        self.layout.addWidget(self.cell_filter_combobox, image_height_in_rows + 3, 1, 1, 2)
#        self.layout.addWidget(self.cell_group_edit_label, image_height_in_rows + 3, 4)
#        self.layout.addWidget(self.cell_group_edit_combobox, image_height_in_rows + 3, 5)
        self.layout.addWidget(self.suggested_depth_label, image_height_in_rows + 3, 6, 1, 2)
        
        self.layout.addWidget(self.cell_group_label, image_height_in_rows + 5, 0)
        self.layout.addWidget(self.cell_group_combobox, image_height_in_rows + 5, 1, 1, 2)
        self.layout.addWidget(self.xz_line_length_label, image_height_in_rows + 6, 0)
        self.layout.addWidget(self.xz_line_length_combobox, image_height_in_rows + 6, 1)
        self.layout.addWidget(self.cell_merge_distance_label, image_height_in_rows + 6, 2)
        self.layout.addWidget(self.cell_merge_distance_combobox, image_height_in_rows + 6, 3)
        self.layout.addWidget(self.create_xz_lines_button, image_height_in_rows + 6, 4)
        self.layout.addWidget(self.roi_pattern_parameters_label, image_height_in_rows + 7, 0, 1, 4)
        self.layout.addWidget(self.roi_pattern_parameters_lineedit, image_height_in_rows + 7, 4)
        self.layout.addWidget(self.cell_info, image_height_in_rows + 8, 0, 1, 5)
        
        self.layout.setRowStretch(15, 15)
        self.layout.setColumnStretch(15, 15)
        self.setLayout(self.layout)

class MainWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        #MES related
        self.z_stack_button = QtGui.QPushButton('Create Z stack', self)
        self.resendjobs_button = QtGui.QPushButton('Resend Jobs', self)
        self.updatejobs_button = QtGui.QPushButton('Update Jobs', self)
        #Stage related
        self.experiment_control_groupbox = ExperimentControlGroupBox(self)
        self.scan_region_groupbox = ScanRegionGroupBox(self)
        self.measurement_datafile_status_groupbox = MeasurementDatafileStatusGroupbox(self)
        self.override_imaging_channels_label = QtGui.QLabel('Override Imaging Channels', self)
        self.override_imaging_channels_checkbox = QtGui.QCheckBox(self)
        self.record_red_channel_label = QtGui.QLabel('Record Red Channel', self)
        self.record_red_channel_checkbox = QtGui.QCheckBox(self)
        self.enable_prepost_scan_label = QtGui.QLabel('Enable Pre/Post scan', self)
        self.enable_prepost_scan_checkbox = QtGui.QCheckBox(self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.experiment_control_groupbox, 0, 0, 2, 4)
#        self.layout.addWidget(self.set_objective_value_button, 2, 8, 1, 1)        
        self.layout.addWidget(self.scan_region_groupbox, 4, 0, 2, 4)
        self.layout.addWidget(self.measurement_datafile_status_groupbox, 0, 4, 6, 2)
        
        self.layout.addWidget(self.z_stack_button, 9, 0, 1, 1)
        self.layout.addWidget(self.resendjobs_button, 9, 1, 1, 1)
        self.layout.addWidget(self.updatejobs_button, 9, 2, 1, 1)
        
        self.layout.addWidget(self.override_imaging_channels_label, 10, 0, 1, 1)
        self.layout.addWidget(self.override_imaging_channels_checkbox, 10, 1, 1, 1)
        self.layout.addWidget(self.record_red_channel_label, 10, 2, 1, 1)
        self.layout.addWidget(self.record_red_channel_checkbox, 10, 3, 1, 1)
        self.layout.addWidget(self.enable_prepost_scan_label, 10, 4, 1, 1)
        self.layout.addWidget(self.enable_prepost_scan_checkbox, 10, 5, 1, 1)
        
        self.layout.setRowStretch(11, 10)
        self.layout.setColumnStretch(11, 10)
        self.setLayout(self.layout)

################### Debug/helper widgets #######################
class HelpersWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        #generate connection name list
        self.connection_names = ['']
        for k, v in self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].items():
            if 'GUI' in k:
                self.connection_names.append(k.replace('GUI', '').replace('_', '').lower())
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.TAB_SIZE['col'], self.config.TAB_SIZE['row'])
        
    def create_widgets(self):
        #Helpers
        self.save_xy_scan_button = QtGui.QPushButton('Save xy image',  self)
        self.help_button = QtGui.QPushButton('Help',  self)
        self.override_enforcing_set_stage_origin_checkbox = QtGui.QCheckBox(self)
        self.override_enforcing_set_stage_origin_checkbox.setToolTip('Do not check for set stage origin')
        self.add_simulated_measurement_file_button = QtGui.QPushButton('Add simulated measurement file',  self)
        self.rebuild_cell_database_button = QtGui.QPushButton('Rebuild cell database button',  self)
        #Network related
        self.show_connected_clients_button = QtGui.QPushButton('Show connected clients',  self)
        self.show_network_messages_button = QtGui.QPushButton('Show network messages',  self)
        self.select_connection_list = QtGui.QComboBox(self)
        self.select_connection_list.addItems(QtCore.QStringList(self.connection_names))
        self.send_command_button = QtGui.QPushButton('Send command',  self)
        self.gui_test_button = QtGui.QPushButton('Gui test',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_connected_clients_button, 0, 0, 1, 1)
        self.layout.addWidget(self.show_network_messages_button, 0, 1, 1, 1)
        self.layout.addWidget(self.select_connection_list, 0, 2, 1, 1)
        self.layout.addWidget(self.send_command_button, 0, 3, 1, 1)
        
        self.layout.addWidget(self.save_xy_scan_button, 1, 0, 1, 1)
        self.layout.addWidget(self.help_button, 1, 1, 1, 1)
        self.layout.addWidget(self.override_enforcing_set_stage_origin_checkbox, 1, 2, 1, 1)
        self.layout.addWidget(self.add_simulated_measurement_file_button, 1, 3, 1, 1)
        self.layout.addWidget(self.rebuild_cell_database_button, 1, 4, 1, 1)
        
        self.layout.addWidget(self.gui_test_button, 2, 0)
        
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)

class CommonWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        #generate connection name list
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.COMMON_TAB_SIZE['col'], int(self.config.COMMON_TAB_SIZE['row']))
        
    def create_widgets(self):
        self.show_gridlines_label = QtGui.QLabel('Show gridlines', self)
        self.show_gridlines_checkbox = QtGui.QCheckBox(self)
        self.show_gridlines_checkbox.setCheckState(2)
        self.show_xzlines_label = QtGui.QLabel('Show xz lines', self)
        self.show_xzlines_checkbox = QtGui.QCheckBox(self)
        self.connected_clients_label = QtGui.QLabel('', self)
        self.set_stage_origin_button = QtGui.QPushButton('Set stage origin', self)
        self.set_stage_origin_button.setStyleSheet(QtCore.QString(BUTTON_HIGHLIGHT))
        self.read_stage_button = QtGui.QPushButton('Read stage', self)
        self.move_stage_button = QtGui.QPushButton('Move stage', self)
        self.tilt_brain_surface_button = QtGui.QPushButton('Tilt brain surface', self)
        self.tilt_brain_surface_button.setToolTip(BRAIN_TILT_HELP)
        self.enable_tilting_label = QtGui.QLabel('Enable tilting', self)
        self.enable_tilting_checkbox = QtGui.QCheckBox(self)
        self.enable_xy_scan_with_move_stage_label = QtGui.QLabel('XY scan after\n move stage', self)
        self.enable_xy_scan_with_move_checkbox = QtGui.QCheckBox(self)
        
        self.stop_stage_button = QtGui.QPushButton('Stop stage', self)
        self.set_objective_button = QtGui.QPushButton('Set objective', self)
        self.enable_reset_objective_origin_after_moving_label = QtGui.QLabel('Set objective to 0\n after moving it', self)
        self.enable_set_objective_origin_after_moving_checkbox = QtGui.QCheckBox(self)
        self.enable_intrinsic_label = QtGui.QLabel('Enable intrinsic', self)
        self.enable_intrinsic_checkbox = QtGui.QCheckBox(self)
        
        self.current_position_label = QtGui.QLabel('', self)
        
        self.registration_subimage_label = QtGui.QLabel('Registration subimage, upper left (x,y),\nbottom right (x,y) [um]', self)
        self.registration_subimage_combobox = QtGui.QComboBox(self)
        self.registration_subimage_combobox.setEditable(True)
        self.register_button = QtGui.QPushButton('Register', self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.show_gridlines_label, 0, 0)
        self.layout.addWidget(self.show_gridlines_checkbox, 0, 1)
        self.layout.addWidget(self.show_xzlines_label, 0, 2)
        self.layout.addWidget(self.show_xzlines_checkbox, 0, 3)
        self.layout.addWidget(self.connected_clients_label, 0,4, 1, 4)
        
        self.layout.addWidget(self.set_stage_origin_button, 2, 0, 1, 1)
        self.layout.addWidget(self.read_stage_button, 2, 1, 1, 1)
        self.layout.addWidget(self.move_stage_button, 2, 2, 1, 1)
        self.layout.addWidget(self.enable_xy_scan_with_move_stage_label, 2, 3, 1, 1)
        self.layout.addWidget(self.enable_xy_scan_with_move_checkbox, 2, 4, 1, 1)
        self.layout.addWidget(self.stop_stage_button, 2, 5, 1, 1)
        self.layout.addWidget(self.set_objective_button, 2, 6, 1, 1)
        self.layout.addWidget(self.enable_reset_objective_origin_after_moving_label, 2, 7, 1, 1)
        self.layout.addWidget(self.enable_set_objective_origin_after_moving_checkbox, 2, 8, 1, 1)
        
        self.layout.addWidget(self.enable_intrinsic_label, 2, 9, 1, 1)
        self.layout.addWidget(self.enable_intrinsic_checkbox, 2, 10, 1, 1)
        
        self.layout.addWidget(self.current_position_label, 0, 8, 1, 2)
        self.layout.addWidget(self.tilt_brain_surface_button, 1, 5, 1, 1)
        self.layout.addWidget(self.enable_tilting_label, 1, 0, 1, 1)
        self.layout.addWidget(self.enable_tilting_checkbox, 1, 1, 1, 1)
        
        self.layout.addWidget(self.registration_subimage_label, 1, 6, 1, 2)
        self.layout.addWidget(self.registration_subimage_combobox, 1, 8, 1, 3)
        self.layout.addWidget(self.register_button, 1, 11)
        
        self.layout.setRowStretch(10, 10)
        self.layout.setColumnStretch(10, 10)
        self.setLayout(self.layout)


class StandardIOWidget(QtGui.QWidget):
    def __init__(self, parent, config):
        QtGui.QWidget.__init__(self, parent)
        self.config = config
        self.create_widgets()
        self.create_layout()
        self.resize(self.config.STANDARDIO_WIDGET_TAB_SIZE['col'], self.config.STANDARDIO_WIDGET_TAB_SIZE['row'])
        
    def create_widgets(self):
        self.text_out = QtGui.QTextEdit(self)
        self.text_out.setPlainText('')
        self.text_out.setReadOnly(True)
        self.text_out.ensureCursorVisible()
        self.text_out.setCursorWidth(5)
        self.text_in = QtGui.QTextEdit(self)
        self.text_in.setToolTip('self.printc()')
        self.text_in.setFixedHeight(50)
        self.execute_python_button = QtGui.QPushButton('Execute python code',  self)
        self.clear_console_button = QtGui.QPushButton('Clear console',  self)
        
    def create_layout(self):
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.text_out, 0, 0, 30, 3)
        self.layout.addWidget(self.text_in, 1, 3, 1, 2)
        self.layout.addWidget(self.execute_python_button, 0, 3, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.addWidget(self.clear_console_button, 0, 4, 1, 1)#, alignment = QtCore.Qt.AlignTop)
        self.layout.setRowStretch(300, 300)
        self.layout.setColumnStretch(0, 100)
        self.setLayout(self.layout)
        
parameter_extract = re.compile('EOC(.+)EOP', re.DOTALL)
command_extract = re.compile('SOC(.+)EOC')

################### Poller #######################
class MainPoller(Poller):
    #Initializing, loader methods
    def __init__(self, parent):
        self.gui_thread_queue = Queue.Queue()
        Poller.__init__(self, parent)
        self.xz_scan_acquired = False
        self.stage_origin_set = False
        self.cell_status_changed_in_cache = False
        self.queues = {}
        self.queues['mouse_file_handler'] = Queue.Queue()
        self.init_network()
        self.mes_interface = mes_interface.MesInterface(self.config, self.queues, self.connections)
        self.init_variables()
        self.load_context()
        self.initialize_mouse_file()
        #Timer for updating process status
        self.process_status_timer = QtCore.QTimer()
        self.process_status_timer.timeout.connect(self.update_process_status)
        self.process_status_timer.start(10000)
        
    def update_process_status(self):
        try:
            if not hasattr(self, 'mouse_file'):
                return
            animalid= os.path.basename(self.mouse_file).split('_')[1]
            region=str(self.parent.get_current_region_name())
            user=str(self.animal_parameters['user'] if self.animal_parameters.has_key('user') else 'default_user')
            path=os.path.join('v:\\animals', user, '{0}_{1}.txt'.format(animalid,region))
            if os.path.exists(path):
                sig=sum([i for i in os.stat(path)])
                if not hasattr(self, 'lastmtime') or self.lastmtime!=sig or (hasattr(self, 'last_update') and time.time()-self.last_update>120):
                    txt=file.read_text_file(path)
                    self.lastmtime=sig
                    self.parent.main_widget.measurement_datafile_status_groupbox.process_status_label.setText('\n'.join(file.read_text_file(path).split('\n')[-20:]))
                    self.last_update=time.time()
            else:
                self.parent.main_widget.measurement_datafile_status_groupbox.process_status_label.setText('')
        except:
            self.printc(traceback.format_exc())
            
            
    def processstatus2gui(self):
        animalid= os.path.basename(self.mouse_file).split('_')[1]
        region=self.parent.get_current_region_name()
        user=self.animal_parameters['user'] if self.animal_parameters.has_key('user') else 'default_user'
        print 'v:\\animals', user, '{0}_{1}.txt'.format(animalid,region)
        path=os.path.join('v:\\animals', user, '{0}_{1}.txt'.format(animalid,region))
        if os.path.exists(path):
            self.parent.main_widget.measurement_datafile_status_groupbox.process_status_label.setText('\n'.join(file.read_text_file(path).split('\n')[-20:]))
        
    def connect_signals(self):
        Poller.connect_signals(self)
        self.parent.connect(self, QtCore.SIGNAL('mouse_file_list_changed'),  self.parent.mouse_file_list_changed)
        self.parent.connect(self, QtCore.SIGNAL('update_scan_regions'),  self.parent.update_scan_regions)
        self.parent.connect(self, QtCore.SIGNAL('show_image'),  self.parent.show_image)
        self.parent.connect(self, QtCore.SIGNAL('update_widgets_when_mouse_file_changed'),  self.parent.update_widgets_when_mouse_file_changed)
        self.parent.connect(self, QtCore.SIGNAL('ask4confirmation'),  self.parent.ask4confirmation)
        self.parent.connect(self, QtCore.SIGNAL('notify'),  self.parent.notify)
        self.parent.connect(self, QtCore.SIGNAL('select_cell_changed'),  self.parent.select_cell_changed)
    
    def init_run(self):
        self.connect_signals_to_widgets()
        
    def connect_signals_to_widgets(self):
        self.parent.connect(self, QtCore.SIGNAL('clear_image_display'), self.parent.images_widget.clear_image_display)
        
    def init_network(self):
        self.command_relay_server = network_interface.CommandRelayServer(self.config)
        self.connections = {}
        self.queues['mes'] = {}
        self.queues['mes']['out'] = Queue.Queue()
        self.queues['mes']['in'] = Queue.Queue()
        self.connections['mes'] = network_interface.start_client(self.config, 'GUI', 'GUI_MES', self.queues['mes']['in'], self.queues['mes']['out'])
        self.queues['stim'] = {}
        self.queues['stim']['out'] = Queue.Queue()
        self.queues['stim']['in'] = Queue.Queue()
        self.connections['stim'] = network_interface.start_client(self.config, 'GUI', 'GUI_STIM', self.queues['stim']['in'], self.queues['stim']['out'])
        self.queues['analysis'] = {}
        self.queues['analysis']['out'] = Queue.Queue()
        self.queues['analysis']['in'] = Queue.Queue()
        self.connections['analysis'] = network_interface.start_client(self.config, 'GUI', 'GUI_ANALYSIS', self.queues['analysis']['in'], self.queues['analysis']['out'])
    
    def init_jobhandler(self):
        if not self.jobhandler_reset_issued:
            status = self.command_relay_server.get_connection_status()
            if status['GUI_ANALYSIS/GUI'] and status['GUI_ANALYSIS/ANALYSIS']:
                self.reset_jobhandler()
                self.jobhandler_reset_issued = True
            
    def reset_jobhandler(self):
        self.queues['analysis']['out'].put('SOCreset_jobhandlerEOCEOP')
        
    def show_image(self, image, channel, scale, line = [], origin = None):
        self.emit(QtCore.SIGNAL('show_image'), image, channel, scale, line, origin)
        
    def update_scan_regions(self):
        self.emit(QtCore.SIGNAL('update_scan_regions'))
        
    def run_in_all_iterations(self):
        self.update_network_connection_status()
        
    def close(self):
        self.save_cells()
        if hasattr(self, 'mouse_file'):
            h = hdf5io.Hdf5io(self.config.CONTEXT_FILE,filelocking=False)
            h.last_region_name = self.parent.get_current_region_name()
            h.last_mouse_file_name = os.path.split(self.mouse_file)[1]
            h.save(['last_region_name', 'last_mouse_file_name'], overwrite = True)
            h.close()
            self.printc('Copy mouse file for jobhandler')
            
        self.printc('Wait till server is closed')
        self.queues['mes']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['stim']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.queues['analysis']['out'].put('SOCclose_connectionEOCstop_clientEOP')
        self.command_relay_server.shutdown_servers()
        #Delete MES tmp files
        try:
            for f in os.listdir(tempfile.gettempdir()):
               #print f, tempfile.gettempdir()
                fullpath = os.path.join(tempfile.gettempdir(), f)
                if '.mat' == fullpath[-4:] or '.hdf5' == fullpath[-5:]:
                    try:
                        os.remove(fullpath)
                        print (fullpath, 'removed')
                        self.printc((fullpath, 'removed'))
                    except:
                        print traceback.format_exc()
                        import pdb
                        pdb.set_trace()
        except:
            print traceback.format_exc()
            
        
        time.sleep(3.0)

    def periodic(self):
        #are_new_file, self.mouse_files = update_mouse_files_list(self.config, self.mouse_files)
        are_new_file=False
        if are_new_file:
            self.emit(QtCore.SIGNAL('mouse_file_list_changed'))
        #self.init_jobhandler()
        now = time.time()
        if now - self.prev_date_updated > ANESTHESIA_HISTORY_UPDATE_PERIOD:
            self.parent.update_anesthesia_history_date_widget()
            self.prev_date_updated = now
            #print time.time()

    def handle_commands(self):
        '''
        Handle commands coming via queues (mainly from network thread
        '''
        try:
            for k, queue in self.queues.items():                
                if hasattr(queue, 'has_key') and queue.has_key('in') and not queue['in'].empty():
                    messages = queue['in'].get()
                    if 'EOPSOC' in messages:
                        messages = messages.replace('EOPSOC','EOP@@@SOC').split('@@@')
                    else:
                        messages = [messages]
                    self.messages =messages 
                    for message in messages:
                        command = command_extract.findall(message)
                        if len(command) > 0:
                            command = command[0]
                        parameter = parameter_extract.findall(message)
                        self.p=parameter
                        if len(parameter) > 0:
                            parameter = parameter[0]
                        if command == 'connection':
                            message = command
                        elif command == 'echo' and parameter == 'GUI':
                            message = ''
                        elif message == 'connected to server':
                            #This is sent by the local queued client and its meaning can be confusing, therefore not shown
                            message = ''
                        elif message == 'SOCacquire_z_stackEOCOKEOP':
                            message = 'Z stack acquisition complete.'
                        elif message == 'SOCacquire_z_stackEOCsaveOKEOP' and os.path.exists(self.z_stack_path):
                            time.sleep(0.1)
                            self.z_stack = matlabfile.read_z_stack(self.z_stack_path)
                            self.read_stage(display_coords = False)
                            self.z_stack['stage_position'] = utils.pack_position(self.stage_position-self.stage_origin, 0)
                            self.z_stack['add_date'] = utils.datetime_string().replace('_', ' ')
                            hdf5io.save_item(self.mouse_file.replace('.hdf5', '_z_stack.hdf5'), 'z_stack', self.z_stack,filelocking=False)
                            self.printc('Z stack is saved to {0}' .format(z_stack_file_path))
                            os.remove(self.z_stack_path)
                        elif command == 'notify':
                            self.printc(parameter)
                            self.notify(parameter)
                        else:
                            self.printc(utils.time_stamp_to_hm(time.time()) + ' ' + k.upper() + ' '  +  message)
                            if 'error' in message.lower() and k.upper()=='STIM':
                                self.notify(message)
        except:
            self.printc(traceback.format_exc())
                
    def mouse_file_changed(self):
        self.wait_mouse_file_save()
        newmousefn=[fn for fn in list_mouse_files(self.config) if os.path.basename(fn)== str(self.parent.main_widget.scan_region_groupbox.select_mouse_file.currentText())][0]
        if newmousefn!=self.mouse_file:
            self.printc('Mouse file has changed to {0}'.format(newmousefn))
            self.mouse_file = newmousefn
            self.load_mouse_file()
    #        self.backup_mousefile()
            self.reset_jobhandler()
            self.emit(QtCore.SIGNAL('update_widgets_when_mouse_file_changed'))
        
    def pass_signal(self, signal_id):
        self.signal_id_queue.put(str(signal_id))
        
    ########## Manage context ###############
    def init_variables(self):
        self.files_to_delete = []
        self.jobhandler_reset_issued = False
        self.prev_date_updated = 0.0
        self.issued_ids = []
        
    def initialize_mouse_file(self):
        '''
        Finds out which mouse file to load and loadds data from it
        '''
        are_new_files, self.mouse_files, mouse_files_full = update_mouse_files_list(self.config)
        if len(self.mouse_files)>0:
            if self.last_mouse_file_name in self.mouse_files:
                mouse_file = self.last_mouse_file_name
            else:
                mouse_file = self.mouse_files[0]
#            self.mouse_file = [fn for fn in file.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH,extension='hdf5')[1] if os.path.basename(fn)== mouse_file][0]
            self.mouse_file = [fn for fn in mouse_files_full if os.path.basename(fn)== mouse_file][0]
            self.load_mouse_file()
            
    def load_mouse_file(self):
        '''
        Loads scan region, cell and meanimage data from mouse file
        '''
        if os.path.isfile(self.mouse_file):
            #Make a local copy
            self.local_mouse_file = os.path.join(tempfile.gettempdir(), os.path.split(self.mouse_file)[1])
            if os.path.exists(self.local_mouse_file):
                os.remove(self.local_mouse_file)
            shutil.copy(self.mouse_file, self.local_mouse_file)
            #clean out attributes
            attributes = ['scan_regions', 'cells', 'images', 'animal_parameters']
            for attribute in attributes:
                if hasattr(self, attribute):
                    setattr(self, attribute,  {})
            h = hdf5io.Hdf5io(self.local_mouse_file,filelocking=False)
            varname = h.find_variable_in_h5f('animal_parameters', regexp=True)[0]
            h.load(varname)
            self.animal_parameters = getattr(h, varname)
            self.printc('Loading scan regions')
            scan_regions = h.findvar('scan_regions')
            if scan_regions is None:
                self.scan_regions = {}
            else:
                if ENABLE_SCAN_REGION_SERIALIZATION:
                    if isinstance(scan_regions, dict) and isinstance(scan_regions.values()[0], dict):
                        self.scan_regions = copy.deepcopy(scan_regions)
                    elif hasattr(scan_regions.values()[0], 'dtype'):
                        self.scan_regions={}
                        for srn in scan_regions.keys():
                            self.scan_regions[srn] = utils.array2object(copy.deepcopy(scan_regions[srn]))
                else:
                    self.scan_regions = copy.deepcopy(scan_regions)
            if 0:
                self.printc('Loading cells')
                cells  = copy.deepcopy(h.findvar('cells'))#Takes long to load cells
                if cells is not None:
                    if hasattr(cells, 'dtype'):
                        self.cells = utils.array2object(cells)
                    else:
                        self.cells = cells
                self.printc('Loading mean images')
                images  = copy.deepcopy(h.findvar('images'))#Takes long to load images
                if images is not None:
                    self.images = images
            anesthesia_history = copy.deepcopy(h.findvar('anesthesia_history'))#Takes long to load images
            if anesthesia_history is not None:
                self.anesthesia_history = copy.deepcopy(anesthesia_history)
            h.close()
        
    def load_context(self):
        context_hdf5 = hdf5io.Hdf5io(self.config.CONTEXT_FILE,filelocking=False)
        context_hdf5.load('stage_origin')
        context_hdf5.load('stage_position')
        if hasattr(context_hdf5, 'stage_position') and hasattr(context_hdf5, 'stage_origin') :
            self.stage_origin = context_hdf5.stage_origin
            self.stage_position = context_hdf5.stage_position
        else:
            self.stage_position = numpy.zeros(3)
            self.stage_origin = numpy.zeros(3)
        self.xy_scan = context_hdf5.findvar('xy_scan')
        self.xz_scan = context_hdf5.findvar('xz_scan')
        self.last_region_name = context_hdf5.findvar('last_region_name')
        self.last_mouse_file_name = context_hdf5.findvar('last_mouse_file_name')
        context_hdf5.close()
        self.stage_position_valid = False
        self.scan_regions = {}
        
    def save_context(self):
        try:
            if 0:
                context_hdf5 = hdf5io.Hdf5io(self.config.CONTEXT_FILE,filelocking=False)
                context_hdf5.stage_origin = copy.deepcopy(self.stage_origin)
                context_hdf5.stage_position = copy.deepcopy(self.stage_position)
                context_hdf5.save('stage_origin',overwrite = True)
                context_hdf5.save('stage_position', overwrite = True)
                if hasattr(self,  'xy_scan'):
                    context_hdf5.xy_scan = copy.deepcopy(self.xy_scan)
                    context_hdf5.save('xy_scan', overwrite = True)
                if hasattr(self, 'xz_scan'):
                    context_hdf5.xz_scan = copy.deepcopy(self.xz_scan)
                    context_hdf5.save('xz_scan', overwrite = True)
                context_hdf5.close()
            else:#NOT TESTED
                import tempfile
                tmp_context_file=os.path.join(tempfile.gettempdir(),  'context.hdf5')
                if os.path.exists(tmp_context_file):
                    os.remove(tmp_context_file)
                context_hdf5 = hdf5io.Hdf5io(tmp_context_file,filelocking=False)
                context_hdf5.stage_origin = copy.deepcopy(self.stage_origin)
                context_hdf5.stage_position = copy.deepcopy(self.stage_position)
                context_hdf5.save('stage_origin',overwrite = True)
                context_hdf5.save('stage_position', overwrite = True)
                if hasattr(self,  'xy_scan'):
                    context_hdf5.xy_scan = copy.deepcopy(self.xy_scan)
                    context_hdf5.save('xy_scan', overwrite = True)
                if hasattr(self, 'xz_scan'):
                    context_hdf5.xz_scan = copy.deepcopy(self.xz_scan)
                    context_hdf5.save('xz_scan', overwrite = True)
#                context_hdf5.last_region_name = self.parent.get_current_region_name()
#                context_hdf5.last_mouse_file_name = os.path.split(self.mouse_file)[1]
                context_hdf5.close()
                import shutil
                os.remove(self.config.CONTEXT_FILE)
                shutil.move(tmp_context_file, self.config.CONTEXT_FILE)#Context file is always saved to new file
        except:
            self.printc(traceback.format_exc())
            self.printc('Context file NOT updated')
        
    ############## Measurement file handling ########################
    def add_cells_to_database(self, id, update_gui = True):
#        self.save_cells()
        region_name, measurement_file_path, info = self.read_scan_regions(id)
        #read cell info from measurement file
        h_measurement = hdf5io.Hdf5io(measurement_file_path,filelocking=False)
        scan_mode = h_measurement.findvar('call_parameters')['scan_mode']
        self.scan_regions[region_name]['process_status'][id]['find_cells_ready'] = True
        if scan_mode == 'xz':
            soma_rois = h_measurement.findvar('soma_rois')
            if soma_rois is not None:
                number_of_new_cells = len(soma_rois)
            else:
                number_of_new_cells = 0
            self.scan_regions[region_name]['process_status'][id]['info']['number_of_cells'] = number_of_new_cells
            h_measurement.close()
            #Save changes
            self.save2mouse_file('scan_regions')
            self.printc('{1} cells found in {0} but not added to database because it is an xz scan'.format(id, number_of_new_cells))
            if update_gui:
                self.parent.update_cell_list()
                self.parent.update_cell_filter_list()
                self.parent.update_jobhandler_process_status()
            return
        if not hasattr(self,  'images'):
            self.images = {}
        self.images[id] = {}
        self.images[id]['meanimage'] = h_measurement.findvar('meanimage')
        scale = h_measurement.findvar('image_scale')
        self.images[id]['scale'] = scale
        origin = h_measurement.findvar('image_origin')
        self.images[id]['origin'] = origin
        self.images = copy.deepcopy(self.images)
        if not hasattr(self,  'cells'):
            self.cells = {}
        if not self.cells.has_key(region_name):
            self.cells[region_name] = {}
        soma_rois = h_measurement.findvar('soma_rois')
        roi_centers = h_measurement.findvar('roi_centers')
        roi_plots = h_measurement.findvar('roi_plots')
        depth = int(numpy.round(h_measurement.findvar('position')['z'][0], 0))
        stimulus = h_measurement.findvar('stimulus_class')
        if soma_rois is None or len(soma_rois) == 0:
            number_of_new_cells = 0
        else:
            number_of_new_cells = len(soma_rois)
            if number_of_new_cells > 200:
                number_of_new_cells = 50
        self.scan_regions[region_name]['process_status'][id]['info']['number_of_cells'] = number_of_new_cells
        for i in range(number_of_new_cells):
            cell_id = ('{0}_{1}_{2:2}_{3}'.format(depth, id,  i, stimulus)).replace(' ', '0')
            self.cells[region_name][cell_id] = {}
            self.cells[region_name][cell_id]['depth'] = depth
            self.cells[region_name][cell_id]['id'] = id
            self.cells[region_name][cell_id]['soma_roi'] = soma_rois[i]
            self.cells[region_name][cell_id]['roi_center'] = roi_centers[i]
            self.cells[region_name][cell_id]['accepted'] = False
            self.cells[region_name][cell_id]['group'] = 'none'
            self.cells[region_name][cell_id]['add_date'] = utils.datetime_string().replace('_', ' ')
            self.cells[region_name][cell_id]['stimulus'] = stimulus
            self.cells[region_name][cell_id]['scale'] = scale
            self.cells[region_name][cell_id]['origin'] = origin
            self.cells[region_name][cell_id]['roi_plot'] = roi_plots[i]
            self.cells[region_name][cell_id]['cell_id'] = copy.deepcopy(cell_id)
        h_measurement.close()
        #Save changes
        self.save2mouse_file(['cells', 'scan_regions', 'images'])
        self.printc('{1} cells added from {0}'.format(id, number_of_new_cells))
        if update_gui:
            self.parent.update_cell_list()
            self.parent.update_cell_filter_list()
            self.parent.update_jobhandler_process_status()

    def set_process_status_flag(self, id, flag_names):
        region_name, measurement_file_path, info = self.read_scan_regions(id)
        if region_name is None:
            return
        id_not_found = False
        for flag_name in flag_names:
            if self.scan_regions[region_name]['process_status'].has_key(id):
                self.scan_regions[region_name]['process_status'][id][flag_name] = True
            else:
                id_not_found = True
        self.save2mouse_file('scan_regions')
        if id_not_found:
            self.printc('Unknown id ({0}), probably mouse file is changed', format(id))
        else:
            self.printc('Process status flag set: {1} -> {0}'.format(flag_names[0],  id))
        self.parent.update_jobhandler_process_status()
    
    def add_measurement_id(self, id):
        region_name, measurement_file_path, info = self.read_scan_regions(id)
        if region_name is None:
            return
        if not self.scan_regions[region_name].has_key('process_status'):
            self.scan_regions[region_name]['process_status'] = {}
        if self.scan_regions[region_name]['process_status'].has_key(id):
            if not self.ask4confirmation('ID ({0} already exists, do you want to reimport this measurement?' .format(id)):
                return
        self.scan_regions[region_name]['process_status'][id] = {}
        self.scan_regions[region_name]['process_status'][id]['fragment_check_ready'] = False
        self.scan_regions[region_name]['process_status'][id]['mesextractor_ready'] = False
        self.scan_regions[region_name]['process_status'][id]['find_cells_ready'] = False
        self.scan_regions[region_name]['process_status'][id]['info'] = {}
        self.scan_regions[region_name]['process_status'][id]['info'] = info
        self.save2mouse_file('scan_regions')
        self.printc('Measurement ID added: {0}'.format(id))
        self.parent.update_jobhandler_process_status()
        self.parent.update_file_id_combobox()
        
    def add_id(self):
        self.add_measurement_id(self.parent.get_current_file_id())
        
    def read_scan_regions(self, id):
        #read call parameters
        time.sleep(1.0)#Make sure that measurement file is not accessed any more
        measurement_file_path = file.get_measurement_file_path_from_id(id, self.config)
        if measurement_file_path is None or not os.path.exists(measurement_file_path):
            self.printc('Measurement file not found: {0}, {1}' .format(measurement_file_path,  id))
            return 3*[None]
        measurement_hdfhandler = hdf5io.Hdf5io(measurement_file_path,filelocking=False)
        fromfile = measurement_hdfhandler.findvar(['call_parameters', 'position', 'experiment_config_name'])
        call_parameters = fromfile[0]
        if not call_parameters.has_key('scan_mode'):
            self.printc('Scan mode does not exists')
            measurement_hdfhandler.close()
            return 3*[None]
        if call_parameters['intrinsic']:
            self.printc('Intrinsic recording session, not adding to automated analysis')
            measurement_hdfhandler.close()
            return 3*[None]
        laser_intensity = measurement_hdfhandler.findvar('laser_intensity', path = 'root.'+ '_'.join(cg.get_mes_name_timestamp(measurement_hdfhandler)))
        measurement_hdfhandler.close()
        info = {'depth': fromfile[1]['z'][0], 'stimulus':fromfile[2], 'scan_mode':call_parameters['scan_mode'], 'laser_intensity': laser_intensity}
        #Read the database from the mouse file pointed by the measurement file
        mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, call_parameters['mouse_file'])
        if not os.path.exists(mouse_file):
            self.printc('Mouse file ({0}) assigned to measurement ({1}) is missing' .format(mouse_file,  id))
            return 3*[None]
        if self.mouse_file != mouse_file:
            self.printc('Mouse file was changed from {0} to {1}'.format(mouse_file, self.mouse_file))
            return 3*[None]
#        if not self.scan_regions.has_key(call_parameters['region_name']):
#            self.printc('{0} region does not exits, probably mouse file was changed recently'.format(call_parameters['region_name']))
#            return 3*[None]
        if self.scan_regions[call_parameters['region_name']].has_key(id):
            self.printc('ID already exists: {0}'.format(id))
            return 3*[None]
        return call_parameters['region_name'], measurement_file_path, info
 
    def rebuild_cell_database(self):
        self.clear_process_status()
        measurement_file_paths = file.filtered_file_list(self.config.EXPERIMENT_DATA_PATH, ['fragment','hdf5'], fullpath = True,filter_condition='and')
        for measurement_path in measurement_file_paths:
            id = file.parse_fragment_filename(measurement_path)['id']
            flags = ['fragment_check_ready', 'mesextractor_ready']
            self.add_measurement_id(id)
            self.set_process_status_flag(id, flags)
            self.add_cells_to_database(id, update_gui = (measurement_file_paths[-1] == measurement_path))
        
    def clear_process_status(self):
        self.cells = {}
        for region_name in self.scan_regions.keys():
            self.scan_regions[region_name]['process_status'] = {}
        self.save2mouse_file(['scan_regions', 'cells'])
        
    def remove_measurement_file_from_database(self, id_to_remove = None, process_status_update = False):
        self.printc('Removing measurement id...')
        fields_to_save = []
        if id_to_remove is None:
            id_to_remove = self.parent.get_current_file_id()
        region_name = self.parent.get_current_region_name()
        if utils.safe_has_key(self.scan_regions, region_name) and not process_status_update and self.scan_regions[region_name]['process_status'].has_key(id_to_remove):
            del self.scan_regions[region_name]['process_status'][id_to_remove]
            fields_to_save.append('scan_regions')
            self.printc('Scan regions updated')
        if hasattr(self, 'images') and utils.safe_has_key(self.images, id_to_remove):
            del self.images[id_to_remove]
            fields_to_save.append('images')
            self.printc('Meanimages updated')
        if hasattr(self, 'cells') and utils.safe_has_key(self.cells, region_name):
            for cell_id in self.cells[region_name].keys():
                if id_to_remove in cell_id:
                    del self.cells[region_name][cell_id]
            fields_to_save.append('cells')
            self.printc('Cells updated')
        self.save2mouse_file(fields_to_save)
        if not process_status_update:
            self.parent.update_jobhandler_process_status()
            self.parent.update_file_id_combobox()
            self.parent.update_cell_list()
            self.parent.update_cell_filter_list()
            self.parent.update_meanimage()
            self.parent.update_cell_group_combobox()
            self.printc('{0} measurement is removed'.format(id_to_remove))
            
    def set_measurement_file_process_state(self):
        self.printc('Setting state of measurement id...')
        selected_id = self.parent.get_current_file_id()
        target_state = str(self.parent.main_widget.measurement_datafile_status_groupbox.set_to_state_combobox.currentText())
        region_name = self.parent.get_current_region_name()
        if target_state == any(['not processed', 'mesextractor_ready']):#remove cells, mean images and roi curves
            self.remove_measurement_file_from_database(id_to_remove = selected_id, keep_process_status_entry = True)
        #Modify process status
        if utils.safe_has_key(self.scan_regions, region_name) and self.scan_regions[region_name]['process_status'].has_key(selected_id):
            if target_state == 'not processed':
                self.scan_regions[region_name]['process_status'][selected_id]['mesextractor_ready'] = False
                self.scan_regions[region_name]['process_status'][selected_id]['fragment_check_ready'] = False
                self.scan_regions[region_name]['process_status'][selected_id]['find_cells_ready'] = False
            elif target_state == 'mesextractor_ready':
                self.scan_regions[region_name]['process_status'][selected_id]['find_cells_ready'] = False
            elif target_state == 'find_cells_ready':
                self.scan_regions[region_name]['process_status'][selected_id]['find_cells_ready'] = True
        self.save2mouse_file('scan_regions', wait_save = True)
        self.parent.update_jobhandler_process_status()
        self.parent.update_file_id_combobox()
        self.queues['analysis']['out'].put('SOCclear_joblistEOCEOP')
        self.printc('Measurement file status is updated')

    def next_cell(self):
        current_index = self.parent.roi_widget.select_cell_combobox.currentIndex()
        current_index += 1
        if current_index >= len(self.cell_ids):
            current_index = len(self.cell_ids)-1
            self.emit(QtCore.SIGNAL('select_cell_changed'))
        else:
            self.parent.roi_widget.select_cell_combobox.setCurrentIndex(current_index)
        
    def previous_cell(self):
        current_index = self.parent.roi_widget.select_cell_combobox.currentIndex()
        current_index -= 1
        if current_index < 0:
            current_index = len(self.cell_ids)-1
        self.parent.roi_widget.select_cell_combobox.setCurrentIndex(current_index)
        
    def accept_cell(self):
        self.select_cell(True)
        
    def ignore_cell(self):
        self.select_cell(False)
        
    def select_cell(self, selection):
        self.cells[self.parent.get_current_region_name()][self.parent.get_current_cell_id()]['accepted'] = selection
        if selection:
            cell_group_name = str(self.parent.roi_widget.cell_group_combobox.currentText())
            if cell_group_name == '':
                self.printc('No cell group name provided')
                return
            self.cells[self.parent.get_current_region_name()][self.parent.get_current_cell_id()]['group'] = cell_group_name
        self.next_cell()
        self.cell_status_changed_in_cache = True
        
    def calculate_suggested_depth(self):
        current_group = str(self.parent.roi_widget.cell_group_combobox.currentText())
        region_name = self.parent.get_current_region_name()
        if current_group != '' and self.cells.has_key(region_name):
            depths = [cell['depth'] for cell in self.cells[region_name].values() if cell['group'] == current_group]
            self.suggested_depth = numpy.round(numpy.array(list(set(depths))).mean(), 0)
        else:
            self.suggested_depth = numpy.nan
        
    def save_cells(self):
        if hasattr(self, 'cells') and self.cell_status_changed_in_cache:
            self.save2mouse_file('cells')
            self.parent.update_cell_group_combobox()
            self.cell_status_changed_in_cache = False
            self.printc('Cells saved')

################### Stage #######################
    def read_stage(self, display_coords = False):
        self.printc('Reading stage and objective position, please wait')
        result = False
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCreadEOP')
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], self.config.GUI_STAGE_TIMEOUT):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()
                if 'SOCstageEOC' in response:
                    self.stage_position = self.parse_list_response(response)
                    result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
                    if not result:
                        self.printc('MES does not respond')
                    if display_coords:
                        self.printc('rel: {0}, abs: {1}'.format(self.stage_position - self.stage_origin, self.stage_position))
                    else:
                        self.printc('Read stage ready')
                    self.save_context()
                    self.parent.update_position_display()
                    result = True
        else:
            self.printc('stage is not accessible')
        return result

    def set_stage_origin(self):
        result = False
        self.printc('Stage origin: {0}'.format(self.stage_origin))
        if not self.mes_interface.overwrite_relative_position(0, self.config.MES_TIMEOUT):
            self.printc('Setting objective to 0 did not succeed')
            return result
        if not self.stage_position_valid:
            self.read_stage(display_coords = False)
            self.stage_position_valid = True
        self.stage_origin = self.stage_position
        self.save_context()
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCoriginEOP')
        if utils.wait_data_appear_in_queue(self.queues['stim']['in'], 10.0):
            while not self.queues['stim']['in'].empty():
                response = self.queues['stim']['in'].get()
                if 'SOCstageEOC' in response:
                    self.printc('Origin set')
                    self.stage_origin_set = True
                    result = True
        self.origin_set = True
        self.parent.update_position_display()
        self.printc('Stage origin: {0}'.format(self.stage_origin))
        return result
        
    def tilt_brain_surface(self):
        if self.parent.common_widget.enable_tilting_checkbox.checkState() != 2:
            self.printc('Tilting NOT enabled')
            return
        self.parent.common_widget.enable_tilting_checkbox.setCheckState(0)
        movement = map(float, self.parent.scanc().split(','))
        if len(movement) != 2:
            self.printc('Invalid coordinates')
            return
        if abs(movement[0]) > self.config.TILTING_LIMIT or abs(movement[1]) > self.config.TILTING_LIMIT:
            self.printc('Requested tilting is too big')
            return
        if not self.ask4confirmation('Make surre that anesthesia tube not touching mouse nose'):
            return
        mg = stage_control.MotorizedGoniometer(self.config, id = 1)
        speed = 150#IDEA: speed may depend on movement
        if mg.set_speed(speed):
            time.sleep(1.0)
            result = mg.move(numpy.array(movement))
            if not result:
                self.printc('Tilting was NOT successful')
            else:
                self.printc('Tilting mouse successful')
                position, result = mg.read_position()
                if not result:
                    self.printc('New position is unknown')
                else:
                    self.printc('{0} degree'.format(position))
        else:
            self.printc('Setting goniometer speed was NOT successful')
        mg.release_instrument()
        
    def move_stage(self):
        movement = self.parent.scanc().split(',')
        if len(movement) == 2:
            #Only two values are accepted
            movement.append('0')
        else:
            self.printc('invalid coordinates')
            return
        #Disbaled: self.parent.main_widget.scan_region_groupbox.scan_regions_combobox.setEditText('')
        self.move_stage_relative(movement)
        if self.parent.common_widget.enable_xy_scan_with_move_checkbox.checkState() != 0:
            self.acquire_xy_scan()

    def move_stage_relative(self, movement):
        if hasattr(self, 'xy_scan'): #to avoid saving false data at saving regions
            del self.xy_scan
        if hasattr(self, 'xz_scan'):
            del self.xz_scan
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCset,{0},{1},{2}EOP'.format(movement[0], movement[1], movement[2]))
        self.printc('movement {0}, {1}'.format(movement[0], movement[1]))
        if not utils.wait_data_appear_in_queue(self.queues['stim']['in'], self.config.GUI_STAGE_TIMEOUT):
            self.printc('Stage does not respond, 1')
            return False
        while not self.queues['stim']['in'].empty():
            response = self.queues['stim']['in'].get()
            if 'SOCstageEOC' in response:
                self.stage_position = self.parse_list_response(response)
                self.save_context()
                self.parent.update_position_display()
                self.printc('New position rel: {0}, abs: {1}'.format(self.stage_position - self.stage_origin, self.stage_position))
                return True
        self.printc('Stage does not respond, 2')
        return False

    def stop_stage(self):
        utils.empty_queue(self.queues['stim']['in'])
        self.queues['stim']['out'].put('SOCstageEOCstopEOP')
        self.printc('Stage stopped')
        
    def resendjobs(self):
        self.queues['stim']['out'].put('SOCresendjobsEOCEOP')
        self.printc('Stim is requested to resend jobs to Jobhandler')

################### MES #######################
    def set_objective(self):
        try:
            position = float(self.parent.scanc())
        except ValueError:
            self.printc('No position is given')
            return
        if self.mes_interface.set_objective(position, self.config.MES_TIMEOUT):
            self.objective_position = position
            if self.parent.common_widget.enable_set_objective_origin_after_moving_checkbox.checkState() != 0:
                self.parent.common_widget.enable_set_objective_origin_after_moving_checkbox.setCheckState(0) 
                if not self.mes_interface.overwrite_relative_position(0, self.config.MES_TIMEOUT):
                    self.printc('Setting objective to 0 did not succeed')
                else:
                    self.objective_position = 0.0
            self.parent.update_position_display()
            self.printc('Objective is set to {0} um'.format(position))
        else:
            self.printc('MES did not respond')
            
    def set_objective_relative_value(self):
        try:
            position = float(self.parent.scanc())
        except ValueError:
            self.printc('No position is given')
            return
        if self.mes_interface.overwrite_relative_position(position, self.config.MES_TIMEOUT):
            self.printc('Objective relative value is set to {0} um'.format(position))
        else:
            self.printc('MES did not respond')
            
    def acquire_z_stack(self):
        self.printc('Starting z stack, please wait')
        try:
            self.z_stack_path, results = self.mes_interface.start_z_stack(self.config.MES_TIMEOUT)
            self.printc((self.z_stack_path, results))
        except:
            self.printc(traceback.format_exc())
            
    def acquire_xy_scan(self, use_region_parameters = False):
        self.printc('Acquire two photon image')
        if self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() != 0 or use_region_parameters:
            #Load scan settings from parameter file
            parameter_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'scan_region_parameters.mat')
            if self.create_parameterfile_from_region_info(parameter_file_path, 'xy'):
                self.xy_scan, result = self.mes_interface.acquire_xy_scan(self.config.MES_TIMEOUT, parameter_file = parameter_file_path)
            else:
                self.xy_scan = {}
                result = False
        elif self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() == 0:
            self.xy_scan, result = self.mes_interface.acquire_xy_scan(self.config.MES_TIMEOUT)
        if hasattr(self.xy_scan, 'has_key'):
            if self.xy_scan.has_key('path'):#For unknown reason this key is not found sometimes
                self.files_to_delete.append(self.xy_scan['path'])
        else:
            del self.xy_scan
        if result:
            if self.xy_scan.has_key(self.config.DEFAULT_PMT_CHANNEL):
                self.show_image(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], 0, self.xy_scan['scale'], origin = self.xy_scan['origin'])
            elif self.xy_scan.has_key('pmtURraw'):
                self.show_image(self.xy_scan['pmtURraw'], 0, self.xy_scan['scale'], origin = self.xy_scan['origin'])
            self.save_context()
            #Update objective position to ensure synchronzation with manual control of objective
            self.objective_position = self.xy_scan['objective_position'] 
            self.parent.update_position_display()
            self.printc('Image acquiring ready')
            return True
        else:
                self.printc('No image acquired')
        return False
        
    def acquire_xz_scan(self, use_region_parameters = False):
        '''
        The correct scan time needs to be defined by the user
        '''
        self.printc('Acquire vertical scan')
        channels = 'both'
        if self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.checkState() != 0 or use_region_parameters:
            parameter_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'xz_scan_region_parameters.mat')
            if not self.create_parameterfile_from_region_info(parameter_file_path, 'xz'):
                return False
            self.xz_scan, result = self.mes_interface.vertical_line_scan(parameter_file = parameter_file_path, channels =channels)
            self.files_to_delete.append(parameter_file_path)
        else:
            self.xz_scan, result = self.mes_interface.vertical_line_scan(channels =channels)
        if not result:
            self.printc('Vertical scan did not succeed')
            return result
        if hasattr(self.xz_scan, 'has_key'):
            if self.xz_scan.has_key('path'):#For unknown reason this key is not found sometimes
                self.files_to_delete.append(self.xz_scan['path'])
        #Update objective position to ensure synchronzation with manual control of objective
        self.objective_position = self.xz_scan['objective_position']
        objective_position_marker = [[0, self.objective_position, 
                                      0.04*self.xz_scan['scaled_image'].shape[0] * self.xz_scan['scaled_scale']['col'], self.objective_position]]
        
        self.parent.update_position_display()
        if self.config.DEFAULT_PMT_CHANNEL == 'pmtURraw' and self.xz_scan.has_key('scaled_image_red'):
            self.show_image(self.xz_scan['scaled_image_red'], 2, self.xz_scan['scaled_scale'], line = objective_position_marker, origin = self.xz_scan['origin'])
        else:
            self.show_image(self.xz_scan['scaled_image'], 2, self.xz_scan['scaled_scale'], line = objective_position_marker, origin = self.xz_scan['origin'])
        self.save_context()
        self.xz_scan_acquired = True
        return result
        
    def create_xz_lines(self):
        self.printc('Creating xz lines,  please wait...')
        if not hasattr(self, 'animal_parameters'):
            self.printc('Animal parameters are not available, roi filename is unknown')
            return
        region_name = self.parent.get_current_region_name()
        result,  self.objective_position, self.objective_origin = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT, with_origin = True)
        if not result:
            self.printc('Objective position is not available')
            return
        if os.path.exists(self.mouse_file):
            merge_distance = str(self.parent.roi_widget.cell_merge_distance_combobox.currentText())
            if merge_distance =='':
                merge_distance = self.config.CELL_MERGE_DISTANCE
            else:
                merge_distance = float(merge_distance)
            self.xz_config = {}
            self.xz_config['merge_distance'] = merge_distance
            self.xz_config['cell_group'] = self.parent.get_current_cell_group()
            self.roi_locations, self.rois = experiment_data.read_merge_rois(self.cells, 
                                cell_group = self.xz_config['cell_group'],
                                region_name =  region_name, 
                                objective_position = self.objective_position, 
                                objective_origin = self.objective_origin, 
                                z_range = self.config.XZ_SCAN_CONFIG['Z_RANGE'], 
                                merge_distance = merge_distance)
            if self.rois is None:
                self.printc('No rois found, check objective position')
                return
            params = str(self.parent.roi_widget.roi_pattern_parameters_lineedit.currentText()).replace(' ', '')
            if len(params)==0:
                roi_pattern_size = 0
                aux_roi_distance = 0
            else:
                roi_pattern_size = int(params.split(',')[0])
                aux_roi_distance = float(params.split(',')[1])
            self.xz_config['roi_pattern_size'] = roi_pattern_size
            self.xz_config['aux_roi_distance'] = aux_roi_distance
            if roi_pattern_size > 1:
                self.roi_locations, self.rois = experiment_data.add_auxiliary_rois(self.rois, roi_pattern_size, self.objective_position, self.objective_origin, 
                                                                     aux_roi_distance = aux_roi_distance, soma_size_ratio = None)
            if self.roi_locations is not None:
                line_length = str(self.parent.roi_widget.xz_line_length_combobox.currentText())
                self.xz_config = dict(self.xz_config.items() + copy.deepcopy(self.config.XZ_SCAN_CONFIG).items())
                if line_length != '':
                    self.xz_config['LINE_LENGTH'] = float(line_length)
                if not self.mes_interface.create_XZline_from_points(self.roi_locations, self.xz_config, True):
                        selfprintc('Creating xz lines did not succeed')
                else:
                    self.printc('{0} xz lines created'.format(self.roi_locations.shape[0]))
            else:
                self.printc('No rois loaded')
    
    ##############################Animal parameters##############################################    
    def save_animal_parameters(self):
        '''
        Saves the following parameters of a mouse:
        - birth date
        - gcamp injection date
        - anesthesia protocol
        - ear punch infos
        - strain
        - user comments

        The hdf5 file is closed.
        '''
        mouse_birth_date = self.parent.animal_parameters_widget.mouse_birth_date.date()
        mouse_birth_date = '{0}-{1}-{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
        gcamp_injection_date = self.parent.animal_parameters_widget.gcamp_injection_date.date()
        gcamp_injection_date = '{0}-{1}-{2}'.format(gcamp_injection_date.day(),  gcamp_injection_date.month(),  gcamp_injection_date.year())                

        id_text = str(self.parent.animal_parameters_widget.id.currentText())
        if id_text == '':
            self.notify('Please provide animal name')
            return
        if not id_text.isalnum():
            self.notify('Animal name can contain only alphanumeric characters')
            return
        user=str(self.parent.animal_parameters_widget.user.currentText())
        if user=='':
            self.notify('Select user!')
            return
        self.animal_parameters = {
            'mouse_birth_date' : mouse_birth_date,
            'gcamp_injection_date' : gcamp_injection_date,
            'id' : id_text,
            'gender' : str(self.parent.animal_parameters_widget.gender.currentText()),
            'ear_punch_l' : str(self.parent.animal_parameters_widget.ear_punch_l.currentText()), 
            'ear_punch_r' : str(self.parent.animal_parameters_widget.ear_punch_r.currentText()),
            'strain' : str(self.parent.animal_parameters_widget.mouse_strain.currentText()),
            'green_labeling' : str(self.parent.animal_parameters_widget.green_labeling.currentText()),
            'red_labeling' : str(self.parent.animal_parameters_widget.red_labeling.currentText()),
            'comments' : str(self.parent.animal_parameters_widget.comments.currentText()),
            'add_date' : utils.datetime_string().replace('_', ' '),
            'both_channels': (self.parent.animal_parameters_widget.imaging_channel_checkbox.checkState() == 2),
            'user':user,
        }        
        name = '{0}_{1}_{2}_{3}_{4}_{5}' .format(self.animal_parameters['id'], self.animal_parameters['strain'], self.animal_parameters['mouse_birth_date'] , self.animal_parameters['gcamp_injection_date'], \
                                         self.animal_parameters['ear_punch_l'], self.animal_parameters['ear_punch_r'])

        #self.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH,self.generate_animal_filename('mouse', self.animal_parameters))
        self.mouse_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(user),self.generate_animal_filename('mouse', self.animal_parameters))
        if not os.path.exists(os.path.dirname(self.mouse_file)):
            os.makedirs(os.path.dirname(self.mouse_file))
        
        if os.path.exists(self.mouse_file):
            self.printc('Animal parameter file already exists')
        else:
            self.scan_regions = {}
            variable_name = 'animal_parameters_{0}'.format(int(time.time()))
            hdf5io.save_item(self.mouse_file, variable_name, self.animal_parameters,filelocking=False)
            self.local_mouse_file = os.path.join(tempfile.gettempdir(), os.path.split(self.mouse_file)[1])
            if os.path.exists(self.local_mouse_file):#Remove existing temp mouse file
                os.remove(self.local_mouse_file)
            hdf5io.save_item(self.local_mouse_file, variable_name, self.animal_parameters,filelocking=False)
            are_new_file, self.mouse_files, full = update_mouse_files_list(self.config, self.mouse_files)
            time.sleep(0.1)#Wait till file is created
            #set selected mouse file to this one
            self.parent.update_mouse_files_combobox(set_to_value = os.path.split(self.mouse_file)[-1])
            #self.parent.update_cell_group_combobox()
            #Clear image displays showing regions
            self.emit(QtCore.SIGNAL('clear_image_display'), 1)
            self.emit(QtCore.SIGNAL('clear_image_display'), 3)
            self.parent.main_widget.scan_region_groupbox.use_saved_scan_settings_settings_checkbox.setCheckState(0)
            self.parent.main_tab.setCurrentIndex(0)#Switch to main tab
            #Initialize anesthesi history
            self.anesthesia_history = []
            self.save2mouse_file('anesthesia_history')
            self.parent.update_anesthesia_history()
            self.parent.update_combo_box_list(self.parent.main_widget.scan_region_groupbox.scan_regions_combobox, [])
            self.printc('{0} animal parameter file saved'.format(id_text))
            
    def add_to_anesthesia_history(self):
        if hasattr(self, 'mouse_file') and os.path.exists(self.mouse_file):
            if not hasattr(self, 'anesthesia_history'):
                self.anesthesia_history = []
            entry = {}
            date = self.parent.animal_parameters_widget.anesthesia_history_groupbox.date.date()
            tme = self.parent.animal_parameters_widget.anesthesia_history_groupbox.date.time()
            timestamp = time.mktime(time.struct_time((date.year(),date.month(),date.day(),tme.hour(),tme.minute(),0,0,0,-1)))
#        mouse_birth_date = '{0}-{1}-{2}'.format(mouse_birth_date.day(),  mouse_birth_date.month(),  mouse_birth_date.year())
            entry['timestamp'] = timestamp
            entry['substance'] = str(self.parent.animal_parameters_widget.anesthesia_history_groupbox.substance_combobox.currentText())
            entry['amount'] = str(self.parent.animal_parameters_widget.anesthesia_history_groupbox.amount_combobox.currentText())
            entry['comment'] = str(self.parent.animal_parameters_widget.anesthesia_history_groupbox.comment_combobox.currentText())
            self.anesthesia_history.append(entry)
            import operator
            self.anesthesia_history.sort(key = operator.itemgetter('timestamp'))
            self.save2mouse_file('anesthesia_history')
            self.parent.update_anesthesia_history()
        
    def remove_last_from_anesthesia_history(self):
        if hasattr(self, 'mouse_file') and os.path.exists(self.mouse_file):
            if not hasattr(self, 'anesthesia_history'):
                self.anesthesia_history = []
            elif len(self.anesthesia_history) > 0:
                self.anesthesia_history.pop()
                self.save2mouse_file('anesthesia_history')
            self.parent.update_anesthesia_history()
        
    ################### Regions #######################
    def add_scan_region(self):
        '''
        The following data are saved:
        -two photon image of the brain surface
        -mes parameter file of two photon acquisition so that later the very same image could be taken to help realignment
        -objective positon where the data acquisition shall take place. This is below the brain surface
        -stage position. If master position is saved, the current position is set to origin. The origin of stimulation software is also 
        '''
        self.printc('Add scan region pressed')
        if not self.xz_scan_acquired and hasattr(self, 'xz_scan'):
            del self.xz_scan
        if not hasattr(self, 'xy_scan'):
            self.printc('No brain surface image is acquired')
            return
        if not utils.safe_has_key(self.xy_scan, 'averaging'):
            self.printc('Please send this to Zoltan:')
            self.printc('=================================')
            self.printc(type(self.xy_scan))
            if hasattr(self.xy_scan, 'has_key'):
                self.printc(self.xy_scan.keys())
            self.printc(self.xy_scan)
            self.printc('=================================')
            
        if self.xy_scan['averaging'] < self.config.MIN_SCAN_REGION_AVERAGING:
            self.printc('Brain surface image averaging is only {0}' .format(self.xy_scan['averaging'], self.config.MIN_SCAN_REGION_AVERAGING))
        if hasattr(self, 'xz_scan') and self.xz_scan['averaging'] < self.config.MIN_SCAN_REGION_AVERAGING:
            self.printc('Number of frames is only {0}' .format(self.xz_scan['averaging']))
        if not (os.path.exists(self.mouse_file) and '.hdf5' in self.mouse_file):
            self.printc('mouse file not found')
            return
        if 0:
            result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
            if not result:
                self.printc('MES does not respond')
                return
        if 0:
            result, laser_intensity = self.mes_interface.read_laser_intensity()
            if not result:
                self.printc('MES does not respond')
                return
        else:
                laser_intensity=0
        if not self.read_stage(display_coords = False):#Objective position also read
            self.printc('Stage cannot be accessed')
            return
        if self.scan_regions == None:
            self.scan_regions = {}
        region_name = self.parent.get_current_region_name()
        self.printc('1. Laser intensity read')
        if region_name == '':
            region_name = 'r'
        if self.scan_regions.has_key(region_name):
            #Ask for confirmation to overwrite if region name already exists
            #if not self.ask4confirmation('Overwriting scan region'):
#            self.emit(QtCore.SIGNAL('show_overwrite_region_messagebox'))
#            while self.gui_thread_queue.empty() :
#                time.sleep(0.1) 
#            if not self.gui_thread_queue.get():
                self.printc('Region already exists, not saved')
                return
        else:
            relative_position = numpy.round(self.stage_position-self.stage_origin, 0)
            region_name_tag = '_{0}_{1}'.format(int(relative_position[0]),int(relative_position[1]))
            region_name = region_name + region_name_tag
            region_name = region_name.replace(' ', '_')
            #Ask for confirmation to overwrite if region name already exists
            if self.scan_regions.has_key(region_name) and not self.ask4confirmation('Overwriting scan region'):
                self.printc('Region not saved')
                return
            self.printc('2. region name generated')
        if not('master' in region_name or '0_0' in region_name or self.has_master_position(self.scan_regions)):
            self.printc('Master position has to be defined')
            return
        if 'master' == region_name.replace(region_name_tag, ''):
           if not self.set_stage_origin():
                self.printc('Setting origin did not succeed')
                return
           else:
                relative_position = numpy.round(self.stage_position-self.stage_origin, 0)
                region_name = 'master_{0}_{1}'.format(int(relative_position[0]),int(relative_position[1]))
        self.printc('3. region name finalized')
        scan_region = {}
        scan_region['add_date'] = utils.datetime_string().replace('_', ' ')
        scan_region['position'] = utils.pack_position(self.stage_position-self.stage_origin, self.objective_position)
        scan_region['laser_intensity'] = laser_intensity
        scan_region['xy'] = {}
        if self.xy_scan.has_key(self.config.DEFAULT_PMT_CHANNEL):
            scan_region['xy']['image'] = self.xy_scan[self.config.DEFAULT_PMT_CHANNEL]
        elif self.xy_scan.has_key('pmtURraw'):
            scan_region['xy']['image'] = self.xy_scan['pmtURraw']
        scan_region['xy']['scale'] = self.xy_scan['scale']
        scan_region['xy']['origin'] = self.xy_scan['origin']
        scan_region['xy']['mes_parameters']  = self.xy_scan['mes_parameters']
        self.printc('4. scan region dictionary loaded with data')
        #Save xy line scan parameters
        result, line_scan_path, line_scan_path_on_mes = self.mes_interface.get_line_scan_parameters()
        self.printc('5. line scan parameters are read')
        if result and os.path.exists(line_scan_path):
            scan_region['xy_scan_parameters'] = utils.file_to_binary_array(line_scan_path)
            os.remove(line_scan_path)
        self.printc('6. reading vertical scan parameters')
        #Vertical section
        if hasattr(self, 'xz_scan'):
            if self.xz_scan !=  None:
                scan_region['xz'] = self.xz_scan
                scan_region['xz']['mes_parameters'] = utils.file_to_binary_array(self.xz_scan['path'])
            else:
                self.printc('Vertical scan is not available')
        else:
            self.printc('Vertical scan is not available')
        #Save new scan region to hdf5 file
        self.scan_regions[region_name] = scan_region
        self.save2mouse_file('scan_regions')
        self.backup_mousefile()
        self.parent.update_region_names_combobox(region_name)
        self.update_scan_regions()#This is probably redundant
        self.printc('{0} scan region saved'.format(region_name))
        
    def save_xy_scan(self):
        if not self.ask4confirmation('XY scan config will be overwritten'):
            return
        region_name = self.parent.get_current_region_name()
        if not self.xy_scan is None:
            
            if self.xy_scan.has_key(self.config.DEFAULT_PMT_CHANNEL):
                self.scan_regions[region_name]['xy']['image'] = self.xy_scan[self.config.DEFAULT_PMT_CHANNEL]
            elif self.xy_scan.has_key('pmtURraw'):
                self.scan_regions[region_name]['xy']['image'] = self.xy_scan['pmtURraw']
            self.scan_regions[region_name]['xy']['scale'] = self.xy_scan['scale']
            self.scan_regions[region_name]['xy']['origin'] = self.xy_scan['origin']
            self.save2mouse_file('scan_regions')
            self.backup_mousefile()
            self.update_scan_regions()#This is probably redundant
            self.printc('XY scan updated')
        
    def save_xz_scan(self):
        if not self.ask4confirmation('XZ scan config will be overwritten'):
            return
        region_name = self.parent.get_current_region_name()
        if not self.xz_scan is None:
            self.scan_regions[region_name]['xz'] = self.xz_scan
            self.scan_regions[region_name]['xz']['mes_parameters'] = utils.file_to_binary_array(self.xz_scan['path'])
            self.save2mouse_file('scan_regions')
            self.backup_mousefile()
            self.update_scan_regions()#This is probably redundant
            self.printc('XZ scan updated')
        
    def save_xyt_scan(self):
        if not self.ask4confirmation('XYT scan config will be overwritten'):
            return
        region_name = self.parent.get_current_region_name()
        if not self.xy_scan is None:
            self.printc('Reading XYT line scan parameters')
            result, line_scan_path, line_scan_path_on_mes = self.mes_interface.get_line_scan_parameters()
            if result and os.path.exists(line_scan_path):
                self.scan_regions[region_name]['xy_scan_parameters'] = utils.file_to_binary_array(line_scan_path)
                self.save2mouse_file('scan_regions')
                self.backup_mousefile()
                os.remove(line_scan_path)
                self.update_scan_regions()#This is probably redundant
                self.printc('XYT scan updated')
            else:
                self.printc('XYT scan parameters from {0} cannot be read, {1}'.format(line_scan_path,result))

    def remove_scan_region(self):
        selected_region = self.parent.get_current_region_name()
        if not self.ask4confirmation('Do you want to remove {0} scan region?' .format(selected_region)):
            return
        if selected_region != 'master' and 'r_0_0' not in selected_region:
            if self.scan_regions.has_key(selected_region):
                del self.scan_regions[selected_region]
            self.save2mouse_file('scan_regions')
            self.parent.main_widget.scan_region_groupbox.scan_regions_combobox.setCurrentIndex(0)
            self.parent.update_region_names_combobox()
            self.update_scan_regions()
            self.printc('{0} region removed'.format(selected_region))
        else:
            self.printc('Master region cannot be removed')

    def move_to_region(self):
        '''
        Use cases:
        1. move stage and objective without realignment
        2. move stage and objective and realign both vertically and in xy
        (3. Realign objective at experiment batches - will be implemented in stimulation sw)
        '''
        selected_region = self.parent.get_current_region_name()
        if self.parent.helpers_widget.override_enforcing_set_stage_origin_checkbox.checkState() != 0:
            self.stage_origin_set = True
        if not self.stage_origin_set:
            self.printc('WARNING: origin not set')
            #return When origin is not set, only a notification will be shown, but stage is moved to region
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_move'] .checkState() != 0:
            self.printc('Move objective to saved position')
            if abs(self.scan_regions[selected_region]['position']['z']) > self.config.OBJECTIVE_POSITION_LIMIT:
                self.printc('Objective position is not correct')
                return
            if not self.mes_interface.set_objective(self.scan_regions[selected_region]['position']['z'], self.config.MES_TIMEOUT):
                self.printc('Setting objective did not succeed')
                return
            self.printc('Objective set to {0} um'.format(self.scan_regions[selected_region]['position']['z']))
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['stage_move'] .checkState() != 0:
            if not (self.has_master_position(self.scan_regions) and self.scan_regions.has_key(selected_region)):
                self.printc('Master position is not defined')
                return
            self.printc('Move stage to saved region position')
            master_position_name = self.get_master_position_name(self.scan_regions)
            current_relative_position = self.stage_position - self.stage_origin
            master_position = numpy.array([self.scan_regions[master_position_name]['position']['x'][0], self.scan_regions[master_position_name]['position']['y'][0], current_relative_position[-1]])
            target_relative_position = numpy.array([self.scan_regions[selected_region]['position']['x'][0], self.scan_regions[selected_region]['position']['y'][0], current_relative_position[-1]])
            movement = target_relative_position - current_relative_position
            if not self.move_stage_relative(movement):
                return
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['stage_realign'] .checkState() != 0:
            self.printc('Realign stage')
            if not self.acquire_xy_scan(use_region_parameters = True):
                return
            self.printc('Register with saved image.')
            #calculate translation between current and saved brain surface image
            if not self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['xy']['image'], self.xy_scan['scale'], self.xy_scan['origin']):
                return
            if abs(self.suggested_translation['col'])  > self.config.MAX_REALIGNMENT_OFFSET or abs(self.suggested_translation['row']) > self.config.MAX_REALIGNMENT_OFFSET:
                self.printc('Suggested translation is not plausible')
                return
            #Translate stage with suggested values
            stage_translation = -numpy.round(numpy.array([self.suggested_translation['col'][0], self.suggested_translation['row'][0], 0.0]), 2)
            if abs(self.suggested_translation['col'])  > self.config.REALIGNMENT_XY_THRESHOLD or abs(self.suggested_translation['row']) > self.config.REALIGNMENT_XY_THRESHOLD:
                self.move_stage_relative(stage_translation)
            else:
                self.printc('Suggested translation is small, stage is not moved')
            if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['stage_origin_adjust'] .checkState() != 0:
                self.printc('Stage origin was corrected with detected offset')
                self.stage_origin = self.stage_origin + stage_translation
            #Get a two photon image and register again, to see whether realignment was successful
            if not self.acquire_xy_scan(use_region_parameters = True):
                return
            if not self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[selected_region]['xy']['image'], self.xy_scan['scale'], self.xy_scan['origin']):
                return
            if abs(self.suggested_translation['col']) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET or abs(self.suggested_translation['row']) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET:
                self.printc('Realignment was not successful {0}' .format(self.suggested_translation)) #Process not interrupted, but moves to vertical realignment
            self.printc('XY offset {0}' .format(self.suggested_translation))
        if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_realign'] .checkState() != 0 and\
                self.scan_regions[selected_region].has_key('xz'):
            self.printc('Realign objective')
            result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
            if not result:
                self.printc('MES does not respond')
                return
            if not self.acquire_xz_scan(use_region_parameters = True):
                self.printc('Vertical scan was not successful')
                return
            #calculate z offset between currently acquired vertical scan and reference data
            if not self.register_images(self.xz_scan['scaled_image'], self.scan_regions[selected_region]['xz']['scaled_image'], self.xz_scan['scaled_scale']):
                return
            vertical_offset = self.suggested_translation['row']
            if abs(vertical_offset)  > self.config.MAX_REALIGNMENT_OFFSET:
                self.printc('Suggested movement is not plausible')
                return
            new_objective_position = self.objective_position + vertical_offset#self.objective_position was updated by vertical scan
            #Move objective
            if abs(vertical_offset)  > self.config.REALIGNMENT_Z_THRESHOLD:
                if not self.mes_interface.set_objective(new_objective_position, self.config.MES_TIMEOUT):
                    self.printc('Setting objective did not succeed')
                    return
                else:
                    self.printc('Objective moved to {0}'.format(new_objective_position))
                    #Change origin when full realignment is done with moving both objective and stage and realign both devices
                    if self.parent.main_widget.scan_region_groupbox.move_to_region_options['checkboxes']['objective_origin_adjust'] .checkState() != 0:
                        if not self.mes_interface.overwrite_relative_position(self.objective_position, self.config.MES_TIMEOUT):
                            self.printc('Setting objective relative value did not succeed')
                            return
                        else:
                            self.printc('Objective relative origin was corrected with detected offset')
                    result, self.objective_position = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT)
                    if not result:
                        self.printc('MES did not respond')
                        return
            else:
                self.printc('Suggested translation is small, objective is not moved.')
            #Verify vertical realignment
            if not self.acquire_xz_scan(use_region_parameters = True):
                self.printc('Vertical scan was not successful')
                return
            if not self.register_images(self.xz_scan['scaled_image'], self.scan_regions[selected_region]['xz']['scaled_image'], self.xz_scan['scaled_scale']):
                return
            vertical_offset = self.suggested_translation['row']
            if abs(vertical_offset) > self.config.ACCEPTABLE_REALIGNMENT_OFFSET:
                self.printc('Realignment was not successful {0}'.format(vertical_offset))
                return
            self.printc('Vertical offset {0}' .format(vertical_offset))
        self.parent.update_position_display()
        self.suggested_translation = utils.cr((0, 0))
        self.printc('Move to region complete')
        
    ################## Experiment control ####################
    def identify_flourescence_intensity_distribution(self):
        '''
        Input parameters:
        - z range
        - max laser power at min/max z
        Performs z linescans at different depths with different laser intensities
        '''
        self.abort_calib = False
        laser_step = 10.0
        #Gather parameters from GUI
        try:
            z_overlap = float(self.parent.scanc())
        except ValueError:
            z_overlap = self.config.DEFAULT_Z_SCAN_OVERLAP
        try:
            z_top, z_bottom = map(float, str(self.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText()).split(','))
        except ValueError:
            z_top = 0
            z_bottom = float(str(self.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText()))
        if z_top < z_bottom:
            self.printc('z bottom must be deeper than z top')
            return
        try:
            max_laser_z_top, max_laser_z_bottom =  map(float, str(self.parent.main_widget.experiment_control_groupbox.laser_intensities_combobox.currentText()).split(','))
        except ValueError:
            max_laser_z_top, max_laser_z_bottom = (30, 50)
        if max_laser_z_top > max_laser_z_bottom:
            self.printc('Laser intensity shall increase with depth')
            return
        tag = int(time.time())
        image_dir = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'vs{0}'.format(tag))
        os.mkdir(image_dir)
        #Calculate objective positions and laser intensities
        z_step = self.config.MES_Z_SCAN_SCOPE - z_overlap
        objective_positions = (z_top - 0.5 * self.config.MES_Z_SCAN_SCOPE - numpy.arange((z_top - z_bottom) / z_step) * z_step).tolist()
        max_laser_intensities = numpy.linspace(max_laser_z_top, max_laser_z_bottom, len(objective_positions))
        calibration_parameters = []
        for i in range(len(objective_positions)):
            max_laser_value_index =  int(max_laser_intensities[i]/laser_step)+1
            min_laser_value_index = max_laser_value_index - 2
            if min_laser_value_index <= 0:
                min_laser_value_index = 1
            calibration_parameters.append({'objective_position' : objective_positions[i], 'laser_intensity': numpy.arange(min_laser_value_index,max_laser_value_index) * laser_step})
        
        #Execute calibration process
        xz_scans = []
        for i1 in range(len(calibration_parameters)):
            if self.abort_calib:
                break
            if not self.mes_interface.set_objective(calibration_parameters[i1]['objective_position'], self.config.MES_TIMEOUT):
                self.printc('MES does not respond')
                return
            else:
                for laser_intensity in calibration_parameters[i1]['laser_intensity']:
                    if self.abort_calib:
                        break
                    #Adjust laserresult, adjusted_laser_intensity = self.mes_interface.set_laser_intensity(laser_intensity)
                    if not result:
                        self.printc('Setting laser intensity did not succeed')
                        return
                    self.printc('Objective: {0} um, laser: {1} %'.format(calibration_parameters[i1]['objective_position'], laser_intensity))
                    #Vertical scan
                    xz_scan,  result = self.mes_interface.vertical_line_scan()
                    if not result:
                        self.printc('Vertical scan did not succeed')
                        return
                    xz_scan['laser_intensity'] = laser_intensity
                    xz_scan['objective_position'] = calibration_parameters[i1]['objective_position']
                    xz_scans.append(xz_scan)
                    self.files_to_delete.append(xz_scan['path'])
                    self.show_image(xz_scan['scaled_image'], 2, xz_scan['scaled_scale'], origin = xz_scan['origin'])
                    imaged.imshow(xz_scan['scaled_image'], save=os.path.join(image_dir, 'xz_scan-{2}-{0}-{1}.png'.format(int(laser_intensity), int(calibration_parameters[i1]['objective_position']), tag)))
        self.save_context()
        #Save results to mouse file
        mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, str(self.parent.main_widget.scan_region_groupbox.select_mouse_file.currentText()))
        #TMP:
        mouse_file_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, 'xz_scans-{0}.hdf5'.format(tag))
        self.save2mouse_file('intensity_calibration_data')
        self.printc('Done')
        
    def stop_experiment(self):
        command = 'SOCabort_experimentEOCguiEOP'
        self.queues['stim']['out'].put(command)
        self.printc('Stopping experiment requested, please wait')
        for id in self.issued_ids:
            p = os.path.join(self.config.EXPERIMENT_DATA_PATH, id+'.hdf5')
            if os.path.exists(p):
                os.remove(p)
                self.printc('{0} cancelled'.format(id))

    def graceful_stop_experiment(self):
#        command = 'SOCgraceful_stop_experimentEOCguiEOP'
#        self.queues['stim']['out'].put(command)
        self.printc('Graceful stop requested, please wait')
        for id in self.issued_ids:
            p = os.path.join(self.config.EXPERIMENT_DATA_PATH, id+'.hdf5')
            if os.path.exists(p):
                os.remove(p)
                self.printc('{0} cancelled'.format(id))

    def start_experiment(self):
        self.printc('Experiment started, please wait')
        self.experiment_parameters = {}
        self.experiment_parameters['user']=self.animal_parameters['user'] if self.animal_parameters.has_key('user') else 'default_user'
        self.experiment_parameters['intrinsic'] = self.parent.common_widget.enable_intrinsic_checkbox.checkState() == 2
        if not self.experiment_parameters['intrinsic']:
            self.experiment_parameters['mouse_file'] = os.path.split(self.mouse_file)[1]
            region_name = self.parent.get_current_region_name()
            if len(region_name)>0:
                self.experiment_parameters['region_name'] = region_name
            region_add_timestamp=time.mktime(datetime.datetime.strptime(self.scan_regions[self.experiment_parameters['region_name']]['add_date'], "%Y-%m-%d %H-%M-%S").timetuple())    
            dt=(time.time()-region_add_timestamp)/3600
            if dt>self.config.SCAN_REGION_TIMEOUT:
                if not self.ask4confirmation('Scan region was created {0:.0f} hours ago. Are you sure you want to record from this scan region?'.format(dt)):
                    return
                else:
                    if self.ask4confirmation('Overwrite current scan region\'s add date?\r\nIf yes, datafiles will be copied to today\'s folder, no: datafiles are copied to the folder corresponds to scan region creation date '):
                        self.scan_regions[self.experiment_parameters['region_name']]['add_date']= utils.datetime_string().replace('_', ' ')
        objective_range_string = str(self.parent.main_widget.experiment_control_groupbox.objective_positions_combobox.currentText())
        if len(objective_range_string)>0:
            objective_positions = map(float, objective_range_string.split(','))
            if len(objective_positions) != 3:
                self.printc('Objective range is not in correct format')
                return
            elif objective_positions[0]>0 or objective_positions[1]>0:
                if not self.ask4confirmation('Objective positions should be negative, do you want to continue with these values? {0}'.format(objective_positions[:2])):
                    return
            if objective_positions[0] > objective_positions[1]:
                reverse = True
                tmp = objective_positions[0]
                objective_positions[0] = objective_positions[1]
                objective_positions[1] = tmp
            else:
                reverse = False
            objective_positions[1] += objective_positions[2]
            self.experiment_parameters['objective_positions'] = numpy.arange(*objective_positions)
            self.experiment_parameters['number_of_depths'] = self.experiment_parameters['objective_positions'].shape[0]
            if reverse:
                self.experiment_parameters['objective_positions'] = self.experiment_parameters['objective_positions'].tolist()
                self.experiment_parameters['objective_positions'].reverse()
                self.experiment_parameters['objective_positions'] = numpy.array(self.experiment_parameters['objective_positions'])
            self.experiment_parameters['current_objective_position_index'] = 0
        laser_intensities_string =  str(self.parent.main_widget.experiment_control_groupbox.laser_intensities_combobox.currentText())
        if len(laser_intensities_string) > 0:
            self.experiment_parameters['laser_intensities'] = map(float, laser_intensities_string.replace(' ', '').split(','))
            if len(self.experiment_parameters['laser_intensities']) != 2:
                self.printc('Laser intensity range is not in correct format')
                return
            self.experiment_parameters['laser_intensities'] = numpy.linspace(self.experiment_parameters['laser_intensities'][0],
                                                                                            self.experiment_parameters['laser_intensities'][1], 
                                                                                            self.experiment_parameters['number_of_depths'])
            #generic.expspace(self.experiment_parameters['laser_intensities'][0], self.experiment_parameters['laser_intensities'][1],  self.experiment_parameters['objective_positions'].shape[0])
        #Set back next/prev/redo button texts
        self.parent.main_widget.experiment_control_groupbox.next_depth_button.setText('Next')
        self.parent.main_widget.experiment_control_groupbox.previous_depth_button.setText('Prev')
        self.parent.main_widget.experiment_control_groupbox.redo_depth_button.setText('Redo')
        self.generate_experiment_start_command()
        if self.experiment_parameters.has_key('objective_positions') and self.ask4confirmation('Issue command for all depths?'):
            while True:
                if self.next_experiment()==None:
                    break

    def generate_experiment_start_command(self):
        #TODO:  INTRINSIC: do not expect mouse file and scan regions, chck checkbox which enables intrinsic
        #Ensure that user can switch between different stimulations during the experiment batch
        self.experiment_parameters['experiment_config'] = str(self.parent.main_widget.experiment_control_groupbox.experiment_name.currentText())
        self.experiment_parameters['scan_mode'] = str(self.parent.main_widget.experiment_control_groupbox.scan_mode.currentText())
        self.experiment_parameters['id'] = str(int(time.time()))
        self.issued_ids.append(self.experiment_parameters['id'])
        if self.experiment_parameters.has_key('current_objective_position_index') and self.experiment_parameters.has_key('objective_positions'):
            self.experiment_parameters['objective_position'] = self.experiment_parameters['objective_positions'][self.experiment_parameters['current_objective_position_index']]
            objective_position = self.experiment_parameters['objective_position']
            self.parent.main_widget.experiment_control_groupbox.redo_depth_button.setText('Redo {0} um'.format(objective_position))
            #Update redo and next buttons
            time.sleep(0.1)
            if self.experiment_parameters['current_objective_position_index']+1 < self.experiment_parameters['objective_positions'].shape[0]:
                objective_position = self.experiment_parameters['objective_positions'][self.experiment_parameters['current_objective_position_index']+1]
                self.parent.main_widget.experiment_control_groupbox.next_depth_button.setText('Next {0} um'.format(objective_position))
            if self.experiment_parameters['current_objective_position_index'] > 0:
                objective_position = self.experiment_parameters['objective_positions'][self.experiment_parameters['current_objective_position_index']-1]
                self.parent.main_widget.experiment_control_groupbox.previous_depth_button.setText('Prev {0} um'.format(objective_position))
        if self.experiment_parameters.has_key('current_objective_position_index') and self.experiment_parameters.has_key('laser_intensities'):
            self.experiment_parameters['laser_intensity'] = self.experiment_parameters['laser_intensities'][self.experiment_parameters['current_objective_position_index']]
        #generate parameter file
        parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'.hdf5')
        if os.path.exists(parameter_file):
            time.sleep(1.1)
            self.experiment_parameters['id'] = str(int(time.time()))
            self.issued_ids[-1]=self.experiment_parameters['id']
            parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.experiment_parameters['id']+'.hdf5')
            if os.path.exists(parameter_file):
                self.printc('Experiment ID already exists')
                return
        h = hdf5io.Hdf5io(parameter_file,filelocking=False)
        h.parameters = copy.deepcopy(self.experiment_parameters)
        if h.parameters.has_key('laser_intensities'):
            del h.parameters['laser_intensities']
        if h.parameters.has_key('objective_positions'):
            del h.parameters['objective_positions']
        if not self.experiment_parameters['intrinsic']:
            h.scan_regions = copy.deepcopy(self.scan_regions)
            h.scan_regions = {self.experiment_parameters['region_name'] : h.scan_regions[self.experiment_parameters['region_name']]}#Keep only current scan region
            if h.scan_regions[self.experiment_parameters['region_name']].has_key('process_status'):
                del h.scan_regions[self.experiment_parameters['region_name']]['process_status']#remove the continously increasing and unnecessary node
            h.animal_parameters = copy.deepcopy(self.animal_parameters)
            h.anesthesia_history = copy.deepcopy(self.anesthesia_history)
        if self.parent.main_widget.override_imaging_channels_checkbox.checkState()==2:
            h.animal_parameters['overridden']={'both_channels': h.animal_parameters['both_channels'], 'red_labeling': self.animal_parameters['red_labeling']}
            h.animal_parameters['both_channels']=self.parent.main_widget.record_red_channel_checkbox.checkState()==2
            h.animal_parameters['red_labeling']='yes' if self.parent.main_widget.enable_prepost_scan_checkbox.checkState()==2 else 'no'
        fields_to_save = ['parameters']
        if not self.experiment_parameters['intrinsic']:
            fields_to_save.extend(['scan_regions', 'animal_parameters', 'anesthesia_history'])
        if self.experiment_parameters['scan_mode'] == 'xz':
            h.xz_config = copy.deepcopy(self.xz_config)
            h.rois = copy.deepcopy(self.rois)
            h.roi_locations = copy.deepcopy(self.roi_locations)
            fields_to_save += ['xz_config', 'rois', 'roi_locations']
        h.save(fields_to_save)
        h.close()
        file.wait4file_ready(parameter_file)
        self.printc('{0}{1} parameter file generated'.format(self.experiment_parameters['id'],'/{0} um'.format(self.experiment_parameters['objective_position']) if self.experiment_parameters.has_key('objective_position') else ''))
        command = 'SOCexecute_experimentEOCid={0},experiment_config={1}EOP' .format(self.experiment_parameters['id'], self.experiment_parameters['experiment_config'])
        time.sleep(0.5)
        self.queues['stim']['out'].put(command)
        
    def previous_experiment(self):
        if self.experiment_parameters.has_key('current_objective_position_index') and \
            self.experiment_parameters['current_objective_position_index'] > 0:
            self.experiment_parameters['current_objective_position_index'] -= 1
            self.generate_experiment_start_command()
        
    def redo_experiment(self):
        self.generate_experiment_start_command()
        
    def next_experiment(self):
        if self.experiment_parameters.has_key('current_objective_position_index'):
            self.experiment_parameters['current_objective_position_index'] += 1
            if self.experiment_parameters['current_objective_position_index'] < self.experiment_parameters['objective_positions'].shape[0]:
                self.generate_experiment_start_command()
                return True
       
    ############ 3d scan test ###############
    def show_rc_scan_results(self):
        import pylab as p
        import mpl_toolkits.mplot3d.axes3d as p3
        if hasattr(self, 'scanned_trajectory'):
            scanned_trajectory = self.scanned_trajectory[-1]
            undersample = 10
            x = scanned_trajectory['x'][::undersample]
            y = scanned_trajectory['y'][::undersample]
            z = scanned_trajectory['z'][::undersample]
            fig=p.figure(1)
            ax = p3.Axes3D(fig)
            ax.scatter(x, y, z,  s=4)
            p.figure(2)
            p.plot(scanned_trajectory['masked_line'][::undersample])
            p.plot(scanned_trajectory['roi'][::undersample])
            p.show()
            
    ########### Network debugger tools #################
    def send_command(self):
        connection = str(self.parent.helpers_widget.select_connection_list.currentText())
        if self.queues.has_key(connection):
            self.queues[connection]['out'].put(self.parent.scanc())
        else:
            self.printc('Connection not selected')
        
    def show_connected_clients(self):
        connection_status = self.command_relay_server.get_connection_status()
        connected = []
        for k, v in connection_status.items():
            if v:
                connected.append(k)
        connected.sort()
        connected = str(connected).replace('[','').replace(']', '').replace('\'','').replace(',','\n')
        self.printc(connected)
        self.printc('\n')

    def show_network_messages(self):
        network_messages = self.command_relay_server.get_debug_info()
        for network_message in network_messages:
            endpoint_name = network_message[1].split(' ')
            endpoint_name = (endpoint_name[1] + '/' + endpoint_name[3]).replace(',','')
            message = network_message[1].split('port')[1].split(': ', 1)[1]
            displayable_message = network_message[0] + ' ' + endpoint_name + '>> ' + message
            self.printc(displayable_message)
        self.printc('\n')
        
    def update_network_connection_status(self):
        #Check for network connection status
        if hasattr(self.parent, 'common_widget') and hasattr(self.command_relay_server, 'servers'):
            connection_status = self.command_relay_server.get_connection_status()
            connected = ''
            n_connected = 0
            if connection_status['STIM_MES/MES'] and connection_status['STIM_MES/STIM']:
                connected += 'STIM-MES  '
                n_connected += 1
            if connection_status['GUI_MES/MES'] and connection_status['GUI_MES/GUI']:
                connected += 'MES  '
                n_connected += 1
            if connection_status['GUI_STIM/STIM'] and connection_status['GUI_STIM/GUI']:
                connected += 'STIM  '
                n_connected += 1
            if connection_status['GUI_ANALYSIS/ANALYSIS'] and connection_status['GUI_ANALYSIS/GUI']:
                connected += 'ANALYSIS  '
                n_connected += 1
            n_connections = len(self.config.COMMAND_RELAY_SERVER['CONNECTION_MATRIX'].keys())
            connected = 'Alive connections ({0}/{1}): '.format(n_connected, n_connections) + connected
            self.parent.common_widget.connected_clients_label.setText(connected)
            
    ################ Helper functions ###################
    def show_help(self):
        if webbrowser.open_new_tab(self.config.MANUAL_URL):
            self.printc('Shown in default webbrowser')
            
    def add_simulated_measurement_file(self):
        self.clear_process_status()
        commands = []
        for path in file.listdir_fullpath(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'simulated_data')):
            if '.hdf5' in path:
                h = hdf5io.Hdf5io(path,filelocking=False)
                h.load('call_parameters')
                h.call_parameters['mouse_file'] = os.path.split(self.mouse_file)[1]
                h.save('call_parameters', overwrite = True)
                h.close()
            target_path = os.path.join(self.config.EXPERIMENT_DATA_PATH, os.path.split(path)[1])
            if os.path.exists(target_path):
                os.remove(target_path)
            shutil.copyfile(path, target_path)
            if '.hdf5' in path:
                commands.append('SOCmeasurement_readyEOC{0}EOP'.format(file.parse_fragment_filename(path)['id']))
                self.printc('Simulated file copied: {0}'.format(path))
        time.sleep(1.0)
        for command in commands:
            self.queues['stim']['in'].put(command)
        self.queues['analysis']['out'].put('SOCclear_joblistEOCEOP')
        self.printc('Done')
            
    def save_xy_scan_to_file(self):
        hdf5_handler = hdf5io.Hdf5io(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'xy_scan.hdf5')),filelocking=False)
        hdf5_handler.xy_scan = self.xy_scan
        hdf5_handler.stage_position = self.stage_position
        hdf5_handler.save(['xy_scan', 'stage_position'])
        hdf5_handler.close()
            
    ############# Helpers #############
    def mouse_file2jobhandler(self, mouse_file = None, tag = None):
        result = False
        if not hasattr(self, 'mouse_file'):
            return result
        if mouse_file is None:
            mouse_file = self.mouse_file
        if tag is None:
            tag = 'copy'
        copy_path = mouse_file.replace('.hdf5', '_' +tag+'.hdf5')
        try:
            if os.path.exists(mouse_file) and os.path.isfile(mouse_file):
                time.sleep(1.0)
                if 'jobhandler' in tag:#Stim uses other nodes of mouse file
                    if os.path.exists(copy_path):
                        os.remove(copy_path)
                        time.sleep(0.4)
                    h1=hdf5io.Hdf5io(copy_path,filelocking=False)
                    h1.scan_regions = copy.deepcopy(self.scan_regions)
                    #Keep only process status data
                    for scan_region_name in h1.scan_regions.keys():
                        if not h1.scan_regions[scan_region_name].has_key('process_status'):
                            del h1.scan_regions[scan_region_name]
                        else:
                            for k in h1.scan_regions[scan_region_name].keys():
                                if k != 'process_status':
                                    del h1.scan_regions[scan_region_name][k]
                    h1.save('scan_regions', overwrite=True)
                    h1.close()
                elif 'stim' in tag:
                    if os.path.exists(copy_path):
                        os.remove(copy_path)
                        time.sleep(0.4)
                    h1=hdf5io.Hdf5io(copy_path,filelocking=False)
                    h1.scan_regions = copy.deepcopy(self.scan_regions)
                    h1.animal_parameters = copy.deepcopy(self.animal_parameters)
                    h1.save(['scan_regions', 'animal_parameters'], overwrite=True)
                    if hasattr(self, 'cells'):
                        h1.cells = copy.deepcopy(self.cells)
                        h1.save('cells', overwrite=True)
                    if hasattr(self, 'anesthesia_history'):
                        h1.anesthesia_history = copy.deepcopy(self.anesthesia_history)
                        h1.save('anesthesia_history', overwrite=True)
                    h1.close()
                time.sleep(1.0)
				# Trying to open copied hdf5 file
#                h = hdf5io.Hdf5io(copy_path)#Does not help either
#                h.close()
                result = True
        except:
            self.printc(traceback.format_exc())
        time.sleep(0.2)#Wait to make sure that file is completely copied
        return result
        
    def create_parameterfile_from_region_info(self, parameter_file_path, scan_type):
        selected_region = self.parent.get_current_region_name()
        if not self.scan_regions.has_key(selected_region):
            self.printc('Selected region does not exists')
            return False
        if not self.scan_regions[selected_region].has_key(scan_type):
            self.printc('Parameters for {0} does not exists' .format(scan_type))
            return False
        self.scan_regions[selected_region][scan_type]['mes_parameters'].tofile(parameter_file_path)
        if not os.path.exists(parameter_file_path):
            self.printc('Parameter file not created')
            return False
        else:
            return True

    def create_image_registration_data_file(self, f1, f2):
        image_hdf5_handler = hdf5io.Hdf5io(os.path.join(self.config.CONTEXT_PATH, 'image.hdf5'),filelocking=False)
        image_hdf5_handler.f1 = f1
        image_hdf5_handler.f2 = f2
        image_hdf5_handler.save(['f1', 'f2'], overwrite = True)
        image_hdf5_handler.close()
        
    def cutout_subimage(self, image, box, scale, origin):
        upper_leftx = int((box[0] - origin['col'])/scale['col'])
        upper_lefty = int((box[1] - origin['row'])/scale['row'])
        bottom_rightx = int((box[2] - origin['col'])/scale['col'])
        bottom_righty = int((box[3] - origin['row'])/scale['row'])
        subimage = image[upper_lefty:bottom_righty, upper_leftx:bottom_rightx]
        if any(subimage.shape) < 128:
            new_size = []
            for i in range(2):
                if subimage.shape[i] < 128:
                    s = 128
                else:
                    s = subimage.shape[i]
                new_size.append(s)
            extended_image = numpy.zeros(new_size, dtype = subimage.dtype)
            extended_image[0:subimage.shape[0], 0: subimage.shape[1]]= subimage
            subimage = extended_image
        return subimage
        
    def register(self):
        self.register_images(self.xy_scan[self.config.DEFAULT_PMT_CHANNEL], self.scan_regions[self.parent.get_current_region_name()]['xy']['image'], self.xy_scan['scale'], self.xy_scan['origin'])
        
    def register_images(self, f1, f2, scale, origin = None, print_result = True):
        box = self.parent.get_subimage_box()
        if not origin is None and len(box) ==4:
            f1 = self.cutout_subimage(f1, box, scale, origin)
            f2 = self.cutout_subimage(f2, box, scale, origin)
            if False:
                from PIL import Image
                from visexpA.engine.dataprocessors import generic
                Image.fromarray(generic.normalize(f1,  numpy.uint8)).save(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f1.png')))
                Image.fromarray(generic.normalize(f2,  numpy.uint8)).save(file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'f2.png')))
        self.create_image_registration_data_file(f1, f2)
        utils.empty_queue(self.queues['analysis']['in'])
        arguments = ''
        self.queues['analysis']['out'].put('SOCregisterEOC' + arguments + 'EOP')
        if not utils.wait_data_appear_in_queue(self.queues['analysis']['in'], 15.0):
            self.printc('Analysis not connected')
            return False
        messages_to_put_back = []
        p = self.queues['analysis']['in'].get()
        if 'SOCregisterEOCstartedEOP' not in p:
            self.printc('Image registration did not start,{0}'.format(p))
            messages_to_put_back.append(p)
            return False
        mouse_file_copy_requested = False
        if utils.wait_data_appear_in_queue(self.queues['analysis']['in'], timeout = self.config.MAX_REGISTRATION_TIME):#TODO: the content of the queue also need to be checked
            while not self.queues['analysis']['in'].empty():
                    response = self.queues['analysis']['in'].get()
                    if 'SOCmouse_file_copyEOCjobhandlerEOP' in response:
                        response = response.replace('SOCmouse_file_copyEOCjobhandlerEOP', '')
                        mouse_file_copy_requested = True
                    if 'error' in response:
                        self.printc('Image registration resulted error')
                        return False
                    elif 'register' in response and not 'started' in response:
                        self.registration_result = self.parse_list_response(response) #rotation in angle, center or rotation, translation
                        self.suggested_translation = utils.cr(utils.nd(scale) * self.registration_result[-2:]*numpy.array([-1, 1]))
                        if print_result:
                            self.printc('Suggested translation: {0:.2f}, {1:.2f}'.format(-self.suggested_translation['row'][0], -self.suggested_translation['col'][0]))
                        return True
                    else:
                        messages_to_put_back.append(response)
            for msg in messages_to_put_back:
                self.queues['analysis']['in'].put(msg)
        else:
            self.printc('Analysis does not respond')
        if mouse_file_copy_requested:
            self.queues['analysis']['in'].put('SOCmouse_file_copyEOCjobhandlerEOP')
        return False

    def parse_list_response(self, response):
        return numpy.array(map(float,parameter_extract.findall( response)[0].split(',')))
        
    def has_master_position(self, scan_regions):
        master_position_exists = False
        for saved_region_name in scan_regions.keys():
            if 'master' in saved_region_name or '0_0' in saved_region_name:
                master_position_exists = True
                break
        return master_position_exists

    def get_master_position_name(self, scan_regions):
        master_position_name = ''
        for saved_region_name in scan_regions.keys():
            if 'master' in saved_region_name or '0_0' in saved_region_name:
                master_position_name = saved_region_name
                break
        return master_position_name

    def generate_animal_filename(self, tag, animal_parameters, extension = 'hdf5'):
        name = '{5}_{7}_{0}_{1}_{2}_{3}_{4}.{6}' .format(animal_parameters['strain'], animal_parameters['mouse_birth_date'] , animal_parameters['gcamp_injection_date'], \
                                         animal_parameters['ear_punch_l'], animal_parameters['ear_punch_r'], tag, extension, animal_parameters['id'])
        return name
        
    def ask4confirmation(self, action2confirm):
        self.emit(QtCore.SIGNAL('ask4confirmation'), action2confirm)
        while self.gui_thread_queue.empty() :
            time.sleep(0.1) 
        return self.gui_thread_queue.get()
        
        
    def notify(self, msg):
        self.emit(QtCore.SIGNAL('notify'), str(msg))
        
    def save2mouse_file(self, fields, wait_save = False):
#        #Wait till mouse file handler finishes with copying data fields
#        while self.parent.mouse_file_handler.lock:
#            pass
        if not isinstance(fields, list):
            fields = [fields]
        #create copy of saveable data in mouse file handler
        for field in fields:
            field_value = copy.deepcopy(getattr(self, field))
            if field == 'cells':
                field_value = utils.object2array(self.cells2pickled_ready(field_value))
            self.queues['mouse_file_handler'].put([field, field_value])
        self.mouse_file_saver()
        if wait_save:
            self.wait_mouse_file_save()
                
    def wait_mouse_file_save(self):
        if hasattr(self.parent, 'mouse_file_handler'):
            while self.parent.mouse_file_handler.running:
                    time.sleep(0.1)
                
    def mouse_file_saver(self):
        if hasattr(self, 'mouse_file') and os.path.exists(self.mouse_file) and utils.safe_has_key(self.queues, 'mouse_file_handler') and not self.queues['mouse_file_handler'].empty():
            if not hasattr(self, 'local_mouse_file'):
               self.local_mouse_file = os.path.join(tempfile.gettempdir(), os.path.split(self.mouse_file)[1])
            self.running = True
            h = hdf5io.Hdf5io(self.local_mouse_file,filelocking=False)
            field_names_to_save = []
            while not self.queues['mouse_file_handler'].empty():
                field_name, field_value = self.queues['mouse_file_handler'].get()
                if field_name == 'animal_parameters':
                    field_name += str(int(time.time()))
                if field_name == 'scan_regions' and ENABLE_SCAN_REGION_SERIALIZATION:
                    new_fv={}
                    for srn in field_value.keys():
                        new_fv[srn]=utils.object2array(field_value[srn])
                    field_value = new_fv
                setattr(h, field_name, field_value)
                if not field_name in field_names_to_save:
                    field_names_to_save.append(field_name)
            h.save(field_names_to_save, overwrite = True)
            h.close()
            if os.path.exists(self.mouse_file):
                os.remove(self.mouse_file)
            shutil.copy(self.local_mouse_file, self.mouse_file)
            self.running = False
            self.printc('{0} saved to mouse file'.format(', '.join(field_names_to_save)))
            
    def backup_mousefile(self):
        if hasattr(self, 'animal_parameters') and hasattr(self, 'mouse_file'):
            self.printc('Backing up mouse file')
            try:
                h = hdf5io.Hdf5io(self.mouse_file,filelocking=False)
                h.close()
            except:
                self.printc('Backing up mouse file was not successful')
                return
            if 0:
                self.printc('1')
                dir = os.path.join(self.config.DATABIG_PATH,  utils.date_string().replace('-',''), self.animal_parameters['id'])
                #Mouse file is backed up if 1) backup path exists or 2) animal parameters were created max 8 hours ago
    #            import datetime#TODO: mouse file is backed up at mouse file change (at startup, not backed up when databig folder created only if region save happens
    #            animal_parameter_save_timestamp =  time.mktime(datetime.datetime.strptime(self.animal_parameters['add_date'], "%Y-%m-%d %H-%M-%S").timetuple())
                if not os.path.exists(dir):# and time.time() - animal_parameter_save_timestamp<8*3600:
                    os.makedirs(dir)
    #            if not os.path.exists(dir):
    #                self.printc('Backing up mouse file aborted')
    #                return
                self.printc('2')
                databig_path = os.path.join(dir, os.path.split(self.mouse_file)[1])
                if os.path.exists(databig_path):
                    os.remove(databig_path)
                try:
                    shutil.copy(self.mouse_file, databig_path)
                    self.printc('3')
                except:
                    self.printc(traceback.format_exc())
                    self.printc('Problem with copying mousefile to databig.')
                    self.printc('4')
                self.printc('5')
            if 1:#New backup
                try:
                    #files=[fn for fn in file.find_files_and_folders(self.config.EXPERIMENT_DATA_PATH,extension='hdf5')[1] if os.path.basename(fn)== self.mouse_file]
                    files=[fn for fn in list_mouse_files(self.config) if os.path.basename(fn)== os.path.basename(self.mouse_file)]
                    rn=[rn for rn in self.scan_regions.keys() if self.parent.get_current_region_name() in rn]
                    if len(rn)==1:
                        d=self.scan_regions[rn[0]]['add_date']
                    else:
                        d=self.animal_parameters['add_date']
                    id=str(d.split(' ')[0].replace('-',''))
                    experiment_data.RlvivoBackup(files,str(self.animal_parameters['user'] if self.animal_parameters.has_key('user') else 'default_user'),id,str(self.animal_parameters['id']),todatabig=True)
                except:
                    self.printc(traceback.format_exc())
                    msg='ERROR: Automatic backup failed, please make sure that files are copied to u:\\backup'
                    self.printc(msg)
                    self.notify(msg)
                    raise 
                
    def cells2pickled_ready(self, cells):
        '''
        This is a workaround for a couple of compatibility problems between pickle and hdf5io
        '''
        for sr in cells.values():
            for cell in sr.values():
                if cell['group'] == '':
                    cell['group'] = 'none'
                cell['roi_center'] = utils.rcd((cell['roi_center']['row'], cell['roi_center']['col'], cell['roi_center']['depth']))
        return cells
        
class MouseFileHandler(Poller):
    '''
    Performs all write operations to the moouse file, ensuring that this time consuming procedure does not increase
    main poller's response time.
    '''
    def __init__(self, parent):
        Poller.__init__(self, parent)
        self.running = False
        
    def handle_commands(self):
        '''
        Receives commands from main poller to save data to mouse file
        '''
        if hasattr(self.parent.poller, 'mouse_file') and os.path.exists(self.parent.poller.mouse_file) and utils.safe_has_key(self.parent.queues, 'mouse_file_handler') and not self.parent.queues['mouse_file_handler'].empty():
            self.running = True
            h = hdf5io.Hdf5io(self.parent.poller.mouse_file,filelocking=False)
            field_names_to_save = []
            while not self.parent.queues['mouse_file_handler'].empty():
                field_name, field_value = self.parent.queues['mouse_file_handler'].get()
                if field_name == 'animal_parameters':
                    field_name += str(int(time.time()))
#                if field_name == 'cells':
#                    field_value = utils.object2array(self.cells2pickled_ready(field_value))
                setattr(h, field_name, field_value)
                if not field_name in field_names_to_save:
                    field_names_to_save.append(field_name)
#            try:
#                field_names_to_save.remove('roi_curves')
#            except:
#                pass
            for f in field_names_to_save:
                print f
                h.save(f, overwrite = True)
            h.close()
            self.running = False
            self.printc('{0} saved to mouse file'.format(', '.join(field_names_to_save)))
        else:
            time.sleep(1.0)
            
    def cells2pickled_ready(self, cells):
        '''
        This is a workaround for a couple of compatibility problems between pickle and hdf5io
        '''
        for sr in cells.values():
            for cell in sr.values():
                if cell['group'] == '':
                    cell['group'] = 'none'
                cell['roi_center'] = utils.rcd((cell['roi_center']['row'], cell['roi_center']['col'], cell['roi_center']['depth']))
        return cells

class Image(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setBackground((255,255,255))
        self.roi_default_diameter = 20
#        self.view = self.addViewBox()
        self.plot=self.addPlot()
        self.img = pyqtgraph.ImageItem(border='w')
        self.plot.addItem(self.img)
        self.plot.showGrid(True,True,1.0)
#        self.plot.setZValue(5)
#        self.view.setAspectLocked(True)
#        self.view.setRange(QtCore.QRectF(0, 0, 100, 100))
        self.scene().sigMouseClicked.connect(self.mouse_clicked)
        self.rois = []
#        self.plot.autoRange()
        
    def set_image(self, image):
        im=0.8*numpy.ones((image.shape[0],image.shape[1], 4))*image.max()
        im[:,:,:3]=image
        self.img.setImage(im)

    def mouse_clicked(self,e):
        p=self.img.mapFromScene(e.scenePos())
        if e.double():
            if int(e.buttons()) == 1:
                self.add_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            elif int(e.buttons()) == 2:
                self.remove_roi(p.x()*self.img.scale(), p.y()*self.img.scale())
            self.update_roi_info()
#            print self.roi_info
        
    def add_roi(self,x,y):
        roi = pyqtgraph.CircleROI([x-0.5*self.roi_default_diameter , y-0.5*self.roi_default_diameter ], [self.roi_default_diameter , self.roi_default_diameter ])
        roi.setPen((255,0,0,255), width=2)
        self.rois.append(roi)
        self.plot.addItem(self.rois[-1])
        
    def remove_roi(self,x,y):
        distances = [(r.pos().x()-x)**2+(r.pos().y()-y)**2 for r in self.rois]
        removable_roi = self.rois[numpy.array(distances).argmin()]
        self.plot.removeItem(removable_roi)
        self.rois.remove(removable_roi)
        
    def update_roi_info(self):
        self.roi_info = [[i, self.rois[i].x(), self.rois[i].y()] for i in range(len(self.rois))]
        
class Plots(pyqtgraph.GraphicsLayoutWidget):
    '''
    Number of plots can be updated in runtime
    '''
    def __init__(self,parent):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setBackground((255,255,255))
        self.setAntialiasing(True)
        self.plots = []
        return
#        self.set_plot_num(3,4)
#        traces = []
#        for i in range(3):
#            traces1 = []
#            for j in range(4):
#                traces1.append({'x':numpy.arange(100), 'y': numpy.sin(numpy.arange(100)/(j+1+i)), 'title': (i,j)})
#            traces.append(traces1)
#        self.addplots(traces)
        
    def addplots(self,traces):
        self.plots = []
        self.clear()
        for r in range(self.nrows):
            for c in range(self.ncols):
                self.addplot(traces[r][c])
                    
            self.nextRow()
        
    def set_plot_num(self,nrows,ncols):
        self.nrows=nrows
        self.ncols=ncols
        
    def addplot(self,traces):
        self.plots.append(self.addPlot(title='{0}, {1:.2f}'.format(traces['title'],traces['response_size'])))#, colspan=10, rowspan=10))
        color_index=0
        for trace in traces['trace']:
            if trace.has_key('color'):
                c=trace['color']
            else:
                c = tuple(numpy.cast['int'](numpy.array(colors.get_color(0))*255))
            self.plots[-1].plot(trace['x'], trace['y'], pen=c)
            color_index+=1
        self.plots[-1].showGrid(True,True,1.0)
        c=(255-255*traces['response_size_scaled'],255-255*traces['response_size_scaled'],255-255*traces['response_size_scaled'],128)
        
        self.offtime=self.parent().offtime
        self.ontime=self.parent().ontime
        linear_region = pyqtgraph.LinearRegionItem([self.offtime*0.5, self.offtime*0.5+self.ontime], movable=False, brush = c)
        self.plots[-1].addItem(linear_region)
        self.plots[-1].setMaximumHeight(90)
        
def list_mouse_files(config):
    mfiles=[]
    for dirname in os.listdir(config.EXPERIMENT_DATA_PATH):
        if dirname=='output':
            continue
        dirname=os.path.join(config.EXPERIMENT_DATA_PATH, dirname)
        if os.path.isdir(dirname):
            mfiles.extend([os.path.join(dirname, fn) for fn in os.listdir(dirname) if fn[-5:]=='.hdf5' and 'mouse' in fn])
        elif dirname[-5:]=='.hdf5' and 'mouse' in dirname:
            mfiles.append(dirname)
    return mfiles

        

def update_mouse_files_list(config, current_mouse_files = []):
    
#    new_mouse_files = file.filtered_file_list(config.EXPERIMENT_DATA_PATH,  ['mouse', 'hdf5'], filter_condition = 'and')
   # new_mouse_files = [mouse_file for mouse_file in new_mouse_files if '_jobhandler' not in mouse_file and '_stim' not in mouse_file and '_copy' not in mouse_file and os.path.isfile(os.path.join(config.EXPERIMENT_DATA_PATH,mouse_file))]
    #print len(os.listdir(config.EXPERIMENT_DATA_PATH))
    #fns=os.listdir(config.EXPERIMENT_DATA_PATH)
#    if len(fns)>1000:
#        print  'WARNING: too many files in {0}, please remove the old ones.'.format(config.EXPERIMENT_DATA_PATH)
    #new_mouse_files=[os.path.basename(fn) for fn in file.find_files_and_folders(config.EXPERIMENT_DATA_PATH,extension='hdf5')[1] if 'mouse' in fn and '.hdf5'==fn[-5:]]
    new_mouse_files_full=list_mouse_files(config)
    new_mouse_files=[os.path.basename(fn) for fn in new_mouse_files_full]
    #new_mouse_files=[fn for fn in file.find_files_and_folders(config.EXPERIMENT_DATA_PATH)[1] if 'mouse' in fn and '.hdf5'==fn[-5:]]
    #print 0.05
    new_mouse_files=[fn for fn in new_mouse_files if '_jobhandler' not in fn and '_stim' not in fn]
    #print 0.1
    new_mouse_files.sort()
    current_mouse_files1= current_mouse_files
    current_mouse_files1.sort()
    #print 0.2
    if current_mouse_files1 != new_mouse_files:
        are_new_files = True
    else:
        are_new_files = False
    return are_new_files, new_mouse_files, new_mouse_files_full

if __name__ == '__main__':
    pass
    
