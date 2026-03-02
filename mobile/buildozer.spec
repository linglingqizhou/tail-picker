[app]
title = 尾盘选股器
package.name = tailpicker
package.domain = com
source.dir = mobile
source.include_exts = py,png,jpg,kv,atlas,json
version = 3.1.0
requirements = python3,kivy==2.1.0,akshare,pandas,requests,tabulate,numpy,lxml,beautifulsoup4
orientation = portrait
fullscreen = 0

[android]
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 31
android.minapi = 21
android.ndk = 23b
android.skip_update = False
android.accept_sdk_license = True
android.entrypoint = org.kivy.android.PythonActivity
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.label = 尾盘选股器
android.release_artifact = apk
android.debug_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1
