import os
import sys

class PathManager:
    """
    Manages the search path for .m files.
    """
    def __init__(self):
        # We store explicit paths added via addpath()
        self.paths = []
        self._cache = {}

    def add_path(self, path):
        p = os.path.abspath(path)
        if p not in self.paths:
            self.paths.append(p)
            self.clear_cache()

    def remove_path(self, path):
        p = os.path.abspath(path)
        if p in self.paths:
            self.paths.remove(p)
            self.clear_cache()

    def clear_cache(self):
        self._cache = {}

    def resolve(self, name):
        """
        Finds the .m file for a given function name.
        STRICTLY looks for .m files. No .py support.
        
        Priority:
        1. Current Working Directory (CWD)
        2. Explicit Paths (addpath)
        """
        filename = f"{name}.m"
        
        # 1. Check CWD (Dynamic!)
        cwd = os.getcwd()
        cwd_file = os.path.join(cwd, filename)
        if os.path.exists(cwd_file):
            return cwd_file

        # 2. Check Cache
        if name in self._cache:
            return self._cache[name]

        # 3. Search in explicit paths
        for p in self.paths:
            full_path = os.path.join(p, filename)
            if os.path.exists(full_path):
                self._cache[name] = full_path
                return full_path
        
        return None

# Global instance
path_manager = PathManager()