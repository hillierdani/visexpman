'''calculates positions of n dots moving in 8 directions through the screen'''
import visexpman
import os.path
from PIL import Image
import numpy
from visexpman.engine.vision_experiment import experiment
from visexpman.engine.generic import utils
#from visexpman.engine.visual_stimulation import stimulation_library as stl
#import visexpman.engine.generic.configuration
import visexpman.engine.vision_experiment.command_handler as command_handler
import visexpman.engine.hardware_interface.daq_instrument as daq_instrument
import visexpman.engine.hardware_interface.mes_interface as mes_interface
import time
import visexpA.engine.datahandlers.hdf5io as hdf5io
import pickle
import copy
import visexpA.engine.datahandlers.matlabfile as matlab_mat
import shutil
import os

class MovingDotConfig(experiment.ExperimentConfig):
    def _create_application_parameters(self):
        #place for experiment parameters
        #parameter with range: list[0] - value, list[0] - range
        #path parameter: parameter name contains '_PATH'
        #string list: list[0] - empty        
        self.DIAMETER_UM = [300]
        self.OFFSCREEN_PATH_LENGTH_UM = [300] # how long the dot is moving outside the screen, for circular dot this should equal to diameter, if no pause between directions is needed
        self.ANGLES = [0,  90,  180,  270, 45,  135,  225,  315] # degrees        
        self.SPEED = [1200] #[40deg/s] % deg/s should not be larger than screen size
        self.AMPLITUDE = 0.5
        self.REPEATS = 2
        self.PDURATION = 0
        self.GRIDSTEP = 1.0/1.5 # how much to step the dot's position between each sweep (GRIDSTEP*diameter)
        self.NDOTS = 1
        self.RANDOMIZE = 1
        self.PAUSE_BEFORE_AFTER = 5.0
        self.PRECOND='line from previous direction' #setting this to 'line from previous direction' will insert a line before sweeping the screen with lines from the current direction
        self.runnable = 'MovingDot'
        self.pre_runnable = 'MovingDotPre'
        self.USER_ADJUSTABLE_PARAMETERS = ['DIAMETER_UM', 'SPEED', 'NDOTS', 'RANDOMIZE']        
        self._create_parameters_from_locals(locals())
        
class MovingDot300umConfig(MovingDotConfig):
    def _create_application_parameters(self):
        MovingDotConfig._create_application_parameters(self)
        self.DIAMETER_UM = [200]
        self.OFFSCREEN_PATH_LENGTH_UM = [150] # how long the dot is moving outside the screen, for circular dot this should equal to diameter, if no pause between directions is needed
        self.ANGLES = [0,  90,  180,  270, 45,  135,  225,  315] # degrees        
        self.SPEED = [600] #[40deg/s] % deg/s should not be larger than screen size
        self.AMPLITUDE = 0.5
        self.REPEATS = 2
        self.PDURATION = 0
        self.GRIDSTEP = 1.0 # 

        
        
class MovingDot500umConfig(MovingDotConfig):
    def _create_application_parameters(self):
        MovingDotConfig._create_application_parameters(self)
        self.DIAMETER_UM = [500]
        self.OFFSCREEN_PATH_LENGTH_UM = [150] # how long the dot is moving outside the screen, for circular dot this should equal to diameter, if no pause between directions is needed
        self.ANGLES = [0,  90,  180,  270, 45,  135,  225,  315] # degrees        
        self.SPEED = [1200] #[40deg/s] % deg/s should not be larger than screen size
        self.AMPLITUDE = 0.5
        self.REPEATS = 2
        self.PDURATION = 0
        self.GRIDSTEP = 1.0 # 

class MovingRectangleConfig(MovingDot300umConfig):
    def _create_application_parameters(self):
        MovingDot300umConfig._create_application_parameters(self)
        self.WIDTH_UM = self.DIAMETER_UM
        self.HEIGHT_UM = [1000]
        self.OFFSCREEN_PATH_LENGTH_UM = [500] # how long the dot is moving outside the screen, for circular dot this should equal to diameter, if no pause between directions is needed
        self.runnable = 'MovingRectangle'
        self.pre_runnable = 'MovingRectanglePre'

class ShortMovingDotConfig(MovingDotConfig):
    def _create_application_parameters(self):
        MovingDotConfig._create_application_parameters(self)
        self.DIAMETER_UM = [300]        
        self.ANGLES = [0,45,90,135,180,225,270,315] # degrees
        self.RANDOMIZE=False
        self.SPEED = [4000] #[40deg/s] % deg/s should not be larger than screen size
        self.REPEATS = 1
        self.PAUSE_BEFORE_AFTER = 0.0
        self._create_parameters_from_locals(locals())

class MovingRectangle500umConfig(MovingDot500umConfig):
    def _create_application_parameters(self):
        MovingDotConfig._create_application_parameters(self)
        self.WIDTH_UM = self.DIAMETER_UM
        self.HEIGHT_UM = [1000]
        self.OFFSCREEN_PATH_LENGTH_UM = [500] # how long the dot is moving outside the screen, for circular dot this should equal to diameter, if no pause between directions is needed
        self.runnable = 'MovingRectangle'
        self.pre_runnable = 'MovingRectanglePre'


