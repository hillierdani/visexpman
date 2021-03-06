import time
import os.path
import tempfile
import uuid
import hashlib
import scipy.io
import io
import StringIO
import zipfile
import numpy
import inspect
import cPickle as pickle
import traceback
import gc
import shutil
import copy
import zmq

import experiment
import experiment_data
import visexpman.engine.generic.log as log
from visexpman.engine.generic import utils
from visexpman.engine.generic import file
from visexpman.engine.hardware_interface import mes_interface
from visexpman.engine.hardware_interface import instrument
from visexpman.engine.hardware_interface import daq_instrument
from visexpman.engine.hardware_interface import stage_control

import visexpA.engine.datahandlers.hdf5io as hdf5io
import visexpA.engine.datahandlers.importers as importers

class ExperimentControl(object):
    '''
    Provides methods for running a single experiment or a series of experiments at different depths. These methods are inherited by experiment classes
    that contain the user defined stimulations and other experiment specific functions.
    
    This class supports the following platforms:
    1. MES - RC microscope for in vivo cortical Ca imaging/stimulation
    2. [NOT TESTED] Electrophysiology setup for single cell recordings: stimulation and recording electrophysiology data
    3. [PLANNED] Virtual reality /behavioral experiments
    4. [PLANNED] Multielectrode array experiments / stimulation
    '''

    def __init__(self, config, application_log):
        '''
        Performs some basic checks and sets call parameters
        '''
        self.application_log = application_log
        self.config = config
        if not hasattr(self, 'number_of_fragments'):
            self.number_of_fragments = 1
        if not issubclass(self.__class__,experiment.PreExperiment): #In case of preexperiment, fragment durations is not expected
            if self.config.PLATFORM == 'mes' and not hasattr(self, 'fragment_durations'):
                raise RuntimeError('At MES platform self.fragment_durations variable is mandatory')
            if hasattr(self, 'fragment_durations'):
                if not hasattr(self.fragment_durations, 'index') and not hasattr(self.fragment_durations, 'shape'):
                    self.fragment_durations = [self.fragment_durations]
                    
        
    def run_experiment(self, context):
        '''
        Runs a series or a single experiment depending on the call parameters
        
        Objective positions and/or laser intensity is adjusted at a series or experiments.
        '''
        message_to_screen = ''
        if hasattr(self, 'objective_positions'):
            for i in range(len(self.objective_positions)):
                context['objective_position'] = self.objective_positions[i]                
                if hasattr(self, 'laser_intensities'):
                    context['laser_intensity'] = self.laser_intensities[i]
                context['experiment_count'] = '{0}/{1}'.format(i+1, len(self.objective_positions))
                message_to_screen += self.run_single_experiment(context)
                if self.abort:
                    break
                time.sleep(3.0)#Later connection with MES shall be checked
            self.queues['gui']['out'].put('Experiment sequence complete')
        else:
            message_to_screen = self.run_single_experiment(context)
        if self.abort:#Commands sent after abort are ignored
            utils.empty_queue(self.queues['gui']['in'])
        return message_to_screen

    def run_single_experiment(self, context):
        '''
        Runs a single experiment which parameters are determined by the context parameter and the self.parameters attribute
        '''
        if context.has_key('stage_origin'):
            self.stage_origin = context['stage_origin']
        if context.has_key('pusher'):
            self.pusher=context['pusher']
        message_to_screen = ''
        if not self.connections['mes'].connected_to_remote_client(timeout = 3.0) and self.config.PLATFORM == 'mes':
            message_to_screen = self.printl('No connection with MES, {0}'.format(self.connections['mes'].endpoint_name))
            return message_to_screen
        message = self._prepare_experiment(context)
        if message is not None:
            message_to_screen += message
            message = '{0}/{1} started at {2}' .format(self.experiment_name, self.experiment_config_name, utils.datetime_string())
            if context.has_key('experiment_count'):
                message = '{0} {1}'.format( context['experiment_count'],  message)
            message_to_screen += self.printl(message,  application_log = True) + '\n'
            self.finished_fragment_index = 0
            for fragment_id in range(self.number_of_fragments):
                if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False):
                    message_to_screen += self.printl('Experiment aborted',  application_log = True) + '\n'
                    self.abort = True
                    break
                elif utils.is_graceful_stop_in_queue(self.queues['gui']['in'], False):
                    message_to_screen += self.printl('Graceful stop requested',  application_log = True) + '\n'
                    break
                elif self._start_fragment(fragment_id):
                        if self.number_of_fragments == 1:
                            self.run()
                        else:
                            self.run(fragment_id)
                        if not self._finish_fragment(fragment_id):
                            self.abort = True
                            #close fragment files
                            self.fragment_files[fragment_id].close()
                            break #Do not record further fragments in case of error
                else:
                    self.abort = True
                    if not hasattr(self, 'analog_input') or not hasattr(self.analog_input, 'finish_daq_activity'):
                        break
                    elif self.analog_input.finish_daq_activity(abort = utils.is_abort_experiment_in_queue(self.queues['gui']['in'])):
                        self.printl('Analog acquisition finished')
                        break
                if self.abort:
                    break
        self._finish_experiment()
        #Send message to screen, log experiment completition
        message_to_screen += self.printl('Experiment finished at {0}' .format(utils.datetime_string()),  application_log = True) + '\n'
        self.application_log.flush()
        return message_to_screen
        
    def wait4jobhandler_resp(self,socket):
        t0=time.time()
