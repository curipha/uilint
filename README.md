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
1. Download this repository to your computer
2. Run `make mo`

If you see the following message, step 2 was failed (or simply forgot to do).
Please make sure `gettext` package is installed to your computer and run `make mo` again.

```
FileNotFoundError: [Errno 2] No translation file found for domain: 'messages'
```

Usage
-----------------
```
$ python3 uilint.py path/to/uipath/project
```

Pass the robot project root directory (which contains `project.json` file).

To Do
-----------------
- [ ] Python Packaging
- [x] i18n (messages)
- [ ] Revise error messages
- [ ] Introduce a Plug-in architecture for rules
- [ ] Test for rules
- [ ] Configuration for rules

Translation
-----------------
It uses `gettext` framework to apply translation texts.
Translation texts are defined in `locale/(lang).po` files.
If there is an update for something, simply revise these PO files (and create MO files via `make mo`).

### Add a new language translation
Create a new PO file for non-translated languages to add a new language translation.

1. Add new language code to `langs` variable in `Makefile`
    - Language codes are listed on the [manual](https://www.gnu.org/software/gettext/manual/html_node/Usual-Language-Codes.html) of `gettext`.
2. Run `make po`
3. New PO file (contains a language code as a its file name) will be created in the `locale` directory
4. Edit it

### Update existing translation text
1. Edit a PO file in `locale` directory
2. Run `make mo`
3. `git commit --all` to commit the update

### Add a new untranslated text to the application
1. Make sure the new untranslated text is surrounded by `_()` and its form is begins with `rule:` for rule messages or `msg:` for other messages
2. Run `make po`
3. Edit PO files as same manner as updating existing translation text

(Guide for Japanese) 日本語の説明
----------------------
UiPath が出力する XAML ファイル用のコードチェックツール（コードアナライザ）です．
ありがちな間違いを見つけて警告してくれます．

Python 3.5 かそれ以上が必要です．

ローカルにダウンロードして，翻訳データを作成するために `make mo` してください．
その後 `uilint.py` を実行してください．
引数にロボットのプロジェクトディレクトリ（`project.json` が含まれているディレクトリ）を指定してください．

ライセンスは GPL です．お察しください．
ノウハウはみんなで共有しましょう (\*'ω'\*)
