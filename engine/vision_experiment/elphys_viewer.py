import sys,multiprocessing
import subprocess,tempfile,os,unittest,numpy,scipy.io,scipy.signal
from pylab import *

import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
import pyqtgraph

from visexpman.engine.generic import fileop,introspect,gui

ELECTRODE_ORDER=[16,1,15,2,12,5,13,4,10,7,9,8,11,6,14,3]#TODO: add this to parameter tree

def mcd2raw(filename, nchannels=16,outfolder=None,header_separately=False):
    cmdfile=os.path.join(fileop.visexpman_package_path(), 'data', 'mcd2raw{0}.cmd'.format(nchannels))
    cmdfiletxt_template=fileop.read_text_file(cmdfile)
    if outfolder is None:
        outfolder=tempfile.gettempdir()
    outfile=os.path.join(outfolder,os.path.basename(filename).replace('.mcd','.raw'))
    cmdfiletxt=cmdfiletxt_template.replace('infile', filename).replace('outfile', outfile)
    if header_separately:
        cmdfiletxt=cmdfiletxt.replace('-WriteHeader\n','')
    tmpcmdfile=os.path.join(tempfile.gettempdir(), 'cmd.cmd')
    fileop.write_text_file(tmpcmdfile, cmdfiletxt)
    mcdatatoolpath='c:\\Program Files (x86)\\Multi Channel Systems\\MC_DataTool\MC_DataTool'
    cmd='"{0}" -file {1}'.format(mcdatatoolpath, tmpcmdfile)
    if header_separately:
        cmdfiletxt=cmdfiletxt_template.replace('infile', filename).replace('outfile', outfile.replace('.raw', 'h.raw'))
        tmpcmdfile2=os.path.join(tempfile.gettempdir(), 'cmd2.cmd')
        cmd2='"{0}" -file {1}'.format(mcdatatoolpath, tmpcmdfile2)
        fileop.write_text_file(tmpcmdfile2, cmdfiletxt)
    res1=subprocess.call(cmd, shell=True)==0
    res2= subprocess.call(cmd2, shell=True) == 0 if header_separately else True
    if all([res1,res2]):
        return outfile
        
def read_raw(filename):
    header=[]
    if os.path.exists(filename.replace('.raw', 'h.raw')):
        headerfile=filename.replace('.raw', 'h.raw')
        read_data_separately=True
    else:
        headerfile=filename
        read_data_separately=False
    with open(headerfile) as f:
        for line in f:
            header.append(line)
            if 'EOH' in line:
                headerlen=len(''.join(header))
                if read_data_separately:
                    data=numpy.fromfile(filename,dtype=numpy.int16)
                else:
                    f.seek(headerlen)
                    data=numpy.fromfile(f,dtype=numpy.int16)
                break
    sample_rate=float([item for item in header if 'Sample rate = ' in item][0].split('=')[1])
    ad_scaling=float([item for item in header if 'El = ' in item][0].split('El =')[1].split('\xb5V')[0])*1e-6
    if len([item for item in header if 'An = ' in item])>0:
        ai_scaling=float([item for item in header if 'An = ' in item][0].split('El =')[1].split('\xb5V')[0])*1e-6
    else:
        ai_scaling=None
    channel_names=[item for item in header if 'Streams = ' in item][0].split('=')[1].strip().split(';')
    if data.shape[0]%len(channel_names) != 0:
        raise IOError('Invalid data in {0}. Datapoints: {1}, Channels: {2}'.format(filename, data.shape[0], len(channel_names)))
    data=data.reshape((data.shape[0]/len(channel_names),len(channel_names))).T
    if ai_scaling is not None:
        analog=data[0]*ai_scaling
        offset=2
    else:
        analog=None
        offset=1
    digital=data[offset-1]+2**15
    elphys=data[offset:]
    t=numpy.linspace(0,digital.shape[0]/sample_rate,digital.shape[0])
    return t,analog,digital,elphys,channel_names,sample_rate,ad_scaling
    
def calculate_repetition_boundaries(digital,fsample,pre,post):
    pres=int(pre*fsample)
    posts=int(post*fsample)
    boundaries=numpy.nonzero(numpy.diff(digital))[0]
    boundaries[0::2]-=pres
    boundaries[1::2]+=posts
    return boundaries
    
