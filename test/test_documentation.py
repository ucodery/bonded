from argparse import HelpFormatter

from bonded.settings import CLISettings


def test_up_to_date_options():
    class DocumentationFormatter(HelpFormatter):
        def __init__(self, prog, indent_increment=2, max_help_position=24, width=None):
            super().__init__(
                'bonded',
                indent_increment=indent_increment,
                max_help_position=max_help_position,
                width=80,
            )

    CLISettings.formatter_class = DocumentationFormatter
    help_txt = CLISettings.format_help()
    with open('README.md', 'r') as readme:
        assert (
            help_txt.strip() in readme.read()
        ), 'to update options run "python scripts/generate_documentation.py"'
