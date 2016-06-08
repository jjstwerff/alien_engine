all:	static testing server

static:
	/usr/bin/pylint3 --rcfile ~/bin/pylintrc *.py test/*.py
	pep8 *.py test/*.py

testing:
	nosetests3 --nocapture

server:
	python3 read.py

clean:
	rm coverage .coverage __pycache__ test/*.result -rf

cover:
	rm coverage -rf
	nosetests3 -q --nocapture --cover-erase --cover-tests --with-coverage --cover-html --cover-html-dir=coverage --cover-package=fields,rbtree,read,server,tables,html,testing
	firefox coverage/index.html &
