import os,logging,time,sys,shutil,zipfile,tempfile,ctypes,getpass
import PyQt4.Qt as Qt
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore

TEST=not True

class SelectShortcut(QtGui.QWidget):
    def __init__(self,shortcuts, callback):
        self.callback=callback
        QtGui.QWidget.__init__(self, None)
        self.setGeometry(40,40,300,300)
        self.shortcuts2select = QtGui.QListWidget(self)
        self.shortcuts2select.setSelectionMode(self.shortcuts2select.MultiSelection)
        self.shortcuts2select.addItems(QtCore.QStringList(shortcuts))
        self.install=QtGui.QPushButton('Install Selected')
        self.cancel=QtGui.QPushButton('Cancel')
        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.shortcuts2select, 0, 0, 1, 2)
        self.layout.addWidget(self.install, 1, 0, 1, 1)
        self.layout.addWidget(self.cancel, 1, 1, 1, 1)
        self.setLayout(self.layout)
        self.connect(self.install, QtCore.SIGNAL('clicked()'), self.install_pressed)
        self.connect(self.cancel, QtCore.SIGNAL('clicked()'), self.cancel_pressed)
        
    def install_pressed(self):
        self.selection = [str(i.text()) for i in map(self.shortcuts2select.item, [s.row() for s in self.shortcuts2select.selectedIndexes()])]
        self.close()
        self.callback()
    
    def cancel_pressed(self):
        self.selection=[]
        self.close()
        self.callback()