#        time.sleep(5)
#        try:
#            resp=socket.recv()
#        except zmq.ZMQError:
#            resp='timeout'
        while True:
            try:
                resp=socket.recv(flags=zmq.NOBLOCK)
                break
            except zmq.ZMQError:
                if time.time()-t0>7:
                    resp='timeout'
                    break
            time.sleep(0.5)
        return resp
                        
    def notify_jobhandler(self):
        try:
            data={'id':self.id, 
                    'stimulus': self.experiment_config_name, 
                    'region': str(self.parameters['region_name']), 
                    'user':str(self.animal_parameters['user'] if self.animal_parameters.has_key('user') else 'default_user'),
                    'animal_id': str(self.animal_parameters['id']),
                    'region_add_date':str(self.scan_region['add_date']),
                    'recording_started': self.recording_start_time,
                    'is_measurement_ready': True,
                    'measurement_ready_time': time.time(),
                    'laser': self.laser_intensity,
                    'depth':self.objective_position,
                    'filename': os.path.basename(self.filenames['fragments'][0])}
            self.savejob2stimcontext(data)
#            self.printl('Sending to jobhandler')
#            self.pusher.send(pickle.dumps(data,2),flags=zmq.NOBLOCK)
#            resp=self.wait4jobhandler_resp(self.pusher)
##            print resp
##            pusher.close()
#            if resp != self.id:
#                self.printl('No response from jobhandler. Make sure that jobhandler is running')
#                self.savejob2stimcontext(data)
##                pusher.close()
#                return
#            self.printl('File sent for analysis')
        except:
#            pusher.close()
            self.printl(traceback.format_exc())
#            self.printl('Sending datafile to jobhandler failed, check error mesage on console')
#            self.savejob2stimcontext(data)
            
    def savejob2stimcontext(self,job):
        fn=os.path.join(self.config.CONTEXT_PATH,'stim.hdf5')
        h=hdf5io.Hdf5io(fn,filelocking=False)
        h.load('jobs')
        if not hasattr(h,'jobs'):
            h.jobs=[]
        
        h.jobs.append(job)
        #h.jobs=utils.object2array(h.jobs)
        h.save('jobs')
        h.close()
        self.printl('Job is saved to local context')
                
    def _backup_raw_files(self):
        if self.abort: return
        if 1:
            try:
                files=[]
                for fragment_id in range(self.number_of_fragments):
                    files.extend([self.filenames['mes_fragments'][fragment_id],self.filenames['fragments'][fragment_id]])
                id=str(self.scan_region['add_date']).split(' ')[0].replace('-','')
                experiment_data.RlvivoBackup(files,str(self.animal_parameters['user'] if self.animal_parameters.has_key('user') else 'default_user'),id,str(self.animal_parameters['id']))
            except:
                self.printl(traceback.format_exc())
                self.printl('SOCnotifyEOCERROR: Automatic backup failed, please make sure that files are copied to u:\\backupEOP')
                #import pdb
                #pdb.set_trace()
                #raise 
        else:
          pass
        
    def _load_experiment_parameters(self):
        if not self.parameters.has_key('id'):
            self.printl('Measurement ID is NOT provided')
            return False
        self.parameter_file = os.path.join(self.config.EXPERIMENT_DATA_PATH, self.parameters['id']+'.hdf5')
        if not os.path.exists(self.parameter_file):
            self.printl('Parameter file does NOT exist ({0})'.format(self.parameter_file))
            return False
        if os.path.getsize(self.parameter_file)<200e3:
            self.printl('Parameter file may be corrupt (file size: {0})'.format(os.path.getsize(self.parameter_file)))
            return False
        h = hdf5io.Hdf5io(self.parameter_file,filelocking=False)
        fields_to_load = ['parameters']
        for field in fields_to_load:
            value = h.findvar(field)
            if value is None:
                self.printl('{0} is NOT found in parameter file'.format(field))
                return False
            if field == 'parameters':
                self.parameters = dict(self.parameters.items() + value.items())
                self.scan_mode = self.parameters['scan_mode']
                self.intrinsic = self.parameters['intrinsic']
                self.id = self.parameters['id']
                if self.scan_mode == 'xz':
                    fields_to_load += ['xz_config', 'rois', 'roi_locations']
                if not self.intrinsic:
                    fields_to_load += ['scan_regions', 'animal_parameters', 'anesthesia_history']
            elif field == 'scan_regions':
                self.scan_region = value[self.parameters['region_name']]
            else:
                setattr(self, field,  value)
        h.close()
        try:
            os.remove(self.parameter_file)
        except:
            self.printl(traceback.format_exc())
        return True

    def _prepare_experiment(self, context):
        message_to_screen = ''
        self.frame_counter = 0
        self.stimulus_frame_info = []
        self.start_time = time.time()
        self.filenames = {}
        if not self._load_experiment_parameters():
            self.abort = True
        self._initialize_experiment_log()
        self._initialize_devices()
        if self.abort:
            return
        if self.config.PLATFORM == 'mes':
            time.sleep(1.0)
            result, laser_intensity = self.mes_interface.read_laser_intensity()
            if result:
                self.initial_laser_intensity = laser_intensity
                self.laser_intensity = laser_intensity
            else:
#                 result, laser_intensity = self.mes_interface.read_laser_intensity()
#                 if result:
#                     self.initial_laser_intensity = laser_intensity
#                     self.laser_intensity = laser_intensity
#                 else:
                    self.printl('Laser intensity CANNOT be read')
                    return None
            parameters2set = ['laser_intensity', 'objective_position']
            for parameter_name2set in parameters2set:                
                if self.parameters.has_key(parameter_name2set):
                    value = self.parameters[parameter_name2set]
                elif context.has_key(parameter_name2set) :
                    value = context[parameter_name2set]
                else:
                    value = None
                if not value is None:
                    result, adjusted_value= getattr(self.mes_interface, 'set_'+parameter_name2set)(value)
                    if not result:
                        self.abort = True
                        self.printl('{0} is not set'.format(parameter_name2set.replace('_', ' ').capitalize()))
                    else:
                        self.printl('{0} is set to {1}'.format(parameter_name2set.replace('_', ' ').capitalize(), value))
                        setattr(self,  parameter_name2set,  value)
            #read stage and objective
            raw_stage_pos = self.stage.read_position()
            self.stage_position = raw_stage_pos - self.stage_origin
            msg='DEBUG: Stage position abs {0}, rel: {1}, origin: {2}' .format(raw_stage_pos, self.stage_position, self.stage_origin)
            self.printl(msg,  application_log = True)
            result, self.objective_position, self.objective_origin = self.mes_interface.read_objective_position(timeout = self.config.MES_TIMEOUT, with_origin = True)
            if not result:
                time.sleep(0.4)#This message does not reach gui, perhaps a small delay will ensure it
                self.printl('Objective position cannot be read, check STIM-MES connection')
                return None
        self._prepare_files()
        return message_to_screen 

    def _finish_experiment(self):
        self._finish_data_fragments()
        #Set back laser
        if hasattr(self, 'initial_laser_intensity') and self.parameters.has_key('laser_intensities'):
            result, adjusted_laser_intensity = self.mes_interface.set_laser_intensity(self.initial_laser_intensity)
            if not result:
                self.printl('Setting back laser did NOT succeed')
        self.printl('Closing devices')
        self._close_devices()
        utils.empty_queue(self.queues['gui']['out'])
        #Update logdata to files
        self.log.info('Experiment finished at {0}' .format(utils.datetime_string()))
        self.log.flush()

########## Fragment related ############
    def _start_fragment(self, fragment_id):
        self.printl('Start fragment {0}/{1} '. format(fragment_id+1,  self.number_of_fragments))
        self.stimulus_frame_info_pointer = 0
        self.frame_counter = 0
        self.stimulus_frame_info = []
        if self.config.PLATFORM == 'mes' and not self.intrinsic:
            if not self._pre_post_experiment_scan(is_pre=True):
                return False
        # Start ai recording
        self.experiment_start_timestamp=time.time()
        self.analog_input = daq_instrument.AnalogIO(self.config, self.log, self.start_time)
        if self.analog_input.start_daq_activity():
            self.printl('Analog signal recording started')
        if self.config.PLATFORM == 'mes':
            self.mes_record_time = self.fragment_durations[fragment_id] + self.config.MES_RECORD_START_DELAY
            if self.mes_record_time > self.machine_config.MAXIMUM_RECORDING_DURATION:
                raise RuntimeError('Stimulus too long')
            self.printl('Fragment duration is {0} s, expected end of recording {1}'.format(int(self.mes_record_time), utils.time_stamp_to_hm(time.time() + self.mes_record_time)))
            if not self.intrinsic:
                if self.config.IMAGING_CHANNELS == 'from_animal_parameter' and self.animal_parameters.has_key('both_channels'):
                    if self.animal_parameters['both_channels']:
                        channels = 'both'
                    else:
                        channels = None
                elif self.config.IMAGING_CHANNELS == 'both':
                    channels = 'both'
                else :
                    channels = None
            utils.empty_queue(self.queues['mes']['in'])
            #TODO:  INTRINSIC: wait for trigger: self.parallel_port.getInSelected() or getInPaperOut
            if self.intrinsic:
                self.printl('Intrinsic imaging: waiting for trigger from MES')
                scan_start_success=False
                while True:
                    if utils.is_abort_experiment_in_queue(self.queues['gui']['in'], False):
                        self.abort=True
                        break
                    elif daq_instrument.read_digital_line('Dev1/port0/line0')[0] == 1:
                        scan_start_success=True
                        break
