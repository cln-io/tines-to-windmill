// http_get.ts - HTTP GET with status handling and a typed result.
// Copy to <step_id>.ts. Change the types, the URL, the header and the returned fields.
// Its entries in flow.yaml:
//   item_id: {type: javascript, expr: "flow_input.item_id"}
//   api_key: {type: static, value: "$var:f/my_folder/api_key"}

type Item = { id: string; name: string; tags: string[] };   // only the fields later steps read
type Result = { status: number; item: Item | null };

// aNN <Tines action name>, aNN <status trigger>
export async function main(item_id: string, api_key: string): Promise<Result> {
  const res = await fetch(`https://api.example.com/v1/items/${encodeURIComponent(item_id)}`, {
    headers: { Authorization: `Bearer ${api_key}` },
    signal: AbortSignal.timeout(30_000),   // the Tines "timeout" in seconds x 1000 (Tines default: 30)
  });
  // A status that the story treats as data (it has a trigger for it): return it. Delete this line if there is none.
  if (res.status === 404) return { status: 404, item: null };
  // Any other status: fail the step. Never put a secret in the message.
  if (!res.ok) throw new Error(`GET item ${item_id} returned ${res.status}`);
  const body: any = await res.json();
  return { status: res.status, item: { id: body.id, name: body.name, tags: body.tags ?? [] } };
}
