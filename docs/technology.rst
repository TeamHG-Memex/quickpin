*****************
Technology Primer
*****************

.. contents::
    :depth: 2

Overview
========

This project uses a few web technologies that are very new and may be unfamiliar
to developers. This document offers a quick overview of these technologies and
provides links to find out more.

Dart
====

The client is primarily written in `Dart <https://www.dartlang.org/>`__, which
is a young programming language that is being developed by Google. Dart is
designed to be a much saner language (compared to JavaScript) for building
large, complex, structured applications on the web.

The syntax is clearly inspired by Java, but the language is much looser and more
casual than Java. For example, it has optional static types, functions are
first-class objects, and it has 2 nice syntaxes for anonymous functions.

Dart runs on its own VM, so it is not supported in any mainstream browser. It
_is_ supported in a fork of Chromium called `Dartium
<https://www.dartlang.org/tools/dartium/>`__. Dartium is great for developemnt,
but our users probably aren't running an obscure, experimental browser, so Dart
can be compiled into highly efficient JavaScript for running in production on
mainstream browsers.

Dart also has a lot of other great features, such as fully fledged async support
(they use the term Future instead of Promise), chained accessors (replaces
fluent APIs),

.. note::

    Dart's best feature (IMHO) is that it's not JavaScript. It sheds all of the
    insanity associated with JavaScript and I feel very productive when I'm
    working in Dart. -Mark

You'll find that the basics of Dart are very easy to pick up if you're familiar
with Java and one dynamically typed language. Dart mashes up a lot of
traditional and modern ideas about how to design a good programming language.

Here's a short example to give you some Dart flavor.

.. code:: dart

    class LoginComponent {
        AuthenticationController auth;
        RestApiController server;

        String email='', password='', error='';
        bool buttonBusy = false;

        /// Constructor.
        LoginComponent(this.auth, this.server);

        /// Ask the server to validate the user's credentials and give us an
        /// authentication token for future API requests.
        void login() {
            this.buttonBusy = true;
            var payload = {'email': this.email, 'password': this.password};

            server
                .post('/api/authentication', payload, needsAuth: false)
                .then((response) {
                    this.error = '';
                    auth.checkToken(response.data['token']);
                })
                .catchError((response) {
                    this.error = response.data['message'];
                })
                .whenComplete(() {
                    this.buttonBusy = false;
                });
        }

        // ...snip...
    }

This example shows several nice Dart features.

- The ``LoginComponent`` constructor uses a short hand to assign instance
  properties ``auth`` and ``server``. It doesn't need a constructor body
  to do mundane tasks like ``this.auth = auth;``.
- Dart has a built-in syntax for documenting methods and fields, using
  the ``///`` syntax. This can be converted to documentation using
  ``dartdocgen``.
- The ``login()`` method shows off the ``Future`` system in Dart.
  ``server.post()` returns a ``Future`` object. We can register callbacks
  to run when the future succeeds (``then``) or fails (``catchError``).
  The ``whenComplete`` callback runs in case of success *or* failure; it's
  like a ``finally`` clause for futures.
- The syntax for anonymous functions is less verbose than JavaScript.
  ``() {}`` is a valid definition of anonymous function. Dart also has
  ``=>`` syntax that allows you dispense with the brackets and return a
  value directly, e.g. ``(n) => n*n`` is an anonymous function that
  returns the square of ``n``.

Ok, are you convinced that you want to learn Dart?! Great! Here are some
resources to help you get started.

*Dart Learning Resources*

- `15 Cool Features Of Dart <http://blog.sethladd.com/2012/09/13-cool-features-of-dart.html>`__
- `9 Dart Myths <http://blog.sethladd.com/2012/10/9-dart-myths-debunked.html>`__ (No, this is *not* a Buzzfeed article!)
- `Official Tutorials <https://www.dartlang.org/docs/tutorials/>`__
- `Jesse Warden: Learning Dart (YouTube) <https://www.youtube.com/watch?v=sSLG8bz2ePA&noredirect=1>`__
- `Style Guide <https://www.dartlang.org/articles/style-guide/>`__
- `Dartdoc <https://www.dartlang.org/articles/doc-comment-guidelines/>`__
- `How To Generate Dartdoc <https://www.dartlang.org/tools/dartdocgen/>`__
- `Style Guide <https://www.dartlang.org/articles/style-guide/>`__

*Dart Support*

- You can ask `Mark <https://github.com/mehaase>`__. He doesn't know much more about Dart than you do, but he'll try to help.
- `Dart Tag On StackOverflow <http://stackoverflow.com/questions/tagged/dart>`__ (Dart officially uses SO as a support channel. Good for general questions.)
- `Dart E-mail List <https://groups.google.com/a/dartlang.org/forum/#!forum/misc>`__ (Better than SO for specific bugs or complex questions.)

