#!/usr/bin/env python3
import os
import re
import sys
import argparse
import enum
import gettext
import subprocess
from collections import namedtuple
from functools import reduce
from glob import glob  # Python >= 3.5
from lxml import etree

import uixaml

# Tuple for result records (Result for the project, ResultXAML for each XAMLs)
Result = namedtuple('Result', ('file', 'category', 'message'))
ResultXAML = namedtuple('ResultXAML', ('category', 'message'))


# Enum for message category of results
class MessageCategory(enum.Enum):
  ERROR = enum.auto()
  WARNING = enum.auto()


# Linter class for the project
class Project:
  def __init__(self, projectdir: str) -> None:
    # Errors/Warnings (should be accessed via self.results() method)
    self._results = []

    # Path to project directory
    if not os.path.isdir(projectdir):
      raise ValueError('Given project directory is not found or not a directory.')

    self.projectdir = projectdir

    # Path to the directory of screenshots
    self.ssdir = os.path.join(self.projectdir, '.screenshots')

    # Path to project.json
    self.prjfile = os.path.join(self.projectdir, 'project.json')

    # Get all XAML files including sub-directories
    self.xamlfiles = glob(os.path.join(projectdir, '**', '*.xaml'), recursive=True)

    # List of XAML classes for each XAML file
    self.xamls = []

    # Set of screenshots in the project (hash only, without extensions)
    self.ss_inuse = set()  # Seen in all XAML files
    self.ss_stored = set()  # Stored in the project's screenshot directory

  # Get all stored screenshot files (i.e. return self.ss_stored)
  def stored_screenshots(self) -> set:
    if not any(self.ss_stored):
      if os.path.isdir(self.ssdir):
        self.ss_stored = set(map(lambda f: os.path.splitext(f)[0], os.listdir(self.ssdir)))

    return self.ss_stored

  # Get all in-use screenshots (i.e. return self.ss_inuse)
  def inuse_screenshots(self) -> set:
    if not any(self.ss_inuse):
      self.ss_inuse = reduce(
        lambda s1, s2: s1 | s2,
        list(map(lambda xaml: xaml.inuse_screenshots(), self.xamls)),
        set()
      )

    return self.ss_inuse

  # Convert screenshot hash to actual file path
  def screenshot_path(self, hash: str) -> str:
    return os.path.join(self.ssdir, '%s.png' % hash)

  # Get lint results including results of XAML files
  def results(self) -> list:
    return reduce(
      lambda l1, l2: l1 + l2,
      list(map(lambda xaml: xaml.results(), self.xamls)),
      self._results
    )

  # Linter
  def lint(self) -> None:
    # Check existence of project.json file
    if not os.path.isfile(self.prjfile):
      self._results.append(Result(self.prjfile, MessageCategory.ERROR, _('rule:no-project-file')))

    # Check all XAML files
    xamls = list(map(lambda xamlpath: XAML(self, xamlpath), self.xamlfiles))

    for xaml in xamls:
      xaml.lint()

    self.xamls = xamls


