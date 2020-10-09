import os
import psutil

class PidFileException(Exception):
    pass

class PidFile:
    def __init__(self, config, args):
        if hasattr(args, 'pid'):
            self.pidFile = args.pid
        else:
            self.pidFile = config['Common']['PidFile']

    def alreadyRunning(self):
        if not os.path.exists(self.pidFile):
            return False
        
        with open(self.pidFile, 'r') as f:
            pidfilepid = f.read()
            if psutil.pid_exists(int(pidfilepid)):
                return True
        
        return False

    def __enter__(self):
        if self.alreadyRunning():
            raise PidFileException("There is already an instance of this program running.")

        with open(self.pidFile, 'w') as f:
            f.write(str(os.getpid()))
    
    def __exit__(self, type, value, traceback):
        if os.path.exists(self.pidFile):
            os.remove(self.pidFile)
