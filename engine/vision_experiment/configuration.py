import os
import sys
import numpy
import scipy.interpolate
import visexpman
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.configuration
try:
    import serial
except:
    pass

import tempfile
import unittest

import PyQt4.QtGui as QtGui

import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner

class VisionExperimentConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        '''
        By overdefining this function, the application/user etc specific parameters can be definced here:
            self.PAR_p =   
            
            parameters that the user need to define: (This is a way to force users to create their configs carefully
            EXPERIMENT_CONFIG = 'TestExperimentConfig'
            LOG_PATH = '/media/Common/visexpman_data'
            EXPERIMENT_LOG_PATH = '/media/Common/visexpman_data'
            EXPERIMENT_DATA_PATH = '/media/Common/visexpman_data'
            CAPTURE_PATH = '/media/Common/visexpman_data/Capture'
            
            
            MEASUREMENT_PLATFORM = 'mes', 'elphys', 'mea', 'smallapp'
           
        '''
        visexpman.engine.generic.configuration.Config._create_application_parameters(self)
        
        self.enable_celery = True
        self.temppath = tempfile.gettempdir()
        
        #parameter with range: list[0] - value, list[1] - range
        #path parameter: parameter name contains '_PATH'
        #string list: list[1] - empty
        ############## Ranges ###############
        FPS_RANGE = (1.0,  200.0) 
        COLOR_RANGE = [[0.0, 0.0,  0.0],  [1.0, 1.0,  1.0]]
        PIN_RANGE = [0,  7]        
        PLATFORM = ['undefined', ['mes', 'elphys', 'mea', 'standalone', 'smallapp', 'undefined']]
        EXPERIMENT_FILE_FORMAT = ['undefined', ['hdf5', 'mat', 'undefined']]
        
        ############# Network #####################      
        WAIT_BETWEEN_UDP_SENDS = [0.05,  [0.0,  1.0]]
        CLIENT_UDP_IP = ''
        ENABLE_UDP = False
        UDP_PORT =[446,  [200,  65000]] #RZ Why dont you like 446  Since this is used only in Presentinator setups and there the 446 port is used, this can be 446 instead of 9999
        UDP_BUFFER_SIZE = [65536,  [1,  100000000]]        
        #naming: server - client
        self.BASE_PORT = 10000
        COMMAND_RELAY_SERVER  = {
        'RELAY_SERVER_IP' : '',
        'RELAY_SERVER_IP_FROM_TABLE': False,
        'ENABLE' : False,
        'CLIENTS_ENABLE': False, 
        'TIMEOUT':6.0,#6
        'CONNECTION_MATRIX':
            {
            'GUI_MES'  : {'GUI' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT}, 'MES' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT + 1}}, 
            'STIM_MES'  : {'STIM' : {'IP': '1', 'LOCAL_IP': '', 'PORT': self.BASE_PORT+2}, 'MES' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT + 3}}, 
            'GUI_STIM'  : {'GUI' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT+4}, 'STIM' : {'IP': '', 'LOCAL_IP': '',  'PORT': self.BASE_PORT + 5}}, 
            'GUI_ANALYSIS'  : {'GUI' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT+6}, 'ANALYSIS' : {'IP': '', 'LOCAL_IP': '', 'PORT': self.BASE_PORT + 7}}, 
            },
        'SERVER_IP':{
                     'GUI_MES': '',
                     'STIM_MES': '',
                     'GUI_STIM': '',
                     'GUI_ANALYSIS'  : '',
                     }
        }
        
        ################ Mes parameters #############
        ENABLE_MES = False
        MES_TIMEOUT = [10.0, [1.0, 100.0]]
        MES_RECORD_START_DELAY = [3.0, [1.0, 10.0]]
        OBJECTIVE_POSITION_LIMIT = [1000.0, [500.0, 2000.0]]
        MES_Z_SCAN_SCOPE = [100.0, [0.0, 200.0]]
        DEFAULT_Z_SCAN_OVERLAP = [10.0, [0.0,  50]]
        OBJECTIVE_TRANSIENT_SMOOTHING_TIME = [13, [0, 20]]
        #default XZ scanning config
        XZ_SCAN_CONFIG = {'LINE_LENGTH':20.0, 'Z_PIXEL_SIZE' : 33.0, 'Z_RESOLUTION':3.03, 'Z_RANGE' : 100.0}
        XZ_FRAME_CLIPPING = {'top': 4,  'bottom':3}
        ROI_PATTERN_SIZE = [2, [1, 10]]
        ROI_PATTERN_RADIUS = [1, [0, 50]]
        
        ########### Vision experiment manager GUI #################
        screen_size = utils.cr((800, 600))
        if len(sys.argv) > 0:
            if 'gui' in sys.argv[0]: #if gui is the main module
                screen_size = QtGui.QDesktopWidget().screenGeometry()
                screen_size = utils.cr((0.75*screen_size.width(), 0.9*screen_size.height()))
        MAX_REGISTRATION_TIME = [30.0, [0.5, 600.0]]
        GUI_STAGE_TIMEOUT = [30.0, [0.5, 60.0]]
        DEFAULT_PMT_CHANNEL = ['pmtUGraw',  ['pmtUGraw', 'pmtURraw',  'undefined']]
        GUI_POSITION = utils.cr((5, 5))
        GUI_SIZE = screen_size
        TAB_SIZE = utils.cr((0.27 * screen_size['col'], 0.6 * screen_size['row']))
        COMMON_TAB_SIZE = utils.cr((0.3 * screen_size['col'], 0.1 * screen_size['row']))
        STANDARDIO_WIDGET_TAB_SIZE = utils.cr((0.3 * screen_size['col'], 0.3 * screen_size['row']))
        IMAGE_SIZE = utils.cr((0.33 * screen_size['col'], 0.33 * screen_size['col']))
        OVERVIEW_IMAGE_SIZE = utils.cr((0.6 * screen_size['col'], 0.6* screen_size['col']))
        ROI_INFO_IMAGE_SIZE = utils.rc((int(1.55*IMAGE_SIZE['row']), int(1.35*OVERVIEW_IMAGE_SIZE['col'])))#FIXME: this is not reasonable but working
        ROI_CURVE_IMAGE_CUTOUT = [1600, [0, 2000]]
        SIDEBAR_SIZE = [30, [10, 100]]
        GUI_REFRESH_PERIOD = [2.0, [0.1, 10.0]]
        GREEN_LABELING = ['']
        MANUAL_URL = 'http://pprl/ZoltanRaics/Visexpman/manual'
        SCAN_REGION_TIMEOUT=[12.0, [1.0, 168.0]]
        #realignment parameters
        MAX_REALIGNMENT_OFFSET = [50.0, [10.0, 1000.0]]
        ACCEPTABLE_REALIGNMENT_OFFSET = [2.0, [0.1, 10.0]]
        REALIGNMENT_XY_THRESHOLD = [1.0, [0.1, 10.0]]
        REALIGNMENT_Z_THRESHOLD = [1.0, [0.1, 10.0]]
        CELL_MERGE_DISTANCE = [3.0, [1.0, 20.0]]
        MIN_SCAN_REGION_AVERAGING = [3, [1, 10]]
        
        #############  Jobhandler  ############
        PARSE_PERIOD = [5.0, [0.0, 10.0]]
        MOUSE_FILE_CHECK_PERIOD = [10.0, [0.0, 10.0]]
        ENABLE_MESEXTRACTOR = True
        ENABLE_CELL_DETECTION = True
        ENABLE_ZIGZAG_CORRECTION = True
        
        ############### Display/graphics parameters: ################
        SCREEN_RESOLUTION = utils.rc([600, 800])        
        FULLSCREEN = False
        SCREEN_EXPECTED_FRAME_RATE = [60.0,  FPS_RANGE]
        SCREEN_MAX_FRAME_RATE = [60.0,  FPS_RANGE]
        FRAME_DELAY_TOLERANCE = [2.0,  [1e-2,  10.0]] #in Hz
        BACKGROUND_COLOR = [[0.0, 0.0,  0.0],  COLOR_RANGE]
        GAMMA = [1.0,  [1e-2,  10]]
        FRAME_WAIT_FACTOR = [0.9,  [0.0,  1.0]]
        FLIP_EXECUTION_TIME = [0*1e-3, [0.0, 1.0]]
        ENABLE_FRAME_CAPTURE = False
        MAX_LOG_COLORS = [3,  [0,  100000]]        
        
        ########  Coordinate system selection ########
        COORDINATE_SYSTEM = ['undefined', ['ulcorner','center', 'undefined']] 
        ORIGO = utils.rc((numpy.inf, numpy.inf))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = ['undefined',  ['left', 'right', 'undefined']]
        VERTICAL_AXIS_POSITIVE_DIRECTION = ['undefined',  ['up', 'down', 'undefined']]
        
        ####### Pixel scaling #################
        IMAGE_PROJECTED_ON_RETINA = True
        SCREEN_UM_TO_PIXEL_SCALE = [1.0,  [1e-3,  1e3]] #converts um to pixel [pixel/um]
        
        ########## Commands #############
        COMMAND_DOMAINS = ['keyboard', 'running experiment', 'network interface', 'remote client']
        #Currently the keyboard and running experiment domains are considered:
        #-keyboard: at generating menu for hotkeys
        #-running experiment: during experiment only these commands are accepted
        COMMANDS = { 
                    'hide_menu': {'key': 'h', 'domain': ['keyboard']}, 
                    #Dynamically added to the list: 'experiment_select' : {'key' : None, 'domain': ['keyboard']},
                    'execute_experiment': {'key': 'e', 'domain': ['keyboard', 'network interface', 'remote client']}, 
                    'abort_experiment': {'key': 'a', 'domain': ['running experiment']}, 
                    'bullseye': {'key': 'b', 'domain': ['keyboard', 'network interface', 'remote client']}, 
                    'color': {'key': 'c', 'domain': ['network interface', 'remote client']},
                    'filterwheel': {'key': 'f', 'domain': ['network interface', 'remote client']},
                    'echo' : {'key' : 't', 'domain': ['keyboard', 'network interface', 'remote client']},
                    'set_measurement_id' : {'key' : 'i', 'domain': ['keyboard', 'network interface', 'remote client']},
                    'quit': {'key': 'escape', 'domain': ['keyboard', 'network interface', 'remote client']},#Perhaps this command shall be accepted from keyboard
                    }
        #By overriding this parameter, the user can define additional keyboard commands that are handled during experiment
        USER_EXPERIMENT_COMMANDS = {}
        
        ############## Vision experiment maganer user interface ##########
        ENABLE_TEXT = True
        TEXT_COLOR = [[1.0,  0.0,  0.0] ,  [[0.0, 0.0, 0.0],  [1.0,  1.0,  1.0]]]
        MENU_POSITION = utils.cr((-0.48, 0.45))
        MESSAGE_POSITION = utils.cr((-0.48,-0.15))
        NUMBER_OF_MESSAGE_ROWS = [15, [1, 40]]
        MAX_MESSAGE_LENGTH = [180,  [10,  1000]] #length of message displayed on screen
