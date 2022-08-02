
from setuptools import Extension, setup
import pybind11
import platform
import subprocess
import sys

#---------------------------------------------------------------------------

path_to_anaconda_environment = sys.base_prefix

if platform.system() == "Windows":
    path_to_libraries = path_to_anaconda_environment + r"\Library"

    inc_dirs = [pybind11.get_include(), path_to_libraries+r"\include"]
    lib_dirs = [path_to_libraries + r"\lib"]
    # libs = ["libprotobuf"]
    libs = []
    ex_comp_args = ["/MT"]
    
    protoc_cmd = path_to_libraries + r"\bin\protoc.exe"
	
else: #Linux
    inc_dirs = [pybind11.get_include(), path_to_anaconda_environment + r"/include"]
    lib_dirs = [path_to_anaconda_environment + r"/lib"]
    libs = ["protobuf"]
    ex_comp_args = ["-Wall", "-std=c++11", "-pthread"]
    
    protoc_cmd = "protoc"

#---------------------------------------------------------------------------

protobuf_files = ["protobuf_datatypes.proto"]
protobuf_files = []
for f in protobuf_files: subprocess.run([protoc_cmd, f, "--cpp_out=."])

#---------------------------------------------------------------------------

cpp_exts=[
    Extension(
        name="ES500_Aggregator_Helper",
        sources=["datatypes_global.cpp", "datatypes_global_SE_EV_definitions.cpp", "ES500_aggregator_helper.cpp", "python_bind.cpp"],
        include_dirs=inc_dirs,
        library_dirs=lib_dirs,
        libraries=libs,
        extra_compile_args=ex_comp_args,
        language="c++"
    )
]

#---------------------------------------------------------------------------

exts = cpp_exts 

setup(
    name="ES500_Aggregator",
    ext_modules = exts,
    version="0.1.0"
)