# Linter class for each XAML files
class XAML:
  def __init__(self, project: Project, xamlpath: str):
    # Reference to the project
    self.project = project

    # Errors/Warnings (can access directly if you want a list of ResultXAML)
    self._results = []

    # Screenshots seen in XAML files (hash only, without extensions)
    self.screenshots = set()

    # Path to XAML file
    if not os.path.isfile(xamlpath):
      raise ValueError('Given XAML file path is not found or not a file.')

    self.xamlpath = xamlpath

    # XPath Evaluator
    xaml = etree.parse(self.xamlpath)
    self.xpath = etree.XPathEvaluator(xaml, namespaces=uixaml.xamlns)

  # Get all in-use screenshots (i.e. return self.screenshots)
  def inuse_screenshots(self) -> set:
    if not any(self.screenshots):
      ss = set()
      ss_elem = self.xpath('//ui:*[@InformativeScreenshot]')

      for e in ss_elem:
        ssfile = e.get('InformativeScreenshot')
        ss.add(ssfile)

      self.screenshots = ss

    return self.screenshots

  # Get lint results by a list of Result (not a list of ResultXAML)
  def results(self) -> list:
    return list(map(lambda r: Result(self.xamlpath, r.category, r.message), self._results))

  def lint(self):
    # Check existence of all screenshots
    ss_elems = self.xpath('//ui:*[@InformativeScreenshot]')
    ss_files = self.project.stored_screenshots()

    for e in ss_elems:
      sfile = e.get('InformativeScreenshot')

      if sfile not in ss_files:
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (Activity: %s, Screenshot: %s)' % (
            _('rule:no-screenshots'),
            uixaml.displayname(e),
            sfile
          )
        ))

    #  GetPassword activity should not be used
    getpass = self.xpath('//ui:GetPassword')

    for e in getpass:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (GetPassword: %s)' % (_('rule:no-getpassword'), uixaml.displayname(e))
      ))

    # MessageBox not in a comment
    msgbox = self.xpath('//ui:MessageBox[not(ancestor::ui:CommentOut)]')

    for e in msgbox:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (MessageBox: %s, Message: %s)' % (
          _('rule:messagebox'),
          uixaml.displayname(e),
          e.get('Text')
        )
      ))

    # TerminateWorkflow not in a comment
    terminate = self.xpath('//xaml:TerminateWorkflow[not(ancestor::ui:CommentOut)]')

    for e in terminate:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (TerminateWorkflow: %s, Exception: %s, Reason: %s)' % (
          _('rule:terminateworkflow'),
          uixaml.displayname(e),
          e.get('Exception'),
          e.get('Reason')
        )
      ))

    # Looped activity in a Flowchart
    flow = self.xpath('//xaml:FlowStep[@x:Name = ./xaml:FlowStep.Next/x:Reference/text()]')

    for e in flow:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (Activity: %s)' % (
          _('rule:looped-activity'),
          uixaml.displayname(
            e.xpath(
              './*[not(xaml:FlowStep.Next) and not(sap2010:*)]',
              namespaces=uixaml.xamlns
            )[0]
          )
        )
      ))

    # Empty Sequence
    seq = self.xpath('//xaml:Sequence[not(*) or (count(*) = 1 and ./xaml:Sequence.Variables)]')

    for e in seq:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (Sequence: %s)' % (_('rule:empty-sequence'), uixaml.displayname(e))
      ))

    # Nested Sequence
    seq = self.xpath(r'''
//xaml:Sequence[
  not(ancestor::ui:CommentOut) and
  (
    (count(*) = 1 and ./xaml:Sequence) or
    (count(*) = 2 and ./xaml:Sequence and ./xaml:Sequence.Variables)
  )
]''')

    for e in seq:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (Sequence: %s -> %s))' % (
          _('rule:nested-sequence'),
          uixaml.displayname(e),
          uixaml.displayname(e.xpath('./xaml:Sequence', namespaces=uixaml.xamlns)[0])
        )
      ))

    # Sequence contains many of activities
    seq = self.xpath(r'''
//xaml:Sequence[
  not(ancestor::ui:CommentOut) and
  count(*[not(self::xaml:Sequence.Variables) and not(self::xaml:Sequence)]) > 15
]''')

    for e in seq:
      self._results.append(ResultXAML(
        MessageCategory.WARNING,
        '%s (Sequence: %s)' % (_('rule:max-activities'), uixaml.displayname(e))
      ))

    # TryCatch with empty catch
    trycatch = self.xpath(r'''
//xaml:TryCatch[
  not(./xaml:TryCatch.Catches) or
  ./xaml:TryCatch.Catches/xaml:Catch[count(./xaml:ActivityAction/*) < 2]
]''')

    for e in trycatch:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (TryCatch: %s)' % (_('rule:empty-catch'), uixaml.displayname(e))
      ))

    # Nested If more than 3 times
    seq = self.xpath('//xaml:If[not(ancestor::ui:CommentOut)]//xaml:If//xaml:If')

    for e in seq:
      self._results.append(ResultXAML(
        MessageCategory.WARNING,
        '%s (If: %s, Condition: %s)' % (
          _('rule:nested-if'),
          uixaml.displayname(e),
          e.get('Condition')
        )
      ))

    # Excel Application Scope with Visible enabled
    eas = self.xpath('//ui:ExcelApplicationScope[not(@Visible) or @Visible != "False"]')

    for e in eas:
      self._results.append(ResultXAML(
        MessageCategory.WARNING,
        '%s (Excel Application Scope: %s, File: %s)' % (
          _('rule:no-visible-excel'),
          uixaml.displayname(e),
          e.get('WorkbookPath')
        )
      ))

    # Workbook activities in an Excel Application Scope
    eas = self.xpath('|'.join(map(
      lambda e: '//ui:ExcelApplicationScope//%s' % e, uixaml.wbactivities
    )))

    for e in eas:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (Excel Application Scope: %s, Activity: %s))' % (
          _('rule:workbook-in-excel'),
          uixaml.displayname(
            e.xpath(
              'ancestor::ui:ExcelApplicationScope[1]',
              namespaces=uixaml.xamlns
            )[0]
          ),
          uixaml.displayname(e)
        )
      ))

    # Launch via OpenApplication/StartProcess instead of Application Scope/Browser Scope
    openapp = self.xpath('//ui:OpenApplication[@FileName]|//ui:StartProcess[@FileName]')

    for e in openapp:
      filepath = e.get('FileName').lower()

      if 'excel.exe' in filepath:
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (Activity: %s)' % (_('rule:run-excel'), uixaml.displayname(e))
        ))
      if 'winword.exe' in filepath:
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (Activity: %s)' % (_('rule:run-word'), uixaml.displayname(e))
        ))
      if 'iexplore.exe' in filepath or 'firefox.exe' in filepath or 'chrome.exe' in filepath:
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (Activity: %s)' % (_('rule:run-browser'), uixaml.displayname(e))
        ))

    # SendHotkey with SpecialKey = False
    sendkey = self.xpath('//ui:SendHotkey[@SpecialKey = "False" and @Key != "{x:Null}"]')

    for e in sendkey:
      key = e.get('Key').strip()
      if len(key) > 1 and key.lower() in uixaml.specialkey:
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (SendHotkey: %s, Key: %s)' % (_('rule:false-specialkey'), uixaml.displayname(e), key)
        ))

    # SendHotkey with empty Key
    sendkey = self.xpath('//ui:SendHotkey[not(@Key) or @Key = "{x:Null}"]')

    for e in sendkey:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (SendHotkey: %s)' % (_('rule:empty-specialkey'), uixaml.displayname(e))
      ))

    # SendHotkey for Alt-F4
    sendkey = self.xpath(r'''
//ui:SendHotkey[
  @KeyModifiers="Alt" and @Key="f4" and @SpecialKey="True"
]''')

    for e in sendkey:
      self._results.append(ResultXAML(
        MessageCategory.ERROR,
        '%s (SendHotkey: %s)' % (_('rule:no-altf4'), uixaml.displayname(e))
      ))

    # SendHotkey with empty selector
    sendkey = self.xpath(r'''
//ui:SendHotkey[%s]/ui:SendHotkey.Target/ui:Target[not(@Selector) or @Selector = "{x:Null}"]
''' % ' and '.join(map(lambda e: 'not(ancestor::%s)' % e, uixaml.wndscopes)))

    for e in sendkey:
      self._results.append(ResultXAML(
        MessageCategory.WARNING,
        '%s (SendHotkey: %s)' % (_('rule:empty-selector-sendhotkey'), uixaml.displayname(e))
      ))

    # TypeInto activity which possibly inputs a half-width kana
    typeinto = self.xpath(r'''
//ui:TypeInto[
  @Text and (not(@SimulateType) or @SimulateType = "False")
]''')

    for e in typeinto:
      text = e.get('Text')

      if len(text) < 1:
        continue

      if text[:1] == '[':
        # Text is written in VB expression
        self._results.append(ResultXAML(
          MessageCategory.WARNING,
          '%s (TypeInto: %s, Text: %s)' % (_('rule:kana-typeinto-vb'), uixaml.displayname(e), text)
        ))
      elif re.search(r'[\uff65-\uff9f]', text):
        # Text contains Half-width Kana
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (TypeInto: %s, Text: %s)' % (_('rule:kana-typeinto'), uixaml.displayname(e), text)
        ))

    # And/Or in conditional clause
    andor = self.xpath('//xaml:*[@Condition]')

    for e in andor:
      condition = e.get('Condition').lower()
      normalized_condition = re.sub(r'".*?"', '', condition)  # XXX: Remove texts surrounded by ""

      if ' and ' in normalized_condition or ' or ' in normalized_condition:
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (Activity: %s, Condition: %s)' % (
            _('rule:no-and-or'),
            uixaml.displayname(e),
            condition
          )
        ))

    # Selector check
    selectors = self.xpath('//ui:*[@Selector and @Selector != "{x:Null}"]')

    for e in selectors:
      selector = e.get('Selector')

      if len(selector) < 1:
        continue

      if selector[:1] == '<':
        # Selector is written in pure selector expression
        # (if it starts with '[', it is written in VB expression)
        selxml = etree.fromstring('<selector xmlns:omit="omit">%s</selector>' % selector)
        etree.strip_attributes(selxml, '{omit}*')  # Delete attribute with "omit" namespaces
        normalized_selector = etree.tostring(selxml, encoding='unicode')
      else:
        normalized_selector = selector

      # Tip: Other rules can be implemented here.
      # e.g. Forbid user id like string, test environment identifier, test user id, etc...

      # Selector incl. extensions
      if re.search(r'''title=('[^']+|"[^"]+)\.([0-9a-zA-Z]{3,4}\b|\*)''', normalized_selector):
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (Activity: %s, Selector: %s)' % (
            _('rule:selector-extensions'),
            uixaml.displayname(e),
            selector
          )
        ))
      if re.search(r'''cls=['"]windowsforms10\.''', normalized_selector, re.IGNORECASE):
        self._results.append(ResultXAML(
          MessageCategory.ERROR,
          '%s (Activity: %s, Selector: %s)' % (
            _('rule:selector-windowsforms'),
            uixaml.displayname(e),
            selector
          )
        ))


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='UiLint - A static code analyzer for UiPath XAML files.'
  )
  parser.add_argument(
    'dir',
    help='Specify a directory of UiPath project. (default: current directory)',
    nargs='?',
    default='.'
  )
  parser.add_argument(
    '--lang',
    help='Select language to show messages. (default: en)',
    choices=['ja', 'en'],
    default='en'
  )
  parser.add_argument(
    '--vsts',
    help='Output in VSTS (Azure DevOps) log format. Suiable for running in CI/CD pipeline.',
    # VSTS syntax: https://github.com/Microsoft/vsts-tasks/blob/master/docs/authoring/commands.md
    action='store_true'
  )
  parser.add_argument(
    '--nologo',
    help='Do NOT display a logo.',
    action='store_false',
    dest='logo'
  )
  parser.add_argument(
    '--remove-screenshots',
    help='Remove unused screenshots from Version control system. (default: none)',
    choices=['dryrun', 'file', 'vsts']
  )
  arg = parser.parse_args()

  _ = gettext.translation(
    'messages',
    localedir=os.path.join(os.path.dirname(__file__), 'locale'),
    languages=[arg.lang, 'en']
  ).gettext

  try:
    if not os.path.isdir(arg.dir):
      print(_('msg:directory-not-found'))
      sys.exit(1)
    else:
      arg.dir = os.path.normpath(arg.dir)

    if arg.logo:
      print(r'''
   ___       ___       ___      ___       ___       ___
  /\__\     /\  \     /\__\    /\  \     /\__\     /\  \
 /:/ _/_   _\:\  \   /:/  /   _\:\  \   /:| _|_    \:\  \
/:/_/\__\ /\/::\__\ /:/__/   /\/::\__\ /::|/\__\   /::\__\
\:\/:/  / \::/\/__/ \:\  \   \::/\/__/ \/|::/  /  /:/\/__/
 \::/  /   \:\__\    \:\__\   \:\__\     |:/  /  /:/  /
  \/__/     \/__/     \/__/    \/__/     \/__/   \/__/
              A static code analyzer for UiPath XAML files
'''.lstrip('\r\n'))

    # Initialize project linter
    prj = Project(arg.dir)

    # Check XAML files are exist
    if not any(prj.xamlfiles):
      print(_('msg:no-xamls'))
      sys.exit(1)

    # Do lint
    prj.lint()

    # Show results
    iserror = False
    for result in prj.results():
      if result.category == MessageCategory.ERROR:
        iserror = True

        if arg.vsts:
          print('##vso[task.logissue type=error;sourcepath=%s;]%s'
                % (result.file, result.message))
        else:
          print('%s: [Error] %s' % (result.file, result.message))
      elif result.category == MessageCategory.WARNING:
        if arg.vsts:
          print('##vso[task.logissue type=warning;sourcepath=%s;]%s'
                % (result.file, result.message))
        else:
          print('%s: [Warning] %s' % (result.file, result.message))
      else:
        raise Exception('Result category is not implemented.')

    # Remove unused screenshots
    if arg.remove_screenshots is not None:
      ss_diff = prj.stored_screenshots() - prj.inuse_screenshots()

      if any(ss_diff):
        print(_('msg:remove-screenshots'))

        for ss in ss_diff:
          ss_path = prj.screenshot_path(ss)
          print('%s: %s' % (_('msg:remove-screenshot'), ss_path))

          if arg.remove_screenshots == 'file':
            os.remove(ss_path)
          elif arg.remove_screenshots == 'vsts':
            subprocess.run(
              'tf delete -jwt:"$SYSTEM_ACCESSTOKEN" "%s"' % ss_path,
              shell=True,
              stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL
            )

        if arg.remove_screenshots == 'vsts':
          subprocess.run(
            'tf checkin -jwt:"$SYSTEM_ACCESSTOKEN" -comment:"Remove screeen shot(s)" -noprompt',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
          )

    # Finalize
    if iserror:
      if arg.vsts:
        print('##vso[task.complete result=Failed;]')
      else:
        sys.exit(1)
    else:
      if arg.vsts:
        print('##vso[task.complete result=Succeeded;]')

    sys.stdout.flush()

  except BrokenPipeError:
    # https://docs.python.org/ja/3/library/signal.html#note-on-sigpipe
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())
    sys.exit(1)