class MovingDotPre(experiment.PreExperiment):
    def run(self):
        self.show_fullscreen(color = 0.0, duration = 0.0, flip = False)
        
class MovingRectanglePre(MovingDotPre):
    def run(self):
        self.show_fullscreen(color = 0.0, duration = 0.0, flip = False)

class MovingDot(experiment.Experiment):
    def __init__(self, machine_config, experiment_config, queues, connections, application_log, parameters = {}):
        experiment.Experiment.__init__(self, machine_config, experiment_config, queues, connections, application_log, parameters = parameters)
        
    def pre_first_fragment(self):
        self.show_fullscreen(color = 0.0)
    
    def run(self, fragment_id = 0):
        self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        self.show_dots(numpy.array([self.diameter_pix*self.experiment_config.machine_config.SCREEN_PIXEL_TO_UM_SCALE]*len(self.row_col[fragment_id])), 
                self.row_col[fragment_id], self.experiment_config.NDOTS,  color = [1.0, 1.0, 1.0])
        self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        self.experiment_specific_data ={}
        if hasattr(self, 'shown_line_order'):
            self.experiment_specific_data['shown_line_order'] = self.shown_line_order[fragment_id]
        if hasattr(self,'shown_directions'):
            self.experiment_specific_data['shown_directions']= self.shown_directions[fragment_id]
            
    def cleanup(self):#TODO: this is obsolete
        #add experiment identifier node to experiment hdf5
        experiment_identifier = '{0}_{1}'.format(self.experiment_name, int(self.experiment_control.start_time))
        self.experiment_hdf5_path = os.path.join(self.machine_config.EXPERIMENT_DATA_PATH, experiment_identifier + '.hdf5')
        setattr(self.hdf5, experiment_identifier, {'id': None})
        self.hdf5.save(experiment_identifier)
        
    def prepare(self):
        diameter_pix = self.experiment_config.DIAMETER_UM[0]*self.experiment_config.machine_config.SCREEN_UM_TO_PIXEL_SCALE
        self.diameter_pix = diameter_pix
        self.offscreen_pix = self.experiment_config.OFFSCREEN_PATH_LENGTH_UM[0]*self.experiment_config.machine_config.SCREEN_UM_TO_PIXEL_SCALE
        speed_pix = self.experiment_config.SPEED[0]*self.experiment_config.machine_config.SCREEN_UM_TO_PIXEL_SCALE
        gridstep_pix = numpy.floor(self.experiment_config.GRIDSTEP*diameter_pix)
        movestep_pix = speed_pix/self.experiment_config.machine_config.SCREEN_EXPECTED_FRAME_RATE
        h=self.experiment_config.machine_config.SCREEN_RESOLUTION['row']#monitor.resolution.height
        w=self.experiment_config.machine_config.SCREEN_RESOLUTION['col']#monitor.resolution.width
        hlines_c,hlines_r = numpy.meshgrid(numpy.arange(-self.offscreen_pix, w+self.offscreen_pix,movestep_pix),
            numpy.arange(numpy.ceil(diameter_pix/2), h-numpy.ceil(diameter_pix/2), gridstep_pix))
        vlines_r,vlines_c = numpy.meshgrid(numpy.arange(-self.offscreen_pix, h+self.offscreen_pix,movestep_pix), 
            numpy.arange(numpy.ceil(diameter_pix/2), w-numpy.ceil(diameter_pix/2), gridstep_pix))
        # we go along the diagonal from origin to bottom right and take perpicular diagonals' starting
        # and ing coords and lengths
        # diagonals run from bottom left to top right
        dlines,dlines_len = diagonal_tr(45,diameter_pix,gridstep_pix,movestep_pix,w,h, self.offscreen_pix)

        diag_dur = 4*sum(dlines_len)/speed_pix/self.experiment_config.NDOTS #each diagonal is shown 4 times, this is not optimal, we should look into angles and check the number of diagonal directions
        diag_line_maxlength = max(dlines_len)
        longest_line_dur = max([diag_line_maxlength, (w+self.offscreen_pix*2)])/speed_pix/self.experiment_config.NDOTS # vertical direction has no chance to be longer than diagonal
        if longest_line_dur > self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION: #check if allowed block duration can accomodate the longest line
            raise ValueError('The longest trajectory cannot be shown within the time interval set as MAXIMUM RECORDING DURATION')
        line_len={'hor0': (w+(self.offscreen_pix*2))*numpy.ones((1,hlines_c.shape[0])),  # add 2*line_length to trajectory length, because the dot has to completely run in/out to/of the screen in both directions
                        'ver0' : (h+(self.offscreen_pix*2))*numpy.ones((1,vlines_c.shape[0]))}
        ver_dur = 2*line_len['ver0'].sum()/speed_pix/self.experiment_config.NDOTS #2 vertical directions are to be shown
        hor_dur = 2*line_len['hor0'].sum()/speed_pix/self.experiment_config.NDOTS
        total_dur = (self.experiment_config.PDURATION*8+diag_dur+ver_dur+hor_dur)*self.experiment_config.REPEATS
        nblocks = numpy.ceil(total_dur/self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION)#[0]
        
         # we want at least 2 repetitions in the same recording, but the best is to
        # keep all repetitions in the same recording
        angleset = numpy.sort(numpy.unique(self.experiment_config.ANGLES))
        allangles0 = numpy.tile(angleset, [self.experiment_config.REPEATS])
        permlist = getpermlist(allangles0.shape[0], self.experiment_config.RANDOMIZE)
        allangles = allangles0[permlist]
        
        # hard limit: a block in which all directions are shown the grid must not be sparser than 3*dot size. Reason: we assume dotsize
        # corresponds to excitatory receptive field size. We assume excitatiory receptive field is surrounded by inhibitory fields with same width.
         # here we divide the grid into multiple recording blocks if necessary
        if 0:#nblocks*gridstep_pix > diameter_pix*3:
            self.log.info('Stimulation has to be split into blocks. The number of blocks is too high meaning that the visual field would be covered too sparsely in a block \
                if we wanted to present all angles in every block. We shall show multiple lines in a block but not all angles.')
            self.angles_broken_to_multi_block( w, h, diameter_pix, speed_pix,gridstep_pix, movestep_pix,  hlines_r, hlines_c, vlines_r, vlines_c,   angleset, allangles)
        else:
            vr_all= dict();vc_all=dict()
            vr_all[(90, 270,)] = [vlines_r[b::nblocks, :] for b in range(int(nblocks))]
            vc_all[(90, 270,)] = [vlines_c[b::nblocks, :] for b in range(int(nblocks))]
            vr_all[(0, 180,)] = [hlines_r[b::nblocks, :] for b in range(int(nblocks))]
            vc_all[(0, 180,)]= [hlines_c[b::nblocks, :] for b in range(int(nblocks))]
            self.allangles_in_a_block(diameter_pix,gridstep_pix,movestep_pix,w, h, nblocks,  vr_all, vc_all, angleset, allangles, total_dur)
        self.number_of_fragments = len(self.row_col)
        self.fragment_durations = []
        for fragment_duration in range(self.number_of_fragments):
            self.fragment_durations.append(float(len(self.row_col[fragment_duration]) / self.experiment_config.NDOTS)/self.machine_config.SCREEN_EXPECTED_FRAME_RATE + 2*self.experiment_config.PAUSE_BEFORE_AFTER)
