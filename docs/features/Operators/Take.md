# take
The `take` operator truncates tables to their first N rows.
`limit` is an alias.
By default it truncates every table, i.e. the pattern `*`.
The `from` clause restricts it to tables matching one or more comma separated patterns; any other tables pass through untouched.

The limit has to be a non-negative integer, a negative limit is rejected at compile time.

Kusto queries containing this operator are compatible with Hql and will return the same results.

```
// Truncates all tables to 10 results
Database
| take 10

// limit is the same operator
Database
| limit 10

// Truncates only tables matching so-beats-* to 53 results
Database
| take 53 from ['so-beats-*']

// Truncates tables matching either pattern to 100 results
Database
| take 100 from ['so-beats-*'], ['so-network-*']
```

```
database('json').file('t.json', 'u.json')
| project a
| take 1 from u*

{
    "t.json": [{"a": 1}, {"a": 2}, {"a": 3}],
    "u.json": [{"a": 1}]
}
```
