# QuickPin
QuickPin is a tool for quickly examining social networks, such as Twitter, to identify individuals and groups that are related to specified topics.

Read the [documentation](docs/markdown/quickpin.md).


## Compiling documentation
Requirements:

* [QuickPin Sphinx dependencies](docs/markdown/quickpin.md#id5).
* [Pandoc](http://pandoc.org/installing.html).
* [QuickPin Python dependencies](install/python-dependencies.txt).

There is a seperate branch used for compiling the documenation('rtd'). This contains a method to allow [sphinxcontrib.httpdomain.flask](http://pythonhosted.org/sphinxcontrib-httpdomain) to generate the API endpoint documentation.

1. checkout the 'rtd' branch and ensure it is up to date with the 'master':

```bash
$ git fetch
$ git checkout rtd
$ git rebase master
```

2. Create a PDF:

```bash
$ cd docs 
$ make latexpdf
```

3. Or HTML:
```bash
$ cd docs 
$ make html
```

Unless otherwise specified, output is created in docs/_build (excluded from github repository).

4. To create markdown documentation:

```bash
$ cd docs 
$ python make_markdown.py
```

Which will create docs/markdown/quickpin.md.

