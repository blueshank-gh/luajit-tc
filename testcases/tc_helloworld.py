# expected output: hello world
import runner
class RUNNER(runner.BASE_RUNNER):

    def arguments(self):
        return [
            "FFI",
            "GC64",
            "DEBUG",
            "APICALLS",
            "ASSERTS"
        ]
    
    def execution(self):
        proc = self.load("helloworld.lua")
        if self.expect(proc, "hello world"):
            return 0 # success
        else:
            print(self.stdout)
            print(self.stderr)
            return 1 # failure