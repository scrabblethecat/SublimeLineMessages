import sublime
import sublime_plugin
import subprocess
import re
import collections

class NextErrorCommand(sublime_plugin.TextCommand):
    """Cycles through the next or prev error."""

    def run(self, edit, next):
        """Cycles."""

        views = {view.name(): view for view in self.view.window().views()}
        view = views.get('Python-Errors')
        views = {view.file_name(): view for view in self.view.window().views()}
        if view:
            windowName = view.substr(view.line(0))
            matchingView = views.get(windowName)
        if view and matchingView:
            inc = 1 if next else -1
            currentRegions = view.get_regions('current_error')
            if currentRegions:
                row, col = view.rowcol(currentRegions[0].a)
                line = view.line(view.text_point(row + inc, 0))
                if not view.substr(view.line(line)):
                    matchingView.set_status('pyerror', 'no more errors')
                    return
            elif next:
                line = view.line(view.text_point(1, 0))
            else:
                return

            lineNo = int(view.substr(line)[:4]) - 1
            # print('selected:{}@{}'.format(lineNo, windowName))
            matchingView.sel().clear()
            matchingView.sel().add(matchingView.text_point(lineNo, 0))
            matchingView.show(matchingView.text_point(lineNo, 0))
            matchingView.set_status('pyerror', view.substr(line)[5:])
            view.sel().clear()
            view.add_regions('current_error', [line], 'error', 'dot', sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)

            self.view.window().focus_view(matchingView)