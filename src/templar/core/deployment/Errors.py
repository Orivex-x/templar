import sys
sys.dont_write_bytecode = True

class DeployError(Exception):
    """Base error for deployment failures."""
    pass
