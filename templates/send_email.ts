// send_email.ts - send one email through an smtp resource (Tines "Send Email" action).
// Copy the subject and the body from the story. Replace only the pills.
// Its entries in flow.yaml:
//   smtp: {type: static, value: "$res:f/my_folder/smtp"}
//   to: {type: javascript, expr: "flow_input.recipients"}
//   subject: {type: javascript, expr: "results.transform.summary"}
//   html: {type: javascript, expr: "`<p>${results.transform.summary}</p>`"}
import nodemailer from "nodemailer";

type Smtp = { host: string; port: number; user?: string; password?: string };

// aNN <Tines action name>
export async function main(smtp: Smtp, to: string[], subject: string, html: string) {
  const transport = nodemailer.createTransport({
    host: smtp.host,
    port: smtp.port,
    auth: smtp.user ? { user: smtp.user, pass: smtp.password } : undefined,
  });
  const info = await transport.sendMail({
    from: smtp.user,          // Tines sent from the tenant's own address: say so in the notes
    to,                       // one address or a list ("recipients")
    // cc: [], bcc: [], replyTo: "desk@example.org",        // Tines cc, bcc, reply_to
    subject,
    html,                     // a body without HTML tags: use "text" instead of "html"
    // attachments: [{ filename: "report.pdf", content: base64, encoding: "base64" }],   // Tines base64encodedcontents
  });
  return { message_id: info.messageId };
}
