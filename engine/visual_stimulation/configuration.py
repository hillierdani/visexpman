import os
import sys
import numpy
import visexpman
import visexpman.engine.generic.utils as utils
import visexpman.engine.generic.configuration
try:
    import serial
except:
    pass

import unittest

#TODO: make  naming of *ENABLE* like parameters consistent: ENABLE*
class VisualStimulationConfig(visexpman.engine.generic.configuration.Config):
    def _create_application_parameters(self):
        '''
        By overdefining this function, the application/user etc specific parameters can be definced here:
            self.PAR_p =              
        '''        
        visexpman.engine.generic.configuration.Config._create_application_parameters(self)
        #system parameters
        if os.name == 'nt':
            OS_TYPE = 'win'
        elif os.name == 'posix':
            OS_TYPE = 'linux'
        else:
            OS_TYPE = 'unknown'
        
        #parameter with range: list[0] - value, list[1] - range
        #path parameter: parameter name contains '_PATH'
        #string list: list[1] - empty
        #ranges
        FPS_RANGE = (1.0,  200.0) 
        COLOR_RANGE = [[0.0, 0.0,  0.0],  [1.0, 1.0,  1.0]]
        PIN_RANGE = [0,  7]
        
        #run options: single experiment, user interface
        RUN_MODE = ['single experiment',  ['single experiment',  'user interface',  'unknown']]
            
        #this a valid stimulation file path or an experiment object name
        EXPERIMENT_CONFIG = 'undefined'
        
        #display parameters:
        SCREEN_RESOLUTION = utils.rc([600, 800])        
        FULLSCREEN = True
        SCREEN_EXPECTED_FRAME_RATE = [60.0,  FPS_RANGE]
        SCREEN_MAX_FRAME_RATE = [60.0,  FPS_RANGE]
        FRAME_DELAY_TOLERANCE = [2.0,  [1e-2,  10.0]] #in Hz
        BACKGROUND_COLOR = [[0.0, 0.0,  0.0],  COLOR_RANGE]
        GAMMA = [1.0,  [1e-2,  10]]
        FRAME_WAIT_FACTOR = [0.9,  [0.0,  1.0]]
        FLIP_EXECUTION_TIME = [0*1e-3, [0.0, 1.0]]
        
        #Coordinate system selection
        COORDINATE_SYSTEM = ['undefined', ['ulcorner','center', 'undefined']] 
        ORIGO = utils.rc((numpy.inf, numpy.inf))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = ['undefined',  ['left', 'right', 'undefined']]
        VERTICAL_AXIS_POSITIVE_DIRECTION = ['undefined',  ['up', 'down', 'undefined']]
        
        #pixel scaling
        IMAGE_PROJECTED_ON_RETINA = True
        SCREEN_UM_TO_PIXEL_SCALE = [1.0,  [1e-3,  1e3]] #um / pixel
        
        #Network/UDP settings
        SERVER_UDP_IP = '172.27.29.6'
        SERVER_IP = 'localhost'
        WAIT_BETWEEN_UDP_SENDS = [0.05,  [0.0,  1.0]]
        CLIENT_UDP_IP = ''
        UDP_ENABLE = True
        UDP_PORT = [446,  [300,  65000]]
        UDP_BUFFER_SIZE = [65536,  [1,  100000000]]
        COMMAND_INTERFACE_PORT = [10000, [300,  65000]]
        
        #commands (including commands which are accepted only from udp interface)
#        COMMANDS_IDLE = {
#        'i':'show_status', 
#        's':'start_stimulation',    
#        'b':'bullseye', 
#        'q':'quit', 
#        't':'send_file', 
#        '<':'set_stimulus_file_start', 
#        '>':'set_stimulus_file_end', 
#        'g':'get_log', 
#        #'i':'set_measurement_id', 
#        'y':'start_test', 
#        'c':'set_background_color', 
#        'n':'next_segment'
#        }
        
        COMMAND_DOMAINS = ['keyboard', 'running experiment', 'network interface', 'remote client']
        COMMANDS = {
                    'hide_menu': {'key': 'h', 'domain': ['keyboard']}, 
                    #This command is dynamically added to the list. 'experiment_select' : {'key' : None, 'domain': ['keyboard']}, #I am not sure that this is good
                    'execute_experiment': {'key': 'e', 'domain': ['keyboard', 'network interface', 'remote client']}, 
                    'abort_experiment': {'key': 'a', 'domain': ['keyboard', 'network interface', 'remote client', 'running experiment']}, 
                    'bullseye': {'key': 'b', 'domain': ['keyboard', 'network interface', 'remote client']}, 
                    'quit': {'key': 'q', 'domain': ['keyboard', 'network interface', 'remote client']},                    
                    }
        
        #debug
        ENABLE_FRAME_CAPTURE = False
        
        #logging 
        MAX_LOG_COLORS = [3,  [0,  100000]]
        
