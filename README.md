# Houston

[![Build Status](https://travis-ci.org/squaresLab/Houston.svg?branch=master)](https://travis-ci.org/squaresLab/Houston)
[![Coverage Status](https://coveralls.io/repos/github/squaresLab/Houston/badge.svg?branch=master)](https://coveralls.io/github/squaresLab/Houston?branch=master)

Awesome automated integration-test generation for robotic systems.


## Getting Started

We strongly encourage installing `houston` within a Python virtual
environment, created via [virtualenv](https://virtualenv.pypa.io/en/latest/)
or [pipenv](https://pipenv.readthedocs.io/en/latest/)). To (create and)
enter a `pipenv` project for `houston`, execute the following:

```
$ pipenv shell
(houston) $ ...
```

Before installing `houston`, Z3 must be installed from source within the
virtual environment:

```
(houston) $ git clone https://github.com/Z3Prover/z3 local-z3
(houston) $ cd local-z3
(houston) $ python scripts/mk_make.py
(houston) $ cd build
(houston) $ make install -j4
(houston) $ export PYTHONPATH="${PWD}/python:${PYTHONPATH}"
```

Once Z3 is installed, `houston` can be installed via:

```
(houston) $ pip install .
```

### Executing a test case

```
import houston
import bugzoo

# we use BugZoo to provide an executable snapshot for the system under test
bz = bugzoo.BugZoo()
snapshot = bz.bugs['ardu:X']

# we produce a description of the system under test
sut = houston.ardu.ArduRover(snapshot)

# we generate a test case
# ...

# we
# ...
```
