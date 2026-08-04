// PreToolUse hook (Edit|Write): force a confirmation prompt before touching
// .env files, which hold live API keys (Gemini, Qwen, etc.).
let data = "";
process.stdin.on("data", (c) => (data += c));
process.stdin.on("end", () => {
  let input;
  try {
    input = JSON.parse(data);
  } catch {
    return;
  }
  const filePath = (input.tool_input && input.tool_input.file_path) || "";
  const normalized = filePath.replace(/\\/g, "/");
  const fileName = normalized.split("/").pop() || "";

  if (/^\.env(\.[^/]+)?$/.test(fileName)) {
    console.log(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "ask",
          permissionDecisionReason:
            "This file holds live API keys/secrets. Confirm before editing to avoid " +
            "accidental key leakage or overwrite.",
        },
      })
    );
  }
});