def extract_repetitions(digital,elphys,fsample,pre,post):
    repetition_boundaries=calculate_repetition_boundaries(digital, fsample,pre,post)
    fragments = numpy.split(elphys,repetition_boundaries,axis=1)[1::2]
    fragment_length=min([f.shape[1] for f in fragments])
    repetitions = numpy.array([f[:,:fragment_length] for f in fragments])
    return repetitions
    
def save2mat(filename,**datafields):
    field_names=['t','digital','elphys','channel_names','sample_rate','ad_scaling,repetitions']
    scipy.io.savemat(filename,datafields,oned_as='column',do_compression=True)
    
def filter_trace(pars):
    lowpass, highpass,signal=pars
    lowpassfiltered=scipy.signal.filtfilt(lowpass[0],lowpass[1], signal).real
    highpassfiltered=scipy.signal.filtfilt(highpass[0],highpass[1], signal).real
    return lowpassfiltered, highpassfiltered
    
def filter(elphys, cutoff,order,fs):
    lowpass=scipy.signal.butter(order,cutoff/fs,'low')
    highpass=scipy.signal.butter(order,cutoff/fs,'high')
    lowpassfiltered=numpy.zeros_like(elphys)
    highpassfiltered=numpy.zeros_like(elphys)
    pool=multiprocessing.Pool(introspect.get_available_process_cores())
    pars=[(lowpass,highpass,elphys[i]) for i in range(elphys.shape[0])]
    res=pool.map(filter_trace,pars)
    pool.terminate()
    for i in range(len(res)):
        lowpassfiltered[i]=res[i][0]
        highpassfiltered[i]=res[i][1]
    return lowpassfiltered, highpassfiltered
    
def spikes2bins(pars):
    channel,nrepetitions, repetition_window_length,repetition_boundaries,spike_times,spike_window_boundaries,spike_window=pars
    aggr_per_channel=[]
    spiking_map=numpy.ones((nrepetitions, repetition_window_length), dtype=numpy.uint8)
    for rep in numpy.arange(nrepetitions)*2:
        start=repetition_boundaries[rep]
        end=repetition_boundaries[rep+1]
        spike_times_in_rep = spike_times[channel][numpy.where(numpy.logical_and(spike_times[channel]>start,spike_times[channel]<end))[0]]
        spike_times_in_rep-=start
        aggr_per_channel.extend(list(spike_times_in_rep))
        spiking_map[rep/2][spike_times_in_rep]=0
    hist,b=numpy.histogram(aggr_per_channel,spike_window_boundaries)
    spiking_frq=hist/spike_window/repetition_boundaries.shape[0]/2
    return spiking_frq, image_column_binning(spiking_map,spike_window_boundaries.shape[0]).T

def image_column_binning(img,binning):
    flattened=img[:,:img.shape[1]-img.shape[1]%binning].flatten()
    return flattened.reshape(img.shape[0],(img.shape[1]-img.shape[1]%binning)/binning,binning).mean(axis=1)

def raw2spikes(filename,pre,post,filter_order,fcut,spike_threshold_std, spike_window):
    '''
    1) Extract data from raw file
    2) Filter signal, separate baseline and high frequency part
    3) Low frequency part: average repetitions
    4) High frequency part: detect spikes
    5) Split spikes to repetitions and aggregate them
    6) Calculate spiking frq
    '''
    t,analog,digital,elphys,channel_names,sample_rate,ad_scaling = read_raw(filename)
    l,h=filter(elphys,fcut,filter_order,sample_rate)
    low_frequency_avg=extract_repetitions(digital,l,sample_rate,pre,post).mean(axis=0)
    #threshold for spike detection:
    threshold=h.std(axis=1)*spike_threshold_std
    thresholded=(h.T-threshold).T
    binary=numpy.where(thresholded>0,1,0)
    #Extract spike times:
    spike_indexes=numpy.where(numpy.diff(binary,axis=1)==1)
    spike_times=[spike_indexes[1][numpy.where(spike_indexes[0]==channel)[0]] for channel in set(spike_indexes[0])]
    repetition_boundaries=calculate_repetition_boundaries(digital, sample_rate,pre,post)
    nrepetitions=repetition_boundaries.shape[0]/2
    repetition_window_length=numpy.diff(repetition_boundaries)[::2].max()
    spike_windows=int(spike_window*sample_rate)
    spike_window_boundaries=numpy.arange(repetition_window_length/spike_windows)*spike_windows
    trep=(spike_window_boundaries+0.5*spike_windows)/sample_rate
    spiking_frqs=[]
    spiking_maps = []
    pars=[(channel,nrepetitions, repetition_window_length,repetition_boundaries,spike_times,spike_window_boundaries,spike_window) for channel in range(len(spike_times))]
    pool=multiprocessing.Pool(introspect.get_available_process_cores())
    #r=spikes2bins(pars[0])
    res=pool.map(spikes2bins,pars)
    pool.terminate()
    for i in range(len(res)):
        spiking_frq, spiking_map = res[i]
        spiking_maps.append(spiking_map)
        spiking_frqs.append(spiking_frq)
    spiking_frqs=numpy.array(spiking_frqs)
    spiking_maps = numpy.array(spiking_maps)
    return spiking_frqs,low_frequency_avg*ad_scaling,spiking_maps,sample_rate
        