The :ref:`installation` explains how to get the Dart SDK
and Dartium installed.

Angular.dart
============

Angular may seem unusual if you've never used anything like it.
Angular.dart is similar in spirit to Angular.js 1.x, except that the Angular
team had the benefit of many lessons learned when they started building
Angular.dart. Since Angular.dart was new, the team was able to conduct
experiments and make frequent changes without breaking existing code.

As a result, Angular.dart is in many ways *better* than Angular.js. It is much
simpler in many aspects. In fact, the future release of Angular.js 2.0 plans to
borrow a lot of good ideas back from Angular.dart.

The basic idea behind Angular is to bind data to markup. Angular is responsible
for keeping data bindings and their corresponding views up to date at all times.

Here's a simple example.

.. code:: html

    <h3>Hello {{name}}!</h3>
    Name: <input type="text" ng-model="name">

This example shows the use of mustache syntax for binding data (the ``name``
variable) to a heading. Whenever the value of ``name`` change, Angular will
automatically update the heading to match.

The text input below the heading is also bound to the same ``name`` variable as
the heading via the ``ng-model`` attribute. If you type something in this text
input, Angular will automatically update the value of ``name`` with the text
input's value, and then it will automatically update the heading to reflect the
new value of ``name``.

This sort of data binding makes complex behaviors really simple for programmers.
In fact, the previous example is *completely declarative*: it works without
needing to write a single line of Dart code.

Angular has a lot of other goodies. We won't get into all of them right here,
but there's one more important feature that you should know about: Angular
allows you to create custom HTML tags. Custom HTML tags provide encapsulation
and make it easy to build reusable components that can be composed in a variety
of ways.

Here's an example of implementing breadcrumbs in a re-usable manner. First,
let's look at the Dart code for breadcrumbs.

.. code:: dart

    @Component(
        selector: 'breadcrumbs',
        templateUrl: 'packages/quickpin/component/breadcrumbs.html',
        useShadowDom: false
    )
    class BreadcrumbsComponent {
        @NgOneWay('crumbs')
        List<Breadcrumb> crumbs;
    }

We declare the component using the selector ``breadcrumbs``, which means we can
instantiate the component in an HTML document by writing
``<breadcrumbs></breadcrumbs>``. We also specify a ``templateUrl``, which is a
URL that contains an HTML template for this element. When the element is
instantiated, the template will be rendered and added to the DOM.

The component maintains a list of Breadcrumb objects. (Notice how the optional
static types make the purpose of this class very clear.) This list is passed
into the component from any parent component using the ``@NgOneWay`` decorator.
We'll come back to that in a moment.

Now let's look at the breadcrumb template.

.. code:: html

    <ol class="breadcrumb">
      <li ng-repeat='crumb in crumbs' ng-class='{"active": $last}'>
        <a ng-if='$first' href="{{crumb.url}}">
          <i ng-if='$first' class='fa fa-home'></i>
          {{crumb.name}}
        </a>
        <a ng-if='!$first && !$last' href="{{crumb.url}}">
          {{crumb.name}}
        </a>
        <span ng-if='$last'>{{crumb.name}}</span>
      </li>
    </ol>

This template is based on our Bootstrap theme, so our custom element will look
like it belongs with the rest of the UI. The template has access to the
``crumbs`` list we saw in the Dart class, and it iterates over that list to
render the breadcrumbs.

Now that we've seen how the breadcrumbs element is defined, let's look at how it
might be used. First, we create a list of breadcrumbs:

.. code:: dart

    class FooComponent {
        String foobar = 'foobar';

        List<Breadcrumb> crumbs = [
            new Breadcrumb('QuickPin', '/'),
            new Breadcrumb('Profiles', '/profiles'),
            new Breadcrumb(this.profileName),
        ];
    }

Here we have an example component called `FooComponent`, but the point is that
we can re-use the breadcrumbs component in any other class! To display the bread
crumbs, we just need to add the ``<breadcrumbs>`` element in the template for
``FooComponent``.

.. code:: html

    <breadcrumbs crumbs=crumbs></breadcrumbs>

    <h1>The magic word is {{foobar}}!</h1>

Now when we render a ``FooComponent``, Angular will render this template. It
will see the ``<breadcrumbs`` element, it will instantiate a
``BreadcrumbsComponent``, and it will pass ``FooComponent.crumbs`` to
``BreadcrumbsComponent``.

Angular provides a lot of powerful techniques to build reusable objects, and I'm
just skimming the surface here. If you're ready to learn Angular, here are some
additional learning resources.

*Angular Learning Resources*

