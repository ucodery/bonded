import os

import bonded.settings
from bonded.settings import CLISettings, Settings


def test_no_preferences():
    """all settings have a default"""
    Settings()


def test_excludes():
    """excludes are rewritten to be unanchored, when appropriate"""
    assert Settings().exclude == set()
    assert Settings(exclude={'/dev'}).exclude == {'/dev'}
    assert Settings(exclude={'/dev/'}).exclude == {'/dev/**'}
    assert Settings(exclude={'dev'}).exclude == {'**/dev'}
    assert Settings(exclude={'dev/'}).exclude == {'**/dev/**'}


def test_project_modules(monkeypatch):
    with monkeypatch.context() as m:
        # disable any post_init locating of modules
        m.setattr(os.path, 'isfile', lambda _a: True)
        m.setattr(os, 'listdir', lambda _a: [])
        m.setattr(os, 'walk', lambda _a: [])
        assert Settings().project_modules == set()
        assert Settings(project_modules={'foo', 'bar'}).project_modules == {'foo', 'bar'}

    with monkeypatch.context() as m:
        # single file is being checked
        m.setattr(os.path, 'isfile', lambda _a: True)
        assert Settings(search_path='test.py').project_modules == {'test'}
        assert Settings(search_path='test.md').project_modules == set()
        assert Settings(project_modules={'foo', 'bar'}, search_path='test.py').project_modules == {
            'foo',
            'bar',
            'test',
        }

    with monkeypatch.context() as m:
        # single module is being checked
        m.setattr(os.path, 'isfile', lambda _a: False)
        m.setattr(os, 'listdir', lambda _a: ['__init__.py'])
        assert Settings(search_path='test').project_modules == {'test'}
        assert Settings(project_modules={'foo', 'bar'}, search_path='test').project_modules == {
            'foo',
            'bar',
            'test',
        }

    with monkeypatch.context() as m:
        # possibly multiple packages or modules
        m.setattr(os.path, 'isfile', lambda _a: False)
        m.setattr(os, 'listdir', lambda _a: [])
        m.setattr(os, 'walk', lambda _a: [])
        assert Settings(search_path='test').project_modules == set()

        def test_walk(_):
            yield ('test', ['spam'], ['README', 'build.py'])
            yield (
                'test/spam',
                [
                    'docs',
                ],
                [
                    '__init__.py',
                ],
            )
            yield ('test/spam/docs', [], [])

        m.setattr(os, 'walk', test_walk)
        assert Settings(search_path='test').project_modules == {'spam', 'build'}

    with monkeypatch.context() as m:
        # provided pyproject.toml specifies the package name
        m.setattr(os.path, 'isfile', lambda _a: True)
        m.setattr(os, 'listdir', lambda _a: [])
        m.setattr(os, 'walk', lambda _a: [])
        m.setattr(bonded.settings, 'gather_config', lambda _a: {'project': {'name': 'test'}})
        m.setattr(bonded.settings, 'dist2pkg', {'test': ['test-py']})
        assert Settings(pyproject='pyproject.toml').project_modules == {'test-py'}
        assert Settings(
            search_path='main.py', project_modules={'lib-py'}, pyproject='pyproject.toml'
        ).project_modules == {'main', 'lib-py', 'test-py'}


def test_no_args():
    assert vars(CLISettings.parse_args([])) == {}


def test_multiple_and_many_args():
    """arguments that can have multiple values can specify them multiple
    at a time and many different times
    """
    assert vars(
        CLISettings.parse_args(
            ['--packages', 'foo', 'bar', 'baz', '--packages', 'spam', 'ham', '--packages', 'eggs']
        )
    ) == {'packages': ['foo', 'bar', 'baz', 'spam', 'ham', 'eggs']}
    assert vars(
        CLISettings.parse_args(
            [
                '--ignore-modules',
                'foo',
                'bar',
                'baz',
                '--ignore-modules',
                'spam',
                'ham',
                '--ignore-modules',
                'eggs',
            ]
        )
    ) == {'ignore_modules': ['foo', 'bar', 'baz', 'spam', 'ham', 'eggs']}
    assert vars(
        CLISettings.parse_args(
            [
                '--ignore-packages',
                'foo',
                'bar',
                'baz',
                '--ignore-packages',
                'spam',
                'ham',
                '--ignore-packages',
                'eggs',
            ]
        )
    ) == {'ignore_packages': ['foo', 'bar', 'baz', 'spam', 'ham', 'eggs']}


def test_verbosity():
    assert vars(CLISettings.parse_args(['-v'])) == {'verbose': 1}
    assert vars(CLISettings.parse_args(['-vv'])) == {'verbose': 2}
    assert vars(CLISettings.parse_args(['-vvv'])) == {'verbose': 3}
    assert vars(CLISettings.parse_args(['-vvvv'])) == {'verbose': 4}
    assert vars(CLISettings.parse_args(['-vvvvv'])) == {'verbose': 5}
    assert vars(CLISettings.parse_args(['-vvvvvvv'])) == {'verbose': 7}
    assert vars(CLISettings.parse_args(['-v', '-v', '-v'])) == {'verbose': 3}
    assert vars(CLISettings.parse_args(['-vvv', '-q'])) == {'verbose': 3, 'quiet': True}


def test_search_path():
    assert vars(CLISettings.parse_args(['path'])) == {'search_path': 'path'}
    assert vars(CLISettings.parse_args(['--', 'path'])) == {'search_path': 'path'}
