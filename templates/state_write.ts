// state_write.ts - write the state once, at the end, after the work succeeded.
// Same variable as state_read.ts. This replaces a Tines HTTP call to /api/v1/global_resources/...
// Its entries in flow.yaml:
//   state_var: {type: static, value: f/my_folder/my_flow_state}
//   last_item_id: {type: javascript, expr: "flow_input.item_id"}
import * as wmill from "windmill-client";

type State = { last_item_id?: string };

// aNN <the Tines action that calls the Tines API to write the resource>
export async function main(state_var: string, last_item_id: string | null): Promise<{ saved: State | null }> {
  if (last_item_id === null) return { saved: null };            // nothing was processed: leave the state as it is
  // Read again, change one key, write back. Do not replace keys that this flow does not own.
  const state: State = JSON.parse(await wmill.getVariable(state_var));
  state.last_item_id = last_item_id;                            // never move a cursor past items that were not processed
  await wmill.setVariable(state_var, JSON.stringify(state));
  return { saved: state };
}
