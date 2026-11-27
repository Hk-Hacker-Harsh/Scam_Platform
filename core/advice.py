"""Citizen advice in English and Hindi, shared by the web result page, the API, the extension and the bot."""

ADVICE = {
    "danger": {
        "en": ["Do not click the link, install the app, call the number or share any OTP / PIN.",
               "If you already paid or shared details: call 1930 now and report at cybercrime.gov.in. Ask your bank to block the card / UPI.",
               "Keep screenshots and the message as evidence. Report the number on Sanchar Saathi (Chakshu)."],
        "hi": ["लिंक न खोलें, ऐप इंस्टॉल न करें, नंबर पर कॉल न करें और OTP / PIN किसी को न बताएं।",
               "अगर पैसे कट गए हैं या जानकारी दे दी है तो तुरंत 1930 पर कॉल करें और cybercrime.gov.in पर शिकायत करें।",
               "मैसेज और स्क्रीनशॉट सबूत के लिए संभाल कर रखें।"],
    },
    "caution": {
        "en": ["Treat it as suspicious. Do not click or reply.",
               "Contact the organisation only through the number on your card or its official website, not the one in this message."],
        "hi": ["इसे संदिग्ध मानें। लिंक न खोलें और जवाब न दें।",
               "संस्था से केवल उसकी आधिकारिक वेबसाइट या कार्ड पर लिखे नंबर से संपर्क करें।"],
    },
    "official": {
        "en": ["This is on the official registry. Still check the address bar before entering a password, and never share an OTP."],
        "hi": ["यह आधिकारिक सूची में है। फिर भी पासवर्ड डालने से पहले पता जांचें और OTP कभी न बताएं।"],
    },
    "low": {
        "en": ["No strong warning signs from the checks that could run. That is not a guarantee of safety.",
               "Never share an OTP / PIN and verify unexpected requests through official channels."],
        "hi": ["जो जांचें चल सकीं उनमें कोई बड़ा खतरा नहीं मिला, पर यह सुरक्षा की गारंटी नहीं है।",
               "OTP / PIN कभी किसी को न बताएं।"],
    },
}


def bucket(level):
    if level in ("High", "Confirmed fraud"):
        return "danger"
    if level == "Medium":
        return "caution"
    if level == "Verified official":
        return "official"
    return "low"


def advice(level):
    return ADVICE[bucket(level)]
