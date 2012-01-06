import visexpman.users.zoltan.test.unit_test_runner as unit_test_runner
from visexpman.engine.generic.parameter import Parameter
from visexpman.engine.visual_stimulation.configuration import VisionExperimentConfig
import visexpman.engine.visual_stimulation.experiment as experiment
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.generic.utils as utils
import os
import serial
import numpy
import time

class PPRLConfig(VisionExperimentConfig):
    
    def _set_user_parameters(self):
        RUN_MODE = 'single experiment'
#        RUN_MODE = 'user interface'
        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'gratings_stimulus.py'
        EXPERIMENT = self.STIMULATION_FOLDER_PATH + os.sep + 'increasing_spot_stimulus.py'
        EXPERIMENT = 'MultipleDotTest'
        EXPERIMENT_CONFIG = 'DotsExperimentConfig'
        PRE_EXPERIMENT = 'Pre'
        ENABLE_PRE_EXPERIMENT = True
#        EXPERIMENT = 'ShapeTest'
#        SINGLE_EXPERIMENT = 'GratingMaskTest'
#        SINGLE_EXPERIMENT = 'DrumStimTest'
        LOG_PATH = '/var/log/'
        EXPERIMENT_DATA_PATH = '../../../presentinator/data'
        CAPTURE_PATH = '../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = True
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([600,   800])
#        SCREEN_RESOLUTION = [1680,   1050]
        ENABLE_FRAME_CAPTURE = False
        
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        FRAME_WAIT_FACTOR = 0

        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #multiple stimulus control
        STIMULUS_LIST = ['MyStimulus1',  'MyStimulus2']
        self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST )
        
        SEGMENT_DURATION = 2
        ACTION_BETWEEN_STIMULUS = 'off'

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        
        ORIGO, HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION = utils.coordinate_system('corner')
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        
        self._set_parameters_from_locals(locals())
        
class K247AWindowsConfig(VisionExperimentConfig):
    def _set_user_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = 'c:\\temp\\'
        BASE_PATH='c:\\Data\\stimuli\\'
        EXPERIMENT_DATA_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')#'../../../presentinator/data/capture'
        ENABLE_PARALLEL_PORT = False
        ENABLE_UDP = False
