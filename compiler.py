import subprocess
import platform
import json
import shutil
import pathlib
import os

# Gets the compilers configuration, to be used by everything bellow
def read():
    if (read.config):
        return read.config

    read.config = {}
    with open('compilers.json') as f:
        read.config = json.load(f)
    return read.config
read.config = False

def configuration():
    system = platform.system()
    machine = platform.machine()
    config = read()
    if (not system in config.keys()):
        print(f"Compiler: unable to locate {system} in configuration")
        return None
    config = config[system]
    if (not machine in config.keys()):
        print(f"Compiler: unable to locate {system}.{machine} in configuration")
        return None
    config = config[machine]

    if (not "architectures" in config.keys() or not isinstance(config["architectures"], list)):
        print(f"Compiler: 'architectures' is not an array in {system}.{machine} configuration")
        return None
    
    if (not "compilers" in config.keys() or not isinstance(config["compilers"], list)):
        print(f"Compiler: 'compilers' is not an array in {system}.{machine} configuration")
        return None

    return config

# Locates the specified compiler, like trying to locate gcc, msvc, and etc.
# Note: for msvc its a bit special, we need to use vswhere.exe, then use vcvars64.bat to run luajit/src/msvcbuild.bat with our arguments.
def locate(compiler="MSVC"):
    if compiler.upper() == "MSVC":
        try: # Run vswhere to find the latest Visual Studio installation
            output = subprocess.check_output(
                ["vswhere.exe", "-latest", "-products", "*", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
                shell=True
            ).decode().strip()

            if not output:
                return False

            install_path = pathlib.Path(output)
            vcvars_path = install_path / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"

            if vcvars_path.exists():
                return {
                    "compiler": "MSVC",
                    "msvc": str(install_path),
                    "vcvars": str(vcvars_path),
                }
            else:
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    elif compiler.upper() == "GMAKE":
        make_path = shutil.which("make")
        gcc_path = shutil.which("gcc")

        if make_path and gcc_path:
            return {
                "compiler": "GMAKE",
                "make": make_path,
                "gcc": gcc_path,
            }
        return False

    return False

# This will get an array of carefully sorted arguments.
# It has to be sorted in a certain way depending on how the compiler will see it.
# Like msvc.bat requiring a certain pattern of arguments or else it won't work properly.
def arguments(compiler="MSVC", architecture="x64", flags = []):
    arguments = []
    if (compiler == "MSVC"):
        if ("GC64" in flags):
            arguments.append("gc64")

        if ("DEBUG" in flags):
            arguments.append("debug")

        if ("DYNAMIC" in flags):
            arguments.append("amalg")
            if ("STATIC" in flags):
                arguments.append("static")
            elif ("MIXED" in flags):
                arguments.append("mixed")
        elif ("STATIC" in flags):
            arguments.append("static")

        arguments.append(architecture)
    elif(compiler == "GMAKE"):
        cc = ["gcc"]

        # Architecture & GCC flags
        if architecture == "x64":
            cc.append("-m32")
        elif architecture == "x86":
            cc.append("-m64")
        if "DEBUG" in flags:
            cc.append("-g")

        arguments.append("cc=\"" + " ".join(cc) + "\"")

        xcflags = []
        
        # Features
        if not "FFI" in flags:
            xcflags.append("-DLUAJIT_DISABLE_FFI")
        if "LUA52" in flags:
            xcflags.append("-DLUAJIT_ENABLE_LUA52COMPAT")
        if not "JIT" in flags:
            xcflags.append("-DLUAJIT_DISABLE_JIT")
        if "GC64" in flags:
            xcflags.append("-DLUAJIT_ENABLE_GC64")

        # TODO: CROSS support & TARGET_SYS support
        # TODO: DLUAJIT_NUMMODE support for PPC

        # Debugging Support
        if "SYSMALLOC" in flags:
            xcflags.append("-DLUAJIT_USE_SYSMALLOC")
        if "VALGRIND" in flags:
            xcflags.append("-DLUAJIT_USE_VALGRIND")
        if "GDBJIT" in flags:
            xcflags.append("-DLUAJIT_USE_GDBJIT")
        if "APICALLS" in flags:
            xcflags.append("-DLUA_USE_APICHECK")
        if "ASSERTS" in flags:
            xcflags.append("-DLUA_USE_ASSERT")

        arguments.append("XCFLAGS=\"" + " ".join(xcflags) + "\"")

        # Buildmode - By default its on Mixed
        if "STATIC" in flags:
            arguments.append("buildmode=static")
        elif "DYNAMIC" in flags:
            arguments.append("buildmode=dynamic")
    return arguments

def executable(compiler, architecture):
    if compiler == "MSVC":
        return pathlib.Path() / "luajit" / "src" / "luajit.exe"
    elif compiler == "GMAKE":
        return pathlib.Path() / "luajit" / "src" / "luajit"

def build(compiler, architecture, flags):
    args = arguments(compiler, architecture, flags)
    toolchain = locate(compiler)

    if not toolchain:
        raise Exception(f"Compiler {compiler} not found on this system.")
    
    if toolchain["compiler"] == "MSVC":
        vcvars = toolchain["vcvars"]
        command = f'cmd /C "call "{vcvars}" && cd luajit\src && msvcbuild.bat {" ".join(args)}"'
        print("Compiler: " + command)

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0 or result.stdout.find("Build FAILED") != -1:
            print("Compiler: MSVC build failed!\n", result.stdout, result.stderr)
            return result.returncode or -1
        else:
            print("Compiler: MSVC build succeeded")

        return result.returncode
    elif toolchain["compiler"] == "GMAKE":
        build_dir = os.path.join("luajit", "src")
        result = subprocess.run(
            ["make", "clean"],
            cwd=build_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Compiler: GMAKE clean failed!\n", result.stdout, result.stderr)
            return result.returncode
        else:
            print("Compiler: GMAKE clean succeeded")

        command = ["make"] + args
        print("Compiler Command: " + " ".join(command))

        result = subprocess.run(
            command,
            cwd=build_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Compiler: GMAKE build failed!\n", result.stdout, result.stderr)
        else:
            print("Compiler: GMAKE build succeeded")
        
        return result.returncode
    else:
        print(f"Compiler: Unsupported compiler type: {toolchain['compiler']}")
        return -1