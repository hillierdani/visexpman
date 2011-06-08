import sys
import math
import random
import numpy
import os.path
import os
import time
#from OpenGL.GL import *
#from OpenGL.GLUT import *
import unittest

# valid color configurations: 1.0; 255; (1.0, 0.4, 0), invalid color configuration: (255, 0, 128)

def convert_to_rgb(color):
    if isinstance(color, list) or isinstance(color, tuple):
        return color
    else:
        return [color,  color,  color]
        
def convert_rgb(color):
    '''
    Converts rgb channels from 0...1 range to -1...1 range.
    '''
    converted_color = []
    for color_channel in color:
        converted_color.append(color_channel * 2.0 - 1.0)
    return converted_color
    
    
def convert_greyscale(intensity):
    '''
    Converts greyscale color to Psychopy RGB format which range is -1...1. Greyscale colors are interpreted in 0...1 range.
    '''
    return convert_rgb([intensity,  intensity,  intensity])
    
    
def convert_8_bit_greyscale(intensity):
    '''
    Converts greyscale color to Psychopy RGB format which range is -1...1. Greyscale colors are interpreted in 0...255 range.
    '''    
    return convert_greyscale(float(intensity) / 255.0)

def convert_color(color):
    '''
    Any color format (rgb, greyscale, 8 bit grayscale) is converted to Psychopy rgb format
    '''
    if isinstance(color,  list) or isinstance(color, tuple):
        converted_color = convert_rgb(color)
    elif isinstance(color, float):
        converted_color = convert_greyscale(color)
    elif isinstance(color, int):
        converted_color = convert_8_bit_greyscale(color)
    else:
        converted_color = color
    return converted_color    

def convert_color_from_pp(color_pp):
    '''
    convert color from psychopy format to Presentinator default format (0...1 range)
    '''
    color = []
    for color_pp_channel in color_pp:
        color.append(0.5 * (color_pp_channel + 1.0))
    return color
    
def convert_int_color(color):
    '''
    Rgb color is converted to 8 bit rgb
    '''    
    if isinstance(color,  list):
        return (int(color[0] * 255.0),  int(color[1] * 255.0),  int(color[2] * 255.0))
    else:
        return (int(color * 255.0),  int(color * 255.0),  int(color * 255.0))

def calculate_circle_vertices(diameter,  resolution = 1.0,  start_angle = 0,  end_angle = 360, pos = (0,0),  arc_slice = False):
    '''
    Resolution is in steps / degree
    radius is a list of x and y
    '''
    output_list = False

    if output_list:
        vertices = []
    else:
        n_vertices_arc = (end_angle - start_angle) * resolution + 1
        if abs(start_angle - end_angle) < 360 and arc_slice:
            n_vertices = n_vertices_arc + 1
        else:
            n_vertices = n_vertices_arc
        vertices = numpy.zeros(shape = (n_vertices,  2))
        
    if output_list:
        for i in range(int(start_angle * resolution),  int(end_angle * resolution)):
                    angle = (float(i)*math.pi / 180.0) / resolution
                    vertice = [0.5 * diameter[0] * math.cos(angle) + pos[0],  0.5 * diameter[1] * math.sin(angle) + pos[1]]
                    vertices.append(vertice)
    else:
        start_angle_rad = start_angle * math.pi / 180.0
        end_angle_rad = end_angle * math.pi / 180.0
        angle = numpy.linspace(start_angle_rad,  end_angle_rad, n_vertices_arc)        
        x = 0.5 * diameter[0] * numpy.cos(angle) + pos[0]
        y = 0.5 * diameter[0] * numpy.sin(angle) + pos[1]
        vertices[0:n_vertices_arc, 0] = x
        vertices[0:n_vertices_arc, 1] = y      
    
    if abs(start_angle - end_angle) < 360:
        if output_list:
            if arc_slice:
                vertices.append([0,  0])
        else:
            if arc_slice:                
                vertices[-1] = numpy.array([0,  0])

    return vertices

