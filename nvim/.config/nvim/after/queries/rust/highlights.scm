; extends

; Add a background to SQL passed to sqlx query functions.
(call_expression
  function: [
    (generic_function
      function: (scoped_identifier
        path: (identifier) @_sqlx_path
        name: (identifier) @_sqlx_fn))
    (scoped_identifier
      path: (identifier) @_sqlx_path
      name: (identifier) @_sqlx_fn)
  ]
  arguments: (arguments
    .
    [
      (raw_string_literal
        (string_content) @sqlx.query)
      (string_literal
        (string_content) @sqlx.query)
    ])
  (#eq? @_sqlx_path "sqlx")
  (#any-of? @_sqlx_fn
    "query"
    "query_as"
    "query_as_unchecked"
    "query_as_with"
    "query_scalar"
    "query_scalar_unchecked"
    "query_scalar_with"
    "query_unchecked"
    "query_with")
  (#set! priority 101))
