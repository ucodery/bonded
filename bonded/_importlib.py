from collections import defaultdict
from importlib import machinery  # noqa: F401

import importlib_metadata as metadata
from packaging import utils as pkgutil

pkg2dist = metadata.packages_distributions()
dist2pkg = defaultdict(list)
for pkg, dists in pkg2dist.items():
    #if pkg == '..' or pkg.endswith('.dist-info'):
        #continue
    for dist in dists:
        dist = pkgutil.canonicalize_name(dist)
        dist2pkg[dist].append(pkg)
dist2pkg = dict(dist2pkg)
