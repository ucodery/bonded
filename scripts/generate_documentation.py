import os
from argparse import HelpFormatter

from bonded.settings import CLISettings


def update_readme():
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
    with open('README.md', 'r') as readme_read, open('README.new', 'w') as readme_write:
        for line in readme_read:
            readme_write.write(line)
            if line.strip() == '<!-- replace start -->':
                readme_write.write('```\n')
                readme_write.write(help_txt)
                readme_write.write('```\n')
                while line.strip() != '<!-- replace end -->':
                    line = next(readme_read)
                readme_write.write(line)
    os.rename('README.new', 'README.md')


if __name__ == '__main__':
    update_readme()
