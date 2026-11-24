# Worksheet: review_excursions (workflow w01)

Written while reading the outline (step 2). The flow is checked against it in step 7.

## Entry
- a01 `depots`: schedule `*/20 * * * *`, America/Toronto. Windmill: `0 */20 * * * *`.
- Its payload (three depot codes) becomes the flow input `depot_codes`.

## Shape
- a02 explode over the depots: a loop, one pass per depot.
- a03 get excursions, a04 status 200, a05 drop defrost causes. a09 guards an empty list: not needed, a loop over `[]` does nothing.
- a10 explode over the alerts: an inner loop.
- a12 FAN-OUT x4 per alert: carrier (a12), lab report (a13), claims (a18), sensor audit (group a23), chart (group a24, a26). All of them run; a later step needs all results, so they are parallel branches.
- a13/a14/a15: poll loop on a 404 from the lab (CYCLE). Bounded loop inside the step.
- a24.05/a24.07: submit a render job, then poll the job (CYCLE). Bounded loop inside the step.
- a27..a33: decide whether to report (failed or borderline lab counts), build the HTML report.
- a34 send the report by email. a38 save the cursor.

## Recipes named by the outline
1 6 7 8 9 11 13 14 15 16 17 19 20 22 23 24 25 29 30

## Dead ends and things that do not run
- Disabled branches the index lists as not triggered (door open, power loss): not part of this workflow, not ported.
- a21 claim summary: nothing reads its output.

## Uses
- CREDENTIAL: carrier_directory_key, chart_service, claims_register_key, lab_api_key, sensor_audit_key, tenant_api_token, tracker_api_token
- RESOURCE: excursion_cursor (read at the start, written at the end)

## Outside effects (checklist for step 7)
1. a23.03 request an audit: POST to the audit service -> `sensor_audit`
2. a23.05 start the audit: POST to the audit service -> `sensor_audit`
3. a24.05 submit render job: POST to the chart service -> `chart`
4. a34 send excursion report: email with the chart attached -> `send_report`
5. a38 save cursor: state write, once per depot, after the alerts of that depot -> `save_cursor`

Everything else is a read (GET).