def coordinate_system(type, SCREEN_RESOLUTION=None):
    '''looks up proper settings for commonly used coordinate system conventions'''
    if type=='ulcorner':
        if SCREEN_RESOLUTION == None: raise ValueError('Screen resolution is needed for converting to upper-left corner origo coordinate system.')
        ORIGO = cr((-0.5 * SCREEN_RESOLUTION['col'], 0.5 * SCREEN_RESOLUTION['row']))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'down'
    elif type=='center':
        ORIGO = cr((0, 0))
        HORIZONTAL_AXIS_POSITIVE_DIRECTION = 'right'
        VERTICAL_AXIS_POSITIVE_DIRECTION = 'up'
    else:
        raise ValueError('Coordinate system type '+type+' not recognized')
    return ORIGO, HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION
    
def generate_waveform(waveform_type,  n_sample,  period,  amplitude,  offset = 0,  phase = 0,  duty_cycle = 0.5):
    wave = []
    period = int(period) 
    for i in range(n_sample):
        if period == 0:
            value = 0
        elif waveform_type == 'sin':
            value = 0.5 * amplitude * math.sin(2 * math.pi * float(i) / period + phase * (math.pi/180.0)) + offset
        elif waveform_type == 'cos':
            value = 0.5 * amplitude * math.cos(2 * math.pi * float(i) / period + phase * (math.pi/180.0)) + offset            
        elif waveform_type == 'sqr':
            actual_phase = (i + int(period * (phase / 360.0))) % period
            if actual_phase < duty_cycle * period:
                value = 0.5 * amplitude
            else:
                value = -0.5 * amplitude
            value = value + offset
        elif waveform_type == 'saw':
            actual_phase = (i + int(period * (phase / 360.0))) % period
            value = amplitude * (float(actual_phase) / float(period-1.0)) - 0.5 * amplitude + offset
        elif waveform_type == 'tri':
            actual_phase = (i + int(period * (phase / 360.0))) % period
            if actual_phase < 0.5 * period:
                value = amplitude * (float(actual_phase) / float(0.5*period)) - 0.5 * amplitude + offset
            else:
                value = -amplitude * (float(actual_phase) / float(0.5 * period)) + 1.5 * amplitude + offset
        else:
            value = 0
        wave.append(value)    
    return wave            
    
def um_to_normalized_display(value, config):
    '''
    Converts um dimension data to normalized screen size where the screen range is between -1...1 for both axes and the origo is the center of the screen
    '''
    if not isinstance(value,  list):
        value = [value,  value]
    normalized_x = 2.0 * config.SCREEN_PIXEL_TO_UM_SCALE * float(value[0]) / config.SCREEN_RESOLUTION['col']
    normalized_y = 2.0 * config.SCREEN_PIXEL_TO_UM_SCALE * float(value[1]) / config.SCREEN_RESOLUTION['row']
    return [normalized_x,  normalized_y]

def random_colors(n,  frames = 1,  greyscale = False,  inital_seed = 0):
    '''
    Renerates random colors
    '''    
    random.seed(inital_seed)
    col = []
    if frames == 1:
        for i in range(n):
            r = random.random()
            g = random.random()
            b = random.random()
            if greyscale:
                g = r
                b = r
            col.append([r,g,b])
    else:
        
        for f in range(frames):
            c = []
            for i in range(n):
                r = random.random()
                g = random.random()
                b = random.random()
                if greyscale:
                    g = r
                    b = r
                c.append([r,g,b])
            col.append(c)
    return col
    
def read_text_file(path):
    f = open(path,  'rt')
    txt =  f.read(os.path.getsize(path))
    f.close()            
    return txt
    
def circle_to_numpy(diameter,  resolution = 1.0,  image_size = (100,  100),  color = 1.0,  pos = (0, 0)):
    '''
    diameter: diameter of circle in pixels
    resolution: angle resolution of drawing circle
    image_size: x, y size of image/numpy array in pixels
    color: color of circle, greyscale, range 0...1
    pos : x, y position in pixels, center is 0, 0
    '''
    vertices = calculate_circle_vertices([diameter,  diameter],  resolution)
    import Image,  ImageDraw,  numpy
    image = Image.new('L',  image_size,  0)
    draw = ImageDraw.Draw(image)
    
    vertices_int = []
    for i in vertices:
        vertices_int.append(int(i[0] + image_size[0] * 0.5) + pos[0])
        vertices_int.append(int(i[1] + image_size[1] * 0.5) - pos[1])
    
    
    draw.polygon(vertices_int,  fill = int(color * 255.0))    
    #just for debug
    image.show()
    print numpy.asarray(image)
    return numpy.asarray(image)

