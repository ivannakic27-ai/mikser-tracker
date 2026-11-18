"""Run after `flutter create`: adds INTERNET permission (release builds lack it), https <queries> for url_launcher,
and a readable app label. Usage: python scripts/patch_manifest.py app/android/app/src/main/AndroidManifest.xml"""
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
if "android.permission.INTERNET" not in s:
    s = re.sub(r"(<manifest[^>]*>)",
               r'\1\n    <uses-permission android:name="android.permission.INTERNET"/>\n'
               r'    <queries>\n        <intent>\n            <action android:name="android.intent.action.VIEW"/>\n'
               r'            <data android:scheme="https"/>\n        </intent>\n    </queries>', s, count=1)
s = re.sub(r'android:label="[^"]*"', 'android:label="Mikser tracker"', s, count=1)
open(p, "w", encoding="utf-8").write(s)
print("patched", p)
