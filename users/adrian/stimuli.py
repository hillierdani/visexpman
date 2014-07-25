import random
import time
import numpy
import os.path
import os

from visexpman.engine.generic import utils
from visexpman.engine.vision_experiment import experiment
from visexpman.users.daniel import grating

class ReceptiveFieldExploreConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.SHAPE = 'rect'
        self.COLORS = [1.0]
        self.BACKGROUND_COLOR = 0
        self.SHAPE_SIZE = 400.0
        self.MESH_XY = utils.rc((4,6))
        self.ON_TIME = 0.5*2
        self.OFF_TIME = 0.5*2
        self.PAUSE_BEFORE_AFTER = 2.0
        self.REPEATS = 3
        self.ENABLE_ZOOM = False
        self.SELECTED_POSITION = 1
        self.ZOOM_MESH_XY = utils.rc((3,3))
        self.ENABLE_RANDOM_ORDER = True
        self.runnable='ReceptiveFieldExplore'
        self.pre_runnable='BlackPre'
        self._create_parameters_from_locals(locals())
        
class ReceptiveFieldExplore(experiment.Experiment):
    def calculate_positions(self, display_range, center, repeats, mesh_xy, colors=None):
        positions = []
        step = {}
        for axis in ['row', 'col']:
            step[axis] = display_range[axis]/mesh_xy[axis]
        for repeat in range(repeats):
            for row in range(mesh_xy['row']):
                for col in range(mesh_xy['col']):
                    position = utils.rc(((row+0.5) * step['row']+center['row'], (col+0.5)* step['col']+center['col']))
                    if colors is None:
                        positions.append(position)
                    else:
                        for color in colors:
                            positions.append([position, color])
        return positions, utils.rc((step['row'],step['col']))
    
    def prepare(self):
        if self.experiment_config.ENABLE_ZOOM:
            #Calculate the mesh positions for the whole screen
            positions, display_range = self.calculate_positions(self.machine_config.SCREEN_SIZE_UM, utils.rc((0,0)), 1, self.experiment_config.MESH_XY)
            zoom_center = utils.rc_add(positions[self.experiment_config.SELECTED_POSITION], utils.rc_multiply_with_constant(display_range, 0.5), '-')
            self.positions, display_range = self.calculate_positions(display_range, zoom_center, self.experiment_config.REPEATS, self.experiment_config.ZOOM_MESH_XY, self.experiment_config.COLORS)
            self.shape_size = display_range
        else:
            self.positions, display_range = self.calculate_positions(self.machine_config.SCREEN_SIZE_UM, utils.rc((0,0)), self.experiment_config.REPEATS, self.experiment_config.MESH_XY, self.experiment_config.COLORS)
            self.shape_size = self.experiment_config.SHAPE_SIZE
        if self.experiment_config.ENABLE_RANDOM_ORDER:
            import random
            random.shuffle(self.positions)
        self.fragment_durations = len(self.positions)* (self.experiment_config.ON_TIME + self.experiment_config.OFF_TIME) + 2*self.experiment_config.PAUSE_BEFORE_AFTER
        self.fragment_durations = [self.fragment_durations]
            
    def run(self):
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        for position_color in self.positions:
            if self.abort:
                break
            self.show_shape(shape = self.experiment_config.SHAPE,
                                    size = self.shape_size,
                                    color = position_color[1],
                                    background_color = self.experiment_config.BACKGROUND_COLOR,
                                    duration = self.experiment_config.ON_TIME,
                                    pos = position_color[0])
                                    
            self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.OFF_TIME)
        self.show_fullscreen(color = self.experiment_config.BACKGROUND_COLOR, duration = self.experiment_config.PAUSE_BEFORE_AFTER-self.experiment_config.OFF_TIME)

class MyGrating(grating.MovingGratingNoMarchingConfig):
    def _create_parameters(self):
        grating.MovingGratingNoMarchingConfig._create_parameters(self)
        self.REPEATS = 1
        self.NUMBER_OF_BAR_ADVANCE_OVER_POINT = 3
        self.MARCH_TIME = 1.0#Before
        self.GRATING_STAND_TIME = 0.0#Afterwards
        #Grating parameters
        self.ORIENTATIONS = range(0, 360, 45)
        random.shuffle(self.ORIENTATIONS)
        self.WHITE_BAR_WIDTHS = [300.0]
        self.VELOCITIES = [1200.0]
        self.PAUSE_BEFORE_AFTER = 0.0
        self.pre_runnable='BlackPre'
        self._create_parameters_from_locals(locals())