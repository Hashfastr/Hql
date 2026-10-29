# unnest
The `unnest` operator replaces a table with the contents of one of its object fields.
The object's keys become the table's top level columns, and **every other column is dropped**.
This is an Hql specific operator, Kusto doesn't have it.

If the field holds an array, it is expanded to one row per element first.
An array of objects then gives one column per key.
An array of scalars gives a single column named after the element type.

By default every table is unnested (pattern `*`).
The `on` clause restricts it to tables matching comma separated patterns.
Tables that don't have the field are left as is.

```
database('json').file('t.json')
| project a, o
| unnest o

// t.json rows look like {"a": 1, "o": {"p": 1, "q": "s"}}
{
    "t.json": [{"p": 1, "q": "s"}, {"p": 2, "q": "t"}, {"p": 3, "q": "u"}]
}

// Only unnest tables matching t*, u.json passes through
database('json').file('t.json', 'u.json')
| unnest o on t*
```

Useful for sources that wrap every record in an envelope, for example `| unnest _source`.
