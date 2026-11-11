"""Moduły z konwerterami. Nowa grupa = nowy moduł + jedna linia importu poniżej."""

from . import structured  # noqa: F401  (Grupa A: CSV <-> JSON)
from . import text        # noqa: F401  (Grupa B: TXT <-> DOCX)
from . import office      # noqa: F401  (Grupa C: DOCX/ODT -> PDF, DOCX <-> ODT)
