# Operators
Tabular operators come after a `|` and transform the tables flowing through the pipeline.
For operators used inside expressions (`==`, `has`, `+`, `and`, ...) see [Scalar operators](./Scalar-Operators.md).

## Sources
These start a pipeline.

- [datatable](./Operators/Datatable.md): inline table built from literal values
- [range](./Operators/Range.md): single column table holding a numeric sequence

Database sources such as `database('x').index('y')` are [functions](./Functions/Sources.md).

## Filtering and limiting
- [where / filter](./Operators/Where.md): keep rows matching a predicate
- [take / limit](./Operators/Take.md): keep the first N rows
- [top](./Operators/Top.md): sort, then keep the first N rows

## Shaping fields
- [project](./Operators/Project.md): select and compute fields
- [project-away](./Operators/Project.md#project-away): remove fields
- [project-keep](./Operators/Project.md#project-keep): same as `project`, kept for compatibility
- [project-rename](./Operators/Project.md#project-rename): rename fields
- [project-reorder](./Operators/Project.md#project-reorder): move fields to the front
- [extend](./Operators/Extend.md): add or replace computed fields
- [mv-expand](./Operators/MvExpand.md): one row per array element
- [unnest](./Operators/Unnest.md): replace a table with the contents of an object field

## Ordering
- [sort / order](./Operators/Sort.md): sort rows

## Aggregation
- [summarize](./Operators/Summarize.md): aggregate, optionally grouped
- [count](./Operators/Count.md): row count per table

## Combining tables
- [join](./Operators/Join.md): join with the result of another query
- [union](./Operators/Union.md): merge tables in the pipeline into one
- [rename](./Operators/Rename.md): rename tables

## Not implemented
The grammar parses many more Kusto operators than the ones above, but they don't run yet.
They include `as`, `distinct`, `print`, `parse`, `make-series`, `mv-apply`, `lookup`, `search`, `find`, `fork`, `facet`, `sample`, `serialize`, `render`, `evaluate`, `invoke`, `top-nested`, `top-hitters`, `reduce` and the graph operators.
Using one fails at compile time.