#        print self.shown_directions
            
    def angles_broken_to_multi_block(self, w, h, diameter_pix, speed_pix,gridstep_pix, movestep_pix,  hlines_r, hlines_c, vlines_r, vlines_c,   angleset, allangles):
        '''In a block the maximum possible lines from the same direction is put. Direction is shuffled till all lines to be shown are put into blocks.
        Repetitions are not put into the same block'''
        from copy import deepcopy
        if self.experiment_config.NDOTS > 1:
            raise NotImplementedError('This algorithm is not yet working when multiple dots are to be shown on the screen')
        nlines_in_block_hor = int(numpy.floor(self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION / ((w+self.offscreen_pix*2)/speed_pix/self.experiment_config.NDOTS))) #how many horizontal trajectories fit into a block? 
        nlines_in_block_ver = int(numpy.floor(self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION / ((h+self.offscreen_pix*2)/speed_pix/self.experiment_config.NDOTS))) #how many horizontal trajectories fit into a block? 
        nblocks_hor = int(numpy.ceil(float(hlines_r.shape[0])/nlines_in_block_hor))
        nblocks_ver = int(numpy.ceil(float(vlines_r.shape[0])/nlines_in_block_ver))
        #nlines_in_block_diag=
        line_order = dict()
        lines_rowcol = dict()
        if 90 in angleset:
            line_order[90] = [numpy.arange(b, vlines_r.shape[0], nblocks_ver) for b in range(nblocks_ver)]
            lines_rowcol[90] = [numpy.vstack(numpy.dstack([vlines_r[b::nblocks_ver, :],  vlines_c[b::nblocks_ver, :]])) for b in range(nblocks_ver)]
        if 270 in angleset:
            line_order[270] = [numpy.arange(b, vlines_r.shape[0], nblocks_ver) for b in range(nblocks_ver)]
            lines_rowcol[270] = [numpy.vstack(numpy.dstack([vlines_r[b::nblocks_ver, :][-1::-1, :],  vlines_c[b::nblocks_ver, :][-1::-1, :]])) for b in range(nblocks_ver)]
        if 0 in angleset:
            line_order[0] = [numpy.arange(b, hlines_r.shape[0], nblocks_hor) for b in range(nblocks_hor)]
            lines_rowcol[0] = [numpy.vstack(numpy.dstack([hlines_r[b::nblocks_hor, :],  hlines_c[b::nblocks_hor, :]])) for b in range(nblocks_hor)]
        if 180 in angleset:
            line_order[180] = [numpy.arange(b, hlines_r.shape[0], nblocks_hor) for b in range(nblocks_hor)]
            lines_rowcol[180] = [numpy.vstack(numpy.dstack([hlines_r[b::nblocks_hor, :][-1::-1, :],  hlines_c[b::nblocks_hor, :][-1::-1, :]])) for b in range(nblocks_hor)]
        diag_angles = [a1 for a1 in angleset if a1 in [45, 135, 225, 315]] #this implementation does not require doing the loop for all angles but we do it anyway, eventually another implementation might give different results for different angles
        for a1 in diag_angles:
            line_order[a1]=[]
            lines_rowcol[a1] = []
            row_col_f,linelengths_f = diagonal_tr(a1,diameter_pix,gridstep_pix,movestep_pix,w, h, self.offscreen_pix)
            linelengths_f = numpy.squeeze(linelengths_f) # .shape[1] = NDOTS
            # for diagonal lines we need to find a good combination of lines that fill the available recording time
            while linelengths_f.sum()>0:
                line_order[a1].append([])
                # in a new block, first take the longest line
                cblockdur=0
                while linelengths_f.sum()>0 and cblockdur < self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION:                    
                    li = int(numpy.where(linelengths_f==max(linelengths_f))[0][0])
                    if cblockdur+linelengths_f[li]/speed_pix/self.experiment_config.NDOTS > self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION:
                        break # we found a line that fits into max recording duration
                    line_order[a1][-1].append(int(numpy.where(linelengths_f==linelengths_f[li])[0][0])) #if needed, this converts negative index to normal index
                    cblockdur += max(linelengths_f)/speed_pix/self.experiment_config.NDOTS
                    linelengths_f[li] = 0
                    if linelengths_f.sum()==0: break
                    # then find the line at half-screen distance and take it as next line
                    li = li - int(row_col_f.shape[0]/2) #negative direction automatically wrapped in numpy
                    step=1
                    all_sides = 0
                    while linelengths_f[li]==0: # look at both sides of the line which was already used
                        li += -1*step
                        if cblockdur+linelengths_f[li]/speed_pix/self.experiment_config.NDOTS <  self.experiment_config.machine_config.MAXIMUM_RECORDING_DURATION:
                            break # we found a line that fits into max recording duration
                        allsides+=1
                        if allsides == 2: #both negative and positive offsets from the original lines have been tried
                            step+=1 # step to next two neighbors
                            allsides=0
                        if li + step > len(linelengths_f):
                            li = None
                            break
                    if li== None: # no more lines for this block
                        break
                    else: # append the line to the list of lines in the current block
                        line_order[a1][-1] .append(int(numpy.where(linelengths_f==linelengths_f[li])[0][0]))
                        cblockdur += linelengths_f[li]/speed_pix/self.experiment_config.NDOTS
                        linelengths_f[li]=0
                lines_rowcol[a1].append(numpy.vstack(row_col_f[line_order[a1][-1]]))

        self.row_col = [] # list of coordinates to show on the screen
        self.block_end = [] # index in the coordinate list where stimulation has to stop and microscope needs to save data
        self.shown_directions = [] # list of direction of each block presented on the screen
        self.shown_line_order  = []
        for r in range(self.experiment_config.REPEATS):
            lines_rc = deepcopy(lines_rowcol) # keep original data in case of multiple repetitions. 
            lineo = deepcopy(line_order)
            while sum([len(value) for key, value in lines_rc.items()])>0: # are there lines that have not yet been shown?
                for direction in angleset: # display blocks obeying angle pseudorandom order
                    if len(lines_rc[direction])>0:
                        lrc = lines_rc[direction].pop();# take the last element (containing n lines) and remove from list of lines to be shown
                        self.row_col.append(utils.rc(numpy.array(lrc)))
                        self.block_end.append(len(self.row_col))
                        self.shown_directions.append(direction)
                        self.shown_line_order.append(lineo[direction].pop())
        return 
        
    def allangles_in_a_block(self, diameter_pix,gridstep_pix,movestep_pix,w, h, nblocks,  vr_all, vc_all, angleset, allangles, total_dur):
        '''algortithm that splits the trajectories to be shown into blocks so that each block shows all angles and repetitions'''
        block_dur = total_dur/nblocks
        precond_lines = dict.fromkeys(angleset) # coordinate arrays for each direction, 1 trajectory, middle of the screen
        # ANGLES and repetitions are played within a block
        # coords are in matrix coordinates: origin is topleft corner. 0 degree runs
        # from left to right.
        arow_col = []
        for a in range(len(angleset)):
            arow_col.append([])
            for b in range(int(nblocks)):
                arow_col[a].append([])
                # in order to fit into the time available for one recording (microscope limitation) we keep only every nblocks'th line in one block. This way all blocks have all directions. 
                #For very short block times this would keep only 1 or 2 trajectory from a given direction in a block which is not good because we are supposed to wait between changing directions
               # so that calcium transients can settle and we can clearly distinguish responses belonging to different directions. 
                if numpy.any(angleset[a]==[0,90,180,270]):
                    direction = [k for k in vr_all.keys() if angleset[a] in k][0]
                    vr = vr_all[direction][b]; 
                    vc = vc_all[direction][b]
                    if angleset[a]== 270: # swap coordinates
                        vr = vr[:,-1::-1]
                    elif angleset[a]==180: 
                        vc = vc[:,-1::-1]
                    
                    # try to balance the dot run lengths (in case of multiple dots) so that most of the time the number of dots on screen is constant        
                    segm_length = vr.shape[1]/self.experiment_config.NDOTS #number of coordinate points in the trajectory 1 dot has to run in the stimulation segment
                    cl =range(vr.shape[0]) # this many lines will be shown
                    #partsep = [zeros(1,self.experiment_config.NDOTS),size(vr,2)]
                    partsep = range(0 , vr.shape[0], int(numpy.ceil(segm_length)))
                    if len(partsep)<self.experiment_config.NDOTS+1:
                        partsep.append(vr.shape[1])
                    dots_line_i = [range(partsep[d1-1], partsep[d1]) for d1 in range(1, self.experiment_config.NDOTS+1)] 
                    drc=[]
                    for s1 in range(self.experiment_config.NDOTS): #each dot runs through a full line
                        dl = numpy.prod(vr[:,dots_line_i[s1]].shape) # total number of coordinate points for all the lines in the current direction
                        drc.append(numpy.r_[numpy.reshape(vr[:,dots_line_i[s1]],[1,dl]), 
                            numpy.reshape(vc[:,dots_line_i[s1]],[1,dl])]) # reshape lines to a single list of coordinates
                        if s1>1 and dl < len(drc[s1-1]): # a dot will run shorter than the others
                        # the following line was not tested in python (works in matlab)
                            drc[s1] = numpy.c_[drc[s1],-self.offscreen_pix*numpy.ones(2,len(drc[s1-1])-dl)] # complete with coordinate outside of the screen
                            
                    precond_lines[a] = numpy.c_[vr[vr.shape[0]/2], vc[vr.shape[0]/2]].T
                else: # diagonal line
                    row_col_f,linelengths_f = diagonal_tr(angleset[a],diameter_pix,gridstep_pix,movestep_pix,w, h, self.offscreen_pix)
                    row_col =row_col_f[b::nblocks]
                    linelengths = linelengths_f[b:: nblocks]
                    segm_len = linelengths.sum()/self.experiment_config.NDOTS
                    cl =numpy.cumsum(linelengths)
                    partsep = numpy.c_[numpy.zeros((1,self.experiment_config.NDOTS)),len(linelengths)].T
                    dots_line_i = [[] for i2 in range(self.experiment_config.NDOTS)]
                    for d1 in range(1, self.experiment_config.NDOTS+1):
                        partsep[d1] = numpy.argmin(numpy.abs(cl-(d1)*segm_len))
                        dots_line_i[d1-1] = range(partsep[d1-1],partsep[d1]+1)
                    while 1:
                        part_len = []
                        drc = [[] for i2 in range(self.experiment_config.NDOTS)]
                        for d1 in range(1, self.experiment_config.NDOTS+1):
                            drc[d1-1]=numpy.vstack(row_col[dots_line_i[d1-1]]).T
                            part_len.append(sum(linelengths[dots_line_i[d1-1]]))
                        si = numpy.argmin(part_len) # shortest dot path
                        li = numpy.argmax(part_len) # longest dot path
                        takeable_i = dots_line_i[li]
                        takeable_lengths=linelengths[takeable_i]
                        midpoint = part_len[li]-part_len[si]
                        if numpy.any(takeable_lengths<midpoint):
                            mli = numpy.argmin(numpy.abs(takeable_lengths-midpoint)) # moved line
                            taken_line_i = dots_line_i[li][mli]
                            dll = len(dots_line_i[li])
                            dots_line_i[li] = dots_line_i[li][numpy.c_[range(mli-1),range(mli+1, dll)]]
                            dots_line_i[si] = numpy.c_[dots_line_i[si],  taken_line_i]
                        else:
                            break
                    ml=[]
                    for s1 in range(self.experiment_config.NDOTS): #each dot runs through a full line
                        drc[s1]= numpy.vstack(row_col[dots_line_i[s1]]).T#row_col[dots_line_i[s1]]
                        ml.append(len(drc[s1]))
                    for s1 in range(self.experiment_config.NDOTS):
                        if len(drc[s1])<max(ml): # a dot will run shorter than the others
                            drc[s1] = numpy.c_[drc[s1],-self.offscreen_pix*numpy.ones(2,max(ml)-len(drc[s1]))] # complete with coordinate outside of the screen
                    
                    precond_lines[a] = row_col[row_col.shape[0]/2].T
                arow_col[a][b] = drc
        self.row_col = [] # list of coordinates to show on the screen
        self.line_end = [] # index in coordinate list where a line ends and another starts (the other line can be of the same or a different direction
        self.shown_directions = [] # list of direction of each block presented on the screen
        # create a list of coordinates where dots have to be shown, note when a direction subblock ends, and when a block ends (in case the stimulus has to be split into blocks due to recording duration limit)
        permlist = getpermlist(allangles.shape[0]*(nblocks-1), self.experiment_config.RANDOMIZE)
        for b in range(int(nblocks)):
            self.row_col.append([])
            self.shown_directions.append({'block_start':[], 'block_end':[]})
            self.line_end.append([])
            if hasattr(self.experiment_config, 'PRECOND') and self.experiment_config.PRECOND=='line from previous direction':
                    # show an extra dot trajectory at a direction so that when stimulations starts from black screen, this trajectory can be skipped
                    precond_ai = numpy.where(angleset==allangles[-1])[0][0] # take the previous angle to avoid eventual habituation by repeating the same direction
                    self.row_col[-1].extend([precond_lines[precond_ai][:, c_i]*self.experiment_config.machine_config.SCREEN_PIXEL_TO_UM_SCALE for c_i in range(precond_lines[precond_ai].shape[1])])
                    self.precond_frames = precond_lines[precond_ai].shape[1]
                    # now continue with adding the trajectories actually used in the analysis:
            for a1 in range(len(allangles)):
                cai = numpy.where(angleset==allangles[a1])[0]
                self.shown_directions[-1]['block_start'].append([allangles[a1], len(self.row_col[-1])])
                for f in range(arow_col[cai][b][0].shape[1]):
                    coords = []
                    for n in range(self.experiment_config.NDOTS):
                        coords.append(arow_col[cai][b][n][:,f])
                    self.row_col[-1].extend([c*self.experiment_config.machine_config.SCREEN_PIXEL_TO_UM_SCALE for c in coords])
                self.shown_directions[-1]['block_end'].append([allangles[a1], len(self.row_col[-1])]) # at each coordinate we store the direction, thus we won't need to analyze dot coordinates 
                self.line_end[-1].append(arow_col[cai][b][0].shape[1])
            self.row_col[-1]=utils.rc(numpy.array(self.row_col[-1]))
            # if stim is broken into blocks then angles in different blocks are shown in different order, shuffle angles now:
            allangles = allangles[permlist[(permlist>=b*allangles.shape[0]) * (permlist<(b+1)*allangles.shape[0])]%len(allangles)]
        pass