- `Official Tutorial <https://angulardart.org/tutorial/>`__
- `Angular.dart for Angular.js Developers <http://victorsavkin.com/post/86909839576/angulardart-1-0-for-angularjs-developers>`__ (Great if you know Angular.js, but still pretty good even if you don't know Angular.js.)

*Angular Support*

- `Angular-dart Tag On StackOverflow <http://stackoverflow.com/questions/tagged/angular-dart>`__ (Angular officially uses SO as a support channel. Good for general questions.)
- `Angular.dart Mailing List <https://groups.google.com/forum/#!forum/angular-dart>`__ (Better than SO for specific bugs or complex questions.)

Less (CSS)
==========

Less is a language for producing CSS styles. It aims to be a bit more developer
friendly than plain CSS: it gains increased power and succinct syntax but at the
expense of being a bit more complicated than plain CSS. It allows nested styles
as well as variables, both of which are very useful for making `DRY
<http://en.wikipedia.org/wiki/Don%27t_repeat_yourself>`__ styles.

Let's look at a quick example. We want to make an alert dialog that can have
different colors depending on the severity of the alert. The markup might look
something like this:

.. code:: html

    <div class='alert warning'>
        <img class='icon' src='/images/warning.png'>
        <p class='headline'>Hey buddy, listen up!</p>
        <p class='detail'>
            If you do that one more time, I swear I'm gonna lose it!
        </p>
    </div>

We want the styles to do the following:

- A dark border around the div with a light background.
- An icon in the top left corner.
- The headline is bold and same color as the border.
- The detail paragraph is normal text.

Oh, and we also want to have other color schemes (like ``success``) without
doing a lot of extra work.

Here's how we might do this in Less.

.. code:: css

    @warning-dark: #CC3300; // This is a dark shade of red.
    @warning-light: lighten(@warning-dark, 30%);

    @success-dark: #669900; // This is dark green.
    @success-light: lighten(@success-dark, 30%);

    .alert {
        img.icon {
            position: absolute;
            top: 0.5em;
            left: 0.5em;
        }

        p.headline {
            font-weight: bold;
        }

        &.warning {
            border: 1px solid @warning-dark;
            background-color: @warning-light;

            p.headline {
                color: @warning-dark;
            }
        }

        &.success {
            border: 1px solid @success-dark;
            background-color: @success-light;

            p.headline {
                color: @success-dark;
            }
        }
    }

There are a few interesting things happening in just the first 4 lines.

First, we can use variables to declare our colors once. Note that ``@dark-red``
is used twice in our stylesheet; if we ever want to change the shade of red, we
only have to update it in one place!

Second, we can use a function ``lighten()`` that takes a color and an alpha
value as arguments and returns a color value. This is another way to keep our
styles DRY. If we ever change ``@warning-dark`` from red to brown, then
``@warning-light`` will automatically update to a lighter shade of brown!

Third, Less supports C++ style comments, like ``// foo``. This is often faster
to type than native CSS comments, which are C style, like ``/* foo */``.

Now let's look at the body of the style sheet.

First, we can nest styles. For example, ``img.icon`` is *inside* ``.alert``.
This will compile to CSS code like ``.alert img.icon {…}``. It's a handy
shortcut syntax that allows us not to type ``.alert`` over and over.

We can nest styles arbitrarily deep, and this blends really well with Angular's
custom elements: we can easily and succinctly declare styles that *only* apply
to our custom element and will not affect anything else on the page.

The last interesting thing here is the ampersand: it is a reference to the
parent style. So when we say ``&.warning``, that means ``.alert.warning``. Like
many of Less's features, it's simply a more succinct way to say something.

A browser can't natively read Less, so we need to compile it to CSS to use it in
a real project. I'll use ``lessc`` (Less compiler) to convert to CSS.

.. code:: css

    $ lessc test.less
    .alert img.icon {
      position: absolute;
      top: 0.5em;
      left: 0.5em;
    }
    .alert p.headline {
      font-weight: bold;
    }
    .alert.warning {
      border: 1px solid #cc3300;
      background-color: #ff8c66;
    }
    .alert.warning p.headline {
      color: #cc3300;
    }
    .alert.success {
      border: 1px solid #669900;
      background-color: #bbff33;
    }
    .alert.success p.headline {
      color: #669900;
    }

This output gives a good sense of how Less processes its input into standard
CSS. The resulting CSS is usually more verbose and repetitive than the Less
input, which is exactly the point of using Less.

In QuickPin, we include both Bootstrap and Font Awesome in Less format. We store
styles that are specific to QuickPin in ``/static/less/site.less``. Our server
uses a Flask extension to automatically detect changes to the less source and
re-compile it to native CSS. So as you make changes to the the Less source, you
can simply refresh your browser to see the changes. You may notice a short delay
as the Less is compiled, but that delay will only be incurred when there are
actually changes that need compiling.

*Less Learning Resources*

- `Official Tutorial <http://lesscss.org/>`__
- `Don't Read This Less CSS Tutorial (highly addictive) <http://verekia.com/less-css/dont-read-less-css-tutorial-highly-addictive>`__
