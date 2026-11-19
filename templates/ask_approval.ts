// ask_approval.ts - the script of an approval step (a Tines page in the middle of a workflow).
// The step in flow.yaml must have a "suspend" block beside id and value. The script runs first,
// then the flow waits until a person approves on the approval page, or until the timeout.
// The step right after this one reads the form values as "resume" and the approver as "approvers":
//   comment: {type: javascript, expr: "resume?.comment ?? ''"}
// Its entry in flow.yaml:
//   summary: {type: javascript, expr: "results.transform.summary"}
import * as wmill from "windmill-client";

// aNN <Tines page name>
export async function main(summary: string) {
  // Must be called, or nobody can resume the flow.
  // urls.approvalPage: page with the form and the Approve / Reject buttons.
  // urls.resume, urls.cancel: URLs that another system can POST to instead.
  const urls = await wmill.getResumeUrls("approver");
  // If the story sent the page link to someone (PAGE.<name> in a message or an email),
  // send urls.approvalPage to the same place here.
  return {
    summary,                              // what the Tines page showed: its paragraphs and tables
    approval_page: urls.approvalPage,
  };
}
