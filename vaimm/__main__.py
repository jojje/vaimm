import os
import sys
try:
    from .cli import main
except ImportError:
    from cli import main

# give the program a descriptive name if run from python -m
if sys.argv[0].endswith('__main__.py'):
    sys.argv[0] = os.path.dirname(__file__)

main()
