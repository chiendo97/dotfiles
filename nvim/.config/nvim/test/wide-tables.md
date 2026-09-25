# Wide Table Test for render-markdown.nvim

Open this in a narrow split (`:vsplit` then narrow it) to force tables to
overflow. With the new cell-wrapping (`wrap = true`, `cell = 'trimmed'`),
cells should wrap inside the window width instead of spilling off-screen.

## Table 1 — many columns

| id | name | email | department | location | manager | start_date | salary | status | notes |
|----|------|-------|------------|----------|---------|------------|--------|--------|-------|
| 1 | alice | <a@x.io> | eng | sfo | bob | 2021-03-01 | 145000 | active | senior backend engineer, owns payments service and the internal grpc gateway used by every team |
| 2 | bob | <b@x.io> | eng | nyc | carol | 2019-07-15 | 160000 | active | engineering manager |
| 3 | carol | <c@x.io> | design | remote | dave | 2022-01-10 | 130000 | active | lead product designer |
| 4 | dave | <d@x.io> | eng | sfo | eve | 2020-11-20 | 152000 | active | infra, kubernetes and ci |

## Table 2 — one very long cell

| feature | description |
|---------|-------------|
| cell wrapping | this cell is deliberately much longer than the window width so the renderer has to decide where to break the line. ideally it breaks on word boundaries and preserves readability while keeping the column alignment intact. |
| short cell | fits easily |

## Table 3 — mixed widths, long content in multiple cells

| column_a | column_b | column_c |
|----------|----------|----------|
| short | a moderately long value that may or may not wrap depending on the current window width and the font being used | another long value here with different words to exercise the wrapping logic in a second column at the same time |
| another | short | short |
| third row | medium length | long enough to wrap hopefully on a word boundary rather than in the middle of one of these fairly long words |

## Table 4 — wide with alignment markers

| left-aligned   | center     | right-aligned |
|:---------------|:----------:|--------------:|
| l              |     c      |             1 |
| a longer left  |      c2    |         22222 |
| the longest left cell value in this whole table to force the column to be wide | c3 | 333333 |

*Checklist while testing:*

- [ ] no horizontal overflow / text spilling past the right edge
- [ ] borders (round preset) stay aligned when a cell wraps
- [ ] wrapping splits on word boundaries
- [ ] `nowrap` window option still behaves sensibly
- [ ] resizing the window re-wraps the table
