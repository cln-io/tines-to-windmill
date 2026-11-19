type Branch = { source?: string; [key: string]: any } | null;

const text = (v: unknown) => (v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v));
// Every value put into the HTML body goes through esc().
const esc = (v: unknown) =>
  text(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");

// a16 / a17 (the decision), a28 tag for join (the message); a29 to a33 were join plumbing
export async function main(alert: any, carrier: any, lookups: Branch[]) {
  // Find branch results by name: a failed branch leaves null or an error object in its slot.
  const by = (name: string) => (lookups ?? []).find((r) => r?.source === name) ?? null;
  const lab = by("lab");
  const claims = by("claims");
  const chart = by("chart");

  // Two triggers into one action = OR. A missing count is NULL in Tines and matches neither rule.
  const send = Number(lab?.failed ?? 0) > 0 || Number(lab?.borderline ?? 0) > 2;

  const causes = (alert?.causes ?? []).map((c: any) => esc(c?.code)).join(", ");
  const html =
    `<h2>Temperature excursion on shipment ${esc(alert?.shipment_id)}</h2>\n` +
    `<p>Batch ${esc(alert?.batch_no)}, peak ${esc(alert?.peak_c)} C, causes: ${causes}</p>\n` +
    `<p>Carrier: ${esc(carrier?.name)} (${esc(carrier?.dispatch_phone)})</p>\n` +
    `<p>Lab tests: ${esc(lab?.failed)} failed, ${esc(lab?.borderline)} borderline</p>\n` +
    `<p>Open claims: ${esc(claims?.open_claims)}</p>`;

  return {
    send,
    subject: "Cold chain: excursion needs review",
    html,
    attachment: chart?.base64 ? { filename: chart.filename, base64: chart.base64 } : null,
  };
}
