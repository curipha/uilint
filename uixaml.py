# XML namespaces
xamlns = {
  'xaml': 'http://schemas.microsoft.com/netfx/2009/xaml/activities',  # Default namespace
  'sap2010': 'http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation',
  'ui': 'http://schemas.uipath.com/workflow/activities',
  'x': 'http://schemas.microsoft.com/winfx/2006/xaml',
}

# Set of Workbook activities (as of 18.4.3)
wbactivities = {
  'ui:AppendRange', 'ui:GetTableRange', 'ui:ReadCell', 'ui:ReadCellFormula', 'ui:ReadColumn',
  'ui:ReadRange', 'ui:ReadRow', 'ui:WriteCell', 'ui:WriteRange',
}

# Set of Open/Attach Scopes (as of 18.4.3)
wndscopes = {
  'ui:ElementScope', 'ui:WindowScope', 'ui:BrowserScope', 'ui:OpenApplication', 'ui:OpenBrowser',
}

# Set of Special keys (as of 18.4.3)
specialkey = {
  'add', 'alt', 'lalt', 'ralt', 'back', 'break', 'caps', 'ctrl', 'lctrl', 'rctrl', 'decimal',
  'del', 'div', 'down', 'end', 'enter', 'numEnter', 'esc', 'f1', 'f2', 'f3', 'f4', 'f5', 'f6',
  'f7', 'f8', 'f9', 'f10', 'f11', 'f12', 'home', 'ins', 'left', 'mul', 'num', 'num0', 'num1',
  'num2', 'num3', 'num4', 'num5', 'num6', 'num7', 'num8', 'num9', 'pause', 'pgup', 'pgdn', 'right',
  'scroll', 'shift', 'lshift', 'rshift', 'sleep', 'sub', 'tab', 'up',
}


# Get DisplayName of Activity
def displayname(element) -> str:
  if tag(element) == 'Target':
    element = element.xpath('../..')[0]

  dispname = element.get('DisplayName')
  return dispname if dispname else tag(element)


# Get tag name without namespaces (local name)
def tag(element) -> str:
  tagname = element.tag
  nspos = tagname.find('}')
  return tagname[nspos + 1:] if nspos >= 0 else tagname
