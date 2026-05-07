import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email_config import EMAIL_CONFIG

class EmailNotifier:
    def __init__(self):
        self.smtp_server  = EMAIL_CONFIG['smtp_server']
        self.smtp_port    = EMAIL_CONFIG['smtp_port']
        self.sender_email = EMAIL_CONFIG['sender_email']

    def _build_html_table(self, tsv_filepath):
        """
        Read TSV file, sort by STARTDATUM, and convert to a styled HTML table
        """
        rows    = []
        headers = []

        # Try encodings in order until one works
        for encoding in ('utf-8', 'latin-1', 'cp1252'):
            try:
                with open(tsv_filepath, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                print(f"✓ File read successfully with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                print(f"  encoding {encoding} failed, trying next...")
                continue
        else:
            return "<p>Error: Could not decode file with any known encoding.</p>"

        if not lines:
            return "<p>No data found.</p>"

        headers = lines[0].strip().split('\t')

        for line in lines[1:]:
            if line.strip():
                values = line.strip().split('\t')
                while len(values) < len(headers):
                    values.append('')
                rows.append(dict(zip(headers, values)))

        # Sort by STARTDATUM
        try:
            rows.sort(key=lambda r: r.get('STARTDATUM', ''))
        except Exception:
            pass

        # Build styled HTML table
        html = '''
        <table style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 13px; width: 100%;">
            <thead>
                <tr style="background-color: #4472C4; color: white;">
        '''
        for h in headers:
            html += f'<th style="border: 1px solid #ccc; padding: 6px 10px; text-align: left;">{h}</th>'
        html += '</tr></thead><tbody>'

        for i, row in enumerate(rows):
            bg_color = '#f2f2f2' if i % 2 == 0 else '#ffffff'
            html += f'<tr style="background-color: {bg_color};">'
            for h in headers:
                html += f'<td style="border: 1px solid #ccc; padding: 5px 10px;">{row.get(h, "")}</td>'
            html += '</tr>'

        html += '</tbody></table>'
        return html

    def send_report(self, tsv_filepath, recipient_email, subject, intro_body=""):
        """
        Send email with TSV data rendered as a sorted HTML table in the body
        """
        try:
            print(f"Sending email to {recipient_email} via {self.smtp_server}:{self.smtp_port}...")

            html_table = self._build_html_table(tsv_filepath)

            html_body = f'''
            <html>
            <body style="font-family: Arial, sans-serif; font-size: 13px; color: #333;">
                <p>{intro_body.replace(chr(10), "<br>")}</p>
                <br>
                {html_table}
                <br>
                <p style="color: #888; font-size: 11px;">
                    Automatisch generiert von Planout Export System
                </p>
            </body>
            </html>
            '''

            msg = MIMEMultipart('alternative')
            msg['From']    = self.sender_email
            msg['To']      = recipient_email
            msg['Subject'] = subject

            # Explicitly set utf-8 for the HTML part so umlauts render correctly
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.sendmail(self.sender_email, recipient_email, msg.as_string())

            print(f"✓ Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            print(f"✗ Error sending email: {e}")
            return False