class MovingRectangle(MovingDot):
    def run(self, fragment_id=0):
        number_of_blocks = len(self.shown_directions[fragment_id]['block_start'])
        self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        for block_index in range(-1, number_of_blocks):
            if block_index == -1:
                orientation = 0
                start_index = 0
                end_index = self.shown_directions[fragment_id]['block_start'][0][1]
            else:
                orientation = self.shown_directions[fragment_id]['block_end'][block_index][0]
                start_index = self.shown_directions[fragment_id]['block_start'][block_index][1]
                end_index = self.shown_directions[fragment_id]['block_end'][block_index][1]
            pos = self.row_col[fragment_id][start_index:end_index]
            self.show_shape('r', pos=pos, orientation=orientation, size = utils.rc([self.experiment_config.WIDTH_UM[0],  self.experiment_config.HEIGHT_UM[0]])) 
            if utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                break
#        
#        
#        frame_index = 0
#        block_index = 0
#        precond_shown = False
#        for pos in self.row_col[fragment_id]:
#            if not precond_shown:
#                orientation = self.precond_angle
#            else:
#                orientation = self.shown_directions[fragment_id]['block_end'][block_index][0]
#            self.show_shape('r', pos=pos, orientation=orientation, size = utils.rc([self.experiment_config.WIDTH_UM[0],  self.experiment_config.HEIGHT_UM[0]])) 
#            if hasattr(self,  'precond_frames') and hasattr(self, 'precond_angle') and self.precond_frames == frame_index:
#                precond_shown = True
#            if self.shown_directions[fragment_id]['block_end'][block_index][1] == frame_index:
#                block_index += 1
#            frame_index += 1
#            if utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
#                break
        self.show_fullscreen(color = 0.0, duration = self.experiment_config.PAUSE_BEFORE_AFTER)
        self.experiment_specific_data ={}
        if hasattr(self, 'shown_line_order'):
            self.experiment_specific_data['shown_line_order'] = self.shown_line_order[fragment_id]
        if hasattr(self,'shown_directions'):
            self.experiment_specific_data['shown_directions']= self.shown_directions[fragment_id]

