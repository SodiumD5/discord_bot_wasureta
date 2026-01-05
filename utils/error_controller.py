from datetime import date, datetime
import functools
from apscheduler.schedulers.background import BackgroundScheduler
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import time
from dotenv import load_dotenv


def error_handler(caller_name: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                report.error_record(caller=caller_name, error=e)

                ctx = args[1] if len(args) > 1 else None
                if ctx:
                    from utils.forms import Form

                    form = Form("오류가 발생했습니다.\n나중에 다시 시도해주세요.")
                    await form.smart_send(ctx)
                return None

        return wrapper

    return decorator


class ErrorController:
    def __init__(self):
        self.command_count = 0
        self.error_count = 0
        self.db_error_count = 0
        load_dotenv()
        self.EMAIL = os.getenv("EMAIL")
        self.EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    def error_record(self, caller, error, is_db_error=False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("./Error.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}]\n{caller} 오류 : \n {error}\n\n")
        self.error_count += 1

        if is_db_error:
            self.db_error_count += 1

    def error_read(self):
        try:
            with open("./Error.txt", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "에러 없음"

    def error_clear(self):
        with open("./Error.txt", "w", encoding="utf-8") as f:
            f.write("")
        self.command_count = 0
        self.error_count = 0
        self.db_erorr_count = 0

    def error_report(self):
        error_message = f"총 명령어 {self.command_count}건 중 오류 {self.error_count}건\n\n"
        error_message += report.error_read()

        try:
            msg = MIMEMultipart()
            msg["From"] = self.EMAIL
            msg["TO"] = self.EMAIL
            msg["Subject"] = f"{date.today()} 오류 보고"  # 제목
            msg.attach(MIMEText(error_message, "plain", "utf-8"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.EMAIL, self.EMAIL_PASSWORD)
            server.sendmail(self.EMAIL, self.EMAIL, msg.as_string())
            print("이메일 보고서 전송 됨")
        except Exception as e:
            print(f"이메일 전송 실패 : {e}")
        report.error_clear()

    def test_error(self):
        report.error_record("누군가 부름", "에러임")

    def start_error_scheduler(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.error_report, "cron", hour=0, minute=0)  # 매일 자정 오류 보고
        # scheduler.add_job(self.test_error, "interval", seconds=1)
        scheduler.start()
        return scheduler


report = ErrorController()


if __name__ == "__main__":
    scheduler = report.start_error_scheduler()
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        scheduler.shutdown()
