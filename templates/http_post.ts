// http_post.ts - HTTP POST of JSON with status handling and a typed result.
// Copy to <step_id>.ts. For PUT, PATCH or DELETE change "method". Change the URL, the body and the result.
// Its entries in flow.yaml (here inside a loop):
//   row: {type: javascript, expr: "flow_input.iter.value"}
//   api_key: {type: static, value: "$var:f/my_folder/api_key"}

type Row = { id: string; label: string };
type Result = { status: number; created_id: string | null };

// aNN <Tines action name>
export async function main(row: Row, api_key: string): Promise<Result> {
  const res = await fetch("https://api.example.com/v1/labels", {
    method: "POST",
    headers: { Authorization: `Bearer ${api_key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ item: row.id, label: row.label }),   // the Tines "payload"
    signal: AbortSignal.timeout(30_000),
  });
  if (!res.ok) throw new Error(`POST label for ${row.id} returned ${res.status}`);
  const text = await res.text();                                 // the response may be empty
  const body: any = text ? JSON.parse(text) : null;
  return { status: res.status, created_id: body?.id ?? null };
}