def  diagonal_tr(angle,diameter_pix,gridstep_pix,movestep_pix,w,h, offscreen_pix):
    ''' Calculates positions of the dot(s) for each movie frame along the lines dissecting the screen at 45 degrees'''
    cornerskip = numpy.ceil(diameter_pix/2)+diameter_pix # do not show dot where it would not be a full dot, i.e. in the screen corners
    pos_diag = [0 for i in range(3)] #preallocate list. Using this prealloc we can assign elements explicitly (not with append) that makes the code clearer for this algorithm
    diag_start_row = [0 for i in range(3)] ; diag_end_col = [0 for i in range(3)] 
    diag_start_col = [0 for i in range(3)] ; diag_end_row = [0 for i in range(3)] 
    # pos_diag is a diagonal running at 45 degree from the vertical (?):
    # we space perpendicularly running dots on this diagonal, trajectories are spaced at regular intervals
    pos_diag[0] = numpy.arange(cornerskip, h/numpy.sqrt(2), gridstep_pix) 
    diag_start_row[0] = numpy.sqrt(2)*pos_diag[0]
    diag_start_col[0] = numpy.ones(diag_start_row[0].shape)
    diag_end_row[0] = numpy.ones(diag_start_row[0].shape)
    diag_end_col[0] = diag_start_row[0].copy()
    # we reached the bottom of the screen along the 45 degree diagonal. To continue this diagonal,we now keep row fixed and col moves till w
    pos_diag[1] = numpy.arange(pos_diag[0][-1]+gridstep_pix, w/numpy.sqrt(2), gridstep_pix)
    #!!! small glitch in start coord's first value
    diag_start_col[1] = numpy.sqrt(2)*pos_diag[1]-h
    diag_start_row[1] = numpy.ones(diag_start_col[1].shape)*diag_start_row[0][-1]
    diag_end_col[1] = numpy.sqrt(2)*pos_diag[1]
    diag_end_row[1] = numpy.ones(diag_end_col[1].shape)
    # we reached the right edge of the screen,
    endp = numpy.sqrt(2)*w-2*cornerskip
    pos_diag[2] = numpy.arange(pos_diag[1][-1]+gridstep_pix, endp, gridstep_pix)
    diag_start_col[2] = numpy.sqrt(2)*pos_diag[2]-h
    diag_start_row[2] = numpy.ones(diag_start_col[2].shape)*diag_start_row[0][-1]
    diag_end_row[2] = w - numpy.sqrt(2)*(w*numpy.sqrt(2)-pos_diag[2])
    diag_end_col[2] = numpy.ones(diag_end_row[2].shape)*w

    dlines_len=[]
    dlines=[]
    offs= offscreen_pix*numpy.sqrt(2)#diameter_pix*1/numpy.sqrt(2)
    swap=0
    oppositedir=0 # 45 degrees
    if numpy.any(angle == [45+180,135+180]):
        oppositedir = 1
    if numpy.any(angle==[135,135+180]):
        swap = 1
    dfl =0
    if dfl:
        full = Qt4Plot(None, visible=False)
    for d1 in range(len(pos_diag)):
        for d2 in range(len(pos_diag[d1])):
            dlines_len.append(numpy.sqrt((diag_start_row[d1][d2]+offs-(diag_end_row[d1][d2]-offs))**2+
                (diag_start_col[d1][d2]-offs-(diag_end_col[d1][d2]+offs))**2))
            npix = numpy.ceil(dlines_len[-1]/movestep_pix)
            if swap: # 
                s_r = h-diag_start_row[d1][d2]-offs
                e_r = h-diag_end_row[d1][d2]+offs
            else:
                s_r = diag_start_row[d1][d2]+offs
                e_r = diag_end_row[d1][d2]-offs
            
            s_c = diag_start_col[d1][d2]-offs
            e_c = diag_end_col[d1][d2]+offs
            if oppositedir:
                aline_row = numpy.linspace(e_r,s_r,npix)
                aline_col = numpy.linspace(e_c,s_c,npix)
            else:
                aline_row = numpy.linspace(s_r,e_r,npix)
                aline_col = numpy.linspace(s_c,e_c,npix)
            
            if dfl:
                full.p.setdata([w, 0, 0, h, w, h, w, h],n=[0, 0, 0, 0, w, 0, 0, h],  penwidth=w,  color=Qt.Qt.black)#, vlines =self.rawfullblockstartinds)
                full.p.adddata(diag_start_row[d1][d2],diag_start_col[d1][d2], color=Qt.Qt.green, type='x')
                full.p.adddata(diag_end_row[d1][d2],diag_end_col[d1][d2], color=Qt.Qt.blue, type='x')
                full.p.adddata(s_r,s_c, color=Qt.Qt.red, type='x')
                full.p.adddata(e_r,e_c, color=Qt.Qt.darkRed, type='x')
                full.p.addata(aline_row,aline_col)
                #axis equal
                #axis([1-diameter_pix,w+diameter_pix,1-diameter_pix,h+diameter_pix])axis ij #plot in PTB's coordinate system
            dlines.append(numpy.c_[aline_row, aline_col])
    row_col = dlines
    return numpy.array(row_col),numpy.array(dlines_len) #using array instead of list enables fancy indexing of elements when splitting lines into blocks
        


