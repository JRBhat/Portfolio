import os
from past.utils import old_div
import logging
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
try:
    from pycuda.compiler import SourceModule, compile
    from pycuda.driver import CompileError
    import pycuda.driver as drv
    import pycuda.gpuarray as gpuarray
    from pycuda.elementwise import ElementwiseKernel
    from pycuda.tools import PageLockedMemoryPool
except ImportError as inst:
    LOGGER.debug("Error %s" % inst)
import numpy as np

try:
    import pycuda.autoinit
except Exception as inst:
    LOGGER.debug("Error %s" % inst)


class Singleton(object):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class convertToLab(Singleton):
    """
    XYZ to lab CUDA functions
    --------------------------
    TODO: refactoring for mode='CUDA','NP','ColorMath','fastest','OpenCL'
    """
    #def whitepoint d65
    whitePointD65 = (0.95043, 1.0, 1.0889)
    XYZTosRGBMatrix = np.matrix([[3.2406, -1.5372, -0.4986],[-0.9689, 1.8758, 0.0415],[0.0557, -0.2040, 1.0570]], np.float32)
    sRGBToXYZMatrix = XYZTosRGBMatrix.I
    XYZToAdobeMatrix = np.matrix([[2.04159, -0.56501, -0.34473],[-0.96924, 1.87597, 0.04156],[0.01344, -0.11836, 1.01517]],np.float32)
    adobeToXYZAdobeMatrix = XYZToAdobeMatrix.I
    cuda_block = (512, 1, 1)
    kernel_directory = None
    cuda_version = None
    compiler_exists = False
    cuda_version_list = dict([(vers, dict([('name', '%d_%d' % (vers[0], vers[1])), ('arch', 'compute_%d%d' % (vers[0], 0 if vers[0] >= 2 else vers[1])), ('code', 'sm_%d%d' % (vers[0], vers[1]))])) for vers in [(2,0), (2,1),(3,0), (4,0),(5,0),(6,0), (6,1)]])#sorted(study_data)[:10]

    def create_cuda_code(self, do_local_compile=False, do_compile_version=None):
        cuda_code_xyz_to_lab = """
        __global__ void doXYZNorm(float3 *xyz, float3 *xyzNorm, float Xn, float Yn, float Zn)
        {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            xyzNorm[i].x=xyz[i].x/Xn;
            xyzNorm[i].y=xyz[i].y/Yn;
            xyzNorm[i].z=xyz[i].z/Zn;
        }
        __global__ void doSqrtXYZToLab(float3 *xyz, float3 *lab)
        {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            lab[i].x=116.0*xyz[i].y-16.0;
            lab[i].y=500*(xyz[i].x-xyz[i].y);
            lab[i].z=200*(xyz[i].y-xyz[i].z);
        }
        __global__ void doXYZNormInPlace(float3 *xyz, float Xn, float Yn, float Zn)
        {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            xyz[i].x=xyz[i].x/Xn;
            xyz[i].y=xyz[i].y/Yn;
            xyz[i].z=xyz[i].z/Zn;
        }
        __global__ void doXYZNormInverseInPlace(float3 *xyz, float Xn, float Yn, float Zn)
        {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            xyz[i].x=xyz[i].x*Xn;
            xyz[i].y=xyz[i].y*Yn;
            xyz[i].z=xyz[i].z*Zn;
        }
        __global__ void doSqrtXYZToLabInPlace(float3 *xyz)
        {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            float l=116.0*xyz[i].y-16.0;
            float a=500*(xyz[i].x-xyz[i].y);
            float b=200*(xyz[i].y-xyz[i].z);
            xyz[i].x=l;
            xyz[i].y=a;
            xyz[i].z=b;
        }
        __global__ void doLabToSqrtXYZInPlace(float3 *lab)
        {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            float y=(lab[i].x+16.0)/116.0;
            float x=y+lab[i].y/500.0;
            float z=y-lab[i].z/200.0;
            lab[i].x=x;
            lab[i].y=y;
            lab[i].z=z;
        }
        """
        cuda_code_matrix_col = """
        __global__ void doMultiplyColMatrix(float3 *rgb, float3 *xyz, float convMatrix0, float convMatrix1, float convMatrix2, float convMatrix3, float convMatrix4, float convMatrix5, float convMatrix6, float convMatrix7, float convMatrix8)
        {
          const int i= threadIdx.x+ blockIdx.x* blockDim.x;
          xyz[i].x=rgb[i].x * convMatrix0 + rgb[i].y * convMatrix1 + rgb[i].z * convMatrix2;
          xyz[i].y=rgb[i].x * convMatrix3 + rgb[i].y * convMatrix4 + rgb[i].z * convMatrix5;
          xyz[i].z=rgb[i].x * convMatrix6 + rgb[i].y * convMatrix7 + rgb[i].z * convMatrix8;
        }
        __global__ void doMultiplyColMatrixInPlace(float3 *rgb, float convMatrix0, float convMatrix1, float convMatrix2, float convMatrix3, float convMatrix4, float convMatrix5, float convMatrix6, float convMatrix7, float convMatrix8)
        {
          const int i= threadIdx.x+ blockIdx.x* blockDim.x;
          float r=rgb[i].x * convMatrix0 + rgb[i].y * convMatrix1 + rgb[i].z * convMatrix2;
          float g=rgb[i].x * convMatrix3 + rgb[i].y * convMatrix4 + rgb[i].z * convMatrix5;
          float b=rgb[i].x * convMatrix6 + rgb[i].y * convMatrix7 + rgb[i].z * convMatrix8;
          rgb[i].x=r;
          rgb[i].y=g;
          rgb[i].z=b;
        }
        """
        cuda_code_rgb_to_hsv = """
        __device__ float3 convert_one_pixel_to_hsv(float3 pixel) {
            float r, g, b;   
            float h, s, v;
            r = (float) pixel.x;
            g = (float) pixel.y;
            b = (float) pixel.z;
            float max = fmax(r, fmax(g, b));
            float min = fmin(r, fmin(g, b));
            float diff = max - min;
            v = max;
            if(v == 0.0f) { // black
                h = s = 0.0f;
            } else {
                s = diff / v;
                if(diff < 0.001f) { // grey
                    h = 0.0f;
                } else { // color
                    if(max == r) {
                        h = 60.0f * (g - b)/diff;
                        if(h < 0.0f) { h += 360.0f; }
                    } else if(max == g) {
                        h = 60.0f * (2 + (b - r)/diff);
                    } else {
                        h = 60.0f * (4 + (r - g)/diff);
                    }
                }	
            }
            float3 ret;
            ret.x=h;
            ret.y=s;
            ret.z=v;
            return ret;
        }        
        __global__ void convert_to_hsv(float3 *rgb) {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            float3 rgb_pixel = rgb[i];
            float3 hsv_pixel = convert_one_pixel_to_hsv(rgb_pixel);
            rgb[i] = hsv_pixel;
        }
        __device__ float3 convert_one_pixel_to_rgb(float3 pixel) {
	        float r, g, b;
	        float h, s, v;
	        h = pixel.x;
	        s = pixel.y;
	        v = pixel.z;
	        float f = h/60.0f;
	        float hi = floorf(f);
	        f = f - hi;
	        float p = v * (1 - s);
	        float q = v * (1 - s * f);
	        float t = v * (1 - s * (1 - f));
	        if(hi == 0.0f || hi == 6.0f) {
		        r = v;
		        g = t;
		        b = p;
	        } else if(hi == 1.0f) {
		        r = q;
		        g = v;
		        b = p;
	        } else if(hi == 2.0f) {
		        r = p;
		        g = v;
		        b = t;
	        } else if(hi == 3.0f) {
		        r = p;
		        g = q;
		        b = v;
	        } else if(hi == 4.0f) {
		        r = t;
		        g = p;
		        b = v;
	        } else {
		        r = v;
		        g = p;
		        b = q;
	        }
	        //unsigned char red = (unsigned char) __float2uint_rn(255.0f * r);
	        //unsigned char green = (unsigned char) __float2uint_rn(255.0f * g);
	        //unsigned char blue = (unsigned char) __float2uint_rn(255.0f * b);
	        //unsigned char alpha = (unsigned char) __float2uint_rn(pixel.w);
	        float3 ret;
            ret.x=r;
            ret.y=g;
            ret.z=b;
            return ret;
        }
        __global__ void convert_to_rgb(float3 *hsv) {
            const int i= threadIdx.x+ blockIdx.x* blockDim.x;
            float3 hsv_pixel = hsv[i];
            float3 rgb_pixel = convert_one_pixel_to_rgb(hsv_pixel);
            hsv[i] = rgb_pixel;
        }
        """
        code_cuda_elementwise = """
        __global__ void labSQRTInPlace(float *x, unsigned long long n)
        {
            unsigned tid = threadIdx.x;
            unsigned total_threads = gridDim.x*blockDim.x;
            unsigned cta_start = blockDim.x*blockIdx.x;
            unsigned i;
            for (i = cta_start + tid; i < n; i += total_threads)
            {
            (x[i]<0.008856451680)?(x[i]=(24389.0/27.0*x[i]+16.0)/116.0):(x[i]=powf(x[i],1.0/3.0));
            }
        }
        __global__ void labSQRTInverseInPlace(float *x, unsigned long long n)
        {
            unsigned tid = threadIdx.x;
            unsigned total_threads = gridDim.x*blockDim.x;
            unsigned cta_start = blockDim.x*blockIdx.x;
            unsigned i;
            for (i = cta_start + tid; i < n; i += total_threads)
            {
            (x[i]<0.206896552)?(x[i]=108.0*x[i]/841.0 - 432.0/24389.0):(x[i]=powf(x[i],3.0));
            }
        }
        __global__ void srgbGammaRemoveInPlace(float *x, unsigned long long n)
        {
            unsigned tid = threadIdx.x;
            unsigned total_threads = gridDim.x*blockDim.x;
            unsigned cta_start = blockDim.x*blockIdx.x;
            unsigned i;
            for (i = cta_start + tid; i < n; i += total_threads)
            {
            (x[i]<=0.04045)?(x[i]=x[i]/12.92):(x[i]=powf((x[i]+0.055)/1.055,2.4));
            }
        }
        __global__ void adobeGammaRemoveInPlace(float *x, unsigned long long n)
        {
            unsigned tid = threadIdx.x;
            unsigned total_threads = gridDim.x*blockDim.x;
            unsigned cta_start = blockDim.x*blockIdx.x;
            unsigned i;
            for (i = cta_start + tid; i < n; i += total_threads)
            {
            x[i]=powf(x[i], 2.0 + 51.0/256.0);
            }
        }
        __global__ void srgbGammaApplyInPlace(float *x, unsigned long long n)
        {
            unsigned tid = threadIdx.x;
            unsigned total_threads = gridDim.x*blockDim.x;
            unsigned cta_start = blockDim.x*blockIdx.x;
            unsigned i;
            for (i = cta_start + tid; i < n; i += total_threads)
            {
            (x[i]<=0.0031308)?(x[i]=x[i]*12.92):(x[i]=1.055*powf(x[i],1.0/2.4) - 0.055);
            }
        }
        __global__ void adobeGammaApplyInPlace(float *x, unsigned long long n)
        {
            unsigned tid = threadIdx.x;
            unsigned total_threads = gridDim.x*blockDim.x;
            unsigned cta_start = blockDim.x*blockIdx.x;
            unsigned i;
            for (i = cta_start + tid; i < n; i += total_threads)
            {
            x[i]=powf(x[i], 1.0/ (2.0 + 51.0/256.0));
            }
        }
"""
        code_definitions_dict = {'xyz_to_lab': cuda_code_xyz_to_lab, 'matrix_col': cuda_code_matrix_col, 'rgb_to_hsv':cuda_code_rgb_to_hsv, 'elementwise':code_cuda_elementwise}#, 'test':cuda_code_xyz_to_lab+cuda_code_matrix_col+cuda_code_rgb_to_hsv
        if do_local_compile:
            try:
               compile("")
            except CompileError as inst:
                LOGGER.error("Cannot compile CUDA code")
                LOGGER.error(inst)
                raise
            if do_compile_version is not None:
                for version in do_compile_version:
                    version_name = self.cuda_version_list[version]['name']
                    version_arch = self.cuda_version_list[version]['arch']
                    version_code = self.cuda_version_list[version]['code']
                    do_work=True
                    for code_file_name, cuda_code in list(code_definitions_dict.items()):
                        if not(do_work):
                            continue
                        LOGGER.debug("Compile & write %s" % ("%s_%s.cubin" % (code_file_name, version_name)))
                        try:
                            cuda_code_bin = compile(cuda_code, no_extern_c=int(False), arch=version_arch, code=version_code)
                            with open(os.path.join(self.kernel_directory, "%s_%s.cubin" % (code_file_name, version_name)), "wb") as f:
                                f.write(cuda_code_bin)
                        except Exception as inst:
                            del self.cuda_version_list[version]
                            do_work=False

            self.modXYZToLab = self.SourceModule(code_definitions_dict['xyz_to_lab'])
            self.modRGBToXYZ = self.SourceModule(code_definitions_dict['matrix_col'])
            self.modRGBToHSV = self.SourceModule(code_definitions_dict['rgb_to_hsv'])
            self.modElementwise = self.SourceModule(code_definitions_dict['elementwise'])
        else:
            version_name = self.cuda_version_list[self.cuda_version]['name']
            version_arch = self.cuda_version_list[self.cuda_version]['arch']
            version_code = self.cuda_version_list[self.cuda_version]['code']
            LOGGER.debug("Read %s" % os.path.join(self.kernel_directory, "%s_%s.cubin" % ('xyz_to_lab', version_name)))
            self.modXYZToLab = self.drv.module_from_file(os.path.join(self.kernel_directory, "%s_%s.cubin" % ('xyz_to_lab', version_name)))
            LOGGER.debug("Read %s" % os.path.join(self.kernel_directory, "%s_%s.cubin" % ('matrix_col', version_name)))
            self.modRGBToXYZ = self.drv.module_from_file(os.path.join(self.kernel_directory, "%s_%s.cubin" % ('matrix_col', version_name)))
            LOGGER.debug("Read %s" % (os.path.join(self.kernel_directory, "%s_%s.cubin" % ('rgb_to_hsv', version_name))))
            self.modRGBToHSV = self.drv.module_from_file(os.path.join(self.kernel_directory, "%s_%s.cubin" % ('rgb_to_hsv', version_name)))
            LOGGER.debug("Read %s" % (os.path.join(self.kernel_directory, "%s_%s.cubin" % ('elementwise', version_name))))
            self.modElementwise = self.drv.module_from_file(os.path.join(self.kernel_directory, "%s_%s.cubin" % ('elementwise', version_name)))
        self.rgbToHsv = self.modRGBToHSV.get_function("convert_to_hsv")#self.modRGBToHSV.get_function("convert_to_hsv")
        self.doXYZNormInPlace = self.modXYZToLab.get_function("doXYZNormInPlace")
        self.doXYZNormInverseInPlace = self.modXYZToLab.get_function("doXYZNormInverseInPlace")
        self.doSqrtXYZToLabInPlace = self.modXYZToLab.get_function("doSqrtXYZToLabInPlace")
        self.doLabToSqrtXYZInPlace = self.modXYZToLab.get_function("doLabToSqrtXYZInPlace")
        self.doColMatrixMultInPlace = self.modRGBToXYZ.get_function("doMultiplyColMatrixInPlace")
        
        self.labSQRTInPlace = self.modElementwise.get_function("labSQRTInPlace")

        self.labSQRTInverseInPlace = self.modElementwise.get_function("labSQRTInverseInPlace")
        
        self.srgbGammaRemoveInPlace = self.modElementwise.get_function("srgbGammaRemoveInPlace")

        self.adobeGammaRemoveInPlace = self.modElementwise.get_function("adobeGammaRemoveInPlace")
       
        self.srgbGammaApplyInPlace = self.modElementwise.get_function("srgbGammaApplyInPlace")

        self.adobeGammaApplyInPlace = self.modElementwise.get_function("adobeGammaApplyInPlace")

    def dummy_test(self):
        """test for cuda functions
        """
        drv.init()
        LOGGER.debug("%d device(s) found." % drv.Device.count())
        for ordinal in range(drv.Device.count()):
            dev = drv.Device(ordinal)
            LOGGER.debug("Device #%d: %s" % (ordinal, dev.name()))
            LOGGER.debug(" Compute Capability: %d.%d" % dev.compute_capability())
            LOGGER.debug(" Total Memory: %s KB" % (dev.total_memory() // (1024)))
            atts = [(str(att), value)
                    for att, value in dev.get_attributes().items()]
            atts.sort()
            for att, value in atts:
                LOGGER.debug(" %s: %s" % (att, value))

    def __init__(self):
        """initialize cuda
        """
        LOGGER.debug("Init CUDA")
        LOGGER.debug("Init CUDA ElementwiseKernel")
        LOGGER.debug("Init CUDA pycuda.autoinit")
        try:
            LOGGER.debug("Init CUDA import pycuda.driver as drv")
        except Exception as inst:
            LOGGER.debug("Error %s" % inst)
            LOGGER.debug("Init CUDA import pycuda.gpuarray as gpuarray")
        self.SourceModule = SourceModule
        self.ElementwiseKernel = ElementwiseKernel
        self.drv = drv
        self.gpuarray = gpuarray
        LOGGER.debug("Init CUDA self.cuda_version = drv.Device(0).compute_capability()")
        try:
            self.cuda_version = drv.Device(0).compute_capability()
            LOGGER.debug("Init CUDA device Version %s" % str(drv.Device(0).compute_capability()))
            (free,total) = drv.mem_get_info()
            LOGGER.debug("Init CUDA device: Memory: (%d, %d)" % (free,total))
        except Exception as inst:
            LOGGER.debug("Error %s" % inst)
            LOGGER.debug("Init CUDA import pycuda.gpuarray as gpuarray")
        self.compiler_exists = True
        from .Util import main_is_frozen
        if main_is_frozen():
                LOGGER.debug("main is frozen")
                self.compiler_exists = False
        if self.compiler_exists:
            try:
                compile("")
            except CompileError as inst:
                self.compiler_exists = False
                pass
            except Exception as inst:
                LOGGER.warning("Cuda compilation not working (not necessary)")
                LOGGER.debug(inst)
                self.compiler_exists = False
                pass
        self.cuda_version = drv.Device(0).compute_capability()
        from os import getcwd, path
        self.kernel_directory = path.join(getcwd(), 'cubin')
        from .Util import createDirectory
        createDirectory(self.kernel_directory)
        self.create_cuda_code(do_local_compile=self.compiler_exists, do_compile_version=list(self.cuda_version_list.keys()))#self.compiler_exists    
    
    def handle_data(func):
        """decorator for conversion functions, 

        :param func: function to decorate
        :type func: function
        """
        def wrapped_function(self, inData_numpy, whitePointRef=None):
            """

            :param inData_numpy: input array 
            :type inData_numpy: ndarray
            :param whitePointRef: define the color "white" in image, defaults to None
            :type whitePointRef: tupel, optional
            :return: convertet array
            :rtype: ndarray
            """
            if whitePointRef is None:
                whitePointRef = self.whitePointD65
            shape = inData_numpy.shape
            ttype = inData_numpy.dtype
            if np.issubdtype(ttype, int) and not ((ttype.type is np.uint8) or (ttype.type is np.uint16)):
                LOGGER.warning("Imagetype is integer but not uint8 or uint16!")
            if np.issubdtype(ttype, int) or (ttype.type is np.uint8) or (ttype.type is np.uint16):
                inData_numpy = old_div(inData_numpy.astype(np.float32), np.iinfo(ttype).max)
            inData_numpy = np.ascontiguousarray(inData_numpy.reshape(shape[0] * shape[1], shape[2]), np.float32)
            sz = inData_numpy.shape[0]
            (free,total) = self.drv.mem_get_info()
            LOGGER.debug("CUDA device: Memory: (%d, %d)" % (free,total))
            splits_needed = max(int(np.ceil(1.0 * sz * inData_numpy.shape[1] * 4 / free)), int(np.ceil(1.0 * sz / (self.cuda_block[0] * 65535))))
            out_data = np.zeros_like(inData_numpy)
            parts = np.unique((np.floor(np.linspace(0, np.ceil(old_div(sz, self.cuda_block[0])), splits_needed + 1)) * self.cuda_block[0]).astype(int))
            if len(parts) == 1:
                parts = np.array([parts[0], sz])
            else:
                parts[-1] = max(parts[-1], sz)
            for part_idx in range(splits_needed):
                part = slice(parts[part_idx], parts[part_idx + 1],1)
                ll = inData_numpy[part, :].shape
                if ll[0] % self.cuda_block[0] > 0:
                    pps = np.vstack([inData_numpy[part, :], np.zeros([self.cuda_block[0] - (ll[0] % self.cuda_block[0]), ll[1]], inData_numpy.dtype)])
                else:
                    pps = inData_numpy[part, :]
                out_data[part, :] = func(self, pps, whitePointRef)[:ll[0], ...]
            return out_data.reshape(shape)
        return wrapped_function

    @handle_data
    def xyzToLab(self, inData_numpy, whitePointRef=None):
        """converts an array XYZ to CIELAB using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)

        self.doXYZNormInPlace(in_arr, np.float32(whitePointRef[0]), np.float32(whitePointRef[1]), np.float32(whitePointRef[2]), block=self.cuda_block, grid=grid)
        self.labSQRTInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doSqrtXYZToLabInPlace(in_arr, block=self.cuda_block, grid=grid)

        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data

    @handle_data
    def sRGBToXYZ(self, inData_numpy, whitePointRef=None):
        """converts an array RGB to XYZ using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)

        self.srgbGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.sRGBToXYZMatrix[0, 0], self.sRGBToXYZMatrix[0, 1], self.sRGBToXYZMatrix[0, 2], self.sRGBToXYZMatrix[1, 0], self.sRGBToXYZMatrix[1, 1], self.sRGBToXYZMatrix[1, 2], self.sRGBToXYZMatrix[2, 0], self.sRGBToXYZMatrix[2, 1], self.sRGBToXYZMatrix[2, 2] , block=self.cuda_block, grid=grid)
 
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 
    
    @handle_data
    def norm_sRGBToXYZ(self, inData_numpy, whitePointRef=None):
        """converts an array from sRGB to XYZ using cuda(gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]), 1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.srgbGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

    @handle_data
    def sRGBToLab(self, inData_numpy, whitePointRef=None):
        """converts an array from sRGB to CIELAB using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.srgbGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.sRGBToXYZMatrix[0, 0], self.sRGBToXYZMatrix[0, 1], self.sRGBToXYZMatrix[0, 2], self.sRGBToXYZMatrix[1, 0], self.sRGBToXYZMatrix[1, 1], self.sRGBToXYZMatrix[1, 2], self.sRGBToXYZMatrix[2, 0], self.sRGBToXYZMatrix[2, 1], self.sRGBToXYZMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.doXYZNormInPlace(in_arr, np.float32(whitePointRef[0]), np.float32(whitePointRef[1]), np.float32(whitePointRef[2]), block=self.cuda_block, grid=grid)
        self.labSQRTInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doSqrtXYZToLabInPlace(in_arr, block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data

    
    @handle_data
    def adobeRGBToLab(self, inData_numpy, whitePointRef=None):
        """converts an array from adobe RGB to CIELAB using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div(sz, self.cuda_block[0]) + 1,1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.adobeGammaRemoveInPlace(in_arr, np.prod(in_arr.shape).astype(np.uint), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.adobeToXYZAdobeMatrix[0, 0], self.adobeToXYZAdobeMatrix[0, 1], self.adobeToXYZAdobeMatrix[0, 2], self.adobeToXYZAdobeMatrix[1, 0], self.adobeToXYZAdobeMatrix[1, 1], self.adobeToXYZAdobeMatrix[1, 2], self.adobeToXYZAdobeMatrix[2, 0], self.adobeToXYZAdobeMatrix[2, 1], self.adobeToXYZAdobeMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.doXYZNormInPlace(in_arr, np.float32(whitePointRef[0]), np.float32(whitePointRef[1]), np.float32(whitePointRef[2]), block=self.cuda_block, grid=grid)
        self.labSQRTInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doSqrtXYZToLabInPlace(in_arr, block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 


    @handle_data
    def adobeRGBToXYZ(self, inData_numpy, whitePointRef=None):
        """converts an array from adobe RGB to XYZ using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div(sz, self.cuda_block[0]) + 1,1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.adobeGammaRemoveInPlace(in_arr, np.prod(in_arr.shape).astype(np.uint), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.adobeToXYZAdobeMatrix[0, 0], self.adobeToXYZAdobeMatrix[0, 1], self.adobeToXYZAdobeMatrix[0, 2], self.adobeToXYZAdobeMatrix[1, 0], self.adobeToXYZAdobeMatrix[1, 1], self.adobeToXYZAdobeMatrix[1, 2], self.adobeToXYZAdobeMatrix[2, 0], self.adobeToXYZAdobeMatrix[2, 1], self.adobeToXYZAdobeMatrix[2, 2] , block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

    @handle_data
    def adobeRGBTosRGB(self, inData_numpy, whitePointRef=None):
        """converts an array from adobe RGB to sRGB using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.adobeGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.adobeToXYZAdobeMatrix[0, 0], self.adobeToXYZAdobeMatrix[0, 1], self.adobeToXYZAdobeMatrix[0, 2], self.adobeToXYZAdobeMatrix[1, 0], self.adobeToXYZAdobeMatrix[1, 1], self.adobeToXYZAdobeMatrix[1, 2], self.adobeToXYZAdobeMatrix[2, 0], self.adobeToXYZAdobeMatrix[2, 1], self.adobeToXYZAdobeMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.XYZTosRGBMatrix[0, 0], self.XYZTosRGBMatrix[0, 1], self.XYZTosRGBMatrix[0, 2], self.XYZTosRGBMatrix[1, 0], self.XYZTosRGBMatrix[1, 1], self.XYZTosRGBMatrix[1, 2], self.XYZTosRGBMatrix[2, 0], self.XYZTosRGBMatrix[2, 1], self.XYZTosRGBMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.srgbGammaApplyInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

    @handle_data
    def adobeRGBToNormSRGB(self, inData_numpy, whitePointRef=None):
        """converts an array from adobe RGB to sRGB using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.adobeGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.adobeToXYZAdobeMatrix[0, 0], self.adobeToXYZAdobeMatrix[0, 1], self.adobeToXYZAdobeMatrix[0, 2], self.adobeToXYZAdobeMatrix[1, 0], self.adobeToXYZAdobeMatrix[1, 1], self.adobeToXYZAdobeMatrix[1, 2], self.adobeToXYZAdobeMatrix[2, 0], self.adobeToXYZAdobeMatrix[2, 1], self.adobeToXYZAdobeMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.XYZTosRGBMatrix[0, 0], self.XYZTosRGBMatrix[0, 1], self.XYZTosRGBMatrix[0, 2], self.XYZTosRGBMatrix[1, 0], self.XYZTosRGBMatrix[1, 1], self.XYZTosRGBMatrix[1, 2], self.XYZTosRGBMatrix[2, 0], self.XYZTosRGBMatrix[2, 1], self.XYZTosRGBMatrix[2, 2] , block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 
    
    @handle_data
    def LabTosRGB(self, inData_numpy, whitePointRef=None):
        """converts an array from CIELAB to sRGB using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.doLabToSqrtXYZInPlace(in_arr, block=self.cuda_block, grid=grid)
        self.labSQRTInverseInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doXYZNormInverseInPlace(in_arr, np.float32(whitePointRef[0]), np.float32(whitePointRef[1]), np.float32(whitePointRef[2]), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.XYZTosRGBMatrix[0, 0], self.XYZTosRGBMatrix[0, 1], self.XYZTosRGBMatrix[0, 2], self.XYZTosRGBMatrix[1, 0], self.XYZTosRGBMatrix[1, 1], self.XYZTosRGBMatrix[1, 2], self.XYZTosRGBMatrix[2, 0], self.XYZTosRGBMatrix[2, 1], self.XYZTosRGBMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.srgbGammaApplyInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

    @handle_data
    def LabToXYZ(self, inData_numpy, whitePointRef=None):
        """converts an array from CIELAB to XYZ using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.doLabToSqrtXYZInPlace(in_arr, block=self.cuda_block, grid=grid)
        self.labSQRTInverseInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doXYZNormInverseInPlace(in_arr, np.float32(whitePointRef[0]), np.float32(whitePointRef[1]), np.float32(whitePointRef[2]), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.XYZTosRGBMatrix[0, 0], self.XYZTosRGBMatrix[0, 1], self.XYZTosRGBMatrix[0, 2], self.XYZTosRGBMatrix[1, 0], self.XYZTosRGBMatrix[1, 1], self.XYZTosRGBMatrix[1, 2], self.XYZTosRGBMatrix[2, 0], self.XYZTosRGBMatrix[2, 1], self.XYZTosRGBMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.srgbGammaApplyInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

    @handle_data
    def HSVTosRGB(self, inData_numpy, whitePointRef=None):
        """converts an array from HSV to sRGB using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.hsvToRgb(in_arr, block=self.cuda_block, grid=grid)
        self.srgbGammaApplyInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)       
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

    @handle_data
    def adobeRGBToHSV(self, inData_numpy, whitePointRef=None):
        """converts an array from adobe RGB to HSV using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.adobeGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.adobeToXYZAdobeMatrix[0, 0], self.adobeToXYZAdobeMatrix[0, 1], self.adobeToXYZAdobeMatrix[0, 2], self.adobeToXYZAdobeMatrix[1, 0], self.adobeToXYZAdobeMatrix[1, 1], self.adobeToXYZAdobeMatrix[1, 2], self.adobeToXYZAdobeMatrix[2, 0], self.adobeToXYZAdobeMatrix[2, 1], self.adobeToXYZAdobeMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.doColMatrixMultInPlace(in_arr, self.XYZTosRGBMatrix[0, 0], self.XYZTosRGBMatrix[0, 1], self.XYZTosRGBMatrix[0, 2], self.XYZTosRGBMatrix[1, 0], self.XYZTosRGBMatrix[1, 1], self.XYZTosRGBMatrix[1, 2], self.XYZTosRGBMatrix[2, 0], self.XYZTosRGBMatrix[2, 1], self.XYZTosRGBMatrix[2, 2] , block=self.cuda_block, grid=grid)
        self.rgbToHsv(in_arr, block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

    
    @handle_data
    def sRGBToHSV(self, inData_numpy, whitePointRef=None):
        """converts an array from sRGB to HSV using cuda (gpu)

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.srgbGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        self.rgbToHsv(in_arr, block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 


    @handle_data
    def sRGBTonormSRGB(self, inData_numpy, whitePointRef=None):
        """converts an array from sRGB to normalized sRGB using cuda (gpu) 

        :param inData_numpy: array to convert
        :type inData_numpy: ndarray
        :param whitePointRef: define the color "white" in image, defaults to None
        :type whitePointRef: tupel, optional
        :return: converted array
        :rtype: ndarray
        """
        if whitePointRef is None:
            whitePointRef = self.whitePointD65
        sz = inData_numpy.shape[0]
        grid = (old_div((sz + self.cuda_block[0] - 1), self.cuda_block[0]),1)
        in_arr = self.gpuarray.to_gpu(inData_numpy)
        self.srgbGammaRemoveInPlace(in_arr, np.prod(in_arr.shape), block=self.cuda_block, grid=grid)
        out_data = in_arr.get()
        in_arr.gpudata.free()
        del in_arr
        return out_data 

if __name__ == "__main__":
    #
    # Set up test scenario.
    #

    # Create a simple test kernel.
    mod = SourceModule("""
    __global__ void my_kernel(float *d) {
        const int i = threadIdx.x;
        for (int m=0; m<100; m++) {
            for (int k=0; k<100 ; k++)
                d[i] = d[i] * 2.0;
            for (int k=0; k<100 ; k++)
                d[i] = d[i] / 2.0;
        }
        d[i] = d[i] * 2.0;
    }
    """)
    my_kernel = mod.get_function("my_kernel")

    pool = PageLockedMemoryPool()
    # Create the test data on the host.
    N = 1024 # Size of datasets.
    n = 8 # Number of datasets (and concurrent operations) used.
    im_data = np.random.randn(N).astype(np.float32)

    data, data_check, d_data = [], [], []
    for k in range(n):
        xx = np.random.randn(N).astype(np.float32)
        data.append(drv.pagelocked_empty_like(xx)) # Create random data.
        data[-1][:] = xx
        data_check.append(xx.copy()) # For checking the result afterwards.
        
        d_data.append(drv.mem_alloc(data[k].nbytes)) # Allocate memory on device.

    #
    # Start concurrency test.
    #

    # Use this event as a reference point.
    ref = drv.Event()
    ref.record()

    # Create the streams and events needed.
    stream, event = [], []
    marker_names = ['kernel_begin', 'kernel_end']
    for k in range(n):
        stream.append(drv.Stream())
        event.append(dict([(marker_names[l], drv.Event()) for l in range(len(marker_names))]))
    # Run kernels many times, we will only keep data from last loop iteration.
    for j in range(10):
        for k in range(n):
            event[k]['kernel_begin'].record(stream[k])
            drv.memcpy_htod_async(d_data[k], data[k], stream=stream[k]) 
            my_kernel(d_data[k], block=(N,1,1), stream=stream[k]) 
        for k in range(n): # Commenting out this line should break concurrency.
            event[k]['kernel_end'].record(stream[k])
    for ev in event:
        event[k]['kernel_end'].synchronize()

    for st in stream:
        print(st.is_done())
    # Transfer data back to host.
    for k in range(n):
        drv.memcpy_dtoh_async(data[k], d_data[k], stream=stream[k]) 
    for st in stream:
        st.synchronize()

    #
    # Output results.
    #

    print('\n=== Device attributes')
    dev = pycuda.autoinit.device
    print('Name:', dev.name())
    print('Compute capability:', dev.compute_capability())
    print('Concurrent Kernels:', \
        bool(dev.get_attribute(drv.device_attribute.CONCURRENT_KERNELS)))
    print('\n=== Checking answers')
    for k in range(n):
        print('Dataset', k, ':', end=' ')
        if (np.linalg.norm((data_check[k] * 2 ** (j + 1)) - data[k]) == 0.0):
            print('passed.')
        else:
            print('FAILED!')

    print('\n=== Timing info (for last set of kernel launches)')
    for k in range(n):
        print('Dataset', k) 
        for l in range(len(marker_names)):
            print(marker_names[l], ':', ref.time_till(event[k][marker_names[l]]))

    pycuda.driver.stop_profiler()