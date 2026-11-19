// failure.ts - the script of value.failure_module (id: failure). Runs after a step has failed.
// The flow still ends as failed. Add this handler only if the story reports its own failures.
// Its entries in flow.yaml:
//   message: {type: javascript, expr: "error.message"}
//   name: {type: javascript, expr: "error.name"}
//   step_id: {type: javascript, expr: "error.step_id"}

export async function main(message: string, name: string, step_id: string) {
  // Report the failure here if the story did (for example POST to a chat webhook, or send an email).
  console.error(`step ${step_id} failed: ${name}: ${message}`);
  return { failed_step: step_id, error_name: name, error_message: message };
}
