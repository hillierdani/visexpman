#TODO: remove these 3 imports:
import sys
import os
import numpy


version = 'v0.4.0'
if '--vu' in sys.argv:
    USER_MODULE= str(sys.argv[sys.argv.index('--vu')+1]+".users")
else:
    USER_MODULE='visexpman.users'
try:
    from visexpman.applications.visexp_smallapp import rotate_images
except:
    pass
try:
    from visexpman.applications.led_stimulator import led_stimulator
except:
    pass
#try:
#    from visexpman.applications.video_splitter import video_splitter
#except:
#    pass
