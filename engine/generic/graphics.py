import time
import numpy
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import pygame
import Image

class Screen(object):
    """
    Use cases:
    - Standalone, interactive applications with animation
    - Visual stimulation with external control loop
    - Generating single frame (for development purposes)
    
    Functionalities:
    - Maintain and watch frame rate
    - Helper functions: display text, image
    - 
    """
    def __init__(self, configuration, graphics_mode = 'single_frame'):
        """
        The following actions are performed:
        (- Calculates pixel scaling parameters based on coordinate system type)
        - Creates screen
        - Set background color
        - Scales screen
        
        graphics_mode:
        - standalone - interactive, standalone grpahics applications
        - external - control loop is implemented externally. flip has to be called separately
        - single_frame - shows a single frame while key is pressed or for a certain time
        
        Expected configurations:
        - SCREEN_RESOLUTION
        - FULLSCREEN
        - SCREEN_EXPECTED_FRAME_RATE
        - BACKGROUND_COLOR
        - FRAME_WAIT_FACTOR
        - COORDINATE_SYSTEM
        or
        - ORIGO
        - HORIZONTAL_AXIS_POSITIVE_DIRECTION
        - VERTICAL_AXIS_POSITIVE_DIRECTION        
        
        
        Future: GAMMA, TEXT_COLOR
        """
        self.config = configuration
        self.mode = graphics_mode
        self.position = [0.0, 0.0, 0.0]
        self.heading = 0.0
        self.roll = 0.0
        self.pitch = 0.0
        self.position_step = 10.0
        self.angle_step = 10.0
        self.flip_time = time.time()
        self.flip_time_previous = self.flip_time
        self.frame_rate = 0.0
        self.wait_time_left = 0.0
        self.elapsed_time = 0.0        
        #frame wait time calculation
        self.frame_wait_time = self.config.FRAME_WAIT_FACTOR * 1.0 / self.config.SCREEN_EXPECTED_FRAME_RATE - self.config.FLIP_EXECUTION_TIME        
        glutInit()
        #create screen using parameters in config
        self.create_screen()
        #setting background color to clear color
        glClearColor(self.config.BACKGROUND_COLOR[0], self.config.BACKGROUND_COLOR[1], self.config.BACKGROUND_COLOR[2], 0.0)
        glEnable(GL_DEPTH_TEST)
        
        self.scale_screen()
        
        self.initialization()
        
    def create_screen(self):
        '''
        Create pygame screen using SCREEN_RESOLUTION and FULLSCREEN parameters
        '''
        flags = pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.OPENGL
        if self.config.FULLSCREEN:
            flags = flags | pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row']), flags)
        
    def close_screen(self):
        pygame.quit()
        
    def __del__(self):
        self.close_screen()
        
    def run(self):
        """
        Main loop for updating screen.
        """        
        if self.mode == 'single_frame':
            self.set_viewpoint(self.position,  self.heading,  self.roll, self.pitch)
            glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.draw_scene()
            self.flip()
            wait = True
            while wait:
                for event in pygame.event.get():
                    if event.type == 5 or event.type == 6:
                        wait = False
        elif self.mode == 'standalone':
            run_loop = True
            while run_loop:
                glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

                #default view is set
                self.set_view((0, 0, 0),  0, 0, 0)
                #glDisable(GL_LIGHTING) if light is enabled               
                self.render_before_set_view()
                self.set_view(self.position,  self.heading,  self.roll, self.pitch)
                self.draw_scene()
                self.flip()
                for event in pygame.event.get():
                    if event.type == 5 or event.type == 6:
                        run_loop = False
                    if event.type == pygame.KEYDOWN:
                        key_pressed = pygame.key.name(event.key)
                        if key_pressed == 'escape':
                            run_loop = False
                        self.keyboard_handler(key_pressed)
        elif self.mode == 'external':
            pass
    
    def flip(self):
        '''
        Flips screen buffers in a timed way to maintain expected frame rate. before_flip and after_flip are placeholders for user specific functions that should 
        be executed synchronized to flipping
        self.frame_rate is calculated here. Wait time before flip is calculated by considering elapsed time since last flip and frame_wait_time that describes the 
        required frame rate
        '''
        self.before_flip()
        self.elapsed_time = time.time() - self.flip_time_previous
        self.wait_time_left = self.frame_wait_time - self.elapsed_time
        if self.wait_time_left > 0.0:
            time.sleep(self.wait_time_left)
        pygame.display.flip()
        self.flip_time = time.time()
        self.frame_rate = 1.0 / (self.flip_time - self.flip_time_previous)
        self.after_flip()
        self.flip_time_previous = self.flip_time
        
    def scale_screen(self):
        '''
        Set projection matrix according to HORIZONTAL_AXIS_POSITIVE_DIRECTION, VERTICAL_AXIS_POSITIVE_DIRECTION parameters.
        Set viewport according to screen resolution and origo.
        
        !!! Only orthographic projection is supported this time !!!
        '''
        glMatrixMode (GL_PROJECTION)
        glLoadIdentity()
        left = -0.5 * self.config.SCREEN_RESOLUTION['col']
        right = 0.5 * self.config.SCREEN_RESOLUTION['col']
        bottom = 0.5 * self.config.SCREEN_RESOLUTION['row']
        top = -0.5 * self.config.SCREEN_RESOLUTION['row']
        if self.config.HORIZONTAL_AXIS_POSITIVE_DIRECTION == 'left':
            left = left * -1.0
            right = right * -1.0
        if self.config.VERTICAL_AXIS_POSITIVE_DIRECTION == 'up':
            top = top * -1.0
            bottom = bottom * -1.0
        z_range = max(self.config.SCREEN_RESOLUTION['row'], self.config.SCREEN_RESOLUTION['col'])
        glOrtho(left, right, bottom, top,  -z_range, z_range)
        
        #set viewport according to ORIGO parameter
        lower_left_corner_x = self.config.ORIGO['col']
        lower_left_corner_y = self.config.ORIGO['row']
        glViewport(lower_left_corner_x, lower_left_corner_y, self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row'])
        
    def clear_screen(self, color = (0.0, 0.0, 0.0, 0.0)):
        #clears screen to color
        glClearColor(color[0], color[1], color[2], 0.0)
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)        
        
    def set_view(self, position,  heading,  roll, pitch):
        '''
        Sets viewing by translating and rotating model.
        '''        
        glMatrixMode (GL_MODELVIEW)
        glLoadIdentity()
        glRotatef(roll,  0.0, 0.0, 1.0)
        glRotatef(pitch, 1.0, 0.0, 0.0)
        glRotatef(heading, 0.0, 1.0, 0.0)
        glTranslatef(position[0],  position[1],  position[2])
        
    def initialization(self):
        pass
        
    def render_text(self, text, color = (1.0,  1.0,  1.0), position = (0.0, 0.0)):
        '''
        Renders text on screen using times new roman characters. Spacing is a constant 12 pixels, so shorter characters like 'l' is diplayed with a little gap
        '''
        glColor3fv(color)
        for i in range(len(text)):
            glRasterPos2f(position[0] + 12 * i, position[1])
            glutBitmapCharacter(GLUT_BITMAP_TIMES_ROMAN_24, ord(text[i]))
        
    def render_imagefile(self, path, position = (0, 0)):
        '''
        Renders an image file on screen with its original size.
        '''
        im = Image.open(path)
        im = im.convert('RGBX')
        self.image_size = im.size
        ix, iy, image = im.size[0], im.size[1], im.tostring('raw', 'RGBX', 0, -1)
        self.image_texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.image_texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glTexImage2D(GL_TEXTURE_2D, 0, 3, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, image)

        glEnable(GL_TEXTURE_2D)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        glBindTexture(GL_TEXTURE_2D, self.image_texture_id)
        glColor3fv((1.0, 1.0, 1.0))
        texture_coordinates = numpy.array(
                             [
                             [1.0, 1.0],
                             [1.0, 0.0],
                             [0.0, 0.0],
                             [0.0, 1.0],
                             ])
        vertices = numpy.array([
                                [position[0] + 0.5 * self.image_size[0], position[1] + 0.5 * self.image_size[1]], 
                                [position[0] + 0.5 * self.image_size[0], position[1] - 0.5 * self.image_size[1]], 
                                [position[0] - 0.5 * self.image_size[0], position[1] - 0.5 * self.image_size[1]], 
                                [position[0] - 0.5 * self.image_size[0], position[1] + 0.5 * self.image_size[1]],                                 
                                ])
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
        glTexCoordPointerf(texture_coordinates)
        glEnableClientState(GL_VERTEX_ARRAY)
        glVertexPointerf(vertices)
        glDrawArrays(GL_POLYGON, 0, 4)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisable(GL_TEXTURE_2D)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        
    def create_texture(self):
        pass
        
    def save_frame(self, path):
        '''
        Saves actual frame in frame buffer to an image file
        '''
        pixels = glReadPixels(0, 0, self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row'],  GL_RGB, GL_UNSIGNED_BYTE)
        Image.fromstring('RGB', (self.config.SCREEN_RESOLUTION['col'], self.config.SCREEN_RESOLUTION['row']), pixels).save(path)        
        
    #Placeholder functions that user can overdefine
    def render_before_set_view(self):        
        #placeholder for graphics items that shall not be translated or rotated by user when viewport is adjusted
        pass
        
    def before_flip(self):
        pass
        
    def after_flip(self):
        pass
    
    def draw_scene(self):
        pass
        
    #Additional helper functions
    def print_viewing_parameters(self):
        print self.position,  self.heading,  self.roll, self.pitch
        
    def keyboard_handler(self, key_pressed):
        '''
        Watches keyboard and modifies position, heading, roll and pitch of model
        '''        
        if key_pressed == 'up':
            self.position[1] = self.position[1] + self.position_step
        elif key_pressed == 'down':
            self.position[1] = self.position[1] - self.position_step
        if key_pressed == 'right':
            self.position[0] = self.position[0] + self.position_step
        elif key_pressed == 'left':
            self.position[0] = self.position[0] - self.position_step
        elif key_pressed == 'page up':
            self.position[2] = self.position[2] + self.position_step
        elif key_pressed == 'page down':
            self.position[2] = self.position[2] - self.position_step
        elif key_pressed == 'q':
            self.heading = self.heading + self.angle_step
        elif key_pressed == 'w':
            self.heading = self.heading - self.angle_step
        elif key_pressed == 'a':
            self.roll = self.roll + self.angle_step
        elif key_pressed == 's':
            self.roll = self.roll - self.angle_step
        elif key_pressed == 'z':
            self.pitch = self.pitch + self.angle_step
        elif key_pressed == 'x':
            self.pitch = self.pitch - self.angle_step
        
if __name__ == "__main__": 
    pass
    
