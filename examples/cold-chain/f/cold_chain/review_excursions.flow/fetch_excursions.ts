import * as wmill from "windmill-client";

type Alert = { id: string; raised_at: string; causes?: { code?: string }[]; [key: string]: any };

// a35 since parameter, a03 get excursions, a04 200, a05 not defrost
export async function main(depot: string, api_token: string, cursor_var: string) {
  // No try/catch: a missing variable or a permission error must fail, not look like a first run.
  const cursor: Record<string, number> = JSON.parse(await wmill.getVariable(cursor_var));
  const last = cursor[depot];
  const since = last === undefined || last === null ? "" : `&since=${last}`;
  const res = await fetch(
    `https://tracker.example.com/v2/depots/${depot}/excursions?state=open&limit=200${since}`,
    { headers: { "X-Auth-Token": api_token } },
  );
  if (res.status !== 200) throw new Error(`tracker returned ${res.status} for depot ${depot}`);
  const items: Alert[] = (await res.json())?.items ?? [];
  // REJECT(..., FILTER(codes, LAMBDA(code, INDEX_OF(code, "defrost"))) |> SIZE(%) > 0)
  // INDEX_OF gives NULL on a miss and a position (0 included, truthy in Tines) on a hit.
  const alerts = items.filter((item) => !(item.causes ?? []).some((c) => String(c?.code ?? "").includes("defrost")));
  const seconds = alerts.map((a) => Math.floor(new Date(a.raised_at).getTime() / 1000));
  return { depot, alerts, latest_s: seconds.length ? Math.max(...seconds) : null };
}
