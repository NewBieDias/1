[app]
title = AlbionHelper
package.name = albionhelper
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json
version = 0.1
requirements = python3,kivy,opencv-python,numpy,mss,requests,pyautogui
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 24
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

[buildozer]
log_level = 2
warn_on_root = 1