def retina2screen(widths, speed=None, config=None, option=None):
    '''converts microns on retina to cycles per pixel on screen
    '''
    if monitor['directly_onto_retina'] == 0:
        visualangles = um2degrees(widths) # 300um is 10 degrees
        #widthsonmonitor = tan(2*pi/360*visualangles)*monitor.distancefrom_mouseeye/monitor.pixelwidth #in pixels
        widthsonmonitor = numpy.pi/180*visualangles*monitor['distance_from_mouse_eye']/monitor['pixel_width'] #in pixels
        if not option is None and option=='pixels':
            return widthsonmonitor

        no_periods_onscreen = monitor['resolution']['width']/(widthsonmonitor*2)
        cyclesperpixel = no_periods_onscreen/monitor['resolution']['width']
        if speed is None:
            return cyclesperpixel
        else: # calculates cycles per second from width on retina and um per second on the retina
            onecycle_pix = 1/cyclesperpixel
            for i in range(len(widths)):
            # from micrometers/s on the retina to cycles per pixel on screen
                speedonmonitor[i] = numpy.pi/180*um2degrees(speed)*monitor['distancefrom_mouseeye']/monitor['pixelwidth']
                cyclespersecond[i] = speedonmonitor[i]/(widthsonmonitor[i]*2) # divide by period, i.e. width*2
                time4onecycle_onscreen[i] = (monitor['resolution']['width']/onecycle_pix[i])/cyclespersecond[i]
            return cyclesperpixel, time4onecycle_onscreen
    elif monitor['directlyonretina']==1:
        widthsonmonitor = widths/monitor['um2pixels']
        no_periods_onscreen = monitor['resolution']['width']/(widthsonmonitor*2)
        if speed is None:
            cyclesperpixel = no_periods_onscreen/monitor['resolution']['width']
            return cyclesperpixel
        else: # calculates cycles per second from width on retina and um per second on the retina
            cyclesperpixel = no_periods_onscreen/monitor['resolution']['width']
            onecycle_pix = 1/cyclesperpixel
            for i in range(len(widths)):
            # from micrometers/s on the retina to cycles per pixel on screen
                speedonmonitor[i]= speed/monitor.um2pixels
                cyclespersecond[i] = speedonmonitor[i]/(widthsonmonitor[i]*2) # divide by period, i.e. width*2
                time4onecycle_onscreen[i,:] = (widthsonmonitor[i]*2)/speedonmonitor[i]#cyclespersecond(i,:)
            return cyclespersecond, time4onecycle_onscreen

def um2degrees(umonretina):
# given umonretina estimates the visual angle, based on 300um on the retina
# is 10 degrees
    return 10.0*numpy.array(umonretina, numpy.float)/300

def filtered_file_list(folder_name,  filter):
    files = os.listdir(folder_name)
    filtered_files = []
    for file in files:
        if isinstance(filter,  list) or isinstance(filter,  tuple):
            found  = False
            for filter_item in filter:                
                if file.find(filter_item) != -1:
                    found = True
            if found:
                filtered_files.append(file)
        elif isinstance(filter,  str):
            if file.find(filter) != -1:
                    filtered_files.append(file)
    return filtered_files

def numpy_circle(diameter, center = (0,0), color = 1.0, array_size = (100, 100)):
    radius_sq = (diameter * 0.5) ** 2
    circle = numpy.ones(array_size)
    coords = numpy.nonzero(circle)
    distance_x = coords[0] - (center[0] + int(0.5 * array_size[0]))
    distance_y = coords[1] - (center[1] + int(0.5 * array_size[1]))
    
    distance_x = distance_x ** 2
    distance_y = distance_y ** 2
    distance = distance_x + distance_y
    active_pixel_mask = numpy.where(distance <= radius_sq, 1, 0)
    circle = circle * 0
    for i in range(len(active_pixel_mask)):
        if active_pixel_mask[i] == 1:
            circle[coords[0][i], coords[1][i]] = color
    return circle 
 
