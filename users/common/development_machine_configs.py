import os
import os.path
import numpy
from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment.configuration import VisionExperimentConfig

class StimulusDevelopment(VisionExperimentConfig):
    '''
    '''
    def _set_user_parameters(self):
        PLATFORM = 'standalone'
        if os.name == 'nt':
            root_folder = 'c:\\data'
        elif os.path.exists('/mnt/datafast/debug'):
            root_folder = '/mnt/datafast/debug'
        LOG_PATH = os.path.join(root_folder, 'log')
        CAPTURE_PATH = os.path.join(root_folder, 'capture')
        for p in [CAPTURE_PATH, LOG_PATH]:
            if not os.path.exists(p):
                os.mkdir(p)
        DATA_PATH = root_folder
        EXPERIMENT_DATA_PATH = root_folder
        EXPERIMENT_LOG_PATH = LOG_PATH
        
        #=== screen ===
        FULLSCREEN = False
        SCREEN_RESOLUTION = utils.cr([800,600])
        COORDINATE_SYSTEM='center'
        ENABLE_FRAME_CAPTURE = False
        SCREEN_EXPECTED_FRAME_RATE = 60.0
        SCREEN_MAX_FRAME_RATE = 60.0
        SCREEN_UM_TO_PIXEL_SCALE = 1.0
        STIM_RECORDS_ANALOG_SIGNALS = False
        EXPERIMENT_FILE_FORMAT = 'hdf5'
        
        #=== hardware ===
        ENABLE_PARALLEL_PORT = False
        self._create_parameters_from_locals(locals())