class ElphysViewerFunctions(unittest.TestCase):
    def generate_datafile(self):
        header=[]
        with open(fileop.listdir_fullpath(self.wf)[0]) as f:
            for line in f:
                header.append(line)
                if 'EOH' in line:
                    break
        header=''.join(header)
        recording_duration=10.0
        fsample=25e3
        stimdur=0.2
        stim_period=1.0
        nstim=8
        spike_amplitude=100
        data=numpy.zeros((17,fsample*recording_duration),dtype=numpy.int16)
        stim_sync=numpy.concatenate((numpy.ones((stim_period-stimdur)*0.5*fsample),numpy.zeros(stimdur*fsample),numpy.ones((stim_period-stimdur)*0.5*fsample)))
        stim_sync=numpy.tile(stim_sync,nstim)
        data[0,-stim_sync.shape[0]:]=stim_sync-2**15
        data[0,:-stim_sync.shape[0]]=data[0,stim_sync.shape[0]]
        data[1:,:]=numpy.cast['int16']=numpy.random.random(data[1:,:].shape)*10-5
        offset=data.shape[1]-stim_sync.shape[0]+((stim_period-stimdur)*0.5+0.5*stimdur)*fsample
        pulses=numpy.arange(nstim)*fsample*stim_period
        indexes=numpy.cast['int'](numpy.concatenate([pulses+offset+d for d in range(3)]))
        for i in ELECTRODE_ORDER:
            data[i][indexes+200*ELECTRODE_ORDER.index(i)]=spike_amplitude
        f=open(os.path.join(self.wf,'g.raw'),'wb')
        f.write(header)
        data.flatten('F').tofile(f)
        f.close()
    
    @unittest.skipIf(os.name!='nt', 'Works only on Windows')
    def test_01_mcd2raw(self):
        from visexpman.users.test import unittest_aggregator
        wf=unittest_aggregator.prepare_test_data('mcd')
        for f in fileop.listdir_fullpath(wf):
            outfile=mcd2raw(f)
            self.assertTrue(os.path.exists(outfile))
            self.assertEqual(int(numpy.log10(os.path.getsize(f))),int(numpy.log10(os.path.getsize(outfile))))
            
    def test_02_raw2mat(self):
        from visexpman.users.test import unittest_aggregator
        self.wf=unittest_aggregator.prepare_test_data('mcdraw')
#        self.generate_datafile()
        for f in fileop.listdir_fullpath(self.wf):
            raw2spikes(f,200e-3,200e-3,3,300,2,5e-3)
#            t,digital,elphys,channel_names,sample_rate,ad_scaling = read_raw(f)
#            self.assertEqual(t.shape[0],digital.shape[0])
#            self.assertEqual(elphys.shape[0]+1,len(channel_names))
#            repetitions=extract_repetitions(digital,elphys,sample_rate,200e-3,200e-3)
#            self.assertTrue(all([r.shape[1] for r in repetitions]))#All elements equal
#            data2mat={}
#            data2mat['t']=t
#            data2mat['digital']=digital
#            data2mat['elphys']=elphys
#            data2mat['channel_names']=channel_names
#            data2mat['sample_rate']=sample_rate
#            data2mat['ad_scaling']=ad_scaling
#            
#            l,h=filter(elphys, 300,3,sample_rate)
#            
#            save2mat(os.path.join('/tmp',os.path.basename(f)).replace('.raw','.mat'),**data2mat)
            
    
            
