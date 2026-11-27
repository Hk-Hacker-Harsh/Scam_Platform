"""Builds the two synthetic test APKs (fake_sbi.apk, benign.apk) used by the tests. Needs pyaxml and a JDK
(keytool, jarsigner); the built files are already in this folder, so this only matters if you change them."""
import sys, zipfile, subprocess, os
from pyaxml import axml
def build(name, pkg, label, perms, target, strings, sign=True):
    xml = f'''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{pkg}" android:versionCode="1" android:versionName="1.0">
<uses-sdk android:minSdkVersion="19" android:targetSdkVersion="{target}"/>
{''.join(f'<uses-permission android:name="android.permission.{p}"/>' for p in perms)}
<application android:label="{label}"><activity android:name=".Main" android:exported="true"/></application>
</manifest>'''
    a = axml.AXML(); a.from_xml(xml)
    with zipfile.ZipFile(name, "w") as z:
        z.writestr("AndroidManifest.xml", a.pack())
        z.writestr("classes.dex", b"dex\n035\x00" + b"\x00".join(s.encode() for s in strings))
    if sign:
        if not os.path.exists("ks.jks"):
            subprocess.run(["keytool","-genkeypair","-keystore","ks.jks","-storepass","passw0rd","-keypass","passw0rd","-alias","a","-keyalg","RSA","-keysize","2048","-dname","CN=Android Debug,O=Android,C=US","-validity","3650"],check=True,capture_output=True)
        subprocess.run(["jarsigner","-keystore","ks.jks","-storepass","passw0rd",name,"a"],check=True,capture_output=True)
build("fake_sbi.apk","com.fakebank.sbi.kyc","SBI KYC Update",["INTERNET","READ_SMS","RECEIVE_SMS","SYSTEM_ALERT_WINDOW","READ_CONTACTS","RECEIVE_BOOT_COMPLETED"],22,
  ["http://185.220.101.5/api/sms","https://api.telegram.org/bot1234567890:AAH_abcdefghijklmnopqrstuvwxyz012345/sendMessage","http://sbi-kyc-update.xyz/login","upi collect refund@abcd","+919876543210"])
build("benign.apk","com.example.notes","Notes",["INTERNET"],34,["https://example.org/help"],sign=True)
print("built")
