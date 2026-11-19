// a18 Check claims register (a19 to a22 only fed dead ends)
export async function main(alert: { shipment_id: string }, api_key: string) {
  const res = await fetch(`https://claims.example.org/api/shipments/${encodeURIComponent(alert.shipment_id)}`, {
    headers: { apikey: api_key },
  });
  const body: any = res.status === 200 ? await res.json() : null;
  return { source: "claims", status: res.status, open_claims: body?.summary?.open_claims ?? null };
}
