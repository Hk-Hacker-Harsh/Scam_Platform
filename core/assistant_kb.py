"""Curated answers for the citizen assistant (English + Hindi). Sources: general public guidance from the
National Cyber Crime Reporting Portal (cybercrime.gov.in, helpline 1930), RBI and Sanchar Saathi (Chakshu).
Each entry: keywords (any match scores), en, hi. Keep answers short, factual and action-oriented."""

FAQ = [
    {"id": "report", "kw": ["report", "complaint", "fir", "1930", "cybercrime", "शिकायत", "रिपोर्ट"],
     "en": "Call 1930 (National Cyber Crime Helpline) as soon as possible, or file a complaint at cybercrime.gov.in. "
           "If money was taken, also call your bank to block the card or UPI. Keep screenshots, the message, the number and the transaction ID.",
     "hi": "जितनी जल्दी हो सके 1930 पर कॉल करें या cybercrime.gov.in पर शिकायत दर्ज करें। पैसे कटे हों तो बैंक को कॉल करके कार्ड या UPI ब्लॉक करवाएं। "
           "स्क्रीनशॉट, मैसेज, नंबर और ट्रांज़ैक्शन ID संभाल कर रखें।"},
    {"id": "otp", "kw": ["otp", "pin", "cvv", "password", "ओटीपी", "पिन"],
     "en": "Never share an OTP, UPI PIN, CVV or password with anyone. Banks, police, courier and telecom staff never ask for them. "
           "You never need a PIN to receive money.",
     "hi": "OTP, UPI PIN, CVV या पासवर्ड किसी को न बताएं। बैंक, पुलिस, कूरियर या टेलीकॉम कर्मचारी कभी ये नहीं मांगते। पैसे लेने के लिए PIN की ज़रूरत नहीं होती।"},
    {"id": "digital_arrest", "kw": ["digital arrest", "cbi", "customs", "parcel", "narcotics", "video call", "arrest", "डिजिटल अरेस्ट", "गिरफ्तार"],
     "en": "'Digital arrest' is a scam. No police, CBI or customs officer arrests anyone over a video call or asks for money to close a case. "
           "End the call, do not transfer money, and call 1930.",
     "hi": "'डिजिटल अरेस्ट' एक धोखा है। पुलिस, CBI या कस्टम वीडियो कॉल पर गिरफ्तारी नहीं करते और केस बंद करने के लिए पैसे नहीं मांगते। कॉल काटें, पैसे न भेजें और 1930 पर कॉल करें।"},
    {"id": "upi_receive", "kw": ["receive", "refund", "qr", "scan", "collect", "cashback", "रिफंड", "स्कैन"],
     "en": "Scanning a QR code or entering your UPI PIN always sends money out of your account. You never scan or enter a PIN to receive a refund or prize. "
           "Decline unknown 'collect' requests.",
     "hi": "QR स्कैन करने या UPI PIN डालने से पैसे हमेशा आपके खाते से जाते हैं। रिफंड या इनाम पाने के लिए कभी स्कैन या PIN की ज़रूरत नहीं होती।"},
    {"id": "kyc", "kw": ["kyc", "account blocked", "update", "pan", "aadhaar", "केवाईसी"],
     "en": "Banks do not block accounts over SMS links. Do KYC only at your branch or in the bank's official app or website, typed in yourself, never through a link in a message.",
     "hi": "बैंक SMS लिंक के ज़रिए खाता ब्लॉक नहीं करते। KYC केवल शाखा में या बैंक के आधिकारिक ऐप/वेबसाइट पर करें, मैसेज के लिंक से नहीं।"},
    {"id": "job", "kw": ["job", "task", "part time", "like", "youtube", "review", "telegram", "earn", "नौकरी", "घर बैठे"],
     "en": "Paid 'tasks' like liking videos or rating hotels are a common scam. They pay small amounts first, then ask you to 'invest' and keep the money. Do not pay to unlock earnings.",
     "hi": "वीडियो लाइक या रिव्यू जैसे 'टास्क' वाली नौकरी आम धोखा है। पहले थोड़े पैसे देते हैं, फिर 'निवेश' करवा कर पैसे रख लेते हैं।"},
    {"id": "investment", "kw": ["investment", "trading", "stock", "ipo", "crypto", "double", "guaranteed", "return", "निवेश", "डबल"],
     "en": "Guaranteed or very high returns are a warning sign. Use only SEBI-registered brokers and apps from official stores. WhatsApp or Telegram 'VIP tip' groups are a common trap.",
     "hi": "गारंटी वाला या बहुत ज़्यादा रिटर्न खतरे का संकेत है। केवल SEBI-पंजीकृत ब्रोकर और आधिकारिक ऐप का उपयोग करें।"},
    {"id": "loan", "kw": ["loan", "instant loan", "processing fee", "लोन"],
     "en": "Real lenders do not ask for a fee before giving a loan, and do not need access to your contacts or photos. Check that the lender is RBI-registered before installing any app.",
     "hi": "असली लोन देने वाले पहले फीस नहीं मांगते और आपके कॉन्टैक्ट या फोटो की ज़रूरत नहीं होती। ऐप इंस्टॉल करने से पहले जांचें कि कंपनी RBI में पंजीकृत है।"},
    {"id": "apk", "kw": ["apk", "app", "install", "download", "ऐप"],
     "en": "Install apps only from the Play Store. An .apk sent on WhatsApp or SMS can read your SMS and OTPs. If you installed one, turn on airplane mode, uninstall it, and call your bank.",
     "hi": "ऐप केवल Play Store से इंस्टॉल करें। WhatsApp या SMS पर भेजा गया .apk आपके SMS और OTP पढ़ सकता है।"},
    {"id": "remote", "kw": ["anydesk", "teamviewer", "screen share", "remote", "quick support", "install anydesk", "rustdesk", "airdroid"],
     "en": "Never install AnyDesk, TeamViewer or any screen-sharing app on someone's request. It lets them see your screen and OTPs. Uninstall it and change your banking passwords.",
     "hi": "किसी के कहने पर AnyDesk, TeamViewer या स्क्रीन-शेयर ऐप कभी इंस्टॉल न करें।"},
    {"id": "lost_money", "kw": ["lost", "paid", "money gone", "deducted", "transferred", "पैसे कट", "पैसे गए"],
     "en": "Act fast: call 1930 now. The first hours matter because banks can freeze the money only while it is still in the chain. Then file at cybercrime.gov.in and inform your bank.",
     "hi": "तुरंत 1930 पर कॉल करें। पहले कुछ घंटे बहुत ज़रूरी हैं, क्योंकि तभी बैंक पैसे रोक सकता है। फिर cybercrime.gov.in पर शिकायत करें।"},
    {"id": "check_number", "kw": ["number", "caller", "spam", "chakshu", "sanchar"],
     "en": "Paste the number here and I will look it up in our cases. You can also report fraud calls and SMS on Sanchar Saathi (Chakshu).",
     "hi": "नंबर यहां भेजें, मैं हमारे केस में जांच दूंगा। आप संचार साथी (चक्षु) पर भी फ्रॉड कॉल की शिकायत कर सकते हैं।"},
]

GREETING_EN = ("I am Satark's assistant. Paste a suspicious message, link, phone number or UPI ID and I will check it, "
               "or ask me about a scam type, what to do, or how to report.")
GREETING_HI = "मैं सतर्क सहायक हूं। कोई संदिग्ध मैसेज, लिंक, नंबर या UPI ID भेजें, मैं जांच करूंगा। धोखे के बारे में या शिकायत कैसे करें, यह भी पूछ सकते हैं।"