def getpermlist(veclength,RANDOMIZE):
    if veclength > 256:
        raise ValueError('Predefined random order is only for vectors with max len 256')
    fullpermlist = numpy.array([200,212,180,52,115,84,122,123,2,113,119,168,112,202,153,80,126,78,59,154,131,118,251,167,141,105,51,181,254,
                15,135,189,173,188,159,45,158,245,10,124,156,190,11,221,208,54,106,71,102,91,66,151,148,225,175,152,48,146,172,98,47,145,57,
                28,201,55,13,9,82,32,114,163,93,64,228,162,29,27,187,134,164,253,127,218,35,109,237,211,17,4,72,116,230,165,233,207,96,198,234,
                81,213,191,62,238,8,183,65,89,161,99,133,38,197,142,111,132,196,169,195,75,58,139,250,244,193,21,90,6,242,63,43,69,30,14,37,226,206,
                140,240,255,76,34,223,110,67,61,125,166,20,239,79,107,121,120,219,40,209,231,104,108,128,224,70,155,92,24,176,204,235,229,26,56,252,
                178,136,74,3,12,117,101,186,130,203,39,16,232,137,246,36,249,7,143,241,129,95,31,138,220,210,185,50,97,214,68,85,243,73,88,215,77,41,
                149,248,194,25,182,23,256,5,236,1,33,103,157,217,19,192,18,147,170,179,174,83,49,44,184,144,53,22,199,222,150,216,227,100,171,42,94,177,86,46,247,205,60,87,160])-1 # was defined in matlab so we transform to 0 based indexing
    if RANDOMIZE:
        permlist = fullpermlist[fullpermlist<veclength] # pick only values that address the vector's values
    else:
        permlist = numpy.arange(veclength).astype(int)
    return permlist

   
