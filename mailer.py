"""
mailer.py — SafeRoad Automated Email Notification System.

Supports standard SMTP providers (Gmail App Password, Brevo, SendGrid, Amazon SES, etc.)
using Python's built-in smtplib and email.message modules (zero external pip packages).

Features:
- Asynchronous dispatch via background threads to keep UI responses fast.
- Formats responsive, clean HTML emails + plain-text fallback.
- Auto-fallback to terminal logging if MAIL_ENABLED is False or credentials are unset.
"""

import logging
import smtplib
import threading
from email.message import EmailMessage
from config import Config

logger = logging.getLogger('saferoad.mailer')


def _send_email_thread(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Internal worker function that runs in a background thread."""
    if not to_email or '@' not in to_email:
        logger.warning(f"[Mailer] Invalid recipient email: {to_email}")
        return

    # Check if real email dispatch is enabled and configured
    if Config.MAIL_ENABLED and Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
        try:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = Config.MAIL_DEFAULT_SENDER or Config.MAIL_USERNAME
            msg['To'] = to_email
            msg.set_content(text_body)
            msg.add_alternative(html_body, subtype='html')

            server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=12)
            if Config.MAIL_USE_TLS:
                server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            logger.info(f"[Mailer] Sent live email to {to_email} - Subject: {subject}")
            print(f"\n[LIVE GMAIL SENT SUCCESSFULLY]\nTo: {to_email}\nSubject: {subject}\n", flush=True)
        except Exception as e:
            logger.error(f"[Mailer] Failed to send live email to {to_email}: {e}")
            print(f"\n[EMAIL DISPATCH ERROR] Failed to send live email to {to_email}: {e}\n", flush=True)
    else:
        # Development / Mock mode preview in console
        preview = (
            "\n" + "=" * 65 + "\n"
            + "[EMAIL SIMULATION / MOCK DISPATCH]\n"
            + f"To:      {to_email}\n"
            + f"Subject: {subject}\n"
            + "Status:  MAIL_ENABLED is False or credentials not configured.\n"
            + "-" * 65 + "\n"
            + text_body.strip() + "\n"
            + "=" * 65 + "\n"
        )
        print(preview, flush=True)


def send_async_email(to_email: str, subject: str, text_body: str, html_body: str) -> None:
    """Dispatch an email asynchronously in a daemon thread."""
    t = threading.Thread(
        target=_send_email_thread,
        args=(to_email, subject, text_body, html_body),
        daemon=True,
    )
    t.start()


def send_report_confirmation(report, base_url: str = 'http://localhost:5000') -> None:
    """Send a beautifully formatted confirmation email when a citizen registers a new road hazard."""
    if not report or not report.submitter_email:
        return

    track_url = f"{base_url.rstrip('/')}/my-reports?report_id={report.report_id}"
    cat_label = getattr(report, 'category_label', report.category)
    date_str = report.created_at.strftime('%d %B %Y, %I:%M %p') if getattr(report, 'created_at', None) else 'Recently'
    priority_level = getattr(report, 'priority_level', 'Medium')

    subject = f"[SafeRoad] Hazard Report Registered: {report.report_id} ({cat_label})"

    text_body = f"""Dear {report.submitter_name},

Thank you for reporting a road hazard on SafeRoad Hyderabad. Your report has been successfully registered into the road safety and municipal maintenance monitoring queue.

============================================================
REPORT SUMMARY:
============================================================
• Complaint ID:    {report.report_id}
• Hazard Type:     {cat_label}
• Location:        {report.location_name}
• Municipal Zone:  {getattr(report, 'zone_name', 'Hyderabad Central')}
• Circle Officer:  {getattr(report, 'assigned_officer', 'Circle Engineering Cell')}
• Severity Rating: {report.severity} / 5
• Assigned Priority: {priority_level}
• Current Status:  {report.status}
• Date Reported:   {date_str}

============================================================
WHAT HAPPENS NEXT:
============================================================
1. Verification: Road engineering cell reviews the location and details.
2. Field Dispatch: Maintenance crew inspects and prioritizes repair.
3. Resolution: Once repairs or sign installations are verified, status is marked Resolved.

Track real-time progress and inspection updates here:
{track_url}

Thank you for being an active citizen and helping make Hyderabad roads safer for everyone!

—
SafeRoad Hyderabad Infrastructure & Road Safety Cell
Web: {base_url}
Support: {Config.MAIL_USERNAME}
"""

    stars = "★" * int(report.severity) + "☆" * (5 - int(report.severity))

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SafeRoad Report Confirmation</title>
</head>
<body style="margin:0; padding:24px 0; background-color:#eef2f6; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; color:#2b2d42; -webkit-font-smoothing:antialiased;">
  <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center">
        <!-- Main Card Container -->
        <table role="presentation" width="100%" style="max-width:620px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 6px 20px rgba(0,0,0,0.07); border:1px solid #dce2e6;" cellspacing="0" cellpadding="0">
          
          <!-- Brand Header -->
          <tr>
            <td style="background:linear-gradient(135deg, #1d3557 0%, #294c7a 100%); padding:32px 28px; text-align:center;">
              <div style="font-size:38px; line-height:1; margin-bottom:10px;">🛣️</div>
              <h1 style="color:#ffffff; margin:0 0 6px; font-size:24px; font-weight:800; letter-spacing:-0.5px;">SafeRoad Hyderabad</h1>
              <p style="color:#e0e8f3; margin:0; font-size:14px; letter-spacing:0.3px;">Citizen Road Hazard Reporting &amp; Safety Monitoring System</p>
            </td>
          </tr>

          <!-- Confirmation Notice -->
          <tr>
            <td style="padding:28px 28px 12px;">
              <h2 style="font-size:20px; color:#1d3557; margin:0 0 10px; font-weight:700;">Report Successfully Registered!</h2>
              <p style="margin:0 0 16px; font-size:15px; line-height:1.6; color:#495057;">
                Dear <strong>{report.submitter_name}</strong>,<br>
                Thank you for documenting and submitting an unsafe road condition. Your complaint has been assigned a unique digital ID and submitted to the municipal traffic inspection queue.
              </p>

              <!-- Highlighted Report ID Card -->
              <table role="presentation" width="100%" style="background:#fff8f4; border:1.5px dashed #e63946; border-radius:8px; margin-bottom:20px;" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="padding:16px 20px; text-align:center;">
                    <div style="font-size:12px; text-transform:uppercase; letter-spacing:1px; color:#6c757d; font-weight:600; margin-bottom:4px;">Official Tracking ID</div>
                    <div style="font-size:26px; font-weight:800; color:#e63946; letter-spacing:1px; font-family:monospace;">{report.report_id}</div>
                  </td>
                </tr>
              </table>

              <!-- Details Table -->
              <table role="presentation" width="100%" style="border-collapse:collapse; margin-bottom:24px; background:#f8f9fa; border-radius:8px; overflow:hidden; border:1px solid #e9ecef;" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:600; font-size:13px; color:#6c757d; width:35%;">Hazard Category</td>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:700; font-size:14px; color:#1d3557;">{cat_label}</td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:600; font-size:13px; color:#6c757d;">Location</td>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-size:14px; color:#212529;">{report.location_name}</td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:600; font-size:13px; color:#6c757d;">Assigned Division</td>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-size:14px; color:#1d3557; font-weight:700;">
                    {getattr(report, 'zone_name', 'Hyderabad Central')}
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:600; font-size:13px; color:#6c757d;">Circle Officer</td>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-size:13px; color:#495057;">
                    {getattr(report, 'assigned_officer', 'Circle Engineering Cell')}
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:600; font-size:13px; color:#6c757d;">Severity Rating</td>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-size:14px; color:#e63946; font-weight:700;">
                    {stars} <span style="color:#6c757d; font-weight:normal; font-size:12px;">({report.severity}/5)</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:600; font-size:13px; color:#6c757d;">Priority Classification</td>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-size:13px; font-weight:700;">
                    <span style="background:{'#f8d7da' if priority_level == 'High' else '#ffe5d0' if priority_level == 'Medium' else '#d1e7dd'}; color:{'#58151c' if priority_level == 'High' else '#7d3300' if priority_level == 'Medium' else '#0a3622'}; padding:3px 10px; border-radius:12px;">{priority_level} Priority</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-weight:600; font-size:13px; color:#6c757d;">Initial Status</td>
                  <td style="padding:12px 16px; border-bottom:1px solid #e9ecef; font-size:13px; font-weight:700;">
                    <span style="background:#fff3cd; color:#856404; padding:3px 10px; border-radius:12px;">Pending Review</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:12px 16px; font-weight:600; font-size:13px; color:#6c757d;">Date &amp; Time</td>
                  <td style="padding:12px 16px; font-size:13px; color:#495057;">{date_str}</td>
                </tr>
              </table>

              <!-- What happens next -->
              <div style="background:#f1f5f9; border-radius:8px; padding:18px 20px; margin-bottom:26px;">
                <h4 style="margin:0 0 10px; font-size:14px; text-transform:uppercase; letter-spacing:0.5px; color:#1d3557;">What Happens Next?</h4>
                <ol style="margin:0; padding-left:18px; font-size:13px; line-height:1.7; color:#495057;">
                  <li><strong>Verification:</strong> Municipal cell cross-checks against duplicate reports and verifies coordinates.</li>
                  <li><strong>Action:</strong> Engineering work order is issued to field maintenance crews.</li>
                  <li><strong>Resolution:</strong> The road hazard is inspected, marked Resolved, and verified with photos.</li>
                </ol>
              </div>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:28px;">
                <tr>
                  <td align="center">
                    <a href="{track_url}" target="_blank" style="background:#e63946; color:#ffffff; font-size:15px; font-weight:700; text-decoration:none; padding:14px 34px; border-radius:8px; display:inline-block; box-shadow:0 4px 12px rgba(230,57,70,0.35);">
                      Track Your Report Live &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="font-size:12px; color:#868e96; text-align:center; margin:0 0 10px;">
                Direct URL: <a href="{track_url}" style="color:#457b9d; word-break:break-all;">{track_url}</a>
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8f9fa; border-top:1px solid #e9ecef; padding:20px 28px; text-align:center; font-size:12px; color:#6c757d; line-height:1.6;">
              <p style="margin:0 0 4px; font-weight:600; color:#495057;">SafeRoad Hyderabad &bull; Urban Road Infrastructure Initiative</p>
              <p style="margin:0;">You are receiving this automated email because this address was provided while submitting a road hazard report. Please do not reply directly to this automated notification.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    send_async_email(report.submitter_email, subject, text_body, html_body)


def send_status_update_notification(report, old_status: str, new_status: str, note: str = '', base_url: str = 'http://localhost:5000') -> None:
    """Send an email to the submitter when an administrator updates report status."""
    if not report or not report.submitter_email:
        return

    track_url = f"{base_url.rstrip('/')}/my-reports?report_id={report.report_id}"
    cat_label = getattr(report, 'category_label', report.category)

    subject = f"[SafeRoad Update] {report.report_id} status changed to '{new_status}'"

    note_text = f"\nAuthority / Field Note: {note}" if note else ""

    text_body = f"""Dear {report.submitter_name},

There has been an official status update regarding your road hazard report on SafeRoad Hyderabad.

Complaint ID:    {report.report_id}
Hazard Type:     {cat_label}
Location:        {report.location_name}
Previous Status: {old_status}
New Status:      {new_status}{note_text}

You can track the complete inspection timeline and view repair updates here:
{track_url}

Thank you for helping keep Hyderabad roads safe.
— SafeRoad Hyderabad Cell
"""

    is_resolved = (new_status == "Resolved")
    status_bg = "#d1e7dd" if is_resolved else "#ffe5d0" if new_status == "Action in Progress" else "#cfe2ff"
    status_color = "#0a3622" if is_resolved else "#7d3300" if new_status == "Action in Progress" else "#084298"
    accent_bar = "#2a9d8f" if is_resolved else "#e63946"

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SafeRoad Status Update</title>
</head>
<body style="margin:0; padding:24px 0; background-color:#eef2f6; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif; color:#2b2d42;">
  <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:620px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 6px 20px rgba(0,0,0,0.07); border:1px solid #dce2e6;" cellspacing="0" cellpadding="0">
          
          <!-- Brand Header -->
          <tr>
            <td style="background:linear-gradient(135deg, #1d3557 0%, #294c7a 100%); padding:28px 24px; text-align:center;">
              <h1 style="color:#ffffff; margin:0 0 4px; font-size:22px; font-weight:800;">🛣️ SafeRoad Hyderabad</h1>
              <p style="color:#e0e8f3; margin:0; font-size:13px;">Official Status Progress Notification</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 26px;">
              <p style="margin:0 0 16px; font-size:15px; line-height:1.6; color:#495057;">
                Dear <strong>{report.submitter_name}</strong>,<br>
                Municipal road authorities have updated the progress on your reported hazard at <strong>{report.location_name}</strong>.
              </p>

              <!-- Status Transition Box -->
              <table role="presentation" width="100%" style="background:#f8f9fa; border-left:5px solid {accent_bar}; border-radius:6px; margin-bottom:22px;" cellspacing="0" cellpadding="0">
                <tr>
                  <td style="padding:18px 20px;">
                    <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.8px; color:#6c757d; font-weight:600; margin-bottom:6px;">
                      Report {report.report_id} &bull; Status Transition
                    </div>
                    <div style="font-size:18px; font-weight:800; color:#1d3557;">
                      <span style="opacity:0.6; text-decoration:line-through;">{old_status}</span> 
                      <span style="color:{accent_bar}; margin:0 8px;">&rarr;</span> 
                      <span style="background:{status_bg}; color:{status_color}; padding:4px 12px; border-radius:14px; font-size:15px;">{new_status}</span>
                    </div>

                    {f'''
                    <div style="margin-top:14px; padding-top:12px; border-top:1px solid #e9ecef; font-size:14px; color:#343a40; line-height:1.5;">
                      <strong>Authority / Field Note:</strong><br>
                      {note}
                    </div>
                    ''' if note else ''}
                  </td>
                </tr>
              </table>

              <!-- CTA Button -->
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
                <tr>
                  <td align="center">
                    <a href="{track_url}" target="_blank" style="background:#1d3557; color:#ffffff; font-size:15px; font-weight:700; text-decoration:none; padding:14px 32px; border-radius:8px; display:inline-block; box-shadow:0 4px 12px rgba(29,53,87,0.35);">
                      View Complete Progress &amp; Timeline &rarr;
                    </a>
                  </td>
                </tr>
              </table>

              <p style="font-size:12px; color:#868e96; text-align:center; margin:0;">
                You can also enter your Report ID <strong style="color:#1d3557;">{report.report_id}</strong> on the SafeRoad <a href="{track_url}" style="color:#457b9d;">tracking page</a> anytime.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#f8f9fa; border-top:1px solid #e9ecef; padding:18px 24px; text-align:center; font-size:12px; color:#6c757d;">
              SafeRoad Hyderabad &bull; Urban Road Infrastructure Initiative &bull; Powered by Citizen Feedback
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    send_async_email(report.submitter_email, subject, text_body, html_body)


def send_petition_signature_confirmation(petition, signature, base_url: str = 'http://localhost:5000') -> None:
    """Send an automated email to a citizen when they sign a road safety petition."""
    if not signature or not signature.signer_email:
        return

    petition_url = f"{base_url.rstrip('/')}/petitions/{petition.petition_id}"
    subject = f"[SafeRoad Petition] Thank you for signing: {petition.title[:50]}..."

    text_body = f"""Dear {signature.signer_name},

Thank you for adding your verified digital signature to the road safety campaign on SafeRoad Hyderabad!

PETITION DETAILS:
• Campaign ID:    {petition.petition_id}
• Title:          {petition.title}
• Location:       {petition.location_name} ({petition.zone_name})
• Target Body:    {petition.target_authority}
• Progress:       {petition.signature_count} of {petition.target_signatures} verified signatures ({petition.progress_percent}%)

{f'Your Comment: "{signature.comment}"' if signature.comment else ''}

Every signature builds collective community pressure on municipal authorities to prioritize real road repairs.

Share and track the petition here:
{petition_url}

Thank you for being an active voice for safer streets in Hyderabad!
— SafeRoad Civic Mobilization Cell
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SafeRoad Petition Signed</title>
</head>
<body style="margin:0; padding:24px 0; background-color:#eef2f6; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; color:#2b2d42;">
  <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:620px; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 6px 20px rgba(0,0,0,0.07); border:1px solid #dce2e6;" cellspacing="0" cellpadding="0">
          <tr>
            <td style="background:linear-gradient(135deg, #e63946 0%, #b82430 100%); padding:28px 24px; text-align:center; color:#fff;">
              <h1 style="margin:0 0 4px; font-size:22px; font-weight:800;">✍️ Signature Recorded!</h1>
              <p style="margin:0; opacity:0.9; font-size:14px;">Community Road Safety Petition &bull; SafeRoad Hyderabad</p>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 26px;">
              <p style="font-size:15px; line-height:1.6; color:#495057; margin:0 0 16px;">
                Dear <strong>{signature.signer_name}</strong>,<br>
                Your signature has been officially registered in support of:
              </p>
              
              <div style="background:#f8f9fa; border-left:4px solid #e63946; padding:16px; border-radius:6px; margin-bottom:20px;">
                <h3 style="margin:0 0 8px; font-size:16px; color:#1d3557;">{petition.title}</h3>
                <div style="font-size:13px; color:#6c757d; margin-bottom:4px;"><i class="fa fa-location-dot me-1"></i>{petition.location_name} &bull; <strong>{petition.zone_name}</strong></div>
                <div style="font-size:13px; color:#1d3557; font-weight:600;">Target: {petition.target_authority}</div>
              </div>

              <!-- Progress bar -->
              <div style="margin-bottom:24px; background:#f1f5f9; padding:14px 18px; border-radius:8px;">
                <div style="display:flex; justify-content:space-between; font-size:13px; font-weight:bold; margin-bottom:6px;">
                  <span><strong>{petition.signature_count}</strong> of {petition.target_signatures} Signatures</span>
                  <span style="color:#e63946;">{petition.progress_percent}% Reached</span>
                </div>
                <div style="background:#dee2e6; height:10px; border-radius:5px; overflow:hidden;">
                  <div style="background:#e63946; width:{petition.progress_percent}%; height:100%;"></div>
                </div>
              </div>

              {f'<div style="background:#fff8f4; border:1px solid #ffd8a8; padding:12px 16px; border-radius:6px; font-size:13px; margin-bottom:22px; font-style:italic;">"{signature.comment}"</div>' if signature.comment else ''}

              <div style="text-align:center; margin:26px 0;">
                <a href="{petition_url}" target="_blank" style="background:#1d3557; color:#ffffff; font-size:15px; font-weight:700; text-decoration:none; padding:14px 34px; border-radius:8px; display:inline-block;">
                  View &amp; Share Petition &rarr;
                </a>
              </div>
            </td>
          </tr>
          <tr>
            <td style="background:#f8f9fa; border-top:1px solid #e9ecef; padding:16px 24px; text-align:center; font-size:12px; color:#6c757d;">
              SafeRoad Hyderabad &bull; Citizen Voice for Better Infrastructure
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    send_async_email(signature.signer_email, subject, text_body, html_body)


def send_petition_creation_confirmation(petition, base_url: str = 'http://localhost:5000') -> None:
    """Send an automated confirmation email to the citizen who launched the petition."""
    if not petition or not petition.creator_email:
        return

    petition_url = f"{base_url.rstrip('/')}/petitions/{petition.petition_id}"
    subject = f"[SafeRoad Petition Live] Your campaign '{petition.title[:45]}...' is now active!"

    text_body = f"""Dear {petition.creator_name},

Congratulations! Your road safety community petition has been launched and is now live on SafeRoad Hyderabad.

Petition ID:  {petition.petition_id}
Title:        {petition.title}
Location:     {petition.location_name}
Target Goal:  {petition.target_signatures} verified signatures
Assigned To:  {petition.target_authority}

Start mobilizing your neighborhood, college peers, and daily commuters:
{petition_url}

When your petition crosses 50% and 100% signature milestones, it is automatically escalated to the Chief Municipal Commissioner and Zonal Engineer!

— SafeRoad Community Action Cell
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SafeRoad Petition Launched</title>
</head>
<body style="margin:0; padding:24px 0; background-color:#eef2f6; font-family:'Segoe UI', sans-serif;">
  <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:620px; background:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #dce2e6;" cellspacing="0" cellpadding="0">
          <tr>
            <td style="background:linear-gradient(135deg, #1d3557, #457b9d); padding:28px 24px; text-align:center; color:#fff;">
              <h1 style="margin:0 0 6px; font-size:22px; font-weight:800;">🚀 Petition Launched!</h1>
              <p style="margin:0; opacity:0.9; font-size:14px;">Your civic campaign is live on SafeRoad</p>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 26px;">
              <p>Dear <strong>{petition.creator_name}</strong>,</p>
              <p>Your community petition has been registered. You can now gather verified signatures from fellow residents and commuters.</p>
              
              <div style="background:#f8f9fa; border-left:4px solid #1d3557; padding:16px; border-radius:6px; margin:20px 0;">
                <h4 style="margin:0 0 6px; font-size:16px;">{petition.title}</h4>
                <div style="font-size:13px; color:#6c757d;">Tracking ID: <strong>{petition.petition_id}</strong> &bull; Goal: <strong>{petition.target_signatures} Signatures</strong></div>
              </div>

              <div style="text-align:center; margin:26px 0;">
                <a href="{petition_url}" target="_blank" style="background:#e63946; color:#ffffff; font-size:15px; font-weight:700; text-decoration:none; padding:14px 34px; border-radius:8px; display:inline-block;">
                  View &amp; Mobilize Signatures &rarr;
                </a>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    send_async_email(petition.creator_email, subject, text_body, html_body)

