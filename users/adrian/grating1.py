from visexpman.engine.vision_experiment import experiment
from visexpman.users.common.grating import MovingGratingNoMarchingConfig
from visexpman.engine.generic import utils
import numpy
import time
import random
import copy
        
class MovingGratingAdrian(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5#after
        self.MARCH_TIME = 3.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 3
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.ENABLE_RANDOM_ORDER = False #True
        if self.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.ORIENTATIONS)


class MovingGratingShort(MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        MovingGratingNoMarchingConfig._create_parameters(self)
        self.GRATING_STAND_TIME = 0.5#after
        self.MARCH_TIME = 3.0#before
        self.PAUSE_BEFORE_AFTER = 1.0
        self.REPEATS = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.ENABLE_RANDOM_ORDER = False #True