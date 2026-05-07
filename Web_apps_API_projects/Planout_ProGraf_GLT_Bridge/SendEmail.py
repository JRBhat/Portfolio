import os
import smtplib
from email.message import EmailMessage

class SendEmail(object):
    """simple wrapper around sending an email for reports and error messages"""

    def __init__(self):
        self.smtpserver=os.environ.get("SMTP_SERVER", "localhost")
        self.targetemailaddress=os.environ.get("NOTIFICATION_EMAIL", "notify@example.com")
        self.collectmsg=""

    def send(self, subject: str, message:str):
        # Create a text/plain message
        msg = EmailMessage()
        msg.set_content(str(message))

        msg['Subject'] = "[PlanoutToGLTBridgeScript] "+str(subject)
        msg['From'] = os.environ.get("SENDER_EMAIL", "sender@example.com")
        msg['To'] = self.targetemailaddress

        # Send the message via our own SMTP server.
        s = smtplib.SMTP(self.smtpserver)
        s.send_message(msg)
        s.quit()

        self.collectmsg = ''

    def collectMsg(self, message:str):
        self.collectmsg+=str(message)+"\n"
        return self.collectmsg

    def hasCollectedMsg(self):
        #is there something stored in self.collectmsg and unsent?
        if self.collectmsg == "":
            return False
        return True

if __name__ == '__main__':
    instance = SendEmail()
    instance.send("testsubject", "testmessage\nsecondline")