#                    return True#tmp
                return scan_start_success
            else:
                #start two photon recording
                if self.scan_mode == 'xyz':
                    scan_start_success, line_scan_path = self.mes_interface.start_rc_scan(self.roi_locations, 
                                                                                          parameter_file = self.filenames['mes_fragments'][fragment_id], 
                                                                                          scan_time = self.mes_record_time, 
                                                                                          channels = channels)
                else:
                    if self.scan_mode == 'xz' and hasattr(self, 'roi_locations'):
                        #Before starting scan, set xz lines
                        if self.roi_locations is None:
                            self.printl('No ROIs found')
                            return False
                    elif self.scan_mode == 'xy':
                        if hasattr(self, 'scan_region'):
                            self.scan_region['xy_scan_parameters'].tofile(self.filenames['mes_fragments'][fragment_id])
                            file.wait4file_ready(self.filenames['mes_fragments'][fragment_id])
                            try:
                                scipy.io.loadmat(self.filenames['mes_fragments'][fragment_id])
                            except:
                                self.scan_region['xy_scan_parameters'].tofile(self.filenames['mes_fragments'][fragment_id])
                                file.wait4file_ready(self.filenames['mes_fragments'][fragment_id])
                                try:
                                    scipy.io.loadmat(self.filenames['mes_fragments'][fragment_id])
                                except:
                                    self.printl('MES scan config file error: it may be corrupt')
                                    return False
