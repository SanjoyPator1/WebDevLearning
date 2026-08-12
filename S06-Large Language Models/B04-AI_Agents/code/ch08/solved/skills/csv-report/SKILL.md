---
name: csv-report
description: Generate a short markdown summary report (totals, averages, one-line takeaway) from a small table of numeric data. Use this when asked to summarize or report on tabular/CSV-style data, not for open-ended data analysis.
---

## Workflow

1. Parse the input rows into a list of numbers.
2. Compute total and average.
3. Fill in `templates/report_template.md` with the computed values.
4. Return the filled template as the final report -- do not add extra commentary outside the template's structure.

## Output Format

A markdown document following exactly the structure in `templates/report_template.md`: a title, a totals line, an average line, and a one-sentence takeaway.

## Definition of Done

The report contains a total, an average, and a takeaway sentence, and no numbers in it were invented -- every figure traces back to the input rows.

## Quality Checks

Common mistake: computing the average over the wrong count (e.g. counting a header row as data). Always confirm the row count excludes headers before dividing.
