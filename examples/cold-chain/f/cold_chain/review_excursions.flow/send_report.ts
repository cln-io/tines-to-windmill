import nodemailer from "nodemailer";

type Smtp = { host: string; port: number; user?: string; password?: string };
type Report = { subject: string; html: string; attachment: { filename: string; base64: string } | null };

// a34 Send excursion report
export async function main(smtp: Smtp, to: string, report: Report) {
  const transport = nodemailer.createTransport({
    host: smtp.host,
    port: smtp.port,
    auth: smtp.user ? { user: smtp.user, pass: smtp.password } : undefined,
  });
  const info = await transport.sendMail({
    from: smtp.user,
    to,
    replyTo: to,
    subject: report.subject,
    html: report.html,
    attachments: report.attachment
      ? [{ filename: report.attachment.filename, content: report.attachment.base64, encoding: "base64" }]
      : [],
  });
  return { message_id: info.messageId, attached: report.attachment !== null };
}
