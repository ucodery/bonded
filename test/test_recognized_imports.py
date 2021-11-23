from io import StringIO
import pytest

from bonded.module_inspection import ModuleInspection

@pytest.fixture(autouse=True)
def module_inspection():
    return ModuleInspection()


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
def test_import_statement(stmt, module_inspection, tmp_path):
    tgt = tmp_path / "test_import_statement.py"
    tgt.write_text(stmt)
    module_inspection.find_imports_from_token(tgt)
    assert "foo" in module_inspection
    assert module_inspection["foo"].found_import_stmt


@pytest.mark.parametrize("stmt",
    [
        "import foo, bar as baz, qux.xuq",
        "import foo; import bar as baz; import qux.xuq",
        "from foo import baz as foo; from bar import *; from qux import xuq",
    ]
)
def test_multi_import(stmt, module_inspection, tmp_path):
    tgt = tmp_path / "test_import_statement.py"
    tgt.write_text(stmt)
    module_inspection.find_imports_from_token(tgt)
    assert "foo" in module_inspection
    assert module_inspection["foo"].found_import_stmt
    assert "bar" in module_inspection
    assert module_inspection["bar"].found_import_stmt
    assert "qux" in module_inspection
    assert module_inspection["qux"].found_import_stmt

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
def test_ignored_import(stmt, module_inspection, tmp_path):
    tgt = tmp_path / "test_ignored_import.py"
    tgt.write_text(stmt)
    module_inspection.find_imports_from_token(tgt)
    assert not module_inspection

@pytest.mark.parametrize("fun",
    [
        "__import__('foo')",
        "import_module('foo')",
        "run_module('foo')",
    ]
)
def test_dynamic_import(fun, module_inspection, tmp_path):
    tgt = tmp_path / "test_dynamic_import.py"
    tgt.write_text(fun)
    module_inspection.find_imports_from_token(tgt)
    assert "foo" in module_inspection
    assert module_inspection["foo"].found_import_fun

@pytest.mark.parametrize("fun",
    [
        "__import__(42)",
        "import_module = 'foo'",
        "run_module.__name__",
    ]
)
def test_lookalike_dynamic_import(fun, module_inspection, tmp_path):
    tgt = tmp_path / "test_lookalike_dynamic_import.py"
    tgt.write_text(fun)
    module_inspection.find_imports_from_token(tgt)
    assert not module_inspection
