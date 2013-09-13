# Copyright 2013 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import datetime
import sys
import textwrap

import coverage as _coverage
import invoke
import pytest


@invoke.task
def tests(suite=None, coverage=False, pdb=False):
    if suite is None:
        coverage = True
        markers = []
    elif suite == "unit":
        markers = ["unit"]
    elif suite == "functional":
        markers = ["functional"]
    elif suite == "coverage":
        coverage = True
        markers = ["unit"]
    else:
        raise ValueError("Invalid name for suite. Must be one of unit, "
                                                        "functional, coverage")

    args = []

    # Add markers to the arguments
    if markers:
        args += ["-m", " and ".join(markers)]

    # Add coverage to the arguments
    if coverage:
        args += ["--cov", "warehouse"]

    # Add pdb to the arguments
    if pdb:
        args += ["--pdb"]

    exitcode = pytest.main(args)
    if exitcode:
        sys.exit(exitcode)

    if suite == "coverage":
        # When testing for coverage we want to fail the test run if we do not
        #   have 100% coverage.
        cov = _coverage.coverage(config_file=".coveragerc")
        cov.load()

        with open("/dev/null", "w") as devnull:
            covered = cov.report(file=devnull)

        if int(covered) < 100:
            print("")
            sys.exit("[FAILED] Coverage is less than 100%")


@invoke.task
def compile():
    # Compile the css for Warehouse
    invoke.run(
        "bundle exec compass compile --force warehouse/static")


@invoke.task
def run():
    # Use foreman to start up all our development processes
    invoke.run("bundle exec foreman start -d devel -e devel/env", pty=True)


@invoke.task
def release():
    # We can only make releases from the master branch, so ensure we are on it
    # TODO: Ensure there are no half committed files or anything like that
    refs = invoke.run("git symbolic-ref -q HEAD", echo=True)
    if "refs/heads/master" not in refs.stdout:
        sys.exit("[ERROR] Can only make releases from the master branch")

    # Determine the next version number using git tags
    version_series = datetime.datetime.utcnow().strftime("%y.%m")
    version_series = ".".join([str(int(x)) for x in version_series.split(".")])
    tags = invoke.run("git tag -l 'v{}.*'".format(version_series), echo=True)
    versions = sorted(tags.stdout.split())
    version_num = int(versions[-1].rsplit(".")[-1]) + 1 if versions else 0
    version = ".".join([version_series, str(version_num)])
    version = ".".join([str(int(x)) for x in version.split(".")])

    # Regenerate __about__.py with the new version number
    with open("warehouse/__about__.py", "w") as about:
        text = textwrap.dedent("""
            # THIS FILE IS AUTOMATICALLY GENERATED, To edit it, see tasks.py
            __all__ = [
                "__title__", "__summary__", "__uri__", "__version__",
                "__author__", "__email__", "__license__", "__copyright__",
            ]

            __title__ = "warehouse"
            __summary__ = "Next Generation Python Package Index"
            __uri__ = "https://github.com/dstufft/warehouse"

            __version__ = "{version}"

            __author__ = "Donald Stufft"
            __email__ = "donald@stufft.io"

            __license__ = "Apache License, Version 2.0"
            __copyright__ = "Copyright 2013 Donald Stufft"
        """).lstrip()
        text = text.format(version=version)
        about.write(text)

    # Commit the new __about__.py
    invoke.run("git add warehouse/__about__.py", echo=True)
    invoke.run("git commit -m 'Bumped version to {}' "
               "warehouse/__about__.py".format(version), echo=True)

    # Tag the new commit
    # TODO: Have this pull a Changelog and embed it in the tag
    invoke.run("git tag -s v{0} -m 'Released version {0}'".format(version),
        echo=True,
    )

    # Checkout our version and clean up any unneeded files
    invoke.run("git checkout v{}".format(version), echo=True)

    # Create our packages & upload them to PyPI
    invoke.run("pip install Wheel", echo=True)
    invoke.run("python setup.py sdist bdist_wheel upload --sign", echo=True)

    # Return to the master branch
    invoke.run("git checkout master", echo=True)

    # Push changes to Origin
    invoke.run("git push origin master", echo=True)
    invoke.run("git push --tags origin", echo=True)
