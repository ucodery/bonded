# Bonded

Do your imports pass inspection?

Bonded is a linter that alerts when requirements are detected which are not
acually used in the project. Bonded searched for all imports of python modules,
both direct and indirect, and associates each with an installed package. If no
imports can be found for a package, it is assumed to be unnecessary to the
project and is flagged so it can be removed, making refactoring requirements
safer.
