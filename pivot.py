#!/home/blissful/scripts/hanping-pivot/.venv/bin/python

"""
Maintains the Hanping Chinese - Writing deck, a clone of the Hanping Chinese deck but with an
inverted card type for writing.

This script modifies the Anki SQL database directly and upserts cards into the inverted deck.
"""

import string
from pprint import pprint
import time
import re
import random
from anki.collection import Collection
from anki.decks import DeckId
from anki.models import NotetypeId
from anki.notes import NoteId

col = Collection("/home/blissful/.local/share/Anki2/User 1/collection.anki2")
assert col.db is not None

COLLECTION_ID = 1
BASE_DECK_ID = 1702789187175
INVERTED_DECK_ID = 1702794938789
WRITING_NOTETYPE_ID = 1702794419655


def guid64() -> str:
    "Return a base91-encoded 64bit random number."

    # https://github.com/ankitects/anki/blob/77cb3220c5e83206725b1f3f2fbdb536dc180ec2/pylib/anki/utils.py#L123
    def base62(num: int, extra: str = "") -> str:
        table = string.ascii_letters + string.digits + extra
        buf = ""
        while num:
            num, mod = divmod(num, len(table))
            buf = table[mod] + buf
        return buf

    def base91(num: int) -> str:
        _BASE91_EXTRA_CHARS = "!#$%&()*+,-./:;<=>?@[]^_`{|}~"
        # all printable characters minus quotes, backslash and separators
        return base62(num, _BASE91_EXTRA_CHARS)

    return base91(random.randint(0, 2**64 - 1))


# Get the new cards to invert.
cursor = col.db.all(
    f"""
    WITH already_inverted_notes AS (
        SELECT id
        FROM notes
        WHERE flds IN (
            SELECT flds
            FROM notes
            WHERE mid = {WRITING_NOTETYPE_ID}
        )
    )
    SELECT id, flds
    FROM notes
    WHERE id NOT IN (SELECT id FROM already_inverted_notes)
    AND mid != {WRITING_NOTETYPE_ID}
    """
)
for row in cursor:
    base_note_id = row[0]
    base_note_desc = re.sub("<[^<]+?>", "", row[1]).replace("\x1f", " ")

    base_note = col.get_note(base_note_id)

    new_note = base_note
    new_note.id = NoteId(0)
    new_note.guid = guid64()
    new_note.mid = NotetypeId(WRITING_NOTETYPE_ID)
    new_note.mod = int(time.time())
    new_note.usn = col.db.scalar("select usn from col")

    print(f"Inserting clone of {base_note_desc}")
    col.add_note(new_note, DeckId(INVERTED_DECK_ID))