def arc_vertices(diameter, n_vertices,  angle,  angle_range,  pos = [0, 0]):
    if not isinstance(diameter,  list):
        diameter_list = [diameter, diameter]
    else:
        diameter_list = diameter   
    
    start_angle = (angle - 0.5 * angle_range)  * numpy.pi / 180.0
    end_angle = (angle + 0.5 * angle_range) * numpy.pi / 180.0
    angles = numpy.linspace(start_angle, end_angle,  n_vertices)
#    angles = angles[1:]
    vertices = numpy.zeros((angles.shape[0],  2))    
    vertices[:, 0] = 0.5 * numpy.cos(angles)
    vertices[:, 1] = 0.5 * numpy.sin(angles)
    return vertices * numpy.array(diameter_list) + numpy.array(pos)
    
def flip_screen(delay):
    import pygame
    time.sleep(delay)
    pygame.display.flip()
    
def text_to_screen(text,  position = (0, 0),  color = [1.0,  1.0,  1.0]):
    glColor3fv(color)
    for i in range(len(text)):
        glRasterPos2f(position[0] + 0.01 * i, position[1])
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(text[i]))

def find_files_and_folders(start_path,  extension = None):
        '''
        Finds all folders and files. With extension the files can be filtered
        '''
        directories = []
        all_files  = []
        directories = []
        for root, dirs, files in os.walk(start_path):            
            for dir in dirs:
                directories.append(root + os.sep + dir)
            for file in files:
                if extension != None:
                    if file.split('.')[1] == extension:
                        all_files.append(root + os.sep + file)
                else:
                    all_files.append(root + os.sep + file)    
        return directories, all_files
        
def find_class_in_module(modules,  class_name, module_name_with_hierarchy = False):
    '''
    Finds the module where a certain class declaration resides
    '''
    module_found = None
    class_declaration_strings = ['class ' + class_name,  'class  ' + class_name]
    for module in modules:
         module_content = read_text_file(module)
         for class_declaration_string in class_declaration_strings:
            if module_content.find(class_declaration_string) != -1:
                if module_name_with_hierarchy:
                    items = module.split(os.sep)                    
                    module_found = ''
                    for item in items:
                        stripped_from_extension = item.replace('.py', '')                        
                        if stripped_from_extension.replace('_', '').isalnum():
                            module_found = module_found + '.' + stripped_from_extension
                    module_found = module_found[1:]
                else:
                    module_found = module.split(os.sep)[-1].split('.')[0]
    return module_found
    
def prepare_dynamic_class_instantiation(modules,  class_name):        
    """
    Imports the necessary module and returns a reference to the class that could be sued for instantiation
    """
    #import experiment class
    module_name = find_class_in_module(modules, class_name,  module_name_with_hierarchy = True)
    __import__(module_name)
    #get referece to class and return with it
    return getattr(sys.modules[module_name], class_name)

def rc(raw):
    return rc_pack(raw, order = 'rc')

def cr(raw):
    return rc_pack(raw, order = 'cr')    
            
def rc_pack(raw, order = 'rc'):
    if order == 'rc':
        index_first = 1
        index_second = 0
    elif order == 'cr':
        index_first = 0
        index_second = 1    
    if isinstance(raw, numpy.ndarray):
        #input is a numpy array
        if raw.dtype == numpy.float:
            return numpy.array(zip(raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.float32,numpy.float32]})
        else:
            return numpy.array(zip(raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.int16,numpy.int16]})
    else:
        #input is a tuple
        if isinstance(raw[0], float):
            return numpy.array((raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.float32,numpy.float32]})
        else:
            return numpy.array((raw[index_first], raw[index_second]),dtype={'names':['col','row'],'formats':[numpy.int16,numpy.int16]})

def rc_add(operand1, operand2):
    '''
    supported inputs:
    - single rc + single rc
    - array of rc + array of rc
    - single rc + array of rc
    - array of rc + single rc
    (- constant + single rc
    - constant + array of rc)
    '''
    if isinstance(operand1, numpy.ndarray) and (isinstance(operand2, numpy.ndarray)):
        if operand1.shape == () and operand2.shape == ():
            return rc((operand1['row'] + operand2['row'], operand1['col'] + operand2['col']))
        elif operand1.shape != () and operand2.shape != ():
            rows = operand1[:]['row'] + operand2[:]['row']
            cols = operand1[:]['col'] + operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape == () and operand2.shape != ():
            rows = operand1['row'] + operand2[:]['row']
            cols = operand1['col'] + operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape != () and operand2.shape == ():
            rows = operand1[:]['row'] + operand2['row']
            cols = operand1[:]['col'] + operand2['col']
            return rc(numpy.array([rows, cols]))
    
    
