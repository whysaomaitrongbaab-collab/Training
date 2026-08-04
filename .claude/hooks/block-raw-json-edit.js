// PreToolUse hook (Edit|Write): force a confirmation prompt before touching
// protected raw training JSON. See training-data/docs/rule_of_tune.md Rule 1 —
// raw JSON of pre-tuning data must never be edited without explicit,
// in-conversation authorization.
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

  const protectedPatterns = [
    // training-data/raw/image/<house>/qwen-output/*.json (extraction output,
    // _document_map.json, _run_summary.json)
    /training-data\/raw\/.*qwen-output\/[^/]+\.json$/,
    // raw_json_<thai text>/0N<house>/*.json — hand-transcribed ground truth
    /raw_json_[^/]*\/[^/]+\/[^/]+\.json$/,
  ];

  if (protectedPatterns.some((re) => re.test(normalized))) {
    console.log(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "ask",
          permissionDecisionReason:
            "This is protected raw training JSON (source ground truth for fine-tuning). " +
            "Per training-data/docs/rule_of_tune.md Rule 1, edits require explicit confirmation " +
            "every time — warn the user this affects fine-tuning accuracy before proceeding, " +
            "and log the change in training-data/raw_json_data_log.md if approved.",
        },
      })
    );
  }
});
