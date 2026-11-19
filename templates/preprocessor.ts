// preprocessor.ts - turns a raw trigger request into the flow inputs.
// Needed only when the flow inputs are not simply the JSON body: headers, query values, a secret check.
// It is value.preprocessor_module in flow.yaml (id: preprocessor, input_transforms: {}), not a step in modules.
// The function is named preprocessor, not main. It cannot read results.
import * as wmill from "windmill-client";
import { timingSafeEqual } from "node:crypto";

type TriggerEvent = {
  kind: string;                        // "webhook", "http" (a route), "email", ...
  body?: any;                          // the parsed JSON body
  query?: Record<string, string>;      // values after "?" in the URL
  headers?: Record<string, string>;    // request headers
};

// aNN <Tines webhook action name>
export async function preprocessor(event: TriggerEvent) {
  const headers = event.headers ?? {};

  // Secret check. Keep it only for a route with authentication_method: none. Otherwise delete these 4 lines.
  // The secret is a NEW value in a secret variable. Never copy the Tines webhook secret.
  const expected = Buffer.from(await wmill.getVariable("f/my_folder/my_flow_webhook_secret"));
  const given = Buffer.from(headers["x-webhook-secret"] ?? "");
  if (given.length !== expected.length || !timingSafeEqual(given, expected))
    throw new Error("wrong or missing webhook secret");

  // Return exactly the properties of schema in flow.yaml.
  return {
    item_id: event.body?.item_id ?? event.query?.item_id ?? null,   // Tines puts query values into body
    // source: headers["x-source"] ?? "",                           // Tines: <webhook>.headers.x_source
  };
}
