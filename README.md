```
    ___       ___       ___      ___       ___       ___
   /\__\     /\  \     /\__\    /\  \     /\__\     /\  \
  /:/ _/_   _\:\  \   /:/  /   _\:\  \   /:| _|_    \:\  \
 /:/_/\__\ /\/::\__\ /:/__/   /\/::\__\ /::|/\__\   /::\__\
 \:\/:/  / \::/\/__/ \:\  \   \::/\/__/ \/|::/  /  /:/\/__/
  \::/  /   \:\__\    \:\__\   \:\__\     |:/  /  /:/  /
   \/__/     \/__/     \/__/    \/__/     \/__/   \/__/
               A static code analyzer for UiPath XAML files
```

UiLint [![CircleCI](https://circleci.com/gh/curipha/uilint.svg?style=svg)](https://circleci.com/gh/curipha/uilint)
=================
A static code analyzer (linter tool) for UiPath XAML files.
This program requires Python 3.5 or above.

Installation
-----------------
1. Download this repository to local computer
2. That's all

Usage
-----------------
```
$ python3 uilint.py path/to/uipath/project
```

Pass the robot project root directory (which contains `project.json` file).

To Do
-----------------
- [ ] Python Packaging
- [ ] i18n (messages)
- [ ] Revise error messages
- [ ] Introduce a Plug-in architecture for checking rules
- [ ] Test for rules
- [ ] Configuration for rules


(Guide for Japanese) 日本語の説明
----------------------
UiPath が出力する XAML ファイル用のコードチェックツール（コードアナライザ）です．
ありがちな間違いを見つけて警告してくれます．英語で．

Python 3.5 かそれ以上が必要です．

ローカルにダウンロードして `uilint.py` を実行してください．
引数にロボットのプロジェクトディレクトリ（`project.json` が含まれているディレクトリ）を指定してください．

ライセンスは GPL です．お察しください．
ノウハウはみんなで共有しましょう (\*'ω'\*)
