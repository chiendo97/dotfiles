local minuet_filetypes = { "python", "lua", "rust", "go", "markdown" }

vim.pack.add({ "https://github.com/milanglacier/minuet-ai.nvim" })

local provider = "openai"
local provider_options = {}
local openai_base_url = vim.env.OPENAI_BASE_URL

if openai_base_url and openai_base_url ~= "" then
    provider = "openai_compatible"

    local openai_endpoint = openai_base_url:gsub("/+$", "")
    if not openai_endpoint:match("/chat/completions$") then
        openai_endpoint = openai_endpoint .. "/chat/completions"
    end

    local optional = {
        max_tokens = 96,
        top_p = 0.9,
    }

    if vim.env.MINUET_DISABLE_THINKING == "1" or vim.env.MINUET_DISABLE_THINKING == "true" then
        optional.chat_template_kwargs = { enable_thinking = false }
    end

    provider_options.openai_compatible = {
        api_key = "OPENAI_API_KEY",
        end_point = openai_endpoint,
        model = vim.env.MINUET_MODEL or "openai/gpt-5-mini",
        name = "OpenAI-compatible",
        optional = optional,
    }
end

require("minuet").setup({
    provider = provider,
    request_timeout = 2.5,
    throttle = 1500,
    debounce = 600,
    n_completions = 1,
    provider_options = provider_options,
    lsp = {
        enabled_ft = minuet_filetypes,
        completion = { enable = false },
        inline_completion = {
            enable = true,
            enabled_auto_trigger_ft = minuet_filetypes,
        },
    },
})
