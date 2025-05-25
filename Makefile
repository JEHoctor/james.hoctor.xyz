PY?=
PELICAN?=uv run pelican -v
PELICANOPTS=

BASEDIR=$(CURDIR)
INPUTDIR=$(BASEDIR)/content
OUTPUTDIR=$(BASEDIR)/output
CONFFILE=$(BASEDIR)/pelicanconf.py
PUBLISHCONF=$(BASEDIR)/publishconf.py


DEBUG ?= 0
ifeq ($(DEBUG), 1)
	PELICANOPTS += -D
endif

RELATIVE ?= 0
ifeq ($(RELATIVE), 1)
	PELICANOPTS += --relative-urls
endif

SERVER ?= "0.0.0.0"

PORT ?= 0
ifneq ($(PORT), 0)
	PELICANOPTS += -p $(PORT)
endif


help:
	@echo 'Makefile for a pelican Web site                                           '
	@echo '                                                                          '
	@echo 'Usage:                                                                    '
	@echo '   make html                           (re)generate the web site          '
	@echo '   make clean                          remove the generated files         '
	@echo '   make regenerate                     regenerate files upon modification '
	@echo '   make publish                        generate using production settings '
	@echo '   make serve [PORT=8000]              serve site at http://localhost:8000'
	@echo '   make serve-global [SERVER=0.0.0.0]  serve (as root) to $(SERVER):80    '
	@echo '   make devserver [PORT=8000]          serve and regenerate together      '
	@echo '   make devserver-global               regenerate and serve on 0.0.0.0    '
	@echo '   make new-post                       create an empty blog post          '
	@echo '   make retitle-post                   rename a blog post                 '
	@echo '   make check-scripts                  run ShellCheck+shfmt on all scripts'
	@echo '   make init                           initialize the repo for development'
	@echo '   make check-precommit                run pre-commit checks              '
	@echo '   make validate                       validate generated HTML and CSS    '
	@echo '   make mirror-redacted                mirror repo without drafts         '
	@echo '                                                                          '
	@echo 'Set the DEBUG variable to 1 to enable debugging, e.g. make DEBUG=1 html   '
	@echo 'Set the RELATIVE variable to 1 to enable relative urls                    '
	@echo '                                                                          '

html:
	$(PELICAN) "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

clean:
	[ ! -d "$(OUTPUTDIR)" ] || rm -rf "$(OUTPUTDIR)"
	rm -rf .venv

regenerate:
	$(PELICAN) -r "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

publish:
	$(PELICAN) "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(PUBLISHCONF)" $(PELICANOPTS)

serve:
	$(PELICAN) -l "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

serve-global:
	$(PELICAN) -l "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS) -b $(SERVER)

devserver:
	$(PELICAN) -lr "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

devserver-global:
	$(PELICAN) -lr "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS) -b 0.0.0.0

new-post:
	@./automation/new-post.sh

retitle-post:
	@./automation/retitle-post.sh

check-scripts:
	uvx --from='shfmt-py' shfmt -d **/*.sh
	uvx --from='shellcheck-py' shellcheck **/*.sh

init:
	git submodule update --init
	uvx --from='pre-commit' pre-commit install
	(cd hyde-personalized/ && uvx --from='pre-commit' pre-commit install)
	npm install

check-precommit:
	uvx --from='pre-commit' pre-commit run --all-files

validate:
	@if [ ! -d output ]; then echo "No output/ directory - run 'make html' or another similar target first" >&2; exit 1; fi
	npx htmlhint output/
	npx csslint output/
	npx stylelint output/
	diff .csslintrc hyde-personalized/.csslintrc

mirror-redacted:
	@./automation/mirror-redacted.sh


.PHONY: help html clean regenerate publish serve serve-global devserver devserver-global new-post retitle-post check-scripts init check-precommit validate mirror-redacted
