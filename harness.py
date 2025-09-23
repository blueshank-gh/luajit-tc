import sys
import compiler
from pathlib import Path
import importlib.util
import time
import os

def testcases(root = "testcases", search = "tc_*.py"):
    root_path = Path(root)
    return [p for p in root_path.rglob(search) if p.is_file()]

def testcase_load(py_file: Path):
    spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in dir(module):
        if name.startswith("RUNNER"):
            class_ = getattr(module, name)
            runtime = class_()
            return runtime

    return None

def execution(runtime):
    code = 0

    if runtime.check() == False:
        print(f"Harness: Skipping {runtime.name}")
        return [code, "skipped"]

    if "compile" in type(runtime).__dict__:
        print("Harness: Detected deferred compiling.")
        execution.compiler_deferred = True
        code = runtime.pre_compile()
        if code != 0:
            runtime.report(code, "pre_compile")
            return [code, "pre_compile"]
        elapsed = time.time()
        code = runtime.compile()
        if code != 0:
            runtime.report(code, "compile")
            return [code, "compile"]
        compile_time = time.time() - elapsed
        print("Harness: Compiling took ", compile_time)
        code = runtime.post_compile()
        if code != 0:
            runtime.report(code, "post_compile")
            return [code, "post_compile"]
        execution.arguments_last = runtime.arguments()
    elif execution.compiler_deferred != False or set(runtime.arguments()) != set(execution.arguments_last):
        code = runtime.pre_compile()
        if code != 0:
            runtime.report(code, "pre_compile")
            return [code, "pre_compile"]
        elapsed = time.time()
        code = runtime.compile()
        if code != 0:
            runtime.report(code, "compile")
            return [code, "compile"]
        compile_time = time.time() - elapsed
        print("Harness: Compiling took ", compile_time)
        code = runtime.post_compile()
        if code != 0:
            runtime.report(code, "post_compile")
            return [code, "post_compile"]
        execution.compiler_deferred = False
        execution.arguments_last = runtime.arguments()

    if os.name == "nt":
        runtime.debugargs = [runtime.debugger, "-hd", "-c", ".lines; g; kv; q;"]
    elif os.name == "linux":
        runtime.debugargs = [
            runtime.debugger,
            "-batch",
            "-ex", "run",
            "-ex", "thread apply all bt full",
            "-ex", "quit",
            "--",
        ]

    code = runtime.pre_execution()
    if code != 0:
        runtime.report(code, "pre_execution")
        return [code, "pre_execution"]
    elapsed = time.time()
    code = runtime.execution()
    if code != 0:
        runtime.report(code, "execution")
        return [code, "execution"]
    execution_time = time.time() - elapsed
    runtime.execution_time = execution_time
    print("Harness: Execution took ", execution_time)
    code = runtime.post_execution()
    if code != 0:
        runtime.report(code, "post_execution")
        return [code, "post_execution"]

    runtime.report(code, "complete")

    return [code, "complete"]
execution.compiler_deferred = None
execution.arguments_last = []

def workflow(compiler_type, architecture_type, search="tc_*.py"):
    if os.name == "nt":
        import cdb
        workflow.debugger = cdb.find(architecture_type)
    elif os.name == "linux":
        import gdb
        workflow.debugger = gdb.find(architecture_type)

    if workflow.debugger == None:
        raise Exception(f"Unable to debugger for testcase runners")
    
    execution.compiler_deferred = None
    tests = testcases(search=search)
    failures = []
    for testcase in tests:
        runner = testcase_load(testcase)
        if not runner:
            raise Exception(f"Unable to locate testcase runner under {testcase}")
        runner.name = testcase
        runner.compiler = compiler_type
        runner.architecture = architecture_type
        runner.debugger = workflow.debugger
        print(f"Harness: Executing {testcase}")
        errors = execution(runner)
        if errors[0] != 0:
            print(f"Harness: Failure from {testcase} -> {errors[0]}")
            failures.append([testcase, errors])

    if len(failures) == 0:
        print("Harness: All testcases have passed")
    else:
        print(f"Harness: {len(tests)-len(failures)}/{len(tests)} have passed")
        for failure in failures:
            print(f"{failure[0]} -> {failure[1][0]} -> {failure[1][1]}")
workflow.debugger = None
workflow.debugargs = []

if __name__ == "__main__":
    args = sys.argv[1:]
    config = compiler.configuration()

    if config != None:
        print("Harness: Running configuration -> ", config)
        for compiler_type in config["compilers"]:
            for architecture_type in config["architectures"]:
                print(f"Harness: Executing {compiler_type}.{architecture_type}")
                if len(args) > 0:
                    workflow(compiler_type, architecture_type, " ".join(args))
                else:
                    workflow(compiler_type, architecture_type)

    pass