return {
    {
        "robitx/gp.nvim",
        cmd = {
            "GpAppend",
            "GpChatFinder",
            "GpChatNew",
            "GpChatPaste",
            "GpChatToggle",
            "GpContext",
            "GpEnew",
            "GpImplement",
            "GpNew",
            "GpNextAgent",
            "GpPopup",
            "GpPrepend",
            "GpProofread",
            "GpRewrite",
            "GpStop",
            "GpTabnew",
            "GpVnew",
        },
        init = function()
            -- Setup shortcuts here (see Usage > Shortcuts in the Documentation/Readme)
            local function keymapOptions(desc)
                return {
                    noremap = true,
                    silent = true,
                    nowait = true,
                    desc = "GPT: " .. desc, -- Improved description prefix
                }
            end

            -- Chat commands
            vim.keymap.set({ "n" }, "<C-g>c", "<cmd>GpChatNew<cr>", keymapOptions("New Chat"))
            vim.keymap.set({ "n" }, "<C-g>t", "<cmd>GpChatToggle<cr>", keymapOptions("Toggle Chat"))
            vim.keymap.set({ "n" }, "<C-g>f", "<cmd>GpChatFinder<cr>", keymapOptions("Chat Finder"))

            vim.keymap.set("v", "<C-g>c", ":<C-u>'<,'>GpChatNew<cr>", keymapOptions("Visual Chat New"))
            vim.keymap.set("v", "<C-g>p", ":<C-u>'<,'>GpChatPaste<cr>", keymapOptions("Visual Chat Paste"))
            vim.keymap.set("v", "<C-g>t", ":<C-u>'<,'>GpChatToggle<cr>", keymapOptions("Visual Toggle Chat"))

            vim.keymap.set({ "n" }, "<C-g><C-x>", "<cmd>GpChatNew split<cr>", keymapOptions("New Chat split"))
            vim.keymap.set({ "n" }, "<C-g><C-v>", "<cmd>GpChatNew vsplit<cr>", keymapOptions("New Chat vsplit"))
            vim.keymap.set({ "n" }, "<C-g><C-t>", "<cmd>GpChatNew tabnew<cr>", keymapOptions("New Chat tabnew"))

            vim.keymap.set("v", "<C-g><C-x>", ":<C-u>'<,'>GpChatNew split<cr>", keymapOptions("Visual Chat New split"))
            vim.keymap.set(
                "v",
                "<C-g><C-v>",
                ":<C-u>'<,'>GpChatNew vsplit<cr>",
                keymapOptions("Visual Chat New vsplit")
            )
            vim.keymap.set(
                "v",
                "<C-g><C-t>",
                ":<C-u>'<,'>GpChatNew tabnew<cr>",
                keymapOptions("Visual Chat New tabnew")
            )

            -- Prompt commands
            vim.keymap.set({ "n" }, "<C-g>r", "<cmd>GpRewrite<cr>", keymapOptions("Inline Rewrite"))
            vim.keymap.set({ "n" }, "<C-g>a", "<cmd>GpAppend<cr>", keymapOptions("Append (after)"))
            vim.keymap.set({ "n" }, "<C-g>b", "<cmd>GpPrepend<cr>", keymapOptions("Prepend (before)"))

            vim.keymap.set("v", "<C-g>r", ":<C-u>'<,'>GpRewrite<cr>", keymapOptions("Visual Rewrite"))
            vim.keymap.set("v", "<C-g>a", ":<C-u>'<,'>GpAppend<cr>", keymapOptions("Visual Append (after)"))
            vim.keymap.set("v", "<C-g>b", ":<C-u>'<,'>GpPrepend<cr>", keymapOptions("Visual Prepend (before)"))
            vim.keymap.set("v", "<C-g>i", ":<C-u>'<,'>GpImplement<cr>", keymapOptions("Implement selection"))
            vim.keymap.set("v", "<C-g>P", ":<C-u>'<,'>GpProofread<cr>", keymapOptions("Proofread selection"))

            vim.keymap.set({ "n" }, "<C-g>gp", "<cmd>GpPopup<cr>", keymapOptions("Popup"))
            vim.keymap.set({ "n" }, "<C-g>ge", "<cmd>GpEnew<cr>", keymapOptions("GpEnew"))
            vim.keymap.set({ "n" }, "<C-g>gn", "<cmd>GpNew<cr>", keymapOptions("GpNew"))
            vim.keymap.set({ "n" }, "<C-g>gv", "<cmd>GpVnew<cr>", keymapOptions("GpVnew"))
            vim.keymap.set({ "n" }, "<C-g>gt", "<cmd>GpTabnew<cr>", keymapOptions("GpTabnew"))

            vim.keymap.set("v", "<C-g>gp", ":<C-u>'<,'>GpPopup<cr>", keymapOptions("Visual Popup"))
            vim.keymap.set("v", "<C-g>ge", ":<C-u>'<,'>GpEnew<cr>", keymapOptions("Visual GpEnew"))
            vim.keymap.set("v", "<C-g>gn", ":<C-u>'<,'>GpNew<cr>", keymapOptions("Visual GpNew"))
            vim.keymap.set("v", "<C-g>gv", ":<C-u>'<,'>GpVnew<cr>", keymapOptions("Visual GpVnew"))
            vim.keymap.set("v", "<C-g>gt", ":<C-u>'<,'>GpTabnew<cr>", keymapOptions("Visual GpTabnew"))

            vim.keymap.set({ "n" }, "<C-g>x", "<cmd>GpContext<cr>", keymapOptions("Toggle Context"))
            vim.keymap.set("v", "<C-g>x", ":<C-u>'<,'>GpContext<cr>", keymapOptions("Visual Toggle Context"))

            vim.keymap.set({ "n", "v", "x" }, "<C-g>s", "<cmd>GpStop<cr>", keymapOptions("Stop"))
            vim.keymap.set({ "n", "v", "x" }, "<C-g>n", "<cmd>GpNextAgent<cr>", keymapOptions("Next Agent"))

            -- Improved delete function with error handling
            local function delete_all_chat_files()
                local dir = vim.fn.expand("$HOME") .. "/.local/share/nvim/gp/chats"
                if vim.fn.isdirectory(dir) == 0 then
                    print("Chat directory does not exist: " .. dir)
                    return
                end

                local files = vim.fn.glob(dir .. "/*", false, true)
                if #files == 0 then
                    print("No chat files to delete")
                    return
                end

                local deleted_count = 0
                for _, file in ipairs(files) do
                    local success = os.remove(file)
                    if success then
                        deleted_count = deleted_count + 1
                    else
                        print("Failed to delete: " .. vim.fn.fnamemodify(file, ":t"))
                    end
                end
                print(string.format("Deleted %d chat files", deleted_count))
            end

            vim.keymap.set("n", "<C-g>da", delete_all_chat_files, keymapOptions("Delete all chats"))
        end,
        config = function()
            -- Gp (GPT prompt) lua plugin for Neovim
            -- https://github.com/Robitx/gp.defaults")

            ---@alias AgentType "chat" | "command"

            ---@class AgentSpec
            ---@field provider string
            ---@field model string

            ---@class Agent
            ---@field provider string
            ---@field name string
            ---@field chat boolean
            ---@field command boolean
            ---@field model string
            ---@field system_prompt string

            -- Define global system prompts
            local chat_system_prompt = require("gp.defaults").chat_system_prompt
            local code_system_prompt = require("gp.defaults").code_system_prompt

            ---@param spec AgentSpec
            ---@param agent_type AgentType
            ---@return Agent
            local function create_agent(spec, agent_type)
                local name_prefix = agent_type == "chat" and "Chat" or "Code"
                local model_name = table.concat({ unpack(vim.split(spec.model, "-", { plain = true }), 1, 3) })
                local name = name_prefix .. model_name:gsub("^%l", string.upper)

                return {
                    provider = spec.provider,
                    name = name,
                    chat = agent_type == "chat",
                    command = agent_type == "command",
                    model = {
                        model = spec.model,
                        max_tokens = 32768,
                    },
                    system_prompt = agent_type == "chat" and chat_system_prompt or code_system_prompt,
                }
            end

            ---@type AgentSpec[]
            local agent_specs = {
                {
                    provider = "openai",
                    model = "openai/gpt-5-mini",
                },
                {
                    provider = "openai",
                    model = "google/gemini-2.5-flash-lite",
                },
            }

            ---@type Agent[]
            local agents = {}

            for _, spec in ipairs(agent_specs) do
                table.insert(agents, create_agent(spec, "chat"))
                table.insert(agents, create_agent(spec, "command"))
            end

            local cfg = {
                providers = {
                    openai = {
                        endpoint = os.getenv("OPENAI_BASE_URL") .. "/chat/completions",
                        secret = os.getenv("OPENAI_API_KEY"),
                    },
                },
                agents = agents,
                toggle_target = "tabnew",
                -- write sensitive data to log file for	debugging purposes (like api keys)
                log_sensitive = false,
                -- if true, finished ChatResponder won't move the cursor to the end of the buffer
                chat_free_cursor = true,
                hooks = {
                    Concise = function(gp, params)
                        local template = "Having following from {{filename}}:\n\n"
                            .. "```{{filetype}}\n{{selection}}\n```\n\n"
                            .. "Please help to make the provided text more concise."

                        local agent = gp.get_command_agent()
                        gp.logger.info("Implementing selection with agent: " .. agent.name)

                        gp.Prompt(params, gp.Target.rewrite, agent, template, nil, nil)
                    end,
                    Proofread = function(gp, params)
                        local template = "Having following from {{filename}}:\n\n"
                            .. "```{{filetype}}\n{{selection}}\n```\n\n"
                            .. "Please help to proofread the provided text."

                        local agent = gp.get_command_agent()
                        gp.logger.info("Implementing selection with agent: " .. agent.name)

                        gp.Prompt(params, gp.Target.rewrite, agent, template, nil, nil)
                    end,
                    Implement = function(gp, params)
                        local template = "Having following from {{filename}}:\n\n"
                            .. "```{{filetype}}\n{{selection}}\n```\n\n"
                            .. "Please rewrite this according to the contained instructions."
                            .. "\n\nRespond exclusively with the snippet that should replace the selection above."

                        local agent = gp.get_command_agent()
                        gp.logger.info("Implementing selection with agent: " .. agent.name)

                        gp.Prompt(params, gp.Target.rewrite, agent, template, nil, nil)
                    end,
                    Explain = function(gp, params)
                        local template = "I have the following text from {{filename}}:\n\n"
                            .. "```{{filetype}}\n{{selection}}\n```\n\n"
                            .. "Please respond by explaining the code above, with the following user's command as `{{command}}`."
                        local agent = gp.get_chat_agent()
                        gp.Prompt(params, gp.Target.popup, agent, template)
                    end,
                    Summarize = function(gp, params)
                        local template = "Please summarize the following text from {{filename}}:\n\n"
                            .. "```{{filetype}}\n{{selection}}\n```\n\n"
                            .. "Provide a brief summary of the code above."
                        local agent = gp.get_chat_agent()
                        gp.Prompt(params, gp.Target.popup, agent, template)
                    end,
                    MakeList = function(gp, params)
                        local template = "Please create a list of key components from the following text in {{filename}}:\n\n"
                            .. "```{{filetype}}\n{{selection}}\n```\n\n"
                            .. "Generate a list of important elements in the code above."
                        local agent = gp.get_chat_agent()
                        gp.Prompt(params, gp.Target.popup, agent, template)
                    end,
                    MakeKeyPoint = function(gp, params)
                        local template = "Please highlight the key points of the following text from {{filename}}:\n\n"
                            .. "```{{filetype}}\n{{selection}}\n```\n\n"
                            .. "Identify the main points of interest in the code above."
                        local agent = gp.get_chat_agent()
                        gp.Prompt(params, gp.Target.popup, agent, template)
                    end,
                },
                whisper = {
                    disable = true,
                },
                image = {
                    disable = true,
                },
            }

            require("gp.defaults").code_system_prompt = "You are an advanced AI code editor designed to assist with programming tasks.\n\n"
                .. "Provide clear and concise code snippets without any additional commentary or explanation.\n"
                .. "Begin and end each response with:\n\n```"

            require("gp.config").agents = {}

            require("gp").setup(cfg)
        end,
    },
}
