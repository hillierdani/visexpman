import tables
from visexpA.engine.datahandlers import hdf5io
import os
import os.path
import numpy
import time

if True:
    import unit_test_runner
    unit_test_runner.run_test('visexpman.engine.visexp_runner.TestVisionExperimentRunner.test_11_microled')
    
else:
    def append2hdf5():
#        p='/mnt/datafast/debug/ea.hdf5'
        p='v:\\debug\\ea.hdf5'
        if os.path.exists(p):
            os.remove(p)
        handle=hdf5io.Hdf5io(p, filelocking=False)
        h=500
        w=540
        sh = h
#        array_c = handle.h5f.createEArray(handle.h5f.root, 'array_c', tables.UInt8Atom(), (0,))#,  filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1))
        array_c = handle.h5f.createEArray(handle.h5f.root, 'array_c', tables.UInt8Atom((h, w)), shape=(0, ), filters=tables.Filters(complevel=1, complib='lzo', shuffle = 1), expectedrows=100)
        array_c.append(numpy.cast['uint8'](256*numpy.random.random((1, h, w))))
        
        from visexpman.engine.generic.introspect import Timer
        for i in range(60*10):
            with Timer(''):
                array_c.append(numpy.cast['uint8'](256*numpy.random.random((1, h, w))))
        handle.close()
        pass

    def read_hdf5():
        p='v:\\debug\\ea.hdf5'
        handle=hdf5io.Hdf5io(p, filelocking=False)
        print handle.h5f.root.array_c.read().shape
        handle.close()

from multiprocessing import Queue, Process
if __name__ == '__main__':
    if False:
        append2hdf5()
        read_hdf5()
#    p='/mnt/datafast/debug/earray1.hdf5'
#    if os.path.exists(p):
#        os.remove(p)
#    fileh = tables.openFile(p, mode='w')
#    a = tables.Float64Atom()
#    # Use ``a`` as the object type for the enlargeable array.
#    array_c = fileh.createEArray(fileh.root, 'array_c', a, (0,))
#    array_c.append(numpy.ones((10,)))
#    array_c.append(0*numpy.ones((10,)))
#
#    # Read the string ``EArray`` we have created on disk.
#    for s in array_c:
#        print 'array_c[%s] => %r' % (array_c.nrow, s)
#    # Close the file.
#    fileh.close()
