"""Fill the database with SYNTHETIC demo cases (reserved .example/.test style domains and fictional numbers only)."""
import os
from app import app
from core.analysis import analyze
db = app.db
S = [
 ("message", "Dear customer, your SBI YONO account is blocked. Update KYC within 24 hours: http://sbi-yono-kyc.example.top/login and share the OTP. Helpline +923001110001"),
 ("message", "SBI Alert: KYC expired. Click http://sbi-yono-kyc.example.top/verify to avoid suspension. Call 9000000001"),
 ("message", "Congratulations! You won Rs 25 lakh lucky draw. Pay processing fee to claim.refund@okaxis and call +923001110001"),
 ("message", "Part time job: like YouTube videos, earn Rs 4000 daily. Join t.me/earnfast_example. Pay deposit to taskpay@abcd"),
 ("message", "Your electricity bill is pending, power will be disconnected tonight. Download app http://bit.ly/pow3r-bill or call 9000000002"),
 ("message", "CBI notice: parcel in your name has drugs. You are under digital arrest. Join video call and pay to safe-account@upi"),
 ("message", "Dial **21*9000000003# to claim cashback. Install AnyDesk to continue"),
 ("url", "https://hdfc-bank-kyc-update.example.cfd/login"),
 ("url", "http://sbi.co.in@evil-site.example.top/login?redirect=http://x.example"),
 ("url", "https://www.onlinesbi.sbi"),
 ("url", "https://раyраl-secure.example"),
 ("email", "From: HDFC Support <hdfc.support@gmail.com>\nReply-To: refund@evil.example.top\nSubject: Account suspended\nAuthentication-Results: mx; spf=fail; dkim=none; dmarc=fail\nContent-Type: text/html\n\n<a href='http://hdfc-bank-kyc-update.example.cfd/login'>www.hdfcbank.com</a> verify now"),
]
for k, t in S:
    analyze(db, k, text=t, source="public")
A = os.path.join("tests", "fixtures", "fake_sbi.apk")
analyze(db, "apk", file_bytes=open(A, "rb").read(), filename="fake_sbi.apk")
db.add_report(1, "Received this on my mother's phone", "")
db.add_report(3, "Lost no money but wanted to report", "")
print("seeded", db.stats()["total"], "cases")
