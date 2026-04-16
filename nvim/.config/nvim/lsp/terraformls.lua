return {
    cmd = { "terraform-ls", "serve" },
    filetypes = { "terraform", "terraform-vars" },
    root_markers = {
        ".terraform",
        ".terraform.lock.hcl",
        "*.tf",
        ".git",
    },
}
