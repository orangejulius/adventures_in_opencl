#from OpenGL.GL import GL_ARRAY_BUFFER, GL_DYNAMIC_DRAW, glFlush, glGenBuffers, glBindBuffer
from OpenGL.GL import *
from OpenGL.arrays import vbo

import numpy
import pyopencl as cl

from initialize import timings       

class Wave:
    def __init__(self, dt, dx, ntracers, params):
        self.clinit()
        self.loadProgram("wave.cl")
        
        self.dt = dt
        self.dx = dx
        self.num = params[0]
        self.ntracers = ntracers 
        self.params = params[1:]
         
    
    @timings
    def execute(self, subintervals):

        dt = numpy.float32(self.dt)
        dx = numpy.float32(self.dx)
        ntracers = numpy.int32(self.ntracers)
        num = numpy.int32(self.num)
        choice = numpy.int32(self.params[0])#choice)
        k = numpy.float32(self.params[1])#k)
        ymin = numpy.float32(self.params[2])#ymin)
        ymax = numpy.float32(self.params[3])#ymax)
        """
        print "in execute, num", self.num
        print "tracers", self.ntracers
        print "choice", choice
        print "k", k
        print "ymin", ymin
        print "ymax", ymax
        print "dt", dt
        print "dx", dx
        """
                
        cl.enqueue_acquire_gl_objects(self.queue, self.gl_objects)

        global_size = (self.num,)
        local_size = None

                
        kernelargs = (self.pos_cl, 
                      self.col_cl, 
                      self.pos_gen_cl, 
                      ntracers,
                      choice,
                      num,
                      k,
                      ymin,
                      ymax,
                      dt,
                      dx
                      )

               
        for i in xrange(0, subintervals):
            self.program.wave(self.queue, global_size, local_size, *(kernelargs))

        cl.enqueue_release_gl_objects(self.queue, self.gl_objects)
        self.queue.finish()
 


    def loadData(self, pos_vbo, col_vbo):
        import pyopencl as cl
        mf = cl.mem_flags
        self.pos_vbo = pos_vbo
        self.col_vbo = col_vbo

        self.pos = pos_vbo.data
        self.col = col_vbo.data

        #Setup vertex buffer objects and share them with OpenCL as GLBuffers
        self.pos_vbo.bind()
        self.pos_cl = cl.GLBuffer(self.ctx, mf.READ_WRITE, int(self.pos_vbo.buffers[0]))
        self.col_vbo.bind()
        self.col_cl = cl.GLBuffer(self.ctx, mf.READ_WRITE, int(self.col_vbo.buffers[0]))

        #pure OpenCL arrays
        self.pos_gen_cl = cl.Buffer(self.ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=self.pos)
        self.queue.finish()

        # set up the list of GL objects to share with opencl
        self.gl_objects = [self.pos_cl, self.col_cl]
 
 
    def clinit(self):
        plats = cl.get_platforms()
        from pyopencl.tools import get_gl_sharing_context_properties
        import sys 
        if sys.platform == "darwin":
            self.ctx = cl.Context(properties=get_gl_sharing_context_properties(),
                             devices=[])
        else:
            self.ctx = cl.Context(properties=[
                (cl.context_properties.PLATFORM, plats[0])]
                + get_gl_sharing_context_properties(), devices=None)
                
        self.queue = cl.CommandQueue(self.ctx)

    def loadProgram(self, filename):
        #read in the OpenCL source file as a string
        f = open(filename, 'r')
        fstr = "".join(f.readlines())
        #print fstr
        #create the program
        self.program = cl.Program(self.ctx, fstr).build()



    def render(self):


        #glColor3f(1,0,0)
        glEnable(GL_POINT_SMOOTH)
        glPointSize(5)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_DEPTH_TEST)

        """
        glColor3f(1., 0, 0)
        glBegin(GL_POINTS)
        for p in self.pos_vbo.data:
            glVertex3f(p[0], p[1], p[2])

        glEnd()
        """

        self.col_vbo.bind()
        glColorPointer(4, GL_FLOAT, 0, self.col_vbo)

        self.pos_vbo.bind()
        glVertexPointer(4, GL_FLOAT, 0, self.pos_vbo)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glDrawArrays(GL_POINTS, 0, self.num*self.ntracers)

        glDisableClientState(GL_COLOR_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)

