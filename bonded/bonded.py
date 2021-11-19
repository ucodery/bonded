import tokenize
import warnings
from enum import IntEnum
from pathlib import Path

from packaging import utils as pkgutil
from provides import provided_modules
from provides.errors import PackageNotFoundError


class Confidence(IntEnum):
    VERY_LOW = 5
    LOW = 10
    MEDIUM = 15
    HIGH = 20
    VERY_HIGH = 25
