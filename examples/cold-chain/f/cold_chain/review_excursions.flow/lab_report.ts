const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// a13 Get batch report from lab, a14 404, a15 wait for lab
export async function main(alert: { batch_no: string }, api_key: string) {
  const call = () =>
    fetch(`https://lab.example.com/api/v3/batches/${encodeURIComponent(alert.batch_no)}`, {
      headers: { "x-lab-key": api_key },
    });
  let res = await call();
  if (res.status === 404) {
    // The story's loop guard lets the 404 -> wait -> retry cycle run once only.
    await sleep(45_000);
    res = await call();
  }
  const body: any = res.status === 200 ? await res.json() : null;
  const counts = body?.result?.counts ?? {};
  return {
    source: "lab",
    status: res.status,
    failed: counts.failed ?? null,
    borderline: counts.borderline ?? null,
  };
}
