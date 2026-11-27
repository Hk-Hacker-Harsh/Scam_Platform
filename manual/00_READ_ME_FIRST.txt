SATARK (सतर्क) – PROJECT MANUAL
R4C Hackathon 2026, Rajasthan Police, PS01: Cyber Fraud / Phishing / Malicious Apps
Last updated: 20 November 2026

Satark checks suspicious messages, links, screenshots / QR codes, Android apps and e-mails, gives a risk level with
the exact reasons, pulls out phone numbers, UPI IDs, domains and other identifiers, links cases that share them, and
gives police officers a dashboard to confirm fraud. Citizens reach it through a website, a Chrome extension and a
Telegram bot. A local AI assistant explains results in English and Hindi.

HOW THIS MANUAL IS ORGANISED
  01_overview.txt              what Satark does, the main ideas, what is built
  02_files.txt                 every folder and file, and what it does
  03_configuration.txt         settings (environment variables) and the instance/ folder
  04_setup_and_run.txt         install, build, run the server, extension, bot, OCR, AI; first-time checklist
  05_where_to_update_what.txt  "I want to change X" -> which file and how
  06_api_reference.txt         every server address (website API, extension / bot API, downloads)
  07_detection_and_scoring.txt checks, strong / weak signals, how High / Medium / Low is decided, linking, caching
  08_ai_assistant.txt          how the assistant works, its safety checks, models we tested
  09_testing.txt               running and writing tests
  10_security_and_privacy.txt  what protects users, officers and the server
  11_troubleshooting.txt       errors we have already met and their fixes
  12_demo_and_submission.txt   prototype, screenshots, deck, demo script, tips for the final
  screenshots/                 PNG screenshots of the website, officer dashboard and extension, plus wireframes

QUICK START (development laptop, Windows)
  1. cd "ps01-platformlatest\ps01-platform"
  2. python app.py                      -> http://127.0.0.1:5000
  3. Officer login: user "police", password in instance\initial_police_password.txt
  4. After changing anything in frontend\src:  cd frontend  then  npm run build
  5. Tests: python -m pytest tests -q

NEVER SHARE: the instance\ folder (database, passwords, API key, Telegram token, session key).
