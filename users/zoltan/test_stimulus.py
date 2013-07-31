import time
import numpy
import serial
import os.path
import os

import visexpman
from visexpman.engine import visexp_runner
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.users.zoltan.test import unit_test_runner

class WDC(VisionExperimentConfig):
    '''
    Visexp runner windows test config
    '''
    def _set_user_parameters(self):

        #paths
        EXPERIMENT_CONFIG = 'DebugExperimentConfig'
        LOG_PATH = unit_test_runner.TEST_working_folder      
        EXPERIMENT_LOG_PATH = unit_test_runner.TEST_working_folder
        EXPERIMENT_DATA_PATH = unit_test_runner.TEST_working_folder        
        ARCHIVE_FORMAT = 'zip'
        
        #hardware
        ENABLE_PARALLEL_PORT = True        
        ACQUISITION_TRIGGER_PIN = 0
        FRAME_TRIGGER_PIN = 2
        
        #screen
        FULLSCREEN = False        
        SCREEN_RESOLUTION = utils.cr([800, 600])
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0             
        COORDINATE_SYSTEM='center'        
        
        self._create_parameters_from_locals(locals())
        
class WhiteNoiseParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.DURATION = 1.0
        self.PIXEL_SIZE = 50.0
        self.FLICKERING_FREQUENCY = 30.0
        self.N_WHITE_PIXELS = None
        self.COLORS = [0.0, 1.0]
        self.runnable = 'WhiteNoiseExperiment'
        self._create_parameters_from_locals(locals())

class WhiteNoiseExperiment(experiment.Experiment):
    def run(self):
        self.white_noise(duration = self.experiment_config.DURATION,
            pixel_size = self.experiment_config.PIXEL_SIZE, 
            flickering_frequency = self.experiment_config.FLICKERING_FREQUENCY, 
            colors = self.experiment_config.COLORS,
            n_on_pixels = self.experiment_config.N_WHITE_PIXELS)
        self.show_fullscreen()

        
class DebugExperimentConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.runnable = 'Debug'
        self.DURATION = 10.0
#        self.pre_runnable = 'TestPre'
        self._create_parameters_from_locals(locals())          
        
class Debug(experiment.Experiment):
    def prepare(self):
        self.fragment_durations = [self.experiment_config.DURATION]
    
    def run(self):
#        oris = [0,45,90]
#        for ori in oris:
#            self.abort=False
#            while True:
#                self.show_grating(duration=10, white_bar_width=300, orientation=ori,display_area = utils.cr((800, 100)),velocity=80,duty_cycle=2.5)
#                break
#                if self.abort:
#                    break
#        return
        self.show_shape(duration=self.experiment_config.DURATION,size=100)
        return
        ncheckers = utils.rc((3, 3))
        colors = numpy.zeros((1, ncheckers['row'], ncheckers['col'], 3))
        colors[0,0,0,:]=numpy.array([1.0, 1.0, 0.0])
        colors[0,1,1,:]=numpy.array([0.0, 1.0, 0.0])
        colors[0,2,2,:]=numpy.array([1.0, 0.0, 0.0])
        self.show_checkerboard(ncheckers, duration = 0.5, color = colors, box_size = utils.rc((10, 10)))
        return
        self.increasing_spot([100,200], 1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, 1.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, color = 1.0, background_color = 0.0, pos = utils.rc((0,  0)))
        t0 = self.machine_config.SCREEN_EXPECTED_FRAME_RATE
        self.flash_stimulus('ff', [1/t0, 2/t0]*3, 1.0)
        self.flash_stimulus('ff', [1/t0, 2/t0], colors = numpy.array([[0.4, 0.6, 1.0]]).T)
        self.flash_stimulus('o', [1.0/t0, 2.0/t0, 1.0/t0, 2.0/t0, 1.0/t0], numpy.array([[0.5, 1.0]]).T, sizes = utils.rc((100, 100)))
        self.flash_stimulus('o', [1.0/t0, 2.0/t0, 1.0/t0, 2.0/t0, 1.0/t0], numpy.array([[0.5, 1.0]]).T, sizes = utils.rc(numpy.array([[100, 100], [200, 200]])))
        self.flash_stimulus('o', [1.0/t0, 2.0/t0, 1.0/t0, 2.0/t0, 1.0/t0], numpy.array([[0.5, 1.0]]).T, sizes = numpy.array([[100, 200]]).T)
        return
        self.show_shape(shape='r', color = numpy.array([[1.0, 0.5]]).T, duration = 2.0/self.machine_config.SCREEN_EXPECTED_FRAME_RATE, size = utils.cr((100.0, 100.0)),pos = utils.cr(numpy.array([[0,100], [0, 100]])))
        self.show_grating(duration = 2.0,  
            white_bar_width = 100,  
            orientation = 90,  
            velocity = numpy.array([400,0]), 
            duty_cycle = 8.0)
        return
        self.show_grating(duration = 5.0,  
            white_bar_width = 100,  
            display_area = utils.rc((100,200)),
            orientation = 45,  
            pos = utils.rc((100,100)),
            velocity = 100,  
            duty_cycle = 1.0)
        self.show_grating(duration = 5.0,  
            white_bar_width = 100,  
            orientation = 90,  
            velocity = 100,  
            duty_cycle = 1.0)
            
if __name__ == "__main__":
    if not True:
        v = visexp_runner.VisionExperimentRunner(['zoltan', 'daniel'], 'SwDebugConfig')
        v.run_experiment(user_experiment_config = 'MovingGratingConfigFindOrientation')
    elif True:
        v = visexp_runner.VisionExperimentRunner(['zoltan', 'chi'], 'SwDebugConfig')
        v.run_experiment(user_experiment_config = 'FullfieldSinewave')
    elif not True:
        v = visexp_runner.VisionExperimentRunner('antonia',  'MEASetup')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
    elif True:
        v = visexp_runner.VisionExperimentRunner(['zoltan', 'chi'], 'SwDebugConfig')
        if True:
            v.run_loop()
        else:
            v.run_experiment(user_experiment_config = 'IncreasingAnnulusParameters')
    else:
        v = visexp_runner.VisionExperimentRunner('zoltan',  'SwDebugConfig')
        v.run_experiment(user_experiment_config = 'WhiteNoiseParameters')
