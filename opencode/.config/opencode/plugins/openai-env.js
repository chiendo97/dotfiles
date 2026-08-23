export const OpenAIEnvHeaders = async ({ $ }) => {
  const command = 'print -rn -- "$OPENAI_API_KEY"'
  const result = await $`zsh -ic ${command}`.quiet()
  const apiKey = result.text().trim()

  return {
    "chat.headers": async (input, output) => {
      if (input.model.providerID !== "zariel") return
      if (!apiKey) {
        throw new Error("OPENAI_API_KEY was not loaded for the zariel provider")
      }

      output.headers.authorization = `Bearer ${apiKey}`
      output.headers["x-bf-vk"] = apiKey
    },
  }
}
