import pytest

from bonded.module_inspection import ModuleInspection


@pytest.fixture(autouse=True)
def module_inspection():
    return ModuleInspection()


@pytest.fixture()
def python_file(request, tmp_path, code):
    tgt = (tmp_path / request.function.__name__).with_suffix('.py')
    tgt.write_text(code)
    return tgt


@pytest.mark.parametrize(
    'code',
    [
        'import foo',
        'import foo.bar',
        'import foo as qux',
        'import foo.bar as qux',
        'from foo import bar',
        'from foo.bar import baz',
        'from foo.bar import (baz.qux)',
        'from foo import (bar as baz)',
        'from foo import bar, baz',
        'from foo import (bar, \nbaz)',
        'from foo import *',
        'yield from inner; import foo',
        'yield from inner; from foo import bar',
        'raise RuntimeError from SyntaxError; import foo',
    ],
)
def test_import_statement(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert 'foo' in module_inspection
    assert module_inspection['foo'].found_import_stmt


@pytest.mark.parametrize(
    'code',
    [
        'import foo, bar as baz, qux.xuq',
        'import foo; import bar as baz; import qux.xuq',
        'from foo import baz as foo; from bar import *; from qux import xuq',
    ],
)
def test_multi_import(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert 'foo' in module_inspection
    assert module_inspection['foo'].found_import_stmt
    assert 'bar' in module_inspection
    assert module_inspection['bar'].found_import_stmt
    assert 'qux' in module_inspection
    assert module_inspection['qux'].found_import_stmt


@pytest.mark.parametrize(
    'code',
    [
        'from . import foo',
        'from .. import foo',
        'from .foo import bar',
        'from .foo.bar import baz',
        'from ...foo.bar import baz',
        'yield from inner',
        'raise RuntimeError from SyntaxError',
    ],
)
def test_ignored_import(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert not module_inspection


@pytest.mark.parametrize(
    'code',
    [
        "__import__('foo')",
        "import_module('foo')",
        "run_module('foo')",
    ],
)
def test_dynamic_import(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert 'foo' in module_inspection
    assert module_inspection['foo'].found_import_fun


@pytest.mark.parametrize(
    'code',
    [
        '__import__(42)',
        "import_module = 'foo'",
        'run_module.__name__',
    ],
)
def test_lookalike_dynamic_import(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert not module_inspection


@pytest.mark.parametrize(
    'code',
    [
        "import foo; __import__('foo')",
        "from foo import bar; import_module('foo')",
        "import foo as bar; run_module('foo')",
    ],
)
def test_statement_and_dynamic_import(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert 'foo' in module_inspection
    assert module_inspection['foo'].found_import_stmt
    assert module_inspection['foo'].found_import_fun


@pytest.mark.parametrize(
    'code',
    [
        'import \\\nfoo, \\\n baz',
        'from foo import (\nbar,\n); import baz',
        'from \\\nfoo import (\\nbar,\\n); import baz',
        "__import__(\\\n'foo'\\\n) and \\n import_module('baz')",
        "__import__(\n'foo'\n) and (\n import_module('baz')\n)",
    ],
)
def test_multiline_import(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert 'foo' in module_inspection
    assert module_inspection['foo'].found_import_stmt or module_inspection['foo'].found_import_fun
    assert 'baz' in module_inspection
    assert module_inspection['baz'].found_import_stmt or module_inspection['baz'].found_import_fun


@pytest.mark.parametrize(
    'code',
    [
        'import sys, os',
        'from sys import path; from os import environ',
        'import sys.path, os.environ',
        'import sys as requests, os as six',
    ],
)
def test_stdlib_imports(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert 'sys' in module_inspection
    assert module_inspection['sys'].found_import_stmt
    assert 'os' in module_inspection
    assert module_inspection['os'].found_import_stmt


@pytest.mark.parametrize(
    'code',
    [
        'from .foo',
        'from ..foo import bar',
        'from ...foo import bar',
    ],
)
def test_relative_modules(python_file, module_inspection):
    module_inspection.find_imports_from_token(python_file)
    assert not module_inspection


@pytest.mark.parametrize(
    'code',
    [
        '[1, 2, 3',
        'varible = """finish this later',
        'import ',
        'from ',
        'import 42',
        'from "this" import zen',
    ],
)
def test_unparsable_python(python_file, module_inspection):
    with pytest.warns(Warning):
        module_inspection.inspect_imports([python_file])
    assert not module_inspection
