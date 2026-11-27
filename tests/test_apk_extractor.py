"""APK extractor: real DEX string table, manifest component rights, asset scanning and identifier cleaning."""
import os
import shutil
import struct
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from core.analysis import analyze
from core.checks.apk.extractor import clean_ids, dex_string_table, manifest_facts
from core.extract import extract_all

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def make_dex(strings, junk=b""):
    """Minimal DEX: header + string_ids + string data (enough for the string-table reader)."""
    n = len(strings)
    data, offs = b"", []
    base = 0x70 + 4 * n
    for s in strings:
        b = s.encode()
        offs.append(base + len(data))
        data += bytes([len(s)]) + b + b"\x00"   # uleb128 length < 128
    hdr = bytearray(0x70)
    hdr[0:8] = b"dex\n035\x00"
    struct.pack_into("<II", hdr, 0x38, n, 0x70)
    return bytes(hdr) + b"".join(struct.pack("<I", o) for o in offs) + data + junk


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PS01_POLICE_PASSWORD", "pw-123")
    monkeypatch.setenv("PS01_API_KEY", "k")
    a = create_app(db_path=str(tmp_path / "t.db"), network=False)
    a.config["TESTING"] = True
    return a


def test_dex_string_table():
    assert dex_string_table(make_dex(["https://a.xyz/x", "Ldalvik/system/DexClassLoader;"])) == ["https://a.xyz/x", "Ldalvik/system/DexClassLoader;"]
    assert dex_string_table(b"not a dex") is None


def test_manifest_component_rights():
    from lxml import etree
    xml = etree.fromstring(b"""<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="x.y">
      <application android:usesCleartextTraffic="true">
        <activity android:name=".A"><intent-filter><action android:name="android.intent.action.VIEW"/></intent-filter></activity>
        <service android:name=".Acc" android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
          <intent-filter><action android:name="android.accessibilityservice.AccessibilityService"/></intent-filter></service>
        <service android:name=".N"><intent-filter><action android:name="android.service.notification.NotificationListenerService"/></intent-filter></service>
        <receiver android:name=".R" android:permission="android.permission.BIND_DEVICE_ADMIN"/>
      </application></manifest>""")
    f = manifest_facts(xml)
    assert {"BIND_ACCESSIBILITY_SERVICE", "BIND_NOTIFICATION_LISTENER_SERVICE", "BIND_DEVICE_ADMIN"} <= set(f["component_perms"])
    assert f["launcher"] is False and f["cleartext"] is True


def test_clean_ids_drops_junk_seen_in_real_apk():
    junk = ("kotlin.array androidmanifest.xml bumptech.glide firebase.please gms.version trn.ust com.example.app "
            "0p@bi tp@fn ctqp.trn.ust.q@od non-@nullable android@android.com 8.1.2.1 0.0.0.0 127.0.0.1 +919999999999 "
            "https://www.google.com/x https://app-measurement.com/a ")
    real = "https://loanlenders-hoogmatic.in/api rvloanwala.co.in http://185.220.101.5:8080/up pay.me@ybl support@quickloan.top"
    ids = clean_ids(extract_all(junk + real))
    assert set(ids["domains"]) == {"loanlenders-hoogmatic.in", "rvloanwala.co.in"}
    assert ids["upis"] == ["pay.me@ybl"]
    assert ids["ips"] == ["185.220.101.5"]
    assert ids["emails"] == ["support@quickloan.top"]
    assert ids["phones"] == []


def test_hybrid_app_assets_and_new_checks(app, tmp_path):
    p = tmp_path / "trojan.apk"
    shutil.copy(os.path.join(FIX, "fake_sbi.apk"), p)
    with zipfile.ZipFile(p, "a") as z:
        z.writestr("classes2.dex", make_dex(["Ldalvik/system/DexClassLoader;", "setComponentEnabledSetting", "upi://collect?pa=x@ybl"],
                                            junk=b"\x01tp@fn\x02kotlin.array\x03"))
        z.writestr("assets/index.android.bundle", b'var a="https://quickloan-rupee.top/api/contacts";var b="http://45.137.21.9:8080/upload";')
        z.writestr("lib/arm64-v8a/libjiagu.so", b"\x7fELF")
        z.writestr("assets/payload.dat", b"dex\n035\x00rest")
    cid = analyze(app.db, "apk", file_bytes=p.read_bytes(), filename="trojan.apk")
    c = app.db.get_case(cid)
    fired = {f["check_id"] for f in c["findings"] if f["status"] == "fired"}
    assert {"apk_runtime_code_loading", "apk_packer_obfuscation", "apk_hidden_launcher", "apk_cleartext_ip_endpoints",
            "apk_sms_plus_upi_collect", "apk_permission_combo"} <= fired
    ids = {(i["type"], i["value"]) for i in c["ids"]}
    assert ("domain", "quickloan-rupee.top") in ids and ("ip", "45.137.21.9") in ids
    assert not any(v in ("kotlin.array", "tp@fn") for _, v in ids)
    a = c["meta"]["apk"]
    assert a["framework"] == "React Native" and a["dex_count"] == 2 and a["scanned_files"] >= 1
    assert "assets/payload.dat" in a["hidden_payloads"]


def test_benign_apk_stays_low(app):
    cid = analyze(app.db, "apk", file_bytes=open(os.path.join(FIX, "benign.apk"), "rb").read(), filename="benign.apk")
    c = app.db.get_case(cid)
    assert c["level"] in ("Low", "Medium") and c["hard"] == 0
