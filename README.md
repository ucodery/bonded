# Bonded

Do your imports pass inspection?


Bonded is a linter that alerts when requirements are detected which are
declared as dependencies but not actually used in the project or when an import
is used that does not map back to any package explicitly declared as a
dependency. By verifying both relationships, projects can be assured that all
modules necessary at runtime are properly captured as direct dependencies, and
not available only because of an indirect relationship. They can also be
assured that the dependencies that are declared are all necessary to the
project.

### How does it work?
Bonded searched for all imports of python modules, both explicit and implicit
and associates each with an installed package. Additionally, bonded will also
note the use of
[plugins](https://setuptools.pypa.io/en/latest/userguide/entry_point.html)
and if the extended package is being used, the package providing the extended
behavior will also be marked as used. Finally, bonded knows which packages
provide executable commands that can be run on the command line and if those
commands are executed, will mark the providing package as used.

If none of the above can be found for a package, it is assumed to be unnecessary
to the project and is flagged so it can be removed, making refactoring
requirements safer.

Bonded also remembers all imports it found while scanning for used packages,
and any that were unable to be matched to installed packages are flagged as
potentially missing dependencies in the package declaration.

### Why can't it ..?
 - tell me the package I should depend on for undeclared modules?
   It is impossible for bonded to know what packages provide what modules if
   those packages are not installed locally. This is partly because python
   distribution names (what you download from pypi.org) and python package names
   (what you import) do not in any way have to relate to each other. It would be
   at best be wrong, at worst dangerous, to suggest you depend on packages based
   solely on name similarity.
 - figure out what modules a package supplies without it being installed locally?
   Bonded is not an environment manager, nor a package manager. Either of these
   tasks are independently complicated and best left to other tools that do them
   well. For the former try
   [nox](https://pypi.org/project/nox/) [tox](https://pypi.org/project/tox/) or
   [hatch](https://pypi.org/project/hatch/), for the latter try
   [pip](https://pypi.org/project/pip/) or
   [hatch](https://pypi.org/project/hatch/). Instead bonded is best used in
   conjunction with these tools.
 - use my virtualenv to figure out what my dependencies are?
   Declared dependencies are not equivalent to the contents of a virtualenv.
   Assuming that they are would remove bonded's ability to find the types of
   bugs where: someone installed it locally but didn't edit the metadata of the
   package, the dependency is only transitive and dependency requirements of
   other packages are being relied upon, a package is needlessly installed as
   there will be many packages required by the package's direct dependencies and
   installed locally but not required by the package itself.
 - read my setup.py?
   Anything can happen in a setup.py and bonded will not execute arbitrary code
   to find out a package's dependencies. Either move them to a declarative
   format, like `setup.cfg`, or tell bonded abut them explicitly with the
   `--package` option.
