vim.g.operator_sandwich_no_default_key_mappings = true
vim.cmd([[
  " add
  silent! nmap <unique> sa <Plug>(sandwich-add)
  silent! xmap <unique> sa <Plug>(sandwich-add)

  " delete
  silent! nmap <unique> sd <Plug>(sandwich-delete)
  silent! xmap <unique> sd <Plug>(sandwich-delete)
  silent! nmap <unique> sdb <Plug>(sandwich-delete-auto)

  " replace
  silent! nmap <unique> sr <Plug>(sandwich-replace)
  silent! xmap <unique> sr <Plug>(sandwich-replace)
  silent! nmap <unique> srb <Plug>(sandwich-replace-auto)
]])