class InstallConfigurator(Qt.QMainWindow):
    def __init__(self):
        if QtCore.QCoreApplication.instance() is None:
            self.qt_app = Qt.QApplication([])
        Qt.QMainWindow.__init__(self)
        self.setWindowTitle('Vision Experiment Manager Installation Configurator')
        self.setGeometry(0,0,0,0)
        if len(sys.argv)>1:
            self.location=sys.argv[1]
        else:
            self.location='unknown'
        self.installer_checksum=2501958671L
        self.logfile = os.path.join('install_log_{0}.txt'.format(time.time()))
        logging.basicConfig(filename= self.logfile,
                    format='%(asctime)s %(levelname)s\t%(message)s',
                    level=logging.INFO)
        self.timer=QtCore.QTimer()
        self.timer.singleShot(50, self.installer)#ms
        self.show()
        if QtCore.QCoreApplication.instance() is not None:
            QtCore.QCoreApplication.instance().exec_()
            
    def log(self,msg):
        logging.info(msg)
        print msg
            
    def installer(self):
        self.log('Install configurator started')
        self.tmpdirs=[]
        self.notifications=[]
        free_bytes = ctypes.c_ulonglong(0)
        if os.name=='nt':
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p('c:\\'), None, None, ctypes.pointer(free_bytes))
            free_min=10
            if free_bytes.value*1e-9 < free_min:
                self.notify('Warning', 'At least {0} GB free space is required'.format(free_min))
                self.close()
                return
        fp=open('python_installed.txt')
        txt=fp.read()
        fp.close()
        if 'usage: python [option] ... [-c cmd | -m mod | file | -] [arg] ...' in txt:
            self.notify('Warning', 'Python is already installed')
            self.close()
            return
        #Ask user to specify location of visexpman
        visexpman_default_folder='x:\\software'
        if self.location=='fmi' and not os.path.exists(visexpman_default_folder):
            if self.ask4confirmation('Please mount x drive manually. Abort installation?s',title='Question'):
                self.close()
                return
        visexpman_default_local_folder='c:\\visexp'
        if os.path.exists(visexpman_default_local_folder):
            if not self.ask4confirmation('{0} already exists, visexpman might be already installed, continue?'.format(visexpman_default_local_folder)):
                self.close()
                return
        if not os.path.exists(visexpman_default_folder):#X is not available then go for local folder
            visexpman_folder = visexpman_default_local_folder
            os.mkdir(visexpman_folder)
        else:
            visexpman_folder = visexpman_default_folder
        self.visexpmanfolder=self.ask4foldername('Please select visexpman package location', visexpman_folder)
        if 'daqmx' in sys.argv:
            self.install_daqmx=True
        else:
            self.install_daqmx=self.ask4confirmation('Do you want to install PyDAQmx and NI DAQ?')
        #Check installers:
        if TEST:
            d=os.path.join('c:\\temp','modules')
        else:
            d=os.path.join(os.getcwd(),'modules')
        self.installer_files=[os.path.join(d,f) for f in os.listdir(d)]
        if self.installer_checksum !=checksum(d):
            self.notify('Error', 'Invalid binari(es) in {0}'.format(self.d))
            self.close()
            return
        #unzip visexpman and offer shortcuts
        visexpman_zip=self.modulename2filename('visexpman')
        z=zipfile.ZipFile(visexpman_zip)
        z.extractall(self.visexpmanfolder)
        z.close()
        self.shortcutfolder=os.path.join(self.visexpmanfolder,'visexpman','shortcuts')
        shortcut_files=[]
        for root, dirs, files in os.walk(self.shortcutfolder):            
            shortcut_files.extend( [(root + os.sep + file).replace(self.shortcutfolder+os.sep,'') for file in files if os.path.splitext(file)[1]=='.bat'])
        shortcut_files.extend(['Stim.bat', 'Vision Experiment Manager.bat'])
        shortcut_files.sort()
        self.s=SelectShortcut(shortcut_files, self.install2)
        self.s.show()
        
    def install2(self):
        stim_bat_content='''
        title Stim
        python c:\visexp\visexpman\engine\visexp_app.py -u tbd -a stim -c tbd
        pause
        '''
        visexpman_bat_content='''
        title Vision Experiment Manager
        python c:\visexp\visexpman\engine\visexp_app.py -u tbd -a main_ui -c tbd
        pause
        '''
        desktop=os.path.join('c:\\Users', getpass.getuser())
        for s in self.s.selection:
            fn=os.path.join(self.shortcutfolder, s)
            if os.path.exists(fn):
                shutil.copy(fn,desktop)
                self.log('{0} copied to {1}'.format(fn,desktop))
            else:
                if 'Stim.bat' in fn:
                    bfn='Stim.bat'
                    content=stim_bat_content
                else:
                    bfn='Vision Experiment Manager.bat'
                    content=visexpman_bat_content
                fp=open(os.path.join(desktop, bfn),'w')
                fp.write(content)
                fp.close()
                self.log('{0} saved'.format(os.path.join(desktop, bfn)))
        #aggregate all files:
        modules=['anaconda', 'opengl','pygame','opencv','pyqtgraph', 'pyserial', 'gedit', 'tcmd', 'meld']
        self.commands=['title Vision Experiment Manager Installer', 'del python_installed.txt']
        for module in modules:
            fn=self.modulename2filename(module)
            #self.commands.append('msiexec \\i {0} \\qb'.format(fn))
            self.commands.append('msiexec {0}'.format(fn))
            self.log('Adding to bat file: {0} ...'.format(fn))
        python_module_folder='c:\\Anaconda\\Lib\\site-packages'
        self.log('Creating pth file')
        fp=open('v.pth', 'wt')
        fp.write(self.visexpmanfolder.replace('\\','\\\\'))
        fp.close()
        self.commands.append('copy v.pth {0}'.format(python_module_folder))
        hfn=self.modulename2filename('hdf5io')
        if not os.path.exists(os.path.join(self.visexpmanfolder,os.path.basename(hfn))):
            shutil.copy(hfn, self.visexpmanfolder)
            self.log('hdf5io copied')
        self.install_ffmpeg()
        self.commands.append('setx path "%path%;{0};c:\\Program Files\\gedit\\bin"'.format(self.visexpmanfolder))
        if self.install_daqmx:
            fn=self.modulename2filename('nidaq')
            folder=self.extract(fn, 'daq')
            self.tmpdirs.append(folder)
            self.commands.append(os.path.join(folder, 'setup.exe'))
            self.log('Extracting daqmx')
            fn=self.modulename2filename('pydaqmx')
            folder=self.extract(fn)
            self.tmpdirs.append(folder)
            self.commands.append('cd {0}'.format(folder))
            self.commands.append('c:\\Anaconda\\python.exe setup.py install')
        fn=self.modulename2filename('zc.lock')
        folder=self.extract(fn)
        self.tmpdirs.append(folder)
        self.commands.append('cd {0}'.format(folder))
        self.commands.append('c:\\Anaconda\\python.exe setup.py install')
        fn=self.modulename2filename('eric')
        folder=self.extract(fn)
        self.tmpdirs.append(folder)
        self.commands.append('cd {0}'.format(folder))
        self.commands.append('c:\\Anaconda\\python.exe install.py')
        create_shortcut='''
            @echo off

            set SCRIPT="%TEMP%\%RANDOM%-%RANDOM%-%RANDOM%-%RANDOM%.vbs"

            echo Set oWS = WScript.CreateObject("WScript.Shell") >> %SCRIPT%
            echo sLinkFile = "%USERPROFILE%\Desktop\myshortcut.lnk" >> %SCRIPT%
            echo Set oLink = oWS.CreateShortcut(sLinkFile) >> %SCRIPT%
            echo oLink.TargetPath = "c:\Anaconda\eric4.bat" >> %SCRIPT%
            echo oLink.Save >> %SCRIPT%

            cscript /nologo %SCRIPT%
            del %SCRIPT%
        '''
        self.log('Extract visexpman to {0}'.format(self.visexpmanfolder))
        self.commands.append(create_shortcut)
        fn=self.modulename2filename('visexpman')
        folder=self.extract(fn)
        self.log('1')
        self.log(folder)
        self.log(self.visexpmanfolder)
        shutil.copytree(folder, self.visexpmanfolder)
        self.log('2')
        #Verify installation
        self.commands.append('cd {0}'.format(self.visexpmanfolder))
        self.commands.append('call shortcuts\\verify_installation.bat')
        self.commands.append('call c:\\Anaconda\\eric4.bat')
        self.notifications.append('change windows theme to classical')
        self.commands.append('echo cleaning up')
        self.commands.extend(['rd /s /q {0}'.format(f) for f in self.tmpdirs])
        self.commands.append('echo Notifications:')
        self.commands.extend(['echo {0}'.format(n) for n in self.notifications])
        self.commands.append('pause')
        self.log('Writing commands to bat file')
        fn='installer2.bat'
        instbatfp=open(fn,'w')
        [instbatfp.write(c+'\r\n') for c in self.commands]
        instbatfp.close()
        self.close()
        self.log('Configurator Done')
            
    def install_ffmpeg(self):
        shutil.copy(self.modulename2filename('ffmpeg'),  self.visexpmanfolder)
        self.notifications.append('add {0} to path environmental variable'.format(self.visexpmanfolder))
        
    def notify(self, title, message):
        QtGui.QMessageBox.question(self, title, message, QtGui.QMessageBox.Ok)
        
    def ask4foldername(self,title, directory):
        foldername = str(QtGui.QFileDialog.getExistingDirectory(self, title, directory))
        if os.name=='nt':
            foldername=foldername.replace('/','\\')
        return foldername
            
    def ask4confirmation(self, action2confirm,title='Confirm:'):
        reply = QtGui.QMessageBox.question(self, title, action2confirm, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.No:
            return False
        else:
            return True
            
    def modulename2filename(self,modulename):
        fn=[f for f in self.installer_files if modulename in os.path.basename(f).lower()]
        if len(fn)!=1:
            self.notify('Error', '{0} installer component does not exists'.format(modulename))
        else:
            return fn[0]
            
    def extract(self, zip,tag=None):
        if tag !=None:
            out=os.path.join(tempfile.gettempdir(), tag)
            if os.path.exists(out):
                shutil.rmtree(out)
            os.mkdir(out)
        else:
            out=tempfile.gettempdir()
        self.log('Extracting: {0}'.format(zip))
        z=zipfile.ZipFile(zip)
        z.extractall(out)
        z.close()
        if tag==None:
             out=[os.path.join(out, f) for f in os.listdir(out) if os.path.isdir(os.path.join(out,f)) and os.path.splitext(os.path.basename(zip))[0] in f][0]
        return out
        
def checksum(folder):
    return sum([os.path.getsize(os.path.join(folder,f)) for f in os.listdir(folder)])

if __name__=='__main__':
    i=InstallConfigurator()
    