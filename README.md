# Bonded

Do your imports pass inspection?

[![bonded - do your imports pass inspection?](https://raw.githubusercontent.com/ucodery/bonded/master/warehouse.png)](https://github.com/ucodery/bonded)


Bonded is a linter that alerts on both missing and unused requirements.

Bonded checks for project requirements that are not actually used in the project
and for imports that don't map back to any requirement explicitly declared as a
dependency. By verifying both relationships, projects can be assured that all
requirements necessary at runtime are properly captured as direct dependencies
and not available only because of an indirect relationship. Projects can also be
assured that the requirements that are declared are all necessary to the project.

## Usage

### Installing
```bash
pip install bonded
```

### Running
```bash
bonded my_project_dir
```

By default bonded will read your pyproject.toml and find all packages or
modules under the given directory. If you maintain requirements across multiple
locations, you will have to tell bonded where to look.
```bash
bonded --requirements dev-requirements.txt --exclude '.*/' ./
```
For more examples, check out [Advanced Usage](#advanced-usage).

## How does it work?
Bonded searches for all imports of python modules, both explicit and implicit
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

## Advanced Usage

### Options

Supported command line options are:
<!-- replace start -->
```
usage: bonded [-h] [--pyproject PYPROJECT] [--setup SETUP]
              [--packages PACKAGES [PACKAGES ...]] [-r REQUIREMENTS]
              [--ignore-modules IGNORE_MODULES [IGNORE_MODULES ...]]
              [--ignore-packages IGNORE_PACKAGES [IGNORE_PACKAGES ...]]
              [--exclude EXCLUDE] [--report {table,extended-table,line,none}]
              [--verbose] [--quiet]
              [search_path]

positional arguments:
  search_path

options:
  -h, --help            show this help message and exit
  --pyproject PYPROJECT
                        Path to a pyproject.toml which will be searched for
                        requirements and bonded settings
  --setup SETUP         Path to a setup.cfg which will be searched for
                        requirements
  --packages PACKAGES [PACKAGES ...]
                        Add a package to be checked for
  -r REQUIREMENTS, --requirements REQUIREMENTS
                        Pip-requirements file used to specify further
                        requirements. Can be specified multiple times
  --ignore-modules IGNORE_MODULES [IGNORE_MODULES ...]
                        These module will not be reported as missing a package
  --ignore-packages IGNORE_PACKAGES [IGNORE_PACKAGES ...]
                        These packages will not be reported as unused
  --exclude EXCLUDE     A glob that will exclude paths otherwise matched
  --report {table,extended-table,line,none}
  --verbose, -v
  --quiet, -q
```
<!-- replace end -->

### Configuration

All [command line options](#options) are also supported as configuration options
in a project's pyproject.toml. Options are specified under the `[tool.bonded]`
table and have the same name and meaning as when specified as a command line
option. The only option that will not have an effect when read from
pyproject.toml is the `pyproject` setting.

For each setting, bonded will start with a default value, then override from
options found in a pyproject.toml, if any, and finally override with options
specified as arguments, if any.

An example entry:
```toml
[tool.bonded]
search_path = 'src/mypackage'
setup = 'src/setup.cfg'
exclude = ['__pycache__/']
```

## Why can't it ..?
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
