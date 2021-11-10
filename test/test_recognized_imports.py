from io import StringIO
import pytest

from bonded.bonded import find_imports_from_token


@pytest.mark.parametrize("stmt",
    [
        "import foo",
        "import foo.bar",
        "import foo as qux",
        "import foo.bar as qux",
        "from foo import bar",
        "from foo.bar import baz",
        "from foo.bar import (baz.qux)",
        "from foo import (bar as baz)",
        "from foo import bar, baz",
        "from foo import (bar, \nbaz)",
        "from foo import *",
        "yield from inner; import foo",
        "yield from inner; from foo import bar",
        "raise RuntimeError from SyntaxError; import foo",
    ],
)
def test_import_statement(stmt, tmp_path):
    tgt = tmp_path / "test_import_statement.py"
    tgt.write_text(stmt)
    assert find_imports_from_token(tgt) == {"foo": "statement"}


@pytest.mark.parametrize("stmt",
    [
        "import foo, bar as baz, qux.xuq",
        "import foo; import bar as baz; import qux.xuq",
        "from foo import baz as foo; from bar import *; from qux import xuq",
    ]
)
def test_multi_import(stmt, tmp_path):
    tgt = tmp_path / "test_import_statement.py"
    tgt.write_text(stmt)
    assert find_imports_from_token(tgt) == {"foo": "statement", "bar": "statement", "qux": "statement"}

@pytest.mark.parametrize("stmt",
    [
        "from . import foo",
        "from .. import foo",
        "from .foo import bar",
        "from .foo.bar import baz",
        "from ...foo.bar import baz",
        "yield from inner",
        "raise RuntimeError from SyntaxError",
    ]
)
def test_ignored_import(stmt, tmp_path):
    tgt = tmp_path / "test_ignored_import.py"
    tgt.write_text(stmt)
    assert find_imports_from_token(tgt) == {}

@pytest.mark.parametrize("fun",
    [
        "__import__('foo')",
        "import_module('foo')",
        "run_module('foo')",
    ]
)
def test_dynamic_import(fun, tmp_path):
    tgt = tmp_path / "test_dynamic_import.py"
    tgt.write_text(fun)
    assert find_imports_from_token(tgt) == {"foo": "function"}

@pytest.mark.parametrize("fun",
    [
        "__import__(42)",
        "import_module = 'foo'",
        "run_module.__name__",
    ]
)
def test_lookalike_dynamic_import(fun, tmp_path):
    tgt = tmp_path / "test_lookalike_dynamic_import.py"
    tgt.write_text(fun)
    assert find_imports_from_token(tgt) == {}
