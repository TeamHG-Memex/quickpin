# QuickPin
QuickPin is a tool for quickly examining social networks, such as Twitter, to identify individuals and groups that are related to specified topics.

Read the [documentation](docs/markdown/quickpin.md).


## Compiling documentation

Requirements:

* [QuickPin dependencies (inc Sphinx)](docs/markdown/quickpin.md#id5).
* [Pandoc](http://pandoc.org/installing.html).
* [QuickPin Python dependencies](install/python-dependencies.txt).

There is a seperate branch used for compiling the documenation('rtd'). This contains a method to allow [sphinxcontrib.httpdomain.flask](http://pythonhosted.org/sphinxcontrib-httpdomain) to generate the API endpoint documentation.

### Checkout the 'rtd' branch

```bash
$ git fetch
$ git checkout rtd
$ git rebase master
```
Rebase ensures the 'rtd' branch is up to date with changes to master.

### Create PDF

```bash
$ cd docs 
$ make latexpdf
```

### Create HTML
```bash
$ cd docs 
$ make html
```

Unless otherwise specified, output is created in docs/_build (excluded from github repository).

### Create Markdown

```bash
$ cd docs 
$ python make_markdown.py
```

This scripts builds a single html file with Sphinx, converts it to markdown with Pandoc, and applies some formatting tweaks. File is stored in docs/markdown/quickpin.md.

