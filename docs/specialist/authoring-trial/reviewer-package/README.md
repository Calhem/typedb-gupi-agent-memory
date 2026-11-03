# Reviewer package: two-document annotation trial

Thank you for reviewing. Everything here is a **provisional draft**: your review decides what changes before
a small trial starts.

## What this is
A small study will ask people to read business documents (minutes, emails, chat) and record carefully:
- who said what
- about whom and when
- how sure anyone can be

Software systems will later be compared against those records. Before anyone writes the trial documents,
we want someone who has **not** worked on any of those systems to check four things:
- that the reading guidelines are clear and fair
- that the spreadsheet for recording them is usable
- that answers will be scored fairly
- that each system's output is translated into the common answer form honestly

No programming knowledge is needed. The fictional organisations and people in the examples are invented.

## What to do (about 2-3 hours)
1. **Read guidelines-v0.md §0-§15** (about 45 minutes). Stop before §16, which contains the answers to the
   practice.
2. **Do the practice** (`practice.md`, about 45 minutes). Five short passages, with questions. Answer them
   in plain words, or try the spreadsheet template (step 4).
3. **Read guidelines §16-§18,** and note where your practice answers differ and who you think is right.
4. **Look at the spreadsheet template** (`../annotation-template/README.md` and its CSV files). Open the
   filled example in `../dry-check/sheets/` in a spreadsheet program, and try adding one or two rows.
5. **Skim the scoring contract** (`../scoring-protocol-v0.md` §1-§4, and Appendix A) and the system
   mappings (`../system-mappings-v0.md`).
6. **Answer the short form** (`core-form.md`, 13 questions). That is all we need.

**Optional, if you have time:**
- `../review-checklist-v0.md`: the full 79-item checklist. Use it to go deeper on any area; it is not
  required.
- `../bias-audit-v0.md`: our own audit of where the guidelines might favour structured systems. Please read
  it **after** answering the form, so that it does not steer you.
- `../scoring-nl-experimental-v0.md`: an experimental, secondary scoring method for free-text answers.

**Please do not read** the software's code, its database schema, or its design records. The point is to
test whether these documents stand on their own.

## What to send back
- the filled `core-form.md`
- your practice answers
- your rough time per step

Please also declare any connection to the project, TypeDB, the owner, or any compared system. A connection
does not disqualify you; it is reported.

## The package's contents and versions
`MANIFEST.sha256` lists every file in the package with its SHA-256, so it is clear exactly which version
you reviewed. From the repository, the package can be built as a single zip with:

    git archive --format=zip -o reviewer-package.zip HEAD $(cut -c67- docs/specialist/authoring-trial/reviewer-package/MANIFEST.sha256)

The manifest's paths are relative to the repository root.
