try:
    import visa
except:
    pass
import unittest

import instrument
from visexpman.engine.generic.introspect import Timer

class LightMeter(instrument.Instrument):
    '''
    Thorlabs PM100USB interface
    '''
    def init_instrument(self):
        '''
        Method for initialize the instrument
        '''
        instruments_list = visa.get_instruments_list()
        self.visa_id = [id for id in instruments_list if 'USB0' in id and 'P2000166' in id]
        if len(self.visa_id) == 0:
            raise RuntimeError('Light meter is not connected')
        else:
            self.visa_id = self.visa_id[0]
        self.vi = visa.instrument(self.visa_id)
        id = self.vi.ask('*IDN?')
        if 'Thorlabs,PM100USB' not in id:
            raise RuntimeError('Device not supported: {0}'.format(id))
        self.vi.write('STAT:OPER:PTR 512')
        self.vi.write('STAT:OPER:NTR 0')
        self.vi.write('SENS:CURR:RANG 1.400000E-2')
        self.vi.write('SENS:CORR:WAV 500')
        if hasattr(self.config, 'LIGHT_METER'):
            avg = self.config.LIGHT_METER['AVERAGING']
        else:
            avg = 200
        self.vi.write('SENS:AVER:COUNT {0}'.format(avg))
        pass
        
        
    def close_instrument(self):
        '''
        Closes instrument, after this the instrument object has to be recreated.
        '''
        self.vi.close()
        
    def start_instrument(self):
        '''
        Starts instrument operation assuming that the initialization has been performed before
        '''
        pass
        
    def read_power(self):
        self.vi.write('CONF:POW')
        return float(self.vi.ask('MEAS?'))

    def read_frequency(self):
        self.vi.write('CONF:FERQ')
        return float(self.vi.ask('MEAS:FREQ?'))
        
class TestLightMeter(unittest.TestCase):
    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_01_lightmeter(self):
        lm = LightMeter(None)
        values = []
        import time
        st = time.time()
        print 'started'
        for i in range(3000):
#            with Timer('readouttime'):
            try:
                v = lm.read_power()
#                v = lm.read_frequency()
                values.append([time.time()-st,  v])
            except:
                print 'error'
        lm.release_instrument()
        import pylab
        import numpy
        values = numpy.array(values)
        pylab.plot(values[:, 0],  values[:, 1])
        from visexpA.engine.datahandlers import hdf5io
        hdf5io.save_item('c:\\_del\\data.hdf5', 'values',  values,  filelocking=False)
        
        print 1/numpy.diff(values[:, 0]).mean()
        pylab.show()

if __name__ == "__main__":
    unittest.main()