import compiler
import subprocess
import threading
import pathlib
import os
from datetime import datetime
    
class BASE_RUNNER:
    name = "base"
    compiler = None
    architecture = None
    debugger = None
    debugargs = []

    stdin = ""
    stdout = ""
    stderr = ""

    compile_time = 0
    execution_time = 0

    def __init__(self):
        pass

    def check(self):
        return True
    
    def executable(self):
        return compiler.executable(self.compiler, self.architecture)
    
    def printout(self):
        print("------------ STDIN ------------")
        print(self.stdin)
        print("------------ STDOUT ------------")
        print(self.stdout)
        print("------------ STDERR ------------")
        print(self.stderr)
    
    def run(self, code):
        current_dir = pathlib.Path(self.name).parent
        executable = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / self.executable()

        args = []
        args += self.debugargs
        args += [executable, "-e"]

        print("Runner: running -> " + " ".join([str(x) if isinstance(x, pathlib.Path) else x for x in args]) + " ...")
        
        args += [code]

        proc = subprocess.Popen(
            args,
            cwd=current_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return proc
    
    def load(self, filename):
        current_dir = pathlib.Path(self.name).parent
        executable = pathlib.Path(os.path.dirname(os.path.realpath(__file__))) / self.executable()

        args = []
        args += self.debugargs
        args += [executable, "-e"]
        args += [f'dofile("{filename}")']

        print("Runner: loading -> " + " ".join([str(x) if isinstance(x, pathlib.Path) else x for x in args]))

        proc = subprocess.Popen(
            args,
            cwd=current_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return proc

    def expect(self, process, expected, timeout=-1, error=False):
        if process is None:
            return False
    
        def target():
            try:
                stdout, stderr = process.communicate(timeout=timeout if timeout > 0 else None)
                self.stdout += stdout
                self.stderr += stderr
            except subprocess.TimeoutExpired:
                process.kill()
                self.stdout, self.stderr = "", ""

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout if timeout > 0 else None)

        if thread.is_alive():
            process.kill()
            thread.join()
            return False

        if error:
            return expected in self.stderr
        
        return expected in self.stdout

    def input(self, process, input, expected=None, timeout=-1, error=False):
        process.stdin.write(input)
        process.stdin.flush()
        stdin += str(input) + "\n"
        if expected != None:
            return self.expect(expected, timeout, error)
        
    def execute(self):
        pass
        
    def arguments(self):
        return []

    def compile(self):
        code = compiler.build(self.compiler, self.architecture, self.arguments())
        if (code != 0):
            return code
        return 0

    def report(self, code, action):
        now = datetime.now()

        report = ""
        report += f"testcase: {self.name}\n"
        report += f"time: {now.strftime('%H:%M:%S')}\n"
        report += f"date: {now.strftime('%Y-%m-%d')}\n"
        report += f"compile time: {self.compile_time}\n"
        report += f"execution time: {self.execution_time}\n"
        report += f"action: {action} [{code}]\n"
        report += "------------ STDIN -------------\n"
        report += self.stdin
        report += "------------ STDOUT ------------\n"
        report += self.stdout
        report += "------------ STDERR ------------\n"
        report += self.stderr

        loc = pathlib.Path(self.name).with_suffix(".report")
        with open(loc, "w", encoding="utf-8") as f:
            f.write(report)

    def pre_compile(self):
        return 0

    def post_compile(self):
        return 0

    def pre_execution(self):
        return 0

    def post_execution(self):
        return 0