#TODO obsolete        SEGMENT_DURATION = [100,  [1,  100000]]
#TODO obsolete        ACTION_BETWEEN_STIMULUS = 'no' #keystroke, wait_xx in sec. no =  off

        ############# External hardware ######################
        #parallel port
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = [0,  PIN_RANGE]
        FRAME_TRIGGER_PIN = [2,  PIN_RANGE]
        FRAME_TRIGGER_PULSE_WIDTH = [1e-3,  [1e-4,  1e-1]]
        #filterwheel settings
        ENABLE_FILTERWHEEL = False
        FILTERWHEEL_SETTLING_TIME = [0.4,  [0,  20]]
        FILTERWHEEL_VALID_POSITIONS = [[1, 6],  [[0, 0],  [100, 100]]]        
#        FILTERWHEEL_SERIAL_PORT = [[{
#                                    'port' :  port,
#                                    'baudrate' : 115200,
#                                    'parity' : serial.PARITY_NONE,
#                                    'stopbits' : serial.STOPBITS_ONE,
#                                    'bytesize' : serial.EIGHTBITS,                                    
#                                    }]]        
#        FILTERWHEEL_FILTERS = [[{
#                                                'ND0': 1, 
#                                                'ND10': 2, 
#                                                'ND20': 3, 
#                                                'ND30': 4, 
#                                                'ND40': 5, 
#                                                'ND50': 6, 
#                                                }]]
        ENABLE_SHUTTER = False
        LED_CONTROLLER_INSTRUMENT_INDEX = [0, [0, 100]]
        SYNC_CHANNEL_INDEX = [-1,  [-1,  10]]
        SYNC_SIGNAL_MIN_AMPLITUDE = [1.5, [0.5, 10.0]]
