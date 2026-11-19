const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const API = "https://charts.example.com/api/v1";
const MAX_POLLS = 30; // the story polls without a limit; 30 x 10 s is this port's bound

// group a24 Find or Render Chart, then a25 200, a26 Retrieve chart image, a27 200
export async function main(alert: { sensor_id: string }, api_key: string) {
  const headers = { "API-Key": api_key, "Content-Type": "application/json" };
  const sensor = alert.sensor_id;
  const none = (stage: string, status: number) => ({ source: "chart", stage, status, filename: null, base64: null });

  const q = encodeURIComponent(`sensor:"${sensor}"`);
  const search = await fetch(`${API}/search/?q=${q}`, { headers });
  const results: any[] = search.status === 200 ? ((await search.json()) as any)?.results ?? [] : [];

  let job: Response;
  if (results.length > 0) {
    // a24.03 Chart found
    job = await fetch(results[0].job_url, { headers });
  } else {
    // a24.04 No chart -> a24.05 Submit render job (retry_on_status 429)
    let submit: Response;
    for (let attempt = 0; ; attempt++) {
      submit = await fetch(`${API}/render/`, {
        method: "POST",
        headers,
        body: JSON.stringify({ sensor, resolution: "minute" }),
      });
      if (submit.status !== 429 || attempt >= 5) break;
      await sleep(5_000 * 2 ** attempt);
    }
    if (submit.status !== 200) return none("submit", submit.status); // a24.11 Accepted, no-match
    const jobUrl = ((await submit.json()) as any)?.job_url;
    // a24.06 Wait for render -> a24.07 Get chart job -> a24.08 Still rendering (404) -> back
    let polls = 0;
    do {
      if (polls++ >= MAX_POLLS) throw new Error(`chart for sensor ${sensor} still rendering after ${MAX_POLLS} polls`);
      await sleep(10_000);
      job = await fetch(jobUrl, { headers });
    } while (job.status === 404);
  }
  if (job.status !== 200) return none("job", job.status); // a25 200
  const jobId = ((await job.json()) as any)?.job?.id;

  const image = await fetch(`https://charts.example.com/images/${jobId}.png`); // a26
  if (image.status !== 200) return none("image", image.status); // a27 200
  return {
    source: "chart",
    stage: "image",
    status: 200,
    filename: `${jobId}.png`,
    base64: Buffer.from(await image.arrayBuffer()).toString("base64"),
  };
}
