APPNAME = server-core
DEPS =
VIRTUALENV = virtualenv
PYTHON = bin/python
EZ = bin/easy_install
NOSE = bin/nosetests -s --with-xunit
FLAKE8 = bin/flake8
COVEROPTS = --cover-html --cover-html-dir=html --with-coverage --cover-package=services
TESTS = services
PKGS = services
COVERAGE = bin/coverage
PYLINT = bin/pylint
PYPI2RPM = bin/pypi2rpm.py
SERVER = dev-auth.services.mozilla.com
SCHEME = https

.PHONY: all build build_extras build_rpms test

all:	build

build:
	$(VIRTUALENV) --no-site-packages --distribute .
	$(PYTHON) build.py $(APPNAME) $(DEPS)
	$(EZ) -U nose
	$(EZ) -U WebTest
	$(EZ) -U PasteDeploy

build_extras:
	$(EZ) -U mysql-python
	$(EZ) -U recaptcha-client
	$(EZ) -U wsgiproxy
	$(EZ) -U wsgi_intercept
	$(EZ) http://ziade.org/python-ldap-2.3.12.tar.gz
	$(EZ) -U coverage
	$(EZ) -U flake8
	$(EZ) -U pylint
	$(EZ) -U pygments

test:
	$(NOSE) $(TESTS)

coverage:
	rm -rf html
	- $(NOSE) $(COVEROPTS) $(TESTS)

build_rpms:
	$(EZ) -U pypi2rpm
	rm -rf $(CURDIR)/rpms
	mkdir $(CURDIR)/rpms
	rm -rf build; $(PYTHON) setup.py --command-packages=pypi2rpm.command bdist_rpm2 --spec-file=Services.spec --dist-dir=$(CURDIR)/rpms
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms cef --version=0.2
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms webob --version=1.0.7
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms paste --version=1.7.5.1
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms pastedeploy --version=1.3.4
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms pastescript --version=1.7.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms mako --version=0.4.1
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms markupsafe --version=0.12
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms beaker --version=1.5.4
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms python-memcached --version=1.47
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms simplejson --version=2.1.6
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms routes --version=1.12.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms sqlalchemy --version=0.6.6
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms mysql-python --version=1.2.3
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms wsgiproxy --version=0.2.2
	$(PYPI2RPM) --dist-dir=$(CURDIR)/rpms recaptcha-client --version=1.0.6

