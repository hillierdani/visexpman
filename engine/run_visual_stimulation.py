import visexpman

import generic.utils
import visual_stimulation.user_interface
import hardware_interface.udp_interface
import visual_stimulation.stimulation_control
import visual_stimulation.command_handler
import visual_stimulation.configuration
import visexpman.users as users
import pkgutil
import inspect

class UnsupportedCommandLineArguments(Exception):
    pass

class VisualStimulation(object):
    def __init__(self, config_class, user):
        '''
        Find out configuration and load the appropriate config nad experiment modules, classes
        '''
        self.config_class=config_class
        self.user=user
        #Lists all folders and python modules residing in the user's folder
        for importer, modname, ispkg in pkgutil.iter_modules('visexpman.users'+self.user):
            __import__('visexpman.users.'+self.user)
            m= __import__('visexpman.users.'+self.user+'.'+modname)
            m = getattr(getattr(visexpman.users, self.user), modname)
            for modname in inspect.getmembers(m):
                if modname[0] == config_class:
                    self.config = modname[1]()
                    pass
        self.directories, self.python_modules = generic.utils.find_files_and_folders('..' + os.sep + 'users' + os.sep + self.user,  'py')
        #find module where the configuration class resides
        config_module_name = generic.utils.find_class_in_module(self.python_modules, self.config_class)
        
        if self.config_class == 'SafestartConfig':            
            #instantiate safe start configuration
            setattr(self,  'config',  getattr(visual_stimulation.configuration, self.config_class)('..'))
        else:
            __import__('users.' + self.user + '.' + config_module_name)
        #instantiate configuration class
            
        # mi van ha senki nem definialt usert???
        setattr(self,  'config',  getattr(getattr(getattr(users,  self.user),  config_module_name), self.config_class)('..'))
        #create screen        
        self.user_interface = visual_stimulation.user_interface.UserInterface(self.config)
        #initialize network interface
        self.udp_interface = hardware_interface.udp_interface.UdpInterface(self.config)
        #initialize stimulation control
        self.stimulation_control = visual_stimulation.stimulation_control.StimulationControl(self, self.config,  self.user_interface,  self.udp_interface)
        #set up command handler
        self.command_handler =  visual_stimulation.command_handler.CommandHandler(self.config,  self.stimulation_control,  self.udp_interface,   self.user_interface)
        if self.config.ENABLE_PRE_EXPERIMENT:
                    self.stimulation_control.runStimulation(self.config.PRE_EXPERIMENT)

    def run(self):
        '''
        Run application. Check for commands coming from either keyboard or network. Command is parsed and handled by command handler
        '''        
        if self.config.RUN_MODE == 'single experiment':
            if os.path.exists(self.config.EXPERIMENT):
                self.stimulation_control.setStimulationFile(self.config.EXPERIMENT)
                self.stimulation_control.runStimulation()
            else:
                try:
                    getattr(getattr(getattr(users,  self.user),  self.stimulation_control.experiment_module_name), self.config.EXPERIMENT)
                    class_exists = True
                except:
                    print 'invalid experiment class'
                    class_exists = False
                if class_exists:
                    self.stimulation_control.runStimulation(self.config.EXPERIMENT)
                
        elif self.config.RUN_MODE == 'user interface':
                while True:
                    #check command interfaces:
                    command_buffer = self.user_interface.user_interface_handler()
                    udp_command =  self.udp_interface.checkBuffer()
                    if udp_command != '':
                        self.udp_interface.send(udp_command + ' OK') 
                    command_buffer = command_buffer + udp_command
                    #parse commands
                    res = self.command_handler.parse(self.stimulation_control.state,  command_buffer)            
                    if res != 'no command executed':
                        self.user_interface.user_interface_handler(res)
                        if self.config.ENABLE_PRE_EXPERIMENT:
                            #rerun pre experiment
                            self.stimulation_control.runStimulation(self.config.PRE_EXPERIMENT)
                        if res == 'quit':
                            self.user_interface.close()
                            break
        else:
            print 'invalid run mode'
    
def find_out_config():
    '''
    Finds out configuration from the calling arguments. The following options are supported:
    - No argument: SafestartConfig is loaded
    - Username and config class name is encoded into one argument in the following form:
        user<separator>configclass, where separator can be: . , / \ <space> 
    - username and config class are provided as separate arguments
    '''        
    separators = [' ',  '.',  ',',  '/',  '\\']
    if len(sys.argv) == 1:
        config_class = 'SafestartConfig'
        user = ''
    elif len(sys.argv) == 2:
        for separator in separators:
            if sys.argv[1].find(separator) != -1:
                user = sys.argv[1].split(separator)[0]
                config_class = sys.argv[1].split(separator)[1]
    elif len(sys.argv) == 3:
        config_class = sys.argv[1]
        user = sys.argv[2]
    else:
        raise UnsupportedCommandLineArguments
    return config_class,  user

if __name__ == "__main__":    
    VisualStimulation(*find_out_config()).run()