class DataFileBrowser(QtGui.QWidget):
    def __init__(self,parent, root, extensions):
        QtGui.QWidget.__init__(self,parent)
        self.root=root
        self.filetree=gui.FileTree(self, root, extensions)
        self.filetree.setColumnWidth(0,250)
        self.filetree.setToolTip('Double click on file to open')
        self.select_folder=QtGui.QPushButton('Select Folder',self)
        self.select_folder.setMaximumWidth(150)
        self.connect(self.select_folder, QtCore.SIGNAL('clicked()'), self.select_folder_clicked)
        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.filetree, 0, 0, 4, 1)
        self.l.addWidget(self.select_folder, 4, 0, 1, 1)
        self.setLayout(self.l)
       
    def select_folder_clicked(self):
        folder=self.parent().parent().ask4foldername('Select folder', self.root)
        if folder=='': return
        self.root=folder
        self.filetree.set_root(folder)
    
class MultiplePlots(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent,nplots,electrode_spacing):
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.nplots=nplots
        self.electrode_spacing=electrode_spacing
        self.setBackground((255,255,255))
        self.setAntialiasing(True)
        self.plots=[]
        for i in range(nplots):
            p=self.addPlot()
            p.enableAutoRange()
            p.showGrid(True,True,1.0)
            self.plots.append(p)
            if (i+1)%2==0 and i!=0:
                self.nextRow()
                
    def plot(self,x,y,pen=(0,0,0),label='',spike=False):
        yi=numpy.array(y)
        ymin=y.min()
        ymax=y.max()
        for i in range(self.nplots):
            self.plots[i].setLabels(left='{1}, {0:1.0f} um'.format(-self.electrode_spacing*i*1e6,label), bottom='time [ms]')
            self.plots[i].setYRange(ymin,ymax)
            if spike:
                curve = self.plots[i].plot(pen=pen,stepMode=True, fillLevel=0, brush=(0,0,255,150))
                curve.setData(x, y[i][1:])
            else:
                curve = self.plots[i].plot(pen=pen)
                curve.setData(x, y[i])
            
class MultipleImages(pyqtgraph.GraphicsLayoutWidget):
    def __init__(self,parent, nplots,electrode_spacing):
        self.nplots=nplots
        pyqtgraph.GraphicsLayoutWidget.__init__(self,parent)
        self.setBackground((255,255,255))
        self.plots=[]
        self.imgs=[]
        for i in range(nplots):
            p=self.addPlot()
            p.setLabels(left='{0:1.0f} um'.format(-electrode_spacing*i*1e6), bottom='t [s]')
            img = pyqtgraph.ImageItem(border='w')
            p.addItem(img)
            self.imgs.append(img)
            self.plots.append(p)
            if (i+1)%4==0 and i!=0:
                self.nextRow()
                
    def set(self,images):
        for i in range(self.nplots):
            self.imgs[i].setImage(images[i])
            self.imgs[i].setLevels([images.min(),images.max()])
            
class CWidget(QtGui.QWidget):
    '''
    The central widget of the user interface which contains the image, the plot and the various controls for starting experiment or adjusting parameters
    '''
    def __init__(self,parent):
        QtGui.QWidget.__init__(self,parent)
        self.df=DataFileBrowser(self,'/tmp',['mat', 'mcd', 'raw'])
        self.df.setMinimumWidth(400)
        self.df.setMaximumWidth(500)
        self.df.setMinimumHeight(400)
        params_config=[\
                {'name': 'Filter Order', 'type': 'int', 'value': 3},
                {'name': 'Filter Cut Frequency', 'type': 'float', 'value': 300, 'siPrefix': True, 'suffix': 'Hz'},
                {'name': 'Spike Threshold', 'type': 'float', 'value': 3, 'suffix': 'std','siPrefix': True},
                {'name': 'Spiking Frequency Window Size', 'type': 'float', 'value': 5e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Pre Stimulus Time', 'type': 'float', 'value': 200e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Post Stimulus Time', 'type': 'float', 'value': 400e-3, 'suffix': 's','siPrefix': True},
                {'name': 'Electrode Spacing', 'type': 'float', 'value': 50e-6, 'suffix': 'm','siPrefix': True},
                {'name': 'Electrode Order', 'type': 'list', 'value': [16,1,15,2,12,5,13,4,10,7,9,8,11,6,14,3]},
                    ]

        self.params = gui.ParameterTable(self, params_config)
        self.params.setMinimumWidth(400)
        self.params.setMaximumWidth(500)
        self.params.setMaximumHeight(300)

        self.l = QtGui.QGridLayout()
        self.l.addWidget(self.df, 0, 0, 1, 1)
        self.l.addWidget(self.params, 0, 1, 1, 1)
        self.setLayout(self.l)

