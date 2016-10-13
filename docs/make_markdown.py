#!/usr/bin/env python
import argparse
import subprocess
import sys
import re


def make_singlehtml_file():
    """
    Build single html docs file using Sphinx.
    """
    subprocess.check_call(['make', 'singlehtml'])


def make_markdown_file():
    """
    Convert _build/singlehtml/index.html to
    markdown/quickpin.md using Pandoc.
    """
    subprocess.check_call(['mkdir', '-p', '_build/markdown'])
    subprocess.check_call(['pandoc',
                           '-s', '_build/singlehtml/index.html',
                           '-o', '_build/markdown/quickpin.md',
                           '-w', 'markdown_github'])


def fix_endpoint_lists(text):
    """
    Unindent entpoint lists.
    """
    pattern = '.*\s+[#+\s\[Endpoints\]].*[\n]*(\s+-\s+)[\*]+.*'
    replacement = '-  '
    text = re.sub(pattern, replacement, text)
    return text


def fix_contents(text):
    """
    Fix empty contents sections.
    """
    pattern = r'.*(Contents:)\s+[^-].*'
    replacement = ''
    text = re.sub(pattern, replacement, text)
    return text


def fix_image(text):
    """
    Replace graphviz object with local svg image.
    """
    pattern = r'.*(digraph system.*}).*'
    replacement = '![QuickPin Architecture](../quickpin-architecture.svg)'
    text = re.sub(pattern, replacement, text)
    return text


def strip_colons(text):
    """
    Strip all ':    '
    """
    pattern = ':   '
    replacement = ''
    return text.replace(pattern, replacement)


def fix_endpoint_headers(text):
    """
    Reformat endpoint items into headings.
    """
    # # Request Headers
    # pattern = r'.*\s+[#+\s\[Endpoints\]].*[\n]*(\s+Request Headers:).*'
    # replacement = '**Request Headers**'
    # text = re.sub(pattern, replacement, text)
    # # Request JSON Object
    # pattern = r'.*\s+[#+\s\[Endpoints\]].*[\n]*(\s+Request JSON Object:).*'
    # replacement = '**Request JSON Object**'
    # text = re.sub(pattern, replacement, text)
    # # Response Headers
    # pattern = r'.*\s+[#+\s\[Endpoints\]].*[\n]*(\s+Response Headers:).*'
    # replacement = '**Response Headers**'
    # text = re.sub(pattern, replacement, text)
    # # Response JSON Object
    # pattern = r'.*\s+[#+\s\[Endpoints\]].*[\n]*(\s+Response JSON Object:).*'
    # replacement = '**Response JSON Object**'
    # text = re.sub(pattern, replacement, text)
    # # Status Codes
    # pattern = r'.*\s+[#+\s\[Endpoints\]].*[\n]*(\s+Status Codes:).*'
    # replacement = '**Status Codes**'
    # text = re.sub(pattern, replacement, text)
    # HTTP Request
    pattern = r'(\s`(GET|PUT|POST|DELETE))'
    replacement = r'#### \g<2>'
    text = re.sub(pattern, replacement, text)
    # HTTP Request URL
    pattern = r'((GET|PUT|POST|DELETE)\s``(.*)`)'
    replacement = r'\g<2> \g<3>'
    text = re.sub(pattern, replacement, text)
    return text


def format_text(text):
    text = strip_colons(text)
    print('[*] Removed rogue colons.')
    # text = fix_endpoint_lists(text)
    # print('[*] Reformated endpoint lists')
    text = fix_endpoint_headers(text)
    print('[*] Reformated endpoint headers.')
    text = fix_image(text)
    print('[*] Replaced image with local svg.')
    text = fix_contents(text)
    print('[*] Removed empty contents sections.')
    print('Done!')
    return text

if __name__ == '__main__':
    description = ('QuickPin Sphinx Markdown Docs Creator\n'
                   '-------------------------------------\n'
                   '\n'
                   'Create and format markdown file using sphinx and pandoc.')

    ap = argparse.ArgumentParser(description=description,
                                 formatter_class=argparse.RawTextHelpFormatter)
    args = ap.parse_args()

    make_singlehtml_file()
    print('[*] Created index.html in ./_build/singlehtml.')
    make_markdown_file()
    print('[*] Created quickpin.md in ./_build/markdown.')

    with open('_build/markdown/quickpin.md') as f:
        text = f.read()

    if not text:
        print('./_build/markdown/quickpin.md is empty!')
        sys.exit()

    # Fix markdown
    text = format_text(text)

    with open('./_build/markdown/quickpin.md', 'w') as f:
        f.write(text)