#                            if os.path.getsize(self.filenames['mes_fragments'][fragment_id])<30e3:
#                                scan_start_success=False
#                                self.printl('MES scan config file error: it may be corrupt')
#                                return scan_start_success
                            self.printl('scan config file OK')
                    scan_start_success, line_scan_path = self.mes_interface.start_line_scan(scan_time = self.mes_record_time, 
                        parameter_file = self.filenames['mes_fragments'][fragment_id], timeout = self.config.MES_TIMEOUT,  scan_mode = self.scan_mode, channels = channels)
                if scan_start_success:
                    self.recording_start_time=time.time()
                    time.sleep(1.0)
                else:
                    self.printl('Scan start ERROR, check netwok connection to MES, restart experiment or rename scan region')
            return scan_start_success
        elif self.config.PLATFORM == 'elphys':
            #Set acquisition trigger pin to high
            self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 1)
            return True
        elif self.config.PLATFORM == 'standalone':
            return True
        return False

    def _stop_data_acquisition(self, fragment_id):
        '''
        Stops data acquisition processes:
        -analog input sampling
        -waits for mes data acquisition complete
        '''
        #Stop external measurements
        if self.config.PLATFORM == 'elphys':
            #Clear acquisition trigger pin
            self.parallel_port.set_data_bit(self.config.ACQUISITION_TRIGGER_PIN, 0)
            data_acquisition_stop_success = True
        elif self.config.PLATFORM == 'mes':
            self.mes_timeout = 0.5 * self.fragment_durations[fragment_id]            
            if self.mes_timeout < self.config.MES_TIMEOUT:
                self.mes_timeout = self.config.MES_TIMEOUT
            #TODO:  INTRINSIC: do not wait for anything
            if self.intrinsic:
                data_acquisition_stop_success = True
            else:
                if not utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                    if self.scan_mode == 'xyz':
                        data_acquisition_stop_success =  self.mes_interface.wait_for_rc_scan_complete(self.mes_timeout)
                    else:
                        data_acquisition_stop_success =  self.mes_interface.wait_for_line_scan_complete(self.mes_timeout)
                    if not data_acquisition_stop_success:
                        self.printl('Line scan complete ERROR {0}'.format(self.mes_timeout))
                else:
                    data_acquisition_stop_success =  False
        elif self.config.PLATFORM == 'standalone':
            data_acquisition_stop_success =  True
        #Stop acquiring analog signals
        if self.analog_input.finish_daq_activity(abort = utils.is_abort_experiment_in_queue(self.queues['gui']['in'])):
            self.printl('Analog acquisition finished')
        return data_acquisition_stop_success

    def _finish_fragment(self, fragment_id):
        result = True
        aborted = False
        if self._stop_data_acquisition(fragment_id):
            if self.config.PLATFORM == 'mes':
                if not utils.is_abort_experiment_in_queue(self.queues['gui']['in']):
                    self.printl('Wait for data save complete')
                    if not self.intrinsic:
                        if self.scan_mode == 'xyz':
                            scan_data_save_success = self.mes_interface.wait_for_rc_scan_save_complete(self.mes_timeout)
                        else:
                            scan_data_save_success = self.mes_interface.wait_for_line_scan_save_complete(self.mes_timeout)
                        if scan_data_save_success:
                            self.printl('MES data save complete')
                        else:
                            self.printl('MES data save did not succeed')
                    else:
                        scan_data_save_success = True
                else:
                    aborted = True
                    scan_data_save_success = False
                result = scan_data_save_success
            else:
                pass
            if not aborted: #TMP and result:
                if self.config.PLATFORM == 'mes':
                    if self.mes_record_time > 30.0:# and self.scan_mode != 'xy':
                        time.sleep(1.0)#Ensure that scanner starts???
                        try:
                            if not self._pre_post_experiment_scan(is_pre=False):
                                self.printl('Post experiment scan was NOT successful')
                        except:
                            self.printl(traceback.format_exc())
                self._save_fragment_data(fragment_id)
                if self.config.PLATFORM == 'mes':
                    for i in range(5):#Workaround for the temporary failure of queue.put().
                        time.sleep(0.1)
                        self.queues['gui']['out'].put('queue_put_problem_dummy_message')
                    time.sleep(0.1)
                    self._backup_raw_files()#Backup comes first then notifying jobhandler. This ensures that even if notification fails backup takes place
                    self.notify_jobhandler()
                    self.printl('SOCmeasurement_readyEOC{0}EOP'.format(self.id))#Notify gui about the new file
                    for i in range(5):
                        time.sleep(0.1)
                        self.queues['gui']['out'].put('queue_put_problem_dummy_message')
        else:
            result = False
            self.printl('Data acquisition stopped with error')
        if not aborted:
            self.finished_fragment_index = fragment_id
        return result

     ############### Devices ##################

    def _initialize_devices(self):
        '''
        All the devices are initialized here, that allow rerun like operations
        '''
        self.parallel_port = instrument.ParallelPort(self.config, self.log, self.start_time)
        self.filterwheels = []
        if hasattr(self.config, 'FILTERWHEEL_SERIAL_PORT'):
            self.number_of_filterwheels = len(self.config.FILTERWHEEL_SERIAL_PORT)
        else:
            #If filterwheels neither configured, nor enabled, two virtual ones are created, so that experiments calling filterwheel functions could be called
            self.number_of_filterwheels = 2
        for id in range(self.number_of_filterwheels):
            self.filterwheels.append(instrument.Filterwheel(self.config, self.log, self.start_time, id =id))
        self.led_controller = daq_instrument.AnalogPulse(self.config, self.log, self.start_time, id = 1)#TODO: config shall be analog pulse specific, if daq enabled, this is always called
        self.analog_input = None #This is instantiated at the beginning of each fragment
        self.stage = stage_control.AllegraStage(self.config, self.log, self.start_time)
        if self.config.PLATFORM == 'mes':
            self.mes_interface = mes_interface.MesInterface(self.config, self.queues, self.connections, log = self.log)

    def _close_devices(self):
        self.parallel_port.release_instrument()
        if self.config.OS == 'win':
            for filterwheel in self.filterwheels:
                filterwheel.release_instrument()
        self.led_controller.release_instrument()
        self.stage.release_instrument()


    ############### File handling ##################
    def _prepare_files(self):
        self._generate_filenames()
        self._create_files()
        self.stimulus_frame_info_pointer = 0

    def _generate_filenames(self):
        ''''
        Generates the necessary filenames for the experiment. The following files are generated during an experiment:
        experiment log file: 
        zipped:
            source code
            module versions
            experiment log

        Fragment file name formats:
        1) mes/hdf5: experiment_name_id_fragment_id
        2) elphys/mat: experiment_name_fragment_id_index

        fragment file(s): measurement results, stimulus info, configs, zip
        '''
        self.filenames['fragments'] = []
        self.filenames['local_fragments'] = []#fragment files are first saved to a local, temporary file
        self.filenames['mes_fragments'] = []
        self.fragment_names = []
        userfolder=os.path.join(self.config.EXPERIMENT_DATA_PATH, self.animal_parameters['user'] if self.animal_parameters.has_key('user') else 'default_user')
        if not os.path.exists(userfolder):
            os.makedirs(userfolder)
        for fragment_id in range(self.number_of_fragments):
            if self.config.EXPERIMENT_FILE_FORMAT == 'mat':
                fragment_name = 'fragment_{0}' .format(self.name_tag)
            elif self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
                fragment_name = 'fragment_{0}_{1}_{2}' .format(self.name_tag, self.id, fragment_id)
            fragment_filename = os.path.join(userfolder, '{0}.{1}' .format(fragment_name, self.config.EXPERIMENT_FILE_FORMAT))
            if self.config.EXPERIMENT_FILE_FORMAT  == 'hdf5' and  self.config.PLATFORM == 'mes':
                if hasattr(self, 'objective_position'):
                    if self.parameters.has_key('region_name'):
                        fragment_filename = fragment_filename.replace('fragment_', 
                        'fragment_{2}_{0}_{1}_'.format(self.parameters['region_name'], self.objective_position, self.scan_mode))
                    elif hasattr(self, 'stage_position'):
                        fragment_filename = fragment_filename.replace('fragment_', 
                        'fragment_{3}_{0:.1f}_{1:.1f}_{2}_'.format(self.stage_position[0], self.stage_position[1], self.objective_position, self.scan_mode))
                self.filenames['mes_fragments'].append(fragment_filename.replace('hdf5', 'mat'))
            elif self.config.EXPERIMENT_FILE_FORMAT == 'mat' and self.config.PLATFORM == 'elphys':
                fragment_filename = file.generate_filename(fragment_filename, last_tag = str(fragment_id))
            local_folder = 'd:\\tmp'
            if not os.path.exists(local_folder):
                local_folder = tempfile.mkdtemp()
            if file.free_space('d:')<1e9:
                raise RuntimeError('D drive is close to full. Free up space')
            local_fragment_file_name = os.path.join(local_folder, os.path.split(fragment_filename)[-1])
            self.filenames['local_fragments'].append(local_fragment_file_name)
            self.filenames['fragments'].append(fragment_filename )
            self.fragment_names.append(fragment_name.replace('fragment_', ''))

    def _create_files(self):
        self.fragment_files = []
        self.fragment_data = {}
        for fragment_file_name in self.filenames['local_fragments']:
            if self.config.EXPERIMENT_FILE_FORMAT  == 'hdf5':
                self.fragment_files.append(hdf5io.Hdf5io(fragment_file_name,self.config))
        if self.config.EXPERIMENT_FILE_FORMAT  == 'mat':
            pass

    def _initialize_experiment_log(self):
        date = utils.date_string()
        self.filenames['experiment_log'] = \
            file.generate_filename(os.path.join(self.config.EXPERIMENT_LOG_PATH, 'log_{0}_{1}.txt' .format(self.name_tag, date)))
        self.log = log.Log('experiment log' + uuid.uuid4().hex, self.filenames['experiment_log'], write_mode = 'user control', timestamp = 'elapsed_time')

    ########## Fragment data ############
    def _prepare_fragment_data(self, fragment_id):
        '''
        Collects and packs all the recorded and generated experiment data, depending on the platform but the following data is handled here:
        - stimulus-recording synchron signal
        - experiment log
        - electrophysiology data
        - user data from stimulation
        - stimulation function call info
        - source code of called software
        - roi data
        - animal parameters
        - anesthesia history
        - pre/post scan data
        '''
        if hasattr(self.analog_input, 'ai_data'):
            analog_input_data = self.analog_input.ai_data
        else:
            analog_input_data = numpy.zeros((2, 2))
            self.printl('Analog input data is NOT available')
        stimulus_frame_info_with_data_series_index, rising_edges_indexes, pulses_detected =\
                            experiment_data.preprocess_stimulus_sync(\
                            analog_input_data[:, self.config.SYNC_CHANNEL_INDEX], 
                            stimulus_frame_info = self.stimulus_frame_info[self.stimulus_frame_info_pointer:], 
                            sync_signal_min_amplitude = self.config.SYNC_SIGNAL_MIN_AMPLITUDE)
        if not pulses_detected:
            self.printl('Stimulus sync signal is NOT detected')
        if self.config.PLATFORM == 'mes':
            a, b, pulses_detected =\
            experiment_data.preprocess_stimulus_sync(\
                            analog_input_data[:, 0], sync_signal_min_amplitude = self.config.SYNC_SIGNAL_MIN_AMPLITUDE)
            if not pulses_detected:
                self.printl('MES sync signal is NOT detected')
        if not hasattr(self, 'experiment_specific_data'):
                self.experiment_specific_data = 0
        if hasattr(self, 'source_code'):
            experiment_source = self.source_code
        else:
            experiment_source = utils.file_to_binary_array(inspect.getfile(self.__class__).replace('.pyc', '.py'))
        software_environment = self._pack_software_environment()
        data_to_file = {
                                    'sync_data' : analog_input_data, 
                                    'current_fragment' : fragment_id, #deprecated
                                    'actual_fragment' : fragment_id,
                                    'rising_edges_indexes' : rising_edges_indexes, 
                                    'number_of_fragments' : self.number_of_fragments, 
                                    'generated_data' : self.experiment_specific_data, 
                                    'experiment_source' : experiment_source, 
                                    'software_environment' : software_environment, 
                                    'machine_config': experiment_data.pickle_config(self.config), 
                                    'experiment_config': experiment_data.pickle_config(self.experiment_config), 
                                    'experiment_start_timestamp':self.experiment_start_timestamp
                                    }
        if self.user_data != {}:
            data_to_file['user_data'] = self.user_data
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            data_to_file['experiment_log'] = numpy.fromstring(pickle.dumps(self.log.log_dict), numpy.uint8)
            stimulus_frame_info = {}
            if stimulus_frame_info_with_data_series_index != 0:
                stimulus_frame_info = self.stimulus_frame_info
            if hasattr(self, 'animal_parameters'):
                data_to_file['animal_parameters'] = self.animal_parameters
            else:
                self.printl('NO animal parameters saved')
            if self.config.PLATFORM == 'mes':
                data_to_file['mes_data_path'] = os.path.split(self.filenames['mes_fragments'][fragment_id])[-1]
                if hasattr(self, 'rois'):
                    data_to_file['rois'] = self.rois
                if hasattr(self, 'roi_locations'):
                    data_to_file['roi_locations'] = self.roi_locations
                if hasattr(self, 'xz_config'):
                    data_to_file['xz_config'] = self.xz_config
                if hasattr(self, 'prepost_scan_image'):
                    data_to_file['prepost_scan_image'] = self.prepost_scan_image
                if hasattr(self, 'scanner_trajectory'):
                    data_to_file['scanner_trajectory'] = self.scanner_trajectory
                if hasattr(self, 'anesthesia_history'):
                    data_to_file['anesthesia_history'] = self.anesthesia_history
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            stimulus_frame_info = stimulus_frame_info_with_data_series_index
        data_to_file['stimulus_frame_info'] = stimulus_frame_info
        self.stimulus_frame_info_pointer = len(self.stimulus_frame_info)
        if self.config.PLATFORM == 'mes':
            if hasattr(self, 'laser_intensity'):
                data_to_file['laser_intensity'] = self.laser_intensity
        return data_to_file

    def _save_fragment_data(self, fragment_id):
        data_to_file = self._prepare_fragment_data(fragment_id)
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            #Save experiment calling parameters:
            self.fragment_files[fragment_id].call_parameters = self.parameters
            self.fragment_files[fragment_id].experiment_name = self.experiment_name
            self.fragment_files[fragment_id].experiment_config_name = self.experiment_config_name