def generate_filename(args):
    '''creates a string that is used as mat file name to store random dot
    positions
    This method has to be the exact port of the matlab def with the same name'''
    type = args[0]
    if hasattr(type, 'tostring'): type=type.tostring()
    radii = l2s(args[0])
    if len(type)==0 or type=='random':
        n_dots,nframes,interleave,interleave_step = args[2:]
        fn = radii+'[0:.0f]-[1:.0f]-[2:.0f]-[3:.0f].mat'.format(n_dots[0], nframes[0], interleave[0], interleave_step[0])
    elif type=='fixed':
        n_dots,gridstep_factor,nblocks,sec_per_block,frames_per_sec=args[1:]
        fn = radii+'[0]-[1:1.2f]-[1]-[2]-[4].mat'.format(n_dots, gridstep_factor,
                                        nblocks, sec_per_block, frames_per_sec)
    elif type=='fixed_compl_random':
        res,ONOFFratio,enforce_complete_dots,bglevel, gridstep_factor,\
            nblocks, white_area_variation_factor,sec_per_block, iniduration, frames_per_sec, bi = args[2:]
        fn = radii+'_[0]_[0]_[1]_[2]_[4]_[5]_[6]_[7]_[8]_[9]'.format(l2s(res, '-','1.0f'),  l2s(gridstep_factor,'-',  '1.2f'),
                            l2s(enforce_complete_dots,'-',  '1.0f'), l2s(sec_per_block), l2s(iniduration), l2s(frames_per_sec, '', '1.2f'), l2s(ONOFFratio, '-', '1.2f'),  
                            l2s(white_area_variation_factor, '', '1.2f'), l2s(bglevel),l2s(bi))
        return fn       
        
