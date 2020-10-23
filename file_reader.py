import os
class FileReader:

    def __init__(self):
        pass

    def get(self, filepath, cookies):
        '''
        Returns a binary string of the file contents, or None.
        '''
        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        return None

    def head(self, filepath, cookies):
        '''
        Returns the size to be returned, or None.
        '''
        if os.path.isfile(filepath):
            return os.path.getsize(filepath)
        return None