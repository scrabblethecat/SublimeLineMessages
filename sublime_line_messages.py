import sublime
import sublime_plugin
import subprocess
import re
import collections


SETTINGS_FILE = 'SublimeLineMessages.sublime-settings'
LINE_MESSAGES = {}

Message = collections.namedtuple('Message', 'filename line message')


class MessageContainer(object):
    """
    A container class that is responsible for the addition, subtraction and
    viewing (in the GUI) of messages.
    """

    def __init__(self, view):
        self.view = view
        self.line_messages = collections.defaultdict(list)
        self.region_key = '{}_line_message'.format(self.view.id())

    def add_message(self, message):
        self.line_messages[message.line].append(message.message)

    def add_regions(self):

        regions = [
            self.view.line(self.view.text_point(line-1, 0)) for line in
                self.line_messages ]

        self.view.add_regions(self.region_key, regions, 'error', '', sublime.DRAW_NO_FILL)

    def clear_regions(self):
        self.view.erase_regions(self.region_key)

    def line_message(self, line):
        if line in self.line_messages:
            return ' '.join(self.line_messages[line])
        return ''


def parser_from_regex(regex):
    """
    Forms a line parser from a regex, returns a parsing function.
    """
    _regex = re.compile(regex)
    def parser(text):
        messages = []
        for line in text.split('\n'):
            result = _regex.match(line)
            if result is not None:
                filename, line, message = result.groups()
                print(filename, line, message)
                if not line: line=1
                messages.append(Message(filename, int(line), message))
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
    return view.rowcol(view.sel()[0].end())[0]


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
        verbose = get_settings_param(self.view, 'verbose', True)

        container = LINE_MESSAGES.setdefault(
            self.view.id(),
            MessageContainer(self.view))

        messages = []
        for tool in tools:
            messages += execute(
                "{} {}".format(tool['command'], tool['options']),
                self.view.file_name(),
                parser_from_regex(tool['parser']))

        messages = sorted(messages, key=lambda x: x.line)

        # clear existing regions.
        container.clear_regions()

        for message in messages:
            container.add_message(message)

        container.add_regions()

        # Show a status window with linter output.
        self.output_view = self.view.window().create_output_panel('messages')
        self.output_view.insert(edit, 0, ''.join(['{}: {}\n'.format(x.line, x.message) for x in messages] ))
        self.view.window().run_command("show_panel", {"panel": "output.messages"})
