..
    Copyright (C) 2018 CERN.

    Asclepias Broker is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/asclepias/asclepias-broker/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with "bug"
is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the GitHub issues for features. Anything tagged with "feature"
is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

Asclepias Broker could always use more documentation, whether as part of the
official Asclepias Broker docs, in docstrings, or even on the web in blog posts,
articles, and such.

Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at
https://github.com/asclepias/asclepias-broker/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

Get Started!
------------

Ready to contribute? Here's how to set up `asclepias-broker` for local development.

1. Fork the `asclepias/asclepias-broker` repo on GitHub.
2. Clone your fork locally:

   .. code-block:: console

      $ git clone git@github.com:your_name_here/asclepias-broker.git

3. Assuming you have ``pipenv``, ``docker`` and ``docker-compose`` installed,
   this is how you set up your fork for local development:

   .. code-block:: console

      $ ./scripts/bootstrap

4. Create a branch for local development:

   .. code-block:: console

      $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass tests:

   .. code-block:: console

      $ ./run-tests.sh

   The tests will provide you with test coverage and also check PEP8
   (code style), PEP257 (documentation), flake8 as well as build the Sphinx
   documentation and run doctests.

6. Commit your changes and push your branch to GitHub:

   .. code-block:: console

      $ git add .
      $ git commit -m "component: summarize changes in 50 chars or less

      * More detailed explanatory text, if necessary. Formatted using
        bullet points, preferably `*`. Wrapped to 72 characters.
      * Explain the problem that this commit is solving. Focus on why you
        are making this change as opposed to how (the code explains that).
        Are there side effects or other unintuitive consequences of this
        change? Here's the place to explain them.
      * The blank line separating the summary from the body is critical
        (unless you omit the body entirely); various tools like `log`,
        `shortlog` and `rebase` can get confused if you run the two
        together.
      * Use words like "Adds", "Fixes" or "Breaks" in the listed bullets to
        help others understand what you did.
      * If your commit closes or addresses an issue, you can mention
        it in any of the bullets after the dot. (closes #XXX) (addresses #YYY)"

      $ git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests and must not decrease test coverage.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring.
3. Check https://travis-ci.org/asclepias/asclepias-broker/pull_requests
   and make sure that all tests pass.
