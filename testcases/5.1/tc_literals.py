import runner
class RUNNER(runner.BASE_RUNNER):

    def arguments(self):
        return [
            "JIT",
            "FFI",
            "GC64",
            "DEBUG",
            "APICALLS",
            "ASSERTS"
        ]
    
    def execution(self):
        proc = self.load("literals.lua")
        if self.expect(proc, "OK"):
            return 0 # success
        else:
            print(self.stdout)
            print(self.stderr)
            return 1 # failure