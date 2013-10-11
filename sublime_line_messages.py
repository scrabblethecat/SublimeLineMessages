import sublime
import sublime_plugin

import subprocess
import re
import collections

SETTINGS_FILE = 'SublimeLineMessages.sublime-settings'

LINE_MESSAGES = {}
LINE_REGION_KEYS = {}

CMD = '/usr/bin/pylint --msg-template="{path}:{line}: [{msg_id}] {msg}" -r no'
RGX = '(.*):([1-9]+):\s(.*)'

Message = collections.namedtuple('Message', 'filename line message')


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
                messages.append(Message(filename, int(line), message))
        return messages
    return parser


def execute(command, filename, parser):
    """
    Executes a command, on a specified filename and then parses output, returns
    a list of message objects.
    """
    try:
        cmd = '{} {}'.format(command, re.escape(filename))
        output = subprocess.check_output(
                    cmd,
                    stderr=subprocess.STDOUT,
                    shell=True).decode()
    except subprocess.CalledProcessError as error:
        output = error.output.decode()
    return parser(output)


def status_toggler(line, vid):
    """Updates statue bar messages."""
    messages = LINE_MESSAGES.get(vid)
    if messages is None:
        return
    sublime.status_message(messages.get(line, ''))


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
        super(SublimeLineMessagesListener).__init__()

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

        messages = execute(
            CMD,
            self.view.file_name(),
            parser_from_regex(RGX))

        # Remove the existing markup.
        region_keys = LINE_REGION_KEYS.get(self.view.id(), [])
        if region_keys:
            for key in region_keys:
                self.view.erase_regions(key)

        line_messsage_data = {x.line:x.message for x in messages}

        # Mark the regions containing lint.
        if messages:
            LINE_MESSAGES[self.view.id()] = line_messsage_data
            LINE_REGION_KEYS[self.view.id()] = []

            for line in line_messsage_data.keys():

                region = self.view.line(self.view.text_point(line, 0))
                key = '{}_{}_message'.format(line, self.view.id())
                LINE_REGION_KEYS[self.view.id()].append(key)

                self.view.add_regions(key,
                    [region],
                    'error',
                    '',
                    sublime.DRAW_NO_FILL)

        # Show a status window with linter output.
        self.output_view = self.view.window().create_output_panel('messages')
        self.output_view.insert(edit, 0, ''.join(['{}: {}\n'.format(x.line, x.message) for x in messages] ))
        self.view.window().run_command("show_panel", {"panel": "output.messages"})
