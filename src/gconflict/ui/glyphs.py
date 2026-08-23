"""The glyph set the design specifies, readable without colour.

Filled versus hollow is what separates the two sides of a conflict when the
terminal is monochrome or the reader cannot distinguish the two accents.
"""

CURRENT = "◆"      # black diamond, the CURRENT side
INCOMING = "◇"      # white diamond, the INCOMING side

PENDING = "●"       # black circle, a file with conflicts left
UNTOUCHED = "○"     # white circle, a file not opened yet
RESOLVED = "✓"      # check mark, saved and staged
UNSUPPORTED = "⚠"   # warning sign, a conflict type gconflict will not touch

RAIL_RESOLVED = "●"  # black circle, a conflict already decided
RAIL_ACTIVE = "◉"    # fisheye, the conflict being shown
RAIL_PENDING = "○"   # white circle, still undecided

STATUS_INFO = "○"
STATUS_SUCCESS = "✓"
STATUS_WARNING = "△"
STATUS_BLOCKED = "⚠"
