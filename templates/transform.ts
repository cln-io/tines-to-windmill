// transform.ts - a step that only computes: no network call, no state.
// Use a separate transform step only when several later steps read its result.
// A transform that one step reads is a line of code inside that step.
// Its entry in flow.yaml:
//   item: {type: javascript, expr: "results.http_get.item"}

// Tines formula helpers. Keep the ones you use, delete the others.
const isBlank = (v: any): boolean =>
  v == null || v === false || v === "" ||
  (Array.isArray(v) ? v.length === 0 : typeof v === "object" && Object.keys(v).length === 0);
const truthy = (v: any): boolean => v !== false && v != null;      // Tines: 0 and "" are truthy
const text = (v: any): string => (v == null ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));

type Item = { id: string; name: string; tags: string[] };
type Result = { rows: { id: string; label: string }[]; summary: string; needs_approval: boolean };

// aNN <Tines action name>: write the formula next to each line that ports it
export async function main(item: Item | null): Promise<Result> {
  const tags = item?.tags ?? [];                                                    // a missing path is NULL in Tines, never an error
  const rows = tags.map((tag) => ({ id: text(item?.id), label: text(tag).toUpperCase() }));   // =MAP_LAMBDA(tags, LAMBDA(t, UPCASE(t)))
  const name = isBlank(item?.name) ? "unnamed" : text(item?.name);                  // =DEFAULT(item.name, "unnamed")
  return {
    rows,
    summary: `${name}: ${rows.length} label(s)`,
    needs_approval: truthy(item) && rows.length > 10,                               // =AND(item, SIZE(rows) > 10)
  };
}
