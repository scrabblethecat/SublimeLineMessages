import sublime
import sublime_plugin
import subprocess
import re
import collections

SETTINGS_FILE = 'SublimeLineMessages.sublime-settings'

LINE_MESSAGES = {}

class Message(object):
    def __init__(self, filename, tool, line, message):
        self.filename = filename
        self.tool = tool
        self.line = line
        self.message = message

    def __str__(self):
        # return '[{:^10}]{:>4}:{}'.format(self.tool, self.line, self.message)
        return '{:>4}:\t{}'.format(self.line, self.message)


class MessageContainer(object):
    """
    A container class that is responsible for the addition, subtraction and
    viewing (in the GUI) of messages.
    """

    def __init__(self, view):
        self.view = view
        self.line_messages = collections.defaultdict(list)
        self.region_key = '{}_line_message'.format(self.view.id())

    def add_message(self, message, noline=False):
        if not noline:
            self.line_messages[message.line].append(message)
        else:
            self.line_messages[0] = message

    def add_regions(self):
        regions = [
            self.view.line(self.view.text_point(line-1, 0)) for line in
                self.line_messages ]
        self.view.add_regions(self.region_key, regions, 'error', 'dot', sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)
        # self.view.add_regions(self.region_key, regions, icon='cross')

    def clear_regions(self):
        self.view.erase_regions(self.region_key)
        self.line_messages = collections.defaultdict(list)

    def line_message(self, line):
        if line in self.line_messages:
            return ' '.join(self.line_messages[line])
        return ''

    def __str__(self):
        text = ''
        for line in sorted(self.line_messages):
            for message in self.line_messages[line]:
                text += str(message) + '\n'
        return text

def parser_from_regex(tool, regex):
    """
    Forms a line parser from a regex, returns a parsing function.
    """
    _regex = re.compile(regex)
    def parser(text):
        messages = []
        for line in text.split('\n'):
            result = _regex.match(line)
            if result is not None:
                filename, lineNo, message = result.groups()
                messages.append(
                    Message(filename,
                            tool,
                            int(lineNo) if lineNo else 1,
                            message))
        return messages
    return parser


def execute(command, filename, parser):
    """
    Executes a command, on a specified filename and then parses output, returns
    a list of message objects.
    """
    try:
        cmd = '{} \"{}\"'.format(command, filename)
        output = subprocess.check_output(
                    cmd,
                    stderr=subprocess.STDOUT,
                    shell=True).decode()
    except subprocess.CalledProcessError as error:
        output = error.output.decode()
    return parser(output)


def status_toggler(line, vid):
    """Updates statue bar messages."""
    container = LINE_MESSAGES.get(vid)
    if container is None:
        return
    sublime.status_message(container.line_message(line))


def line_number(view):
    """Returns the line number from the view."""
    sel = view.sel()
    if sel and len(sel) > 0:
        firstSel = sel[0]
        return view.rowcol(firstSel.end())[0]
    else:
        return 0


def get_settings_param(view, param_name, default=None):
    """Returns parameter settings."""
    def get_plugin_settings():
        """Returns plugin settings."""
        return sublime.load_settings(SETTINGS_FILE)
    plugin_settings = get_plugin_settings()
    project_settings = view.settings()
    return project_settings.get(
        param_name,
        plugin_settings.get(param_name, default))


class LineMessagesListener(sublime_plugin.EventListener):
    """Executes the linter on specific GUI stimuli."""

    def __init__(self):
        super(LineMessagesListener).__init__()

    def on_selection_modified_async(self, view):
        status_toggler(line_number(view), view.id())

    def on_post_save(self, view):
        if view.file_name().endswith('.py'):
            view.run_command("line_messages")


class LineMessagesCommand(sublime_plugin.TextCommand):
    """Encapsulates the execution of a command line linter."""

    def run(self, edit):
        """Executes the linter in another process."""
        sublime.set_timeout_async(self.run_command, 0)

    def run_command(self):
        """Execute the command."""
        self.view.run_command('line_messages_update')


class LineMessagesUpdate(sublime_plugin.TextCommand):
    """Updates the GUI with lint notifications"""

    def run(self, edit):
        """Updates global state and region markers"""

        tools = get_settings_param(self.view, 'tools', [])
        verbose_popup = get_settings_param(self.view, 'verbose_popup', False)
        verbose_buffer = get_settings_param(self.view, 'verbose_buffer', False)
        highlight = get_settings_param(self.view, 'highlight', False)

        container = LINE_MESSAGES.setdefault(
            self.view.id(),
            MessageContainer(self.view))

        messages = []
        for tool in tools:
            messages += execute(
                "{} {}".format(tool['command'], tool['options']),
                self.view.file_name(),
                parser_from_regex(tool['name'], tool['parser']))

        messages = sorted(messages, key=lambda x: x.line)

        # Clear all existing regions.
        container.clear_regions()

        # Add messages.
        for message in messages:
            container.add_message(message, noline=message.line is None)

        # Add highlights to lines.
        if highlight:
            container.add_regions()

        active_view = self.view.window().active_view()

        views = {name: index for (index, name) in enumerate([x.name() for x in self.view.window().views()])}

        if verbose_buffer:
            self.output_view = None
            view_index = views.get('Python-Errors')
            if view_index is not None:
                self.output_view = self.view.window().views()[view_index]

            if self.output_view is None:
                self.output_view = self.view.window().new_file()
                self.output_view.set_name('Python-Errors')
                # self.output_view.set_read_only(True)
                self.output_view.set_scratch(True)

            for region in reversed(self.output_view.find_all('.*')):
                self.output_view.erase(edit, region)

            self.output_view.insert(edit, 0, self.view.file_name() + '\n' + str(container))
            lines = [self.output_view.text_point(line, 0) for line in range(len(messages))]
            regions = [sublime.Region(lineStart, lineStart + 5) for lineStart in lines]
            self.output_view.add_regions('Python-Errors_lines', regions, 'string', '', sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)

        if verbose_popup:
            self.output_view = self.view.window().create_output_panel('messages')
            self.output_view.insert(edit, 0, str(container))
            self.view.window().run_command("show_panel", {"panel": "output.messages"})


class LineClick(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if view.name() == 'Python-Errors':
            line = view.line(view.sel()[0])

            lineNo = int(view.substr(line)[:4]) - 1
            windowName = view.substr(view.line(0))
            views = {view.file_name(): view for view in self.window.views()}
            matchingView = views.get(windowName)
            print('selected:{}@{}'.format(lineNo, windowName))
            matchingView.sel().clear()
            matchingView.sel().add(matchingView.text_point(lineNo, 0))
            matchingView.show(matchingView.text_point(lineNo, 0))
            matchingView.set_status('pyerror', view.substr(line)[5:])
            view.sel().clear()
            view.add_regions('current_error', [line], 'error', 'dot', sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)

            self.window.focus_view(matchingView)
