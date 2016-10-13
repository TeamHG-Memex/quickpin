# QuickPin
QuickPin is a tool for quickly examining social networks, such as Twitter, to identify individuals and groups that are related to specified topics.

Read the [documentation](docs/markdown/quickpin.md).


## Compiling documentation
Install Sphinx:  [Dependencies](docs/markdown/quickpin.md#id5).
Install Pandoc: [Pandoc Installation](http://pandoc.org/installing.html).
Ensure you have installed all [Python dependencies](install/python-dependencies.txt).

There is a seperate branch used for compiling the documenation('rtd'). This contains a method to allow [sphinxcontrib.httpdomain.flask](http://pythonhosted.org/sphinxcontrib-httpdomain) to generate the API endpoint documentation.

To compile docs, checkout the 'rtd' branch and ensure it is up to date with the 'master':

```bash
$ git fetch
$ git checkout rtd
$ git rebase master
```

Then, to create a PDF:

```bash
$ cd docs 
$ make latexpdf
```

Or HTML:
```bash
$ cd docs 
$ make html
```

Unless otherwise specified, output is created in docs/_build (excluded from github repository).

To create markdown documentation, 

```bash
$ cd docs 
$ python make_markdown.py
```

Which will create docs/markdown/quickpin.md.

