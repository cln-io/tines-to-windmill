// state_read.ts - read state that another step writes at the end of the flow.
// The state is a NON-secret variable that holds JSON. The user creates it with the value {}.
// (State that one step both reads and writes: use wmill.getState() / wmill.setState() in that step instead.)
// Its entry in flow.yaml (the path, not "$var:..."; the step reads the variable itself):
//   state_var: {type: static, value: f/my_folder/my_flow_state}
import * as wmill from "windmill-client";

type State = { last_item_id?: string };

// aNN <the Tines action that reads RESOURCE.x>
export async function main(state_var: string): Promise<{ state: State }> {
  // No try/catch: a missing variable or a permission error must fail the step.
  // If it were caught, an error would look like a first run and old work would be done again.
  const state: State = JSON.parse(await wmill.getVariable(state_var));
  return { state };
}
