import logging
import schedule
import time
import threading
import datetime
import os
from EmailNotifier import EmailNotifier

class EmailScheduler:
    def __init__(self, planout_instance):
        self.planout          = planout_instance
        self.scheduler_thread = None
        self.active_jobs      = {}
        self.lock             = threading.Lock()

    def _generate_job_id(self, recipient_email, day, time_str):
        return f"{recipient_email}_{day}_{time_str}".replace(":", "-").replace("@", "_at_")

    def _send_report_job(self, recipient_email, resources, startdatum, enddatum, job_label):
            try:
                logging.info("Running scheduled job: %s", job_label)

                filepath = self.planout.corporatePlannerOutput(
                    startdatum=startdatum,
                    enddatum=enddatum,
                    project="",
                    resource=resources
                )

                email_notifier = EmailNotifier()

                subject = f"Planout Ressourcen-Report ({startdatum.strftime('%d.%m.%Y')} - {enddatum.strftime('%d.%m.%Y')})"

                resource_list    = [r.strip() for r in resources.split(',') if r.strip()] if resources else []
                resource_summary = ", ".join(resource_list) if resource_list else "Alle Ressourcen"

                intro_body = (
                    f"Guten Tag,\n\n"
                    f"anbei finden Sie den Planout Ressourcen-Überblick für den Zeitraum "
                    f"vom {startdatum.strftime('%d.%m.%Y')} bis {enddatum.strftime('%d.%m.%Y')}.\n\n"
                    f"Enthaltene Ressourcen: {resource_summary}\n\n"
                    f"Mit freundlichen Grüßen,\n"
                    f"Ihr Planout Export System"
                )

                # Use send_report instead of send_file
                success = email_notifier.send_report(
                    tsv_filepath=filepath,
                    recipient_email=recipient_email,
                    subject=subject,
                    intro_body=intro_body
                )

                if success:
                    logging.info("Report sent to %s", recipient_email)
                else:
                    logging.error("Failed to send report to %s", recipient_email)

                if os.path.exists(filepath):
                    os.remove(filepath)

            except Exception as e:
                logging.error("Error in scheduled job '%s': %s", job_label, e, exc_info=True)

    def add_job(self, recipient_email, resources, day, time_str, lookahead_days=7):
        try:
            job_id = self._generate_job_id(recipient_email, day, time_str)
            self.remove_job(job_id)

            def job_func():
                startdatum = datetime.date.today()
                enddatum   = startdatum + datetime.timedelta(days=lookahead_days)
                self._send_report_job(
                    recipient_email=recipient_email,
                    resources=resources,
                    startdatum=startdatum,
                    enddatum=enddatum,
                    job_label=job_id
                )

            job = getattr(schedule.every(), day.lower()).at(time_str).do(job_func)

            with self.lock:
                self.active_jobs[job_id] = {
                    'job'            : job,
                    'recipient_email': recipient_email,
                    'resources'      : resources,
                    'day'            : day,
                    'time'           : time_str,
                    'lookahead_days'  : lookahead_days,
                    'created_at'     : datetime.datetime.now().isoformat()
                }

            logging.info("Scheduled job '%s' every %s at %s → %s", job_id, day, time_str, recipient_email)
            return job_id

        except Exception as e:
            logging.error("Error adding job: %s", e)
            return None

    def remove_job(self, job_id):
        with self.lock:
            if job_id in self.active_jobs:
                schedule.cancel_job(self.active_jobs[job_id]['job'])
                del self.active_jobs[job_id]
                logging.info("Removed job '%s'", job_id)
                return True
        return False

    def get_all_jobs(self):
        with self.lock:
            return [
                {k: v for k, v in job_info.items() if k != 'job'}
                | {'job_id': job_id}
                for job_id, job_info in self.active_jobs.items()
            ]

    def trigger_job_now(self, job_id):
        with self.lock:
            if job_id not in self.active_jobs:
                return False
            job_info = self.active_jobs[job_id]

        startdatum = datetime.date.today()
        enddatum   = startdatum + datetime.timedelta(days=job_info['lookahead_days'])
        

        thread = threading.Thread(
            target=self._send_report_job,
            args=(
                job_info['recipient_email'],
                job_info['resources'],
                startdatum,
                enddatum,
                job_id
            ),
            daemon=True
        )
        thread.start()
        return True

    def start(self):
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logging.info("Scheduler already running")
            return

        def run():
            logging.info("Scheduler background thread started")
            while True:
                schedule.run_pending()
                time.sleep(60)

        self.scheduler_thread = threading.Thread(target=run, daemon=True)
        self.scheduler_thread.start()
        logging.info("Scheduler thread started")