#        #grating
#        MIN_PHASE_STEP = [0.001,  [1e-5,  1.0]]
#        GRATING_TEXTURE_RESOLUTION = [512,  [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048]]
        
        #user interface
        TEXT_ENABLE = True
        TEXT_COLOR = [[1.0,  0.0,  0.0] ,  [[0.0, 0.0, 0.0],  [1.0,  1.0,  1.0]]]
#        TEXT_SIZE = [12,  [2,  20]]
        
        STATES = [['idle',  'stimulation'],  None]        

        MENU_POSITION = utils.cr((-0.48, 0.45))
        MESSAGE_POSITION = utils.cr((-0.48,0.0))
        NUMBER_OF_MESSAGE_ROWS = [20, [1, 40]]
        MAX_MESSAGE_LENGTH = [200,  [10,  1000]] #length of message displayed on screen

        #example config
        SHOW_ALL_EXAMPLES = True
        
        #stimulus control
        SEGMENT_DURATION = [100,  [1,  100000]]
        ACTION_BETWEEN_STIMULUS = 'no' #keystroke, wait_xx in sec. no =  off
        
        #== External hardware ==        
        #parallel port
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = [0,  PIN_RANGE]
        FRAME_TRIGGER_PIN = [2,  PIN_RANGE]
        FRAME_TRIGGER_PULSE_WIDTH = [1e-3,  [1e-4,  1e-1]]
        
        #filterwheel settings
        FILTERWHEEL_ENABLE = True
        FILTERWHEEL_SERIAL_PORT = [[{
                                    'port' :  '/dev/ttyUSB0',
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }] ]
                                    
        FILTERWHEEL_SETTLING_TIME = [2.0,  [0,  20]]

        FILTERWHEEL_VALID_POSITIONS = [[1, 6],  [[0, 0],  [100, 100]]]
        
        FILTERWHEEL_FILTERS = [[{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]]
                                                
        ENABLE_SHUTTER = False
        
        #this function call is compulsory
        self._create_parameters_from_locals(locals())

    def _calculate_parameters(self):
        '''
        Function for modifying parameters with calculations and creating new parameters calculated from existing values
        '''
        #== Paths ==
        DEFAULT_IMAGE_FILE = os.path.join(self.PACKAGE_PATH ,'data','images','default.bmp')
        BULLSEYE_FILE = self.PACKAGE_PATH + os.sep + 'data' + os.sep + 'images'+ os.sep +'bullseye.bmp'
        
        #== Accepted keyboard commands and menu text==
        KEYS = []
        KEYBOARD_COMMANDS = {}
        MENU_TEXT = ''
        for k, v in self.COMMANDS.items():            
            if utils.is_in_list(v['domain'], 'keyboard'):
                KEYS.append(v['key'])
                KEYBOARD_COMMANDS[k] = v
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
        if isinstance(self.SCREEN_RESOLUTION, list):
            screen_resolution = 1.0 / numpy.array(self.SCREEN_RESOLUTION)
        elif isinstance(self.SCREEN_RESOLUTION, numpy.ndarray):
            screen_resolution = 1.0 / numpy.array([self.SCREEN_RESOLUTION['col'], self.SCREEN_RESOLUTION['row']])
        SCREEN_UM_TO_NORM_SCALE = 2.0 * self.SCREEN_PIXEL_TO_UM_SCALE_p.v * screen_resolution        
        self.SCREEN_UM_TO_NORM_SCALE_p = visexpman.engine.generic.parameter.Parameter(SCREEN_UM_TO_NORM_SCALE)
        
        #== Coordinate system ==
        if self.COORDINATE_SYSTEM != 'undefined':
            self.ORIGO, self.HORIZONTAL_AXIS_POSITIVE_DIRECTION, self.VERTICAL_AXIS_POSITIVE_DIRECTION= utils.coordinate_system(self.COORDINATE_SYSTEM, self.SCREEN_RESOLUTION)
        else:
            raise ValueError('No coordinate system selected in config,  nor explicit settings for origo and axes was given.')
            
        #== Cooridnate system type dependencies ==
        if self.COORDINATE_SYSTEM == 'ulcorner':
            self.MENU_POSITION_p.v = utils.centered_to_ulcorner_coordinate_system(self.MENU_POSITION_p.v, utils.cr((1.0, 1.0)))
            self.MESSAGE_POSITION_p.v = utils.centered_to_ulcorner_coordinate_system(self.MESSAGE_POSITION_p.v, utils.cr((1.0, 1.0)))
            
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
    
class testApplicationConfiguration(unittest.TestCase):
    def test_ConfigClass(self):
        t = TestConfig()
        self.assertEqual((t.PAR1,  t.PAR2,  t.PAR3),  ('par1', 'par2',  t.PAR1+t.PAR2))
        
class SafestartConfig(VisualStimulationConfig):    
    def _set_user_parameters(self):
        COORDINATE_SYSTEM = 'center'        
        FILTERWHEEL_ENABLE = False
        RUN_MODE = 'user interface'
        ENABLE_PARALLEL_PORT = False
        UDP_ENABLE = False
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([600, 800])        
        self._set_parameters_from_locals(locals())        

if __name__ == "__main__":
    unittest.main()
    
