const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const BASE = "https://audit.example.org/v3/audits";

// group a23 Sensor audit (a23.01 to a23.12)
export async function main(alert: { sensor_id: string }, api_key: string) {
  const headers = { Authorization: api_key, "Content-Type": "application/json" };
  const sensor = alert.sensor_id;

  const search = await fetch(`${BASE}/search?scope=fleet&sensor=${encodeURIComponent(sensor)}`, { headers });
  if (search.status === 200) {
    // a23.10 audit exists -> a23.11 findings
    const known: any = await search.json();
    return result(known?.result?.[0]?.findings, "existing");
  }
  if (search.status !== 204) return { source: "sensor_audit", stage: "search", status: search.status, findings: null };

  // a23.02 no audit yet -> request, start, wait, result; every 200 trigger is an early return
  const request = await fetch(BASE, {
    method: "POST",
    headers,
    body: JSON.stringify({ sensor, kind: "calibration", scope: "fleet" }),
  });
  if (request.status !== 200) return { source: "sensor_audit", stage: "request", status: request.status, findings: null };
  const auditId = ((await request.json()) as any)?.result?.audit_id;

  const start = await fetch(`${BASE}/${auditId}/start`, { method: "PUT", headers });
  if (start.status !== 200) return { source: "sensor_audit", stage: "start", status: start.status, findings: null };

  await sleep(20_000);
  const outcome = await fetch(`${BASE}/${auditId}`, { headers });
  if (outcome.status !== 200) return { source: "sensor_audit", stage: "result", status: outcome.status, findings: null };
  return result(((await outcome.json()) as any)?.result?.findings, "new");
}

function result(findings: any, stage: string) {
  // a23.12 faults>0: the group only returned its findings when there were faults
  const faults = Number(findings?.faults ?? 0);
  return { source: "sensor_audit", stage, status: 200, findings: faults > 0 ? findings : null };
}