#            experiment_data.save_config(self.fragment_files[fragment_id], self.config, self.experiment_config)
            #Save stage and objective position
            if self.config.PLATFORM == 'mes':
                experiment_data.save_position(self.fragment_files[fragment_id], self.stage_position, self.objective_position)
            setattr(self.fragment_files[fragment_id], self.fragment_names[fragment_id], data_to_file)
            self.fragment_files[fragment_id].save([self.fragment_names[fragment_id], 'call_parameters', 'experiment_name', 'experiment_config_name'])
            self.fragment_files[fragment_id].close()
            if hasattr(self, 'fragment_durations'):
                time.sleep(1.0 + 0.01 * self.fragment_durations[fragment_id])#Wait till data is written to disk
            else:
                time.sleep(1.0)
            shutil.copy(self.filenames['local_fragments'][fragment_id], self.filenames['fragments'][fragment_id])
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            self.fragment_data[self.filenames['local_fragments'][fragment_id]] = data_to_file
        self.printl('Measurement data saved to: {0}'.format(os.path.split(self.filenames['fragments'][fragment_id])[1]))

    def _finish_data_fragments(self):
        #Experiment log, source code, module versions
        experiment_log_dict = self.log.log_dict
        if self.config.EXPERIMENT_FILE_FORMAT == 'hdf5':
            pass
        elif self.config.EXPERIMENT_FILE_FORMAT == 'mat':
            for fragment_path, data_to_mat in self.fragment_data.items():
                data_to_mat['experiment_log_dict'] = experiment_log_dict
                data_to_mat['config'] = experiment_data.save_config(None, self.config, self.experiment_config)
                scipy.io.savemat(fragment_path, data_to_mat, oned_as = 'row', long_field_names=True)

    def _pack_software_environment(self):
        software_environment = {}
        module_names, visexpman_module_paths = utils.imported_modules()
        module_versions, software_environment['module_version'] = utils.module_versions(module_names)
        stream = io.BytesIO()
        stream = StringIO.StringIO()
        zipfile_handler = zipfile.ZipFile(stream, 'a')
        for module_path in visexpman_module_paths:
            if 'visexpA' in module_path:
                zip_path = '/visexpA' + module_path.split('visexpA')[-1]
            elif 'visexpman' in module_path:
                zip_path = '/visexpman' + module_path.split('visexpman')[-1]
            if os.path.exists(module_path):
                zipfile_handler.write(module_path, zip_path)
        software_environment['source_code'] = numpy.fromstring(stream.getvalue(), dtype = numpy.uint8)
        zipfile_handler.close()
        return software_environment

    def _pre_post_experiment_scan(self, is_pre):
        '''
        Performs a short scans before and after experiment to save scanner signals and/or red channel static image
        '''
        initial_mes_line_scan_settings_filename = file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'initial_mes_line_scan_settings.mat'))
        xy_static_scan_filename = file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'measure_red_green_channel_xy.mat'))
        scanner_trajectory_filename = file.generate_filename(os.path.join(self.config.EXPERIMENT_DATA_PATH, 'measure_scanner_signals.mat'))
        #Save initial line scan settings
        if hasattr(self, 'animal_parameters') and self.parameters.has_key('scan_mode') and self.parameters['scan_mode'] == 'xy':
            if (utils.safe_has_key(self.animal_parameters, 'red_labeling') and self.animal_parameters['red_labeling'] == 'no') or not self.animal_parameters.has_key('red_labeling'):
                return True
        result, line_scan_path, line_scan_path_on_mes = self.mes_interface.get_line_scan_parameters(parameter_file = initial_mes_line_scan_settings_filename)
        if not result:
            if os.path.exists(initial_mes_line_scan_settings_filename):
                os.remove(initial_mes_line_scan_settings_filename)
            self.printl('Saving initial line scan parameter was NOT successful. Please check MES-STIM connection')
            return False
        #Measure red channel
        self.printl('Recording red and green channel')
        if self.config.BLACK_SCREEN_DURING_PRE_SCAN:
            self.show_fullscreen(color=0.0, duration=0.0,count=False)
        if hasattr(self, 'scan_region'):
            self.scan_region['xy_scan_parameters'].tofile(xy_static_scan_filename)
        result, red_channel_data_filename = self.mes_interface.line_scan(parameter_file = xy_static_scan_filename, scan_time=4.0,
                                                                           scan_mode='xy', channels=['pmtUGraw','pmtURraw'])
        if self.config.BLACK_SCREEN_DURING_PRE_SCAN and hasattr(self.experiment_config, 'pre_runnable') and self.experiment_config.pre_runnable is not None:
            self.experiment_config.pre_runnable.run()
            self._flip()
        if not result:
            try:
                self.printl('Recording red and green channel was NOT successful')
                if os.path.exists(initial_mes_line_scan_settings_filename):
                    os.remove(initial_mes_line_scan_settings_filename)
                if os.path.exists(red_channel_data_filename):
                    os.remove(red_channel_data_filename)
                return False
            except TypeError:
                traceback_info = traceback.format_exc()
                self.printl('{0},  {1}\n{2}'.format(initial_mes_line_scan_settings_filename, red_channel_data_filename, traceback_info))
                return False
        if not hasattr(self, 'prepost_scan_image'):
            self.prepost_scan_image = {}
        if is_pre:
            self.prepost_scan_image['pre'] = utils.file_to_binary_array(red_channel_data_filename)
        else:
            self.prepost_scan_image['post'] = utils.file_to_binary_array(red_channel_data_filename)
        if self.parameters.has_key('scan_mode') and self.parameters['scan_mode'] == 'xz':
            #Measure scanner signal
            self.printl('Recording scanner signals')
            shutil.copy(initial_mes_line_scan_settings_filename, scanner_trajectory_filename)
            result, scanner_trajectory_filename = self.mes_interface.line_scan(parameter_file = scanner_trajectory_filename, scan_time=2.0,
                                                                               scan_mode='xz', channels=['pmtURraw','ScX', 'ScY'], autozigzag = False)
            if not result:
                try:
                    if os.path.exists(initial_mes_line_scan_settings_filename):
                        os.remove(initial_mes_line_scan_settings_filename)
                    if os.path.exists(red_channel_data_filename):
                        os.remove(red_channel_data_filename)
                    if os.path.exists(scanner_trajectory_filename):
                        os.remove(scanner_trajectory_filename)
                except:
                    self.printl(('removing unnecessary files failed:', initial_mes_line_scan_settings_filename, red_channel_data_filename, scanner_trajectory_filename))
                self.printl('Recording scanner signals was NOT successful')
                return False
            if not hasattr(self, 'scanner_trajectory'):
                self.scanner_trajectory = {}
            if is_pre:
                self.scanner_trajectory['pre'] = utils.file_to_binary_array(scanner_trajectory_filename)
            else:
                self.scanner_trajectory['post'] = utils.file_to_binary_array(scanner_trajectory_filename)
            os.remove(scanner_trajectory_filename)
            if not is_pre:
                self.printl('Setting back green channel')
                shutil.copy(initial_mes_line_scan_settings_filename, scanner_trajectory_filename)
                result, scanner_trajectory_filename = self.mes_interface.line_scan(parameter_file = scanner_trajectory_filename, scan_time=1.5,
                                                                               scan_mode='xz', channels=['pmtUGraw'], autozigzag = False)
            if not result:
                self.printl('Setting back green channel was NOT successful')
        os.remove(initial_mes_line_scan_settings_filename)
        os.remove(xy_static_scan_filename)
        return True

    ############### Helpers ##################
    def _get_elapsed_time(self):
        return time.time() - self.start_time

    def printl(self, message,  application_log = False, experiment_log = True):
        '''
        Helper function that can be called during experiment. The message is sent to:
        -standard output
        -gui
        -experiment log
        '''
        print message
        self.queues['gui']['out'].put(str(message))
        if application_log:
            self.application_log.info(message)
        if hasattr(self, 'log') and experiment_log:
            self.log.info(str(message))
        return message