#RZ: send_tcpip_sequence and run_stimulation methods are probably obsolete:
def send_tcpip_sequence(vs_runner, messages, parameters,  pause_before):    
    '''This method is intended to be run as a thread and sends multiple message-parameter pairs. 
    Between sending individual message-parameter pairs, we wait pause_before amount of time. This can be used to allow remote side do its processing.'''
    import socket
    import struct
#    l_onoff = 1                                                                                                                                                           
  #  l_linger = 0                                                                                                                                                          
    #sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,                                                                                                                     
      #           struct.pack('ii', l_onoff, l_linger))
    # Send data
    for i in range(len(messages)):
        while vs_runner.state !='idle':
            time.sleep(0.2)
        time.sleep(pause_before[i])
        print 'slept ' + str(pause_before[i])
        try:
            sock = socket.create_connection(('localhost', 10000))
            sock.sendall('SOC'+messages[i]+'EOC'+parameters[i]+'EOP')
        except Exception as e:
            print e
        finally:  
            sock.close()
    print 'everything sent,  returning'
    return

def run_stimulation(vs):
    vs.run()
    
if __name__ == '__main__':
    import visexpman    
    import sys
    from visexpman.engine import visexp_runner
    cname= 'MBP'
    vs_runner = visexp_runner.VisionExperimentRunner('daniel', cname) #first argument should be a class name
#     commands = [
#                     [0.0,'SOCexecute_experimentEOC'],                    
#                     [0.0,'SOCquitEOC'],
#                     ]
#     cs = command_handler.CommandSender(vs_runner.config, vs_runner, commands)
#     cs.start()
    vs_runner.run_loop()
#     cs.close()

