#!/usr/bin/env python

"""
Maintains the Hanping Chinese - Writing deck, a clone of the Hanping Chinese deck but with an
inverted card type for writing.

This script modifies the Anki SQL database directly and upserts cards into the inverted deck.
"""

import string
import time
import sqlite3
from pathlib import Path
import re
import random

DATABASE_PATH = (
    Path.home() / ".local" / "share" / "Anki2" / "User 1" / "collection.anki2"
)
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


with sqlite3.connect(DATABASE_PATH) as conn:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Get the new cards to invert.
    cursor = conn.execute(
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
        note_guid = guid64()
        cursor = conn.execute(
            f"""
            INSERT INTO notes (guid, mid, mod, usn, tags, flds, sfld, csum, flags, data)
            SELECT
                '{note_guid}'
              , {WRITING_NOTETYPE_ID}
              , {int(time.time())}
              , (SELECT usn FROM col WHERE id = {COLLECTION_ID})
              , tags
              , flds
              , sfld
              , csum
              , flags
              , data
            FROM notes
            WHERE id = {base_note_id}
            RETURNING id
            """,
        )
        note_id = cursor.fetchone()[0]
        print(f"Inserted new note {note_id=} for base note {base_note_desc=}")
        break


print("Done")

# We get some sync error with how the following card insertion works, so we are instead
# inserting a note and then using Check Database to generate the card.

# cursor = conn.execute(
#     f"""
#     INSERT INTO cards (nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data)
#     SELECT
#         {note_id}
#       , {INVERTED_DECK_ID}
#       , ord
#       , {int(time.time())}
#       , (SELECT usn FROM col WHERE id = {COLLECTION_ID})
#       , 0 -- type
#       , 0 -- queue
#       , (SELECT COALESCE(MAX(due), 0) + 1 FROM cards WHERE did = {INVERTED_DECK_ID})
#       , 0 -- ivl
#       , 0 -- factor
#       , 0 -- reps
#       , 0 -- lapses
#       , 0 -- left
#       , 0 -- odue
#       , 0 -- odid
#       , flags
#       , data
#     FROM cards
#     WHERE id = {base_card_id}
#     RETURNING id
#     """,
# )
# card_id = cursor.fetchone()[0]
