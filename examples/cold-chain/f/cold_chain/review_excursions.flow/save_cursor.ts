import * as wmill from "windmill-client";

// a36 slow down, a37 latest seen, a38 save cursor
export async function main(depot: string, latest_s: number | null, cursor_var: string) {
  if (latest_s === null) return { depot, saved: null }; // no alert: the story wrote nothing either
  const cursor: Record<string, number> = JSON.parse(await wmill.getVariable(cursor_var));
  // =MAX(LOCAL.cursor_s, LOCAL.alert_s) + 1, with cursor_s defaulting to 0
  const next = Math.max(Number(cursor[depot] ?? 0), latest_s) + 1;
  cursor[depot] = next;
  await wmill.setVariable(cursor_var, JSON.stringify(cursor));
  return { depot, saved: next };
}
