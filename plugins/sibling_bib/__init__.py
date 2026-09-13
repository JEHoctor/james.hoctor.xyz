"""Point pelican-cite2 at a per-post ``.bib`` file that shares the post's stem.

pelican-cite2 reads citations from one global ``PUBLICATIONS_SRC`` file, optionally merged
with a per-article ``publications_src`` metadata field. The convention on this site is that
``content/<slug>.md`` cites entries from ``content/<slug>.bib``, so this plugin fills in
``publications_src`` automatically whenever such a sibling file exists. An author never has to
write the metadata field by hand.

Three bugs in pelican-cite2 1.1.5 get in the way of per-post files, and this plugin works
around all of them:

* ``_get_global_bib`` calls ``Parser().parse_file(None)`` when ``PUBLICATIONS_SRC`` is unset,
  which raises ``TypeError`` (not the ``PybtexError`` it catches) and aborts the build.
* ``_get_bib`` does ``deepcopy(self.global_bib).add_entries(...)`` for any article with a
  ``publications_src``, which fails on a ``None`` global bibliography.
* ``_get_bib`` passes ``local_bib.entries`` (a dict) to ``BibliographyData.add_entries``, which
  expects ``(key, entry)`` pairs; iterating the dict yields bare keys, so merging any per-article
  file dies with ``ValueError: too many values to unpack``. The method is marked ``TODO Test``
  upstream, and as shipped ``publications_src`` cannot work at all.

The first two are handled by giving pelican-cite2 a global bibliography: an empty
``BibliographyData`` is truthy, so pointing ``PUBLICATIONS_SRC`` at the empty file shipped next
to this module keeps both code paths happy without adding any entries. The third is handled by
replacing ``CitationsProcessor._get_bib`` with a corrected copy. Drop that patch once upstream
fixes it.

Finally, pelican-cite2's inline label markup is tidied after it runs: the whitespace its template
leaves inside the anchor is removed, the label is wrapped in square brackets so the ``number``
label style reads as ``[1]``, and the anchor gets ``class="cite"`` for styling.
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

from pelican import signals
from pelican.generators import ArticlesGenerator, Generator, PagesGenerator
from pelican.plugins.pelican_cite2 import CitationsProcessor
from pybtex.database import BibliographyData, PybtexError
from pybtex.database.input.bibtex import Parser

if TYPE_CHECKING:
    from pelican import Pelican
    from pelican.contents import Content

logger = logging.getLogger(__name__)

_PUBLICATIONS_SRC = "PUBLICATIONS_SRC"
_EMPTY_BIB = Path(__file__).with_name("empty.bib")


def set_default_global_bib(pelican: Pelican) -> None:
    """Give pelican-cite2 an (empty) global bibliography if the site does not configure one."""
    if not pelican.settings.get(_PUBLICATIONS_SRC):
        pelican.settings[_PUBLICATIONS_SRC] = str(_EMPTY_BIB)


def _get_bib(self: CitationsProcessor, article: Content) -> BibliographyData:
    """Return the global bibliography merged with the article's ``publications_src``, if any.

    Corrected copy of ``CitationsProcessor._get_bib`` from pelican-cite2 1.1.5 (see module
    docstring). Per-article entries are layered over the global ones; a duplicate key is a
    ``PybtexError`` and falls back to the global bibliography with a warning, like a parse error.
    """
    refs_file = article.metadata.get("publications_src")
    if refs_file is None:
        return self.global_bib
    try:
        local_bib = Parser().parse_file(refs_file)
        merged = deepcopy(self.global_bib)
        merged.add_entries(local_bib.entries.items())
    except PybtexError as e:
        logger.warning("sibling_bib: failed to load %s: %s", refs_file, e)
        return self.global_bib
    return merged


CitationsProcessor._get_bib = _get_bib  # type: ignore[method-assign] # noqa: SLF001

# What pelican-cite2's templates/label.html emits for each inline citation. The newlines inside the
# anchor render as spaces, so "see [@k]." would come out as "see  1 ." in the browser.
_LABEL_RE = re.compile(r"<a href='#(?P<ref>[^']*)' id='(?P<id>ref-[^']*)'>\s*(?P<label>.*?)\s*</a>", re.DOTALL)


def tidy_labels(generators: list[Generator]) -> None:
    """Rewrite pelican-cite2's inline labels as ``<a class="cite" ...>[label]</a>``.

    Runs on ``all_generators_finalized`` after pelican-cite2 (plugins connect in ``PLUGINS`` order),
    and only touches content that pelican-cite2 marked with a bibliography.
    """
    for generator in generators:
        for content in _contents_of(generator):
            if hasattr(content, "bibliography"):
                content._content = _LABEL_RE.sub(  # noqa: SLF001
                    r'<a class="cite" href="#\g<ref>" id="\g<id>">[\g<label>]</a>',
                    content._content,  # noqa: SLF001
                )


def _contents_of(generator: Generator) -> list[Content]:
    if isinstance(generator, ArticlesGenerator):
        return generator.articles + generator.translations + generator.drafts
    if isinstance(generator, PagesGenerator):
        return generator.pages
    return []


def attach_sibling_bib(content: Content) -> None:
    """Set ``publications_src`` to ``<source stem>.bib`` when that file exists.

    Explicit ``publications_src`` metadata in the post wins over the sibling convention.
    """
    source_path = getattr(content, "source_path", None)
    if not source_path or "publications_src" in content.metadata:
        return
    sibling = Path(source_path).with_suffix(".bib")
    if sibling.is_file():
        content.metadata["publications_src"] = str(sibling)


def register() -> None:
    """Connect to Pelican's signals."""
    signals.initialized.connect(set_default_global_bib)
    signals.content_object_init.connect(attach_sibling_bib)
    signals.all_generators_finalized.connect(tidy_labels)
