"""
Created on Mon Aug 31 10:35:00 2015
@author: rolandd
"""

from visexpman.engine.vision_experiment import experiment

from collections import OrderedDict
from stimuli import *

class SFN01BatchConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        
        self.VARS = OrderedDict()
        self.STIM_TYPE_CLASS = {}
    
        self.STIM_TYPE_CLASS['FullFieldFlashes'] = 'FullFieldFlashesStimulus'
        self.VARS['FullFieldFlashes'] = {}   
        self.VARS['FullFieldFlashes']['BACKGROUND'] = 0.5
        self.VARS['FullFieldFlashes']['COLORS'] = [0.0, 1.0]
        self.VARS['FullFieldFlashes']['ON_TIME'] = 2.0
        self.VARS['FullFieldFlashes']['OFF_TIME'] = 2.0
        self.VARS['FullFieldFlashes']['REPETITIONS'] = 10
        
        # ~30 minutes        
        self.STIM_TYPE_CLASS['FingerPrinting'] = 'FingerPrintingStimulus'
        self.VARS['FingerPrinting'] = {}
        self.VARS['FingerPrinting']['DIRECTIONS'] = [0, 90]  #range(0,360,90)
        self.VARS['FingerPrinting']['SPEEDS'] = [300] #[300, 1600]      
        self.VARS['FingerPrinting']['DURATION'] = 15.0
        self.VARS['FingerPrinting']['INTENSITY_LEVELS'] = 255
        self.VARS['FingerPrinting']['REPEATS'] = 20
        self.VARS['FingerPrinting']['MIN_SPATIAL_PERIOD'] = [10.0, 50.0]
        
        # 30 minutes
        self.STIM_TYPE_CLASS['WhiteNoise'] = 'WhiteNoiseStimulus'
        self.VARS['WhiteNoise'] = {}
        self.VARS['WhiteNoise']['DURATION_MINS'] = 30.0 # min
        self.VARS['WhiteNoise']['PIXEL_SIZE'] = [50.0] # um
        self.VARS['WhiteNoise']['N_WHITE_PIXELS'] = False
        self.VARS['WhiteNoise']['COLORS'] = [0.0, 1.0]
        
        # ~20 minutes
        self.STIM_TYPE_CLASS['Gratings'] = 'MovingGratingStimulus'
        self.VARS['Gratings'] = {}   
        self.VARS['Gratings']['REPEATS'] = 10
        self.VARS['Gratings']['N_BAR_ADVANCES_OVER_POINT'] = 10
        self.VARS['Gratings']['MARCH_TIME'] = 0.0
        self.VARS['Gratings']['GREY_INSTEAD_OF_MARCHING'] = False
        self.VARS['Gratings']['NUMBER_OF_MARCHING_PHASES'] = 1.0
        self.VARS['Gratings']['GRATING_STAND_TIME'] = 1.0
        self.VARS['Gratings']['ORIENTATIONS'] = range(0,360,45)
        self.VARS['Gratings']['WHITE_BAR_WIDTHS'] = [100]
        self.VARS['Gratings']['VELOCITIES'] = [300, 1600]
        self.VARS['Gratings']['DUTY_CYCLES'] = [1]
        self.VARS['Gratings']['PAUSE_BEFORE_AFTER'] = 1.0
        
        # ~15 minutes
        self.STIM_TYPE_CLASS['MovingBars'] = 'MovingShapeStimulus'
        self.VARS['MovingBars'] = {}   
        self.VARS['MovingBars']['SHAPE_SIZE'] = utils.cr((1000, 500)) #um
        self.VARS['MovingBars']['SPEEDS'] = [300, 1600]
        self.VARS['MovingBars']['PAUSE_BETWEEN_DIRECTIONS'] = 1.0
        self.VARS['MovingBars']['REPETITIONS'] = 10
        self.VARS['MovingBars']['DIRECTIONS'] = range(0,360,45)
        self.VARS['MovingBars']['SHAPE_BACKGROUND'] = 0.0
        
        # ~15 minutes
        self.STIM_TYPE_CLASS['DashStimulus'] = 'DashStimulus'
        self.VARS['DashStimulus'] = {}
        self.VARS['DashStimulus']['BARSIZE'] = [40, 100]
        self.VARS['DashStimulus']['GAPSIZE'] = [10, 60]
        self.VARS['DashStimulus']['MOVINGLINES'] = 3
        self.VARS['DashStimulus']['DURATION'] = 5.0 #s
        self.VARS['DashStimulus']['SPEEDS'] = [300, 1600]
        self.VARS['DashStimulus']['DIRECTIONS'] = range(0,360,45)
        self.VARS['DashStimulus']['BAR_COLOR'] = 1.0
        self.VARS['DashStimulus']['REPETITIONS'] = 10
        
        self.runnable = 'BatchStimulus'
        self._create_parameters_from_locals(locals())

class SFN01FullField(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FullFieldFlashes'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01FingerPrinting(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'FingerPrinting'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
        
class SFN01WhiteNoise(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'WhiteNoise'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01Gratings(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'Gratings'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())
        
class SFN01MovingBars(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)
        self.sub_stimulus = 'MovingBars'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())

class SFN01DashStimulus(SFN01BatchConfig):
    def _create_parameters(self):
        SFN01BatchConfig._create_parameters(self)   
        self.sub_stimulus = 'DashStimulus'
        SFN01BatchConfig.extract_experiment_type(self, self)
        self._create_parameters_from_locals(locals())