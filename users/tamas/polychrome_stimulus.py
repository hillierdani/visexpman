from visexpman.engine.generic import utils
import visexpman.engine.vision_experiment.experiment as experiment
from visexpman.engine.hardware_interface import polychrome_interface
from visexpman.engine.hardware_interface import instrument
from visexpman.engine.generic import colors
import time
import numpy
import os.path
import os
import shutil
import random

class PolychromeExpConfig(experiment.ExperimentConfig):
    def _create_parameters(self):
        self.WAVELENGTH_RANGE_NAME = 's'
        self.WAVELENGTH_RANGES = {}
        self.WAVELENGTH_RANGES['uv'] = [330, 350, 370, 390, 410]
        self.WAVELENGTH_RANGES['m'] = [480, 500, 520, 540, 560]
        self.WAVELENGTH_RANGES['f'] = [340, 370, 405, 430, 455, 490, 520, 550]
        self.WAVELENGTH_RANGES['s'] = [[480, 1.0],  [520,  0.5],  [560, 0.7]]
        self.USE_GLOBAL_INTENSITY = False
        self.WAVELENGTH_SHUTTERING = False
        self.OFF_WAVELENGTH = 500.0
        self.INTENSITY = 1.0 #0.1-1.0
        self.ON_TIME = 2.0
        self.OFF_TIME = 4.0
        self.INIT_DELAY = 4.0
        self.runnable = 'PolychromeExperiment'        
        self._create_parameters_from_locals(locals())

class PolychromeExperiment(experiment.Experiment):
    def prepare(self):
        pass

    def run(self):
        self.show_fullscreen(duration = self.experiment_config.INIT_DELAY,  color = 0.0, block_trigger = False, frame_trigger = False)
        self.polychrome = polychrome_interface.Polychrome(self.machine_config)
        if self.machine_config.ENABLE_SHUTTER:
            self.shutter = instrument.Shutter(self.machine_config)
        elif self.experiment_config.WAVELENGTH_SHUTTERING:
            self.polychrome.set_wavelength(self.experiment_config.OFF_WAVELENGTH)
        else:
            self.polychrome.set_intensity(0.0)
        for wl_config in self.experiment_config.WAVELENGTH_RANGES[self.experiment_config.WAVELENGTH_RANGE_NAME]:
            if isinstance(wl_config, list):
                wavelength = wl_config[0]
                intensity = wl_config[1]
            else:
                wavelength = wl_config
            self.printl('Setting wavelenght: {0}'.format(wavelength))
            if self.check_abort_pressed() or self.abort:
                break
            self.polychrome.set_wavelength(wavelength)
            self.show_fullscreen(duration = 0,  color = colors.wavlength2rgb(wavelength), block_trigger = False, frame_trigger = False)
            if self.machine_config.ENABLE_PARALLEL_PORT:
                self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 1)
            #Open shutter
            if self.config.ENABLE_SHUTTER:
                self.shutter.toggle()
            else:
                if self.experiment_config.USE_GLOBAL_INTENSITY:
                    self.polychrome.set_intensity(self.experiment_config.INTENSITY)
                else:
                    self.polychrome.set_intensity(intensity)
            time.sleep(self.experiment_config.ON_TIME)
            if self.check_abort_pressed() or self.abort:
                break
            #close shutter
            if self.machine_config.ENABLE_PARALLEL_PORT:
                self.parallel_port.set_data_bit(self.machine_config.FRAME_TRIGGER_PIN, 0)
            if self.config.ENABLE_SHUTTER:
                self.shutter.toggle()
            elif self.experiment_config.WAVELENGTH_SHUTTERING:
                self.polychrome.set_wavelength(self.experiment_config.OFF_WAVELENGTH)
            else:
                self.polychrome.set_intensity(0.0)
            self.show_fullscreen(duration = 0,  color = 0, block_trigger = False, frame_trigger = False)
            time.sleep(self.experiment_config.OFF_TIME)
        self.finish()
        
    def finish(self):
        self.polychrome.release_instrument()
        if self.machine_config.ENABLE_SHUTTER:
            self.shutter.release_instrument()

#
#
#
#parameters = locals()
#if not parameters.has_key('wavelength_range'):
#    wavelength_range = 'm'
#import time
##parameters
#on_time=2.0
#off_time=4.0
#init_delay = 4.0
#if wavelength_range == 'uv':
#    wavelengths= [330, 350, 370, 390, 410]
#elif wavelength_range == 'm':
#    wavelengths = [480, 500, 520, 540, 560]
#elif wavelength_range == 'f':
#    wavelengths = [340, 370, 405, 430, 455, 490, 520, 550]
#    
#repeats = 1
#def toggle_shutter(shutter_serial_port):    
#    shutter_serial_port.write('ens\r')
#    
#def init_polychrome(config):
#    import ctypes
#    import os.path
#    dllref = ctypes.WinDLL(os.path.join(config.BASE_PATH,'till','TILLPolychrome.dll'))
#    handle = ctypes.c_void_p()
#    dllref.TILLPolychrome_Open(ctypes.pointer(handle),ctypes.c_int(0))
#    return (handle,dllref)
#def set_wavelength(handle, wavelength):
#    import ctypes
#    handle[1].TILLPolychrome_SetRestingWavelength(handle[0],ctypes.c_double(float(wavelength)))
#def close_polychrome(handle):
#    handle[1].TILLPolychrome_Close(handle[0])
#def get_intensity_range(handle):
#    import ctypes
#    motorized_control = ctypes.c_bool()
#    min_intensity = ctypes.c_double()
#    max_intensity = ctypes.c_double()
#    handle[1].TILLPolychrome_GetIntensityRange(handle[0],ctypes.pointer(motorized_control),ctypes.pointer(min_intensity),ctypes.pointer(max_intensity))
#    print motorized_control,min_intensity,max_intensity
#
#start_time = time.time()
#self.st.clear_screen(0, 0)
#import serial
#shutter_serial_port = serial.Serial(port ='COM6', baudrate = 9600, timeout = 0.1)
#shutter_serial_port.open()
#h=init_polychrome(self.config)
#time.sleep(init_delay - (time.time()-start_time))
#for i in range(repeats):
#    for wavelength in wavelengths:
#        set_wavelength(h,wavelength)
#        if self.config.ENABLE_PARALLEL_PORT:
#            self.parallel.setData(self.config.FRAME_TRIGGER_ON)
#        toggle_shutter(shutter_serial_port)
#        time.sleep(on_time)
#        if self.config.ENABLE_PARALLEL_PORT:
#            self.parallel.setData(self.config.FRAME_TRIGGER_OFF)
#        toggle_shutter(shutter_serial_port)
#        time.sleep(off_time)
#        
#shutter_serial_port.close()
#close_polychrome(h)
