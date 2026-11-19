// a12 Look up carrier
export async function main(alert: { vehicle_id: string }, api_key: string) {
  const url = `https://carriers.example.net/v1/vehicles/${encodeURIComponent(alert.vehicle_id)}?key=${encodeURIComponent(api_key)}`;
  const res = await fetch(url);
  const body: any = res.ok ? await res.json() : null;
  return { status: res.status, name: body?.name ?? null, dispatch_phone: body?.dispatch_phone ?? null };
}
