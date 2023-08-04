try:
    from ._version import __version__
except ModuleNotFoundError:
    __version__ = 'dev'