#        STIMULATION_FOLDER_PATH = 'stimulus_examples'        
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.rc([768,   1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [36.0, [0, 100]] #cm
        SCREEN_PIXEL_WIDTH = [0.0425, [0, 0.5]] # mm
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        MAXIMUM_RECORDING_DURATION = [270, [0, 10000]] #seconds

        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        VisionExperimentConfig._create_parameters_from_locals(self, locals())
        #VisionExperimentConfig._set_parameters_from_locals(self, locals())

class RC3DWindowsConfig(VisionExperimentConfig):
    #NOT TESTED
    def _set_user_parameters(self):        
        ENABLE_PARALLEL_PORT = True        
        FULLSCREEN = True
        SCREEN_RESOLUTION = [1600,  1200]
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2        
        EXPERIMENT_DATA_PATH = self.BASE_PATH
        LOG_PATH = self.BASE_PATH
        #test steps:
        # 1. frame rate 60
        # 2. parallel port OK
        # 3 network control
        # 4 stimulus types
        
        self._set_parameters_from_locals(locals())

class MBP(VisionExperimentConfig):
    def _set_user_parameters(self):        
        RUN_MODE = 'single experiment'
        EXPERIMENT_CONFIG = 'MovingDotTestConfig'
        LOG_PATH = '/Users/hd/Documents/DataBase'
        EXPERIMENT_LOG_PATH = LOG_PATH
        BASE_PATH='/Users/hd/Documents/DataBase'
        ARCHIVE_PATH = os.path.join(BASE_PATH,'archive')
        EXPERIMENT_RESULT_PATH = ARCHIVE_PATH
        CAPTURE_PATH = os.path.join(BASE_PATH,'capture')
        FULLSCREEN = False
        EXPERIMENT_DATA_PATH = os.path.join(BASE_PATH,'archive')#'../../../presentinator/data' 
        ENABLE_PARALLEL_PORT = False
        ENABLE_UDP = False
        SCREEN_RESOLUTION = utils.rc([768,   1024])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen
        
        FRAME_WAIT_FACTOR = 0 
        GAMMA = 1.0
        ENABLE_FILTERWHEEL = False
        
        #self.STIMULUS_LIST_p = Parameter(STIMULUS_LIST ) # ez hogy kerulhet ide?  mar ertem de ez nagy kavaras!
        # nem ilyen formaban kellett volna?:STATES = [['idle',  'stimulation'],  None]
        
        SEGMENT_DURATION = 2
        
        MAXIMUM_RECORDING_DURATION = [90, [0, 10000]] #seconds
        ARCHIVE_FORMAT = 'hdf5'
        COORDINATE_SYSTEM='ulcorner'
            
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        VisionExperimentConfig._create_parameters_from_locals(self, locals())
        #VisionExperimentConfig._set_parameters_from_locals(self, locals())
        
class WinDev(VisionExperimentConfig):
    '''
    Windows development machine
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingDotConfig'
        
        #=== paths/data handling ===
        if os.name == 'nt':            
            v_drive_data_folder = 'V:\\data'
        else:            
            v_drive_data_folder = '/home/zoltan/visexp/data'
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        MES_DATA_FOLDER = 'V:\\data'
        ARCHIVE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen
        MAXIMUM_RECORDING_DURATION = [100, [0, 10000]] #100
        
        #=== Network ===
        ENABLE_UDP = False
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '172.27.25.220'
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3        
        
        #=== Others ===
        
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}
        
        
        self._create_parameters_from_locals(locals())
        
class VS3DUS(VisionExperimentConfig):
    '''
    Visual stimulation machine of 3D microscope setup
    '''
    def _set_user_parameters(self):        
        EXPERIMENT_CONFIG = 'MovingDotConfig'
        
        #=== paths/data handling ===
        if os.name == 'nt':
            m_drive_data_folder = 'M:\\Zoltan\\visexpman\\data'
            g_drive_data_folder = 'G:\\User\\Zoltan\\visexpdata'
            v_drive_data_folder = 'V:\\data'
        else:
            m_drive_data_folder = '/media/Common/visexpman_data/test'
            g_drive_data_folder = '/media/Common/visexpman_data/test'
            v_drive_data_folder = '/home/zoltan/visexp/data'
        LOG_PATH = os.path.join(v_drive_data_folder, 'log')
        EXPERIMENT_LOG_PATH = LOG_PATH        
        EXPERIMENT_DATA_PATH = v_drive_data_folder
        MES_DATA_FOLDER = 'V:\\data'
        ARCHIVE_FORMAT = 'hdf5'
        
        #=== screen ===
        FULLSCREEN = True
        SCREEN_RESOLUTION = utils.cr([800, 600])
        COORDINATE_SYSTEM='ulcorner'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0        
        
        #=== experiment specific ===
        IMAGE_PROJECTED_ON_RETINA = False
        SCREEN_DISTANCE_FROM_MOUSE_EYE = [280.0, [0, 300]] #mm
        SCREEN_PIXEL_WIDTH = [0.56, [0, 0.99]] # mm, must be measured by hand (depends on how far the projector is from the screen)
        degrees = 10.0*1/300 # 300 um on the retina corresponds to 10 visual degrees.  
        SCREEN_UM_TO_PIXEL_SCALE = numpy.tan(numpy.pi/180*degrees)*SCREEN_DISTANCE_FROM_MOUSE_EYE[0]/SCREEN_PIXEL_WIDTH[0] #1 um on the retina is this many pixels on the screen
        MAXIMUM_RECORDING_DURATION = [100, [0, 10000]] #100
        
        #=== Network ===
        ENABLE_UDP = False
        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '172.27.26.1'#'172.27.25.220'
#        self.COMMAND_RELAY_SERVER['RELAY_SERVER_IP'] = '172.27.25.220'
        #=== hardware ===
        ENABLE_PARALLEL_PORT = True
        ACQUISITION_TRIGGER_PIN = 2
        FRAME_TRIGGER_PIN = 0
        FRAME_TRIGGER_PULSE_WIDTH = 1e-3
        
        #=== stage ===
        motor_serial_port = {
                                    'port' :  'COM1',
                                    'baudrate' : 19200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }
                                    
        STAGE = [{'serial_port' : motor_serial_port,
                 'enable': True,
                 'speed': 400,
                 'acceleration' : 200,
                 'move_timeout' : 45.0,
                 'um_per_ustep' : (1.0/51.0)*numpy.ones(3, dtype = numpy.float)
                 }]
                 
        #=== Filterwheel ===
        
        ENABLE_FILTERWHEEL = False
        
        FILTERWHEEL_SERIAL_PORT = [{
                                    'port' :  unit_test_runner.TEST_com_port,
                                    'baudrate' : 115200,
                                    'parity' : serial.PARITY_NONE,
                                    'stopbits' : serial.STOPBITS_ONE,
                                    'bytesize' : serial.EIGHTBITS,                                    
                                    }]
                                    
        FILTERWHEEL_FILTERS = [{
                                                'ND0': 1, 
                                                'ND10': 2, 
                                                'ND20': 3, 
                                                'ND30': 4, 
                                                'ND40': 5, 
                                                'ND50': 6, 
                                                }]
                                                
        #=== DAQ ===
        DAQ_CONFIG = [
                    {
                    'ANALOG_CONFIG' : 'ai', #'ai', 'ao', 'aio', 'undefined'
                    'DAQ_TIMEOUT' : 3.0,
                    'SAMPLE_RATE' : 5000,
                    'AI_CHANNEL' : 'Dev1/ai0:1',
                    'MAX_VOLTAGE' : 5.0,
                    'MIN_VOLTAGE' : -5.0,
                    'DURATION_OF_AI_READ' : 2*MAXIMUM_RECORDING_DURATION[0],
                    'ENABLE' : not False
                    }
                    ]
        
        #=== Others ===
        
        USER_EXPERIMENT_COMMANDS = {'stop': {'key': 's', 'domain': ['running experiment']}, 
                                    'next': {'key': 'n', 'domain': ['running experiment']},}
        
        
        self._create_parameters_from_locals(locals())
        
class GratingConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'GratingExperiment'
        self._create_parameters_from_locals(locals())

class GratingExperiment(experiment.Experiment):
    def run(self):
        orientation = [0,45,90]
        ai = daq_instrument.AnalogIO(self.machine_config, self.caller)
        ai.start_daq_activity() 
        for i in range(len(orientation)):
            self.mes_command.put('SOCacquire_line_scanEOCc:\\temp\\test\\line_scan_data{0}.matEOP'.format(i))
            self.show_grating(duration =9.0, profile = 'sqr', orientation = orientation[i], velocity = 500.0, white_bar_width = 100)
            
        ai.finish_daq_activity()
        ai.release_instrument()
            
        #Save 
        if not hasattr(ai, 'ai_data'):
            ai.ai_data = numpy.zeros(2)
        path = utils.generate_filename(os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, 'ai_data.txt'))
        numpy.savetxt(path, ai.ai_data)            
        data_to_hdf5 = {'sync_data' : ai.ai_data}
#         setattr(self.hdf5, mes_fragment_name, data_to_hdf5)
#         self.hdf5.save(mes_fragment_name)

class PixelSizeCalibrationConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'PixelSizeCalibration'
        self._create_parameters_from_locals(locals())

class PixelSizeCalibration(experiment.Experiment):
    '''
    Helps pixel size calibration by showing 50 and 20 um circles
    '''
    def run(self):
        pattern = 0
        self.add_text('Circle at 100,100 um, diameter is 20 um.', color = (1.0,  0.0,  0.0), position = utils.cr((10.0, 30.0)))        
        while True:
            if pattern == 0:
                self.change_text(0, text = 'Circle at 100,100 um, diameter is 20 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 20.0, pos = utils.cr((100, 100)))
            elif pattern == 1:
                self.change_text(0, text = 'Circle at 50,50 um, diameter is 50 um.\n\nPress \'n\' to switch, \'s\' to stop.')
                self.show_shape(shape = 'circle', size = 50.0, pos = utils.cr((50, 50)))
            else:
                pass
            if 'stop' in self.command_buffer:
                break
            elif 'next' in self.command_buffer:
                pattern += 1
                if pattern == 2:
                    pattern = 0
                self.command_buffer = ''
                    
if __name__ == "__main__":
    
    c = UbuntuDeveloperConfig()
    c.print_parameters() 
    