class ElphysViewer(gui.SimpleAppWindow):
    #TODO: context
    #TODO: save params to file
    def init_gui(self):
        self.toolbar = gui.ToolBar(self, ['add_note', 'save','reconvert_all', 'concatenate_files', 'exit'])
        TOOLBAR_HELP = '''
        Add Note: note will be saved to currently open file
        Save: 
        Reconvert All: With current settings apply filtering/spike detection/calculation for all files in selected folder
        Concatenate Files: concatenate electrophysiology traces in all files in a selected folder and save to a raw format.
        '''
        self.addToolBar(self.toolbar)
        self.toolbar.setToolTip(TOOLBAR_HELP)
        self.setWindowTitle('Electrophyisiology Datafile Viewer')
        self.cw=CWidget(self)
        self.setCentralWidget(self.cw)
        self.debugw.setMinimumWidth(800)
        self.debugw.setMinimumHeight(250)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(750)
        self.maximized=False
        self.cw.df.filetree.doubleClicked.connect(self.open_file)
        
    def open_file(self, index):
        self.filename = gui.index2filename(index)
        if os.path.isdir(self.filename): return#Double click on folder is ignored
        ext = fileop.file_extension(self.filename)
        params=self.cw.params.get_parameter_tree(True)
        if ext == 'raw':
            electrode_order=numpy.array(ELECTRODE_ORDER)-1
            pre=params['Pre Stimulus Time']
            post=params['Post Stimulus Time']
            filter_order=params['Filter Order']
            fcut=params['Filter Cut Frequency']
            spike_threshold_std=params['Spike Threshold']
            spike_window=params['Spiking Frequency Window Size']
            self.spiking_frqs,self.low_frequency_avg,self.spiking_maps,self.fsample = raw2spikes(self.filename,pre,post,filter_order,fcut,spike_threshold_std, spike_window)
            self.tplothf=1e3*numpy.linspace(0,self.spiking_frqs.shape[1]*spike_window,self.spiking_frqs.shape[1])
            self.tplotlf=1e3*numpy.linspace(0,self.low_frequency_avg.shape[1]/self.fsample,self.low_frequency_avg.shape[1])
            self.nchannels=self.spiking_frqs.shape[0]
            
            self.hf_plots=MultiplePlots(None,self.nchannels,params['Electrode Spacing'])
            self.hf_plots.setWindowTitle('Spiking Frequency')
            self.hf_plots.plot(self.tplothf,self.spiking_frqs[electrode_order],label='Hz',spike=True)
            
            self.lf_plots=MultiplePlots(None,self.nchannels,params['Electrode Spacing'])
            self.lf_plots.setWindowTitle('DC')
            self.lf_plots.plot(self.tplotlf,self.low_frequency_avg[electrode_order]*1e6,label='uV')

            self.images=MultipleImages(None,self.nchannels,params['Electrode Spacing'])
            self.images.setWindowTitle('Spike maps')
            #Scale maps
            self.scaled_maps=[]
            for i in range(self.spiking_maps.shape[0]):
                self.scaled_maps.append(numpy.repeat(self.spiking_maps[i],int(1.0/spike_window),axis=1))
            self.scaled_maps=numpy.array(self.scaled_maps)
            self.images.set(self.scaled_maps[electrode_order])
            [img.setScale(spike_window) for img in self.images.imgs]
            
            self.hf_plots.show()
            self.lf_plots.show()
            self.images.show()
        self.log('{0} opened'.format(self.filename))

    def exit_action(self):
        self.close()
        [getattr(self,w).close() for w in ['hf_plots', 'lf_plots','images'] if hasattr(self, w)]
        if hasattr(self, 'lf_plots'):
            del self.lf_plots
        if hasattr(self, 'hf_plots'):
            del self.hf_plots
        if hasattr(self, 'images'):
            del self.images
        
    def save_action(self):
        pass
        
    def add_note_action(self):
        pass
        
    def reconvert_all_action(self):
        pass

    def concatenate_files_action(self):
        pass

if __name__=='__main__':
    if len(sys.argv)==1:
        unittest.main()
    else:
        g=ElphysViewer()