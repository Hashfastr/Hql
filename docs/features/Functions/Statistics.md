# Statistics functions

## series_stats()
`series_stats(field [, ignore_nonfinite])` computes summary statistics for a numeric field.
It doesn't aggregate the table: the per-table results are repeated on every row.

Output fields, prefixed with `series_stats_<field>_`:
`min`, `min_idx`, `max`, `max_idx`, `avg`, `stdev`, `variance`.
`min_idx` and `max_idx` are the row positions of the first minimum and the first maximum.

`ignore_nonfinite` is a boolean literal, `false` by default.
When it's `true`, NaN and infinite values are left out of float fields before computing.

Besides the per-table values, it also adds a table named `*` with the statistics computed over **all** tables together (without the `_idx` fields).

```
// a values: 1, 2, 3
database('json').file('t.json')
| extend s = series_stats(a)

// Every row of t.json gets:
"s": {
    "series_stats_a_min": 1, "series_stats_a_min_idx": 0,
    "series_stats_a_max": 3, "series_stats_a_max_idx": 2,
    "series_stats_a_avg": 2.0, "series_stats_a_stdev": 1.0, "series_stats_a_variance": 1.0
}
```
