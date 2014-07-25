from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
import time
import numpy
import os.path
import os
import shutil
import random
            
class SpotCenteredParameters(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SPOT_SIZE = 800  # [100,  200,  300,  400,  500,  1000]  fullfield 2500
        self.ON_TIME = 2 #s
        self.BACKGROUND_TIME = 1
        self.SPOT_CONTRAST_ON = [0.99] #N [0.625, 0.75, 0.87, 0.999] 
        self.REPETITIONS_ALL = 1
        self.BACKGROUND_COLOR = 0.5
        self.DRUG_CONC = 0.0  
        self.BLACK = 0.01
        self.WHITE = 0.999
        
        self.runnable = 'SpotCenteredExperiment'        
        self._create_parameters_from_locals(locals())

class SpotCenteredExperiment(experiment.Experiment):
    def run(self):
        from visexpman.users.antonia.electrode_id_reader import read_electrode_coordinates
        center,size = read_electrode_coordinates()
        for repetitions in range(self.experiment_config.REPETITIONS_ALL):
            self.show_fullscreen(duration = self.experiment_config.BACKGROUND_TIME, color =  self.experiment_config.BACKGROUND_COLOR)
            for spot_contrast_on in self.experiment_config.SPOT_CONTRAST_ON:
                self.show_shape(shape = 'o',  duration = self.experiment_config.ON_TIME, pos = center, color = spot_contrast_on,
                                        background_color = self.experiment_config.BACKGROUND_COLOR,  size = self.experiment_config.SPOT_SIZE)
                if self.abort:
                    break
                 
            if self.abort:
                break
            
  
                     