#                 DAQ_CONFIG = [[
#         {
#         'ANALOG_CONFIG' : 'aio', #'ai', 'ao', 'aio', 'undefined'
#         'DAQ_TIMEOUT' : 1.0, 
#         'AO_SAMPLE_RATE' : 100,
#         'AI_SAMPLE_RATE' : 1000,
#         'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
#         'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai9:0',        
#         'MAX_VOLTAGE' : 5.0,
#         'MIN_VOLTAGE' : 0.0,
#         'DURATION_OF_AI_READ' : 1.0,
#         'ENABLE' : True
#         },
#         {
#         'ANALOG_CONFIG' : 'undefined',
#         'DAQ_TIMEOUT' : 0.0, 
#         'AO_SAMPLE_RATE' : 100,
#         'AI_SAMPLE_RATE' : 1000,
#         'AO_CHANNEL' : unit_test_runner.TEST_daq_device + '/ao0:1',
#         'AI_CHANNEL' : unit_test_runner.TEST_daq_device + '/ai9:0',
#         'MAX_VOLTAGE' : 5.0,
#         'MIN_VOLTAGE' : 0.0,
#         'DURATION_OF_AI_READ' : 1.0,
#         'ENABLE' : True
#         }
#         ]]
        TILTING_LIMIT = [1.5, [0.0, 10.0]]
        ADD_CELLS_TO_MOUSE_FILE = False
        SHOW_OVERVIEW = False
        IMAGING_CHANNELS = 'default' #or 'both'
        BLACK_SCREEN_DURING_PRE_SCAN = False
        STIMULUS2MEMORY=False
        #this function call is compulsory
        self._create_parameters_from_locals(locals())

    def _calculate_parameters(self):
        '''
        Function for modifying parameters with calculations and creating new parameters calculated from existing values
        '''        
        #== Paths ==
        DEFAULT_IMAGE_FILE = os.path.join(self.PACKAGE_PATH ,'data','images','default.bmp')
        BULLSEYE_FILE = self.PACKAGE_PATH + os.sep + 'data' + os.sep + 'images'+ os.sep +'bullseye.bmp'        
    
        #== Command list and menu text ==
        #Check if there is no redundancy in command configuration
        self.COMMANDS = self._merge_commands(self.COMMANDS, self.USER_EXPERIMENT_COMMANDS)        
        MENU_TEXT = ''
        for k, v in self.COMMANDS.items():            
            if utils.is_in_list(v['domain'], 'keyboard'):                
                MENU_TEXT += v['key'] + ' - ' + k + '\n'

        self._create_parameters_from_locals(locals()) # make self.XXX_p from XXX
        
        #== Parallel port pins ==        
        ACQUISITION_TRIGGER_ON = 1<<self.ACQUISITION_TRIGGER_PIN
        self.ACQUISITION_TRIGGER_ON_p = visexpman.engine.generic.parameter.Parameter(ACQUISITION_TRIGGER_ON,  range_ = [0,  255])
        self.ACQUISITION_TRIGGER_OFF_p = visexpman.engine.generic.parameter.Parameter(0,  range_ = [0,  255])
        self.FRAME_TRIGGER_ON_p = visexpman.engine.generic.parameter.Parameter(ACQUISITION_TRIGGER_ON | 1<<self.FRAME_TRIGGER_PIN,  range_ = [0,  255])
        self.FRAME_TRIGGER_OFF_p = visexpman.engine.generic.parameter.Parameter(ACQUISITION_TRIGGER_ON,  range_ = [0,  255])
        
        #== Screen scaling ==
        self.SCREEN_PIXEL_TO_UM_SCALE_p = visexpman.engine.generic.parameter.Parameter(1.0 / self.SCREEN_UM_TO_PIXEL_SCALE,  range_ = [-1000.0,  1000.0])
        screen_resolution = 1.0 / numpy.array([self.SCREEN_RESOLUTION['col'], self.SCREEN_RESOLUTION['row']])
        SCREEN_UM_TO_NORM_SCALE = 2.0 * self.SCREEN_PIXEL_TO_UM_SCALE_p.v * screen_resolution
        self.SCREEN_UM_TO_NORM_SCALE_p = visexpman.engine.generic.parameter.Parameter(SCREEN_UM_TO_NORM_SCALE)
        self.SCREEN_SIZE_UM_p = visexpman.engine.generic.parameter.Parameter(utils.cr((self.SCREEN_RESOLUTION['col'] / self.SCREEN_UM_TO_PIXEL_SCALE, self.SCREEN_RESOLUTION['row'] / self.SCREEN_UM_TO_PIXEL_SCALE)))
        print self.SCREEN_SIZE_UM_p.v
        ######################### Coordinate system #########################
        if self.COORDINATE_SYSTEM != 'undefined':
            self.ORIGO, self.HORIZONTAL_AXIS_POSITIVE_DIRECTION, self.VERTICAL_AXIS_POSITIVE_DIRECTION= utils.coordinate_system(self.COORDINATE_SYSTEM, self.SCREEN_RESOLUTION)
        elif unit_test_runner.TEST_test:
            #In test mode we do not check for raised exception but test for the existence of certain variables
            pass
        elif self.PLATFORM != 'smallapp':
            raise ValueError('No coordinate system selected in config,  nor explicit settings for origo and axes was given.')
            
        self.SCREEN_CENTER_p = visexpman.engine.generic.parameter.Parameter(utils.rc((0,0)))
        #== Cooridnate system type dependencies ==
        if self.COORDINATE_SYSTEM == 'ulcorner':
            self.MENU_POSITION_p.v = utils.centered_to_ulcorner_coordinate_system(self.MENU_POSITION_p.v, utils.cr((1.0, 1.0)))
            self.MESSAGE_POSITION_p.v = utils.centered_to_ulcorner_coordinate_system(self.MESSAGE_POSITION_p.v, utils.cr((1.0, 1.0)))
            self.SCREEN_CENTER_p.v = utils.rc((0.5 * self.SCREEN_SIZE_UM_p.v['row'], 0.5 * self.SCREEN_SIZE_UM_p.v['col']))
            
        ########### Projector gamma correction ############
        if hasattr(self, 'GAMMA_CORRECTION'):
            #normalize
            x = self.GAMMA_CORRECTION[:, 0]
            y = self.GAMMA_CORRECTION[:, 1]
            x = x/x.max()
            y = y/y.max()
            self.GAMMA_CORRECTION = scipy.interpolate.interp1d(y, x, bounds_error  = False, fill_value  = 0.0)
        ########### Context file #########
        if hasattr(self, 'CONTEXT_PATH') and hasattr(self, 'CONTEXT_NAME'):
            self.CONTEXT_FILE_p = visexpman.engine.generic.parameter.Parameter(os.path.join(self.CONTEXT_PATH, self.CONTEXT_NAME))
        
        if hasattr(self, 'EXPERIMENT_DATA_PATH'):
            self.cachepath = self.EXPERIMENT_DATA_PATH#To ensure compatibility with analysis config class #TODO: visexpA and visexpman config classes shall be merged into one class
        self.cacheext = 'hdf5'
        self.packagepath = 'visexpA.users.daniel'

    def _merge_commands(self, command_list, user_command_list):        
        commands = dict(command_list.items() + user_command_list.items())
        for user_command_name in user_command_list.keys():
            if command_list.has_key(user_command_name):
                raise RuntimeError('Redundant command name: {0} is reserved'.format(user_command_name))
        
        all_keys = []
        for k, v in commands.items():            
            if utils.is_in_list(all_keys, v['key']):
                raise RuntimeError('Redundant keyboard command: {0} is reserved'.format(v['key']))
            else:
                all_keys.append(v['key'])
        return commands
        
class TestConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        PAR1 = 'par'
        PAR2 = 'par2'
        self._create_parameters_from_locals(locals())

    def _set_user_parameters(self):
        '''
        Function for overriding the application's default parameter values
        '''
        PAR1 = 'par1'
        self._set_parameters_from_locals(locals())
        pass

    def _calculate_parameters(self):
        '''
        Function for modifying parameters with calculations and creating new parameters calculated from existing values
        '''        
        self.PAR3_p = visexpman.engine.generic.parameter.Parameter(self.PAR1+self.PAR2) 
        self.PAR3 = self.PAR3_p.v
    
class RedundantCommandConfig1(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'
        path = unit_test_runner.TEST_working_folder
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = path
        EXPERIMENT_DATA_PATH = path
        ARCHIVE_FORMAT = 'zip'
        COORDINATE_SYSTEM='center'
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, 'dummy1': {'key': 'e', 'domain': ['running experiment']}, 'dummy': {'key': 'w', 'domain': ['running experiment']},}
        self._create_parameters_from_locals(locals())
        
class RedundantCommandConfig2(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'
        path = unit_test_runner.TEST_working_folder
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = path
        EXPERIMENT_DATA_PATH = path
        ARCHIVE_FORMAT = 'zip'
        COORDINATE_SYSTEM='center'
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, 'dummy1': {'key': 'e', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())        

class RedundantCommandConfig3(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'
        path = unit_test_runner.TEST_working_folder
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = path
        EXPERIMENT_DATA_PATH = path
        ARCHIVE_FORMAT = 'zip'
        COORDINATE_SYSTEM='center'
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, 'bullseye': {'key': 'x', 'domain': ['running experiment']},}
        self._create_parameters_from_locals(locals())
    
class NonRedundantCommandConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'VerySimpleExperimentConfig'        
        path = unit_test_runner.TEST_working_folder
        LOG_PATH = path
        EXPERIMENT_LOG_PATH = path
        EXPERIMENT_DATA_PATH = path
        ARCHIVE_FORMAT = 'zip'
        COORDINATE_SYSTEM='center'
        USER_EXPERIMENT_COMMANDS = {'dummy': {'key': 'd', 'domain': ['running experiment']}, }
        self._create_parameters_from_locals(locals())


class testApplicationConfiguration(unittest.TestCase):
    def test_01_ConfigClass(self):
        t = TestConfig()
        self.assertEqual((t.PAR1,  t.PAR2,  t.PAR3),  ('par1', 'par2',  t.PAR1+t.PAR2))
        
    def test_02_non_redundant_user_command_config(self):        
        commands = { 
                    'hide_menu': {'key': 'h', 'domain': ['keyboard']}, 
                    #Dynamically added to the list: 'experiment_select' : {'key' : None, 'domain': ['keyboard']},
                    'execute_experiment': {'key': 'e', 'domain': ['keyboard', 'network interface', 'remote client']}, 
                    'abort_experiment': {'key': 'a', 'domain': ['running experiment']}, 
                    'bullseye': {'key': 'b', 'domain': ['keyboard', 'network interface', 'remote client']}, 
                    'color': {'key': 'c', 'domain': ['network interface', 'remote client']},
                    'filterwheel': {'key': 'f', 'domain': ['network interface', 'remote client']},
                    'echo' : {'key' : 't', 'domain': ['keyboard', 'network interface', 'remote client']},
                    'set_measurement_id' : {'key' : 'i', 'domain': ['keyboard', 'network interface', 'remote client']},
                    'quit': {'key': 'escape', 'domain': ['keyboard', 'network interface', 'remote client']},
                    'dummy': {'key': 'd', 'domain': ['running experiment']}, 
                    }
        t = NonRedundantCommandConfig()
        self.assertEqual((t.COMMANDS),  (commands))
        
    def test_03_redundant_user_command_config(self):        
        self.assertRaises(RuntimeError,  RedundantCommandConfig1)
        
    def test_04_redundant_user_command_config(self):        
        self.assertRaises(RuntimeError,  RedundantCommandConfig2)
        
    def test_05_redundant_user_command_config(self):        
        self.assertRaises(RuntimeError,  RedundantCommandConfig3)
        
    def test_06_check_default_visexp_config(self):
        t = VisionExperimentConfig()
        self.assertEqual((hasattr(t, 'EXPERIMENT_CONFIG'),
                          hasattr(t, 'LOG_PATH'),
                          hasattr(t, 'EXPERIMENT_LOG_PATH'),
                          hasattr(t, 'EXPERIMENT_DATA_PATH'),
                          hasattr(t, 'CAPTURE_PATH'),
                          hasattr(t, 'FILTERWHEEL_FILTERS'), 
                          hasattr(t, 'FILTERWHEEL_SERIAL_PORT'), 
                          t.ORIGO, 
                          t.HORIZONTAL_AXIS_POSITIVE_DIRECTION, 
                          t.VERTICAL_AXIS_POSITIVE_DIRECTION, 
                          t.COORDINATE_SYSTEM,
                          t.FULLSCREEN, 
                          t.ENABLE_FRAME_CAPTURE, 
                          t.ENABLE_PARALLEL_PORT, 
                          t.ENABLE_FILTERWHEEL, 
                          t.ENABLE_SHUTTER, 
                          ),
                         (False, False, False, False, False, False, False, utils.rc((numpy.inf, numpy.inf)), 'undefined', 'undefined', 'undefined', False, False, False, False, False))
        


if __name__ == "__main__":
    unittest.main()
    
