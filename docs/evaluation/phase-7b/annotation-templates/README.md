# Annotation templates (blank)

These files are for independent contributors: passage authors, annotators and adjudicators. They are
blank, and must stay so in the repository until the corpus is frozen.

| File | Filled by | Rules |
|---|---|---|
| `passages.csv` | passage authors | ../corpus-specification.md |
| `assertions.csv` | each annotator, separately (one copy each: `assertions-A.csv`, `assertions-B.csv`) | ../annotation-guidelines.md §3 |
| `adjudication.csv` | the adjudicator | ../annotation-guidelines.md §6 |
| `contributor-declaration.md` | every contributor | — |

**Spreadsheets:** you can use any spreadsheet program. Keep the column headers exactly, save as CSV in UTF-8,
and paste passage text unchanged (line breaks are allowed inside quoted cells).

**Checking your files:**

    uv run python -I -m gupi.benchmarks.phase7b.annotations check <folder with passages.csv and assertions-*.csv>
    uv run python -I -m gupi.benchmarks.phase7b.annotations compare <assertions-A.csv> <assertions-B.csv> <passages.csv>

`check` reports structural problems only:
- a span that does not occur in the passage
- a participant surface not in the passage
- an unknown value
- a missing id
- a target that does not exist

`compare` lists disagreements for adjudication. Neither command judges whether an annotation is right.
