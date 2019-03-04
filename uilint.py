import os
import re
import sys
import argparse
import subprocess
import glob # Python >= 3.5
from lxml import etree

import uixaml

# Error flag
iserror = False


# Print error message
def error(msg: str, xaml: str = '-') -> None:
  iserror = True

  if arg.vsts:
    print('##vso[task.logissue type=error;sourcepath=%s;]%s' % (xaml, msg))
  else:
    print('%s: [Error] %s' % (xaml, msg))

# Print warning message
def warn(msg: str, xaml: str = '-') -> None:
  if arg.vsts:
    print('##vso[task.logissue type=warning;sourcepath=%s;]%s' % (xaml, msg))
  else:
    print('%s: [Warning] %s' % (xaml, msg))


# Linter
def lint() -> None:
  ss_dir = '%s/.screenshots' % arg.dir # Path to the directory of screenshots
  prjson = '%s/project.json' % arg.dir # Path to project.json

  # Set of screenshots (hash only, without extensions)
  ss_xaml = set() # Seen in XAML files
  ss_file = set(map(lambda f: os.path.splitext(f)[0], os.listdir(ss_dir))) if os.path.isdir(ss_dir) else set() # Stored


  # Get all XAML files including sub-directories
  xamls = glob.iglob('%s/**/*.xaml' % arg.dir, recursive=True)

  if not any(xamls):
    print('No XAML files exist in the specified directory.')
    sys.exit(1)


  # Check existence of project.json file
  if not os.path.isfile(prjson):
    error('project.json file does not exist. Are you running this lint program in CI/CD pipeline? It seems project.json is missed to commit.', prjson)


  for file in xamls:
    xaml  = etree.parse(file)
    xpath = etree.XPathEvaluator(xaml, namespaces=uixaml.xamlns)

    # Check existence of all screenshots
    screen = xpath('//ui:*[@InformativeScreenshot]')

    for e in screen:
      sfile = e.get('InformativeScreenshot')
      ss_xaml.add(sfile)

      if sfile not in ss_file:
        error('Screenshot file does not exist. Are you running this lint program in CI/CD pipeline? It seems a screenshot file is missed to commit. (Activity: %s, Screenshot: %s）' % (uixaml.displayname(e), sfile), file)

    #  GetPassword activity should not be used
    getpass = xpath('//ui:GetPassword')

    for e in getpass:
      error('GetPassword activity should not be used because of compatibility issues. Use Assign activity instead. (GetPassword: %s)' % uixaml.displayname(e), file)

    # MessageBox not in a comment
    msgbox = xpath('//ui:MessageBox[not(ancestor::ui:CommentOut)]')

    for e in msgbox:
      error('Found a MessageBox activity which is not commented out. Do you forget to comment out? (MessageBox: %s, Message: %s)' % (uixaml.displayname(e), e.get('Text')), file)

    # TerminateWorkflow not in a comment
    terminate = xpath('//xaml:TerminateWorkflow[not(ancestor::ui:CommentOut)]')

    for e in terminate:
      error('Found a TerminateWorkflow activity which is not commented out. Do you forget to comment out? (TerminateWorkflow: %s, Exception: %s, Reason: %s）' % (uixaml.displayname(e), e.get('Exception'), e.get('Reason')), file)

    # Looped activity in a Flowchart
    flow = xpath('//xaml:FlowStep[@x:Name = ./xaml:FlowStep.Next/x:Reference/text()]')

    for e in flow:
      error('Found a looped activity in a Flowchart. An infinite loop may occur. (Activity: %s)' % (uixaml.displayname(e.xpath('./*[not(xaml:FlowStep.Next) and not(sap2010:*)]', namespaces=uixaml.xamlns)[0])), file)

    # Empty Sequence
    seq = xpath('//xaml:Sequence[not(*) or (count(*) = 1 and ./xaml:Sequence.Variables)]')

    for e in seq:
      error('Empty Sequence should be removed. (Sequence: %s)' % (uixaml.displayname(e)), file)

    # Nested Sequence
    seq = xpath('//xaml:Sequence[not(ancestor::ui:CommentOut) and ((count(*) = 1 and ./xaml:Sequence) or (count(*) = 2 and ./xaml:Sequence and ./xaml:Sequence.Variables))]')

    for e in seq:
      error('Found a nested Sequence. Please remove an outer Sequence. (Sequence: %s -> %s)' % (uixaml.displayname(e), uixaml.displayname(e.xpath('./xaml:Sequence', namespaces=uixaml.xamlns)[0])), file)

    # Sequence contains many of activities
    seq = xpath('//xaml:Sequence[not(ancestor::ui:CommentOut) and count(*[not(self::xaml:Sequence.Variables) and not(self::xaml:Sequence)]) > 15]')

    for e in seq:
      warn('Many of activities are included in one Sequence. Please consider splitting the Sequence by functional group. (Sequence: %s)' % (uixaml.displayname(e)), file)

    # TryCatch with empty catch
    trycatch = xpath('//xaml:TryCatch[not(./xaml:TryCatch.Catches) or ./xaml:TryCatch.Catches/xaml:Catch[count(./xaml:ActivityAction/*) < 2]]')

    for e in trycatch:
      error('Found a TryCatch activity with an empty catch. Even if the purpose is to ignore any exceptions, how about logging it? (TryCatch: %s)' % (uixaml.displayname(e)), file)

    # Nested If more than 3 times
    seq = xpath('//xaml:If[not(ancestor::ui:CommentOut)]//xaml:If//xaml:If')

    for e in seq:
      warn('If activity nested more than 3 times should be replaced by Flowchart. (If: %s, Condition: %s)' % (uixaml.displayname(e), e.get('Condition')), file)

    # Excel Application Scope with Visible enabled
    eas = xpath('//ui:ExcelApplicationScope[not(@Visible) or @Visible != "False"]')

    for e in eas:
      warn('Visible property on Excel Application Scope should be unchecked if there is no need to show an Excel application on the screen. (Excel Application Scope: %s, File: %s)' % (uixaml.displayname(e), e.get('WorkbookPath')), file)

    # Workbook activities in an Excel Application Scope
    eas = xpath('|'.join(map(lambda e: '//ui:ExcelApplicationScope//%s' % e, uixaml.wbactivities)))

    for e in eas:
      error('Do not use a Workbook activity in the Excel Application Scope. Only Excel activities is adequate inside the Excel Application Scope. (Excel Application Scope: %s, Activity: %s)' % (uixaml.displayname(e.xpath('ancestor::ui:ExcelApplicationScope[1]', namespaces=uixaml.xamlns)[0]), uixaml.displayname(e)), file)

    # Launch an application by using OpenApplication/StartProcess instead of using Application Scope/Browser Scope
    openapp = xpath('//ui:OpenApplication[@FileName]|//ui:StartProcess[@FileName]')

    for e in openapp:
      filepath = e.get('FileName').lower()

      if 'excel.exe' in filepath:
        error('Excel application should be launched via Excel Application Scope not via OpenApplication/StartProcess activity. (Activity: %s)' % uixaml.displayname(e), file)
      if 'winword.exe' in filepath:
        error('Word application should be launched via Word Application Scope not via OpenApplication/StartProcess activity. (Activity: %s)' % uixaml.displayname(e), file)
      if 'iexplore.exe' in filepath or 'firefox.exe' in filepath or 'chrome.exe' in filepath:
        error('Web browser should be launched via Open Browser activity not via OpenApplication/StartProcess activity. (Activity: %s)' % uixaml.displayname(e), file)

    # SendHotkey with SpecialKey = False
    sendkey = xpath('//ui:SendHotkey[@SpecialKey = "False" and @Key != "{x:Null}"]')

    for e in sendkey:
      key = e.get('Key').strip()
      if len(key) > 1 and key.lower() in uixaml.specialkey:
        error('The SendHotkey activity may not work as intended because False is set to SpecialKey property. (SendHotkey: %s, Key: %s)' % (uixaml.displayname(e), key), file)

    # SendHotkey with empty Key
    sendkey = xpath('//ui:SendHotkey[not(@Key) or @Key = "{x:Null}"]')

    for e in sendkey:
      error('Found a SendHotkey activity with empty Key. Do you forget to set it? (SendHotkey: %s)' % uixaml.displayname(e), file)

    # SendHotkey for Alt-F4
    sendkey = xpath('//ui:SendHotkey[@KeyModifiers="Alt" and @Key="f4" and @SpecialKey="True"]')

    for e in sendkey:
      error('Close Application activity should be used instead of sending Alt-F4 by using SendHotkey activity. (SendHotkey: %s)' % uixaml.displayname(e), file)

    # SendHotkey with empty selector
    sendkey = xpath('//ui:SendHotkey[%s]/ui:SendHotkey.Target/ui:Target[not(@Selector) or @Selector = "{x:Null}"]' % ' and '.join(map(lambda e: 'not(ancestor::%s)' % e, uixaml.wndscopes)))

    for e in sendkey:
      warn('Selectors in a SendHotkey activity should not be left blank. Please edit a selector and/or move this activity into any application scopes like Attach Window scope. (SendHotkey: %s)' % uixaml.displayname(e), file)

    # TypeInto activity which possibly inputs a half-width kana
    typeinto = xpath('//ui:TypeInto[@Text and (not(@SimulateType) or @SimulateType = "False")]')

    for e in typeinto:
      text = e.get('Text')

      if len(text) < 1:
        continue

      if text[:1] == '[':
        # Text is written in VB expression
        warn('This TypeInto activity cannot input half-width kana correctly. Please replace it by SetText activity or check a SimulateType property. (TypeInto: %s, Text: %s)' % (uixaml.displayname(e), text), file)
      elif re.search(r'[\uff65-\uff9f]', text):
        # Text contains Half-width Kana
        error('This TypeInto activity will fail to input half-width kana. Please replace it by SetText activity or check a SimulateType property. (TypeInto: %s, Text: %s)' % (uixaml.displayname(e), text), file)

    # And/Or in conditional clause
    andor = xpath('//xaml:*[@Condition]')

    for e in andor:
      condition = e.get('Condition').lower()
      normalized_condition = re.sub(r'".*?"', '', condition) # XXX: Remove texts surrounded by ""

      if ' and ' in normalized_condition or ' or ' in normalized_condition:
        error('It is forbidden to use And/Or in a conditional clause. Please use AndAlso/OrElse instead. (Activity: %s, Condition: %s)' % (uixaml.displayname(e), condition), file)

    # Selector check
    selectors = xpath('//ui:*[@Selector and @Selector != "{x:Null}"]')

    for e in selectors:
      selector = e.get('Selector')

      if len(selector) < 1:
        continue

      if selector[:1] == '<':
        # Selector is written in pure selector expression (if this string starts with '[', it is written in VB expression)
        selxml = etree.fromstring('<selector xmlns:omit="omit">%s</selector>' % selector)
        etree.strip_attributes(selxml, '{omit}*') # Delete attribute with "omit" namespaces
        normalized_selector = etree.tostring(selxml, encoding='unicode')
      else:
        normalized_selector = selector

      # Tip: Forbid user id like string, test environment identifier, test user id, etc...
      if re.search(r'''title=('[^']+|"[^"]+)\.([0-9a-zA-Z]{3,4}\b|\*)''', normalized_selector):
        error('A selector contains an extension-like string. Please replace it by * so that it works in the environment which hides extensions. (Activity: %s, Selector: %s)' % (uixaml.displayname(e), selector), file)
      if re.search(r'''cls=['"]windowsforms10\.''', normalized_selector, re.IGNORECASE):
        error('Window classes starting with "WindowsForms10" should not be used as a selector because they may change due to application version change. (Activity: %s, Selector: %s）' % (uixaml.displayname(e), selector), file)

  # Remove unused screenshots
  if arg.remove_screenshots is not None:
    ss_diff = ss_file - ss_xaml

    if len(ss_diff) > 0:
      warn('Unused screenshot file(s) will be removed.')

      for ss in ss_diff:
        ss_path = '%s/%s.png' % (ss_dir, ss)
        print('Remove screenshot: %s' % ss_path)

        if   arg.remove_screenshots == 'file':
          os.remove(ss_path)
        elif arg.remove_screenshots == 'vsts':
          subprocess.run('tf delete -jwt:"$SYSTEM_ACCESSTOKEN" "%s"' % ss_path, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

      if arg.remove_screenshots == 'vsts':
        subprocess.run('tf checkin -jwt:"$SYSTEM_ACCESSTOKEN" -comment:"Remove screeen shot(s)" -noprompt', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

  # Finish!
  if iserror:
    if arg.vsts:
      print('##vso[task.complete result=Failed;]')
    else:
      sys.exit(1)
  else:
    if arg.vsts:
      print('##vso[task.complete result=Succeeded;]')

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='UiLint - A static code analyzer for UiPath XAML files.')
  parser.add_argument('dir', help='Specify a directory of UiPath project. (default: current directory)', nargs='?', default='.')
  parser.add_argument('--vsts', help='Output in VSTS log format.', action='store_true') # ref. VSTS Log syntax: https://github.com/Microsoft/vsts-tasks/blob/master/docs/authoring/commands.md
  parser.add_argument('--nologo', help='Do NOT display a logo.', action='store_false', dest='logo')
  parser.add_argument('--remove-screenshots', help='Remove unused screenshots from Version control system.', choices=['dryrun', 'file', 'vsts'])
  arg = parser.parse_args()

  if not os.path.isdir(arg.dir):
    print('"%s" is not a directory or does not exist.' % arg.dir)
    sys.exit(1)
  else:
    arg.dir = os.path.normpath(arg.dir)

  if arg.logo:
    print('''\
    ___       ___       ___      ___       ___       ___    
   /\__\     /\  \     /\__\    /\  \     /\__\     /\  \   
  /:/ _/_   _\:\  \   /:/  /   _\:\  \   /:| _|_    \:\  \  
 /:/_/\__\ /\/::\__\ /:/__/   /\/::\__\ /::|/\__\   /::\__\ 
 \:\/:/  / \::/\/__/ \:\  \   \::/\/__/ \/|::/  /  /:/\/__/ 
  \::/  /   \:\__\    \:\__\   \:\__\     |:/  /  /:/  /    
   \/__/     \/__/     \/__/    \/__/     \/__/   \/__/     
               A static code analyzer for UiPath XAML files
''')

  lint()
