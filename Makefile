PY?=
PELICAN?=uvx --from='pelican[markdown]' --with='pelican-render-math,pelican-seo' pelican -v
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
	@echo '   $$(make pelican-command) [args]      Run pelican with provided arguments'
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
	@echo '   make check-scripts                  run ShellCheck on all scripts      '
	@echo '   make init-precommit                 set up pre-commit hooks            '
	@echo '   make check-precommit                run pre-commit checks              '
	@echo '   make find-drafts                    find draft posts                   '
	@echo '   make check-no-drafts                fail if there are draft posts      '
	@echo '   make build-drafts                   build draft posts from all branches'
	@echo '                                                                          '
	@echo 'Set the DEBUG variable to 1 to enable debugging, e.g. make DEBUG=1 html   '
	@echo 'Set the RELATIVE variable to 1 to enable relative urls                    '
	@echo '                                                                          '

pelican-command:
	@echo $(PELICAN)

html:
	$(PELICAN) "$(INPUTDIR)" -o "$(OUTPUTDIR)" -s "$(CONFFILE)" $(PELICANOPTS)

clean:
	[ ! -d "$(OUTPUTDIR)" ] || rm -rf "$(OUTPUTDIR)"

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
	find . -type f -name "*.sh" -exec uvx --from='shellcheck-py' shellcheck {} +

init-precommit:
	uvx --from='pre-commit' pre-commit install

check-precommit:
	uvx --from='pre-commit' pre-commit run --all-files

find-drafts:
	@find content/ -type f -name '*.md' -execdir grep -q '^Status: draft$$' '{}' \; -print

check-no-drafts:
	@./automation/check-no-drafts.sh

build-drafts:
	@./automation/build-drafts.sh


.PHONY: help pelican-command html clean regenerate publish serve serve-global devserver devserver-global new-post retitle-post check-scripts init-precommit check-precommit find-drafts check-no-drafts build-drafts