def rc_multiply(operand1, operand2):
    if isinstance(operand1, numpy.ndarray) and (isinstance(operand2, numpy.ndarray)):
        if operand1.shape == () and operand2.shape == ():
            return rc((operand1['row'] * operand2['row'], operand1['col'] * operand2['col']))
        elif operand1.shape != () and operand2.shape != ():
            rows = operand1[:]['row'] * operand2[:]['row']
            cols = operand1[:]['col'] * operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape == () and operand2.shape != ():
            rows = operand1['row'] * operand2[:]['row']
            cols = operand1['col'] * operand2[:]['col']
            return rc(numpy.array([rows, cols]))
        elif operand1.shape != () and operand2.shape == ():
            rows = operand1[:]['row'] * operand2['row']
            cols = operand1[:]['col'] * operand2['col']
            return rc(numpy.array([rows, cols]))    

def rc_multiply_with_constant(rc_value, constant):
    if rc_value.shape == ():
            return rc((rc_value['row'] * constant, rc_value['col'] * constant))
    else:
            rows = rc_value[:]['row'] * constant
            cols = rc_value[:]['col'] * constant
            return rc(numpy.array([rows, cols]))
    
def coordinate_transform(coordinates, origo, horizontal_axis_positive_direction, vertical_axis_positive_direction):
    '''
    Transforms coordinates to the native coordinate system of visual stimulation software where the origo is in the center of the screen 
    and the positive directions of on the axis's are up and right
    -1 or 2 d numpy arrays where each item of the array is in row,column format
    '''    
    if horizontal_axis_positive_direction == 'right':
        horizontal_axis_positive_direction_ = 1
    elif horizontal_axis_positive_direction == 'left':
        horizontal_axis_positive_direction_ = -1
    if vertical_axis_positive_direction == 'up':
        vertical_axis_positive_direction_ = 1
    elif vertical_axis_positive_direction == 'down':
        vertical_axis_positive_direction_ = -1
    axis_direction = rc((vertical_axis_positive_direction_, horizontal_axis_positive_direction_))    
    return rc_add(rc_multiply(axis_direction, coordinates), origo)

def coordinate_transform_single_point(point, origo, axis_direction):
    '''
    axis_direction: row-column format, row - y axis, column - x axis
    '''
    x = float(origo['col']) + float(axis_direction['col']) * float(point['col'])
    y = float(origo['row']) + float(axis_direction['row']) * float(point['row'])
    if isinstance(point['row'], int):
        x = int(x)
        y = int(y)
    return rc((y, x))

class testCoordinateTransformation(unittest.TestCase):
    pass

if __name__ == "__main__":
#    unittest.main()
    a = [1.0, 2.0, 3.0]
    b = [10.0, 20.0, 30.0]
    c = rc(numpy.array([a, b]))    
#    p = coordinate_transform_single_point(rc((0.0, 1.0)), rc((100.0, -100.0)), rc((-1, 1)) )
#    print p['row']
#    print p['col']

#    print rc_multiply(rc((2, 0)), rc((1, 1)))
#    print rc_multiply(rc(numpy.array([a, b])), rc((0, -10)))
#    print rc_multiply(rc(numpy.array([a, b])), rc(numpy.array([a, b])))
#    print a[:]['row']

#    res = coordinate_transform(cr((100, 100)), cr((-100, 100)), 'right', 'down')
#    print res['col'], res['row']
    
    cols = [0,  100, -100]
    rows = [0,  100, 100]
    coords = cr(numpy.array([cols, rows]))    
    print coords.shape
    res = coordinate_transform(coords, cr((-100, 100)), 'right', 'down')    
#    print res
    print rc_multiply_with_constant(c, 10)
    a = numpy.zeros((3, coords.shape[0]))
    a[0][0] = coords[1]['row']
    
    print a
    
    
