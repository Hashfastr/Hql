# range
The `range` operator generates a single column table holding a sequence of numbers.
It's a source, so it starts a pipeline.

The syntax is `range name from start to end step step`.

- `end` is included if the sequence lands on it exactly.
- If the step moves away from `end`, the table is empty.
- If `start`, `end` and `step` are all integers the column is a `long`, otherwise it's a `double`.
- `step` can't be 0.
- The table is named `range`.

```
range x from 1 to 10 step 3

{
    "range": [{"x": 1}, {"x": 4}, {"x": 7}, {"x": 10}]
}

range x from 0 to 1 step 0.25

{
    "range": [{"x": 0.0}, {"x": 0.25}, {"x": 0.5}, {"x": 0.75}, {"x": 1.0}]
}
```

Only numeric ranges are supported, datetime/timespan ranges are not.
