# Copyright 2015 Canonical, Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Re-usable input widgets
"""

from urwid import (
    ACTIVATE,
    AttrWrap,
    connect_signal,
    Edit,
    Filler,
    IntEdit,
    LineBox,
    PopUpLauncher,
    SelectableIcon,
    Text,
    TOP,
    WidgetWrap,
    )
import logging
import re

from subiquitycore.ui.container import Pile

log = logging.getLogger("subiquitycore.ui.input")


class StringEditor(WidgetWrap):
    """ Edit input class

    Initializes and Edit object and attachs its result
    to the `value` accessor.
    """
    def __init__(self, caption, **kwargs):
        self._edit = Edit(caption=caption, **kwargs)
        self.error = None
        super().__init__(self._edit)

    def keypress(self, size, key):
        if self.error:
            self._edit.set_edit_text("")
            self.error = None
        return super().keypress(size, key)

    def set_error(self, msg):
        self.error = msg
        return self._edit.set_edit_text(msg)

    @property
    def value(self):
        return self._edit.get_edit_text()

    @value.setter  # NOQA
    def value(self, value):
        self._edit.set_edit_text(value)


class PasswordEditor(StringEditor):
    """ Password input prompt with masking
    """
    def __init__(self, caption, mask="*"):
        super().__init__(caption, mask=mask)


class RealnameEditor(StringEditor):
    """ Username input prompt with input rules
    """

    def keypress(self, size, key):
        ''' restrict what chars we allow for username '''

        realname = r'[a-zA-Z0-9_\- ]'
        if re.match(realname, key) is None:
            return False

        return super().keypress(size, key)


class EmailEditor(StringEditor):
    """ Email input prompt with input rules
    """

    def keypress(self, size, key):
        ''' restrict what chars we allow for username '''

        realname = r'[-a-zA-Z0-9_.@+=]'
        if re.match(realname, key) is None:
            return False

        return super().keypress(size, key)


class UsernameEditor(StringEditor):
    """ Username input prompt with input rules
    """

    def keypress(self, size, key):
        ''' restrict what chars we allow for username '''

        userlen = len(self.value)
        if userlen == 0:
            username = r'[a-z_]'
        else:
            username = r'[a-z0-9_-]'

        # don't allow non username chars
        if re.match(username, key) is None:
            return False

        return super().keypress(size, key)


class IntegerEditor(WidgetWrap):
    """ IntEdit input class
    """
    def __init__(self, caption, default=0):
        self._edit = IntEdit(caption=caption, default=default)
        super().__init__(self._edit)

    @property
    def value(self):
        return self._edit.get_edit_text()


class _PopUpButton(SelectableIcon):
    """It looks a bit like a radio button, but it just emits 'click' on activation."""

    signals = ['click']

    states = {
        True: "(+) ",
        False: "( ) ",
        }

    def __init__(self, option, state):
        p = self.states[state]
        super().__init__(p + option, len(p))

    def keypress(self, size, key):
        if self._command_map[key] != ACTIVATE:
            return key
        self._emit('click')


class _PopUpSelectDialog(WidgetWrap):
    """A list of PopUpButtons with a box around them."""

    def __init__(self, parent, cur_index):
        self.parent = parent
        group = []
        for i, option in enumerate(self.parent._options):
            if option[1]:
                btn = _PopUpButton(option[0], state=i==cur_index)
                connect_signal(btn, 'click', self.click, i)
                group.append(AttrWrap(btn, 'menu_button', 'menu_button focus'))
            else:
                btn = Text("    " + option[0])
                group.append(AttrWrap(btn, 'info_minor'))
        pile = Pile(group)
        pile.set_focus(group[cur_index])
        fill = Filler(pile, valign=TOP)
        super().__init__(LineBox(fill))

    def click(self, btn, index):
        self.parent.index = index
        self.parent.close_pop_up()

    def keypress(self, size, key):
        if key == 'esc':
            self.parent.close_pop_up()
        else:
            return super().keypress(size, key)

class SelectorError(Exception):
    pass

class Selector(PopUpLauncher):
    """A widget that allows the user to chose between options by popping up this list of options.

    (A bit like <select> in an HTML form).
    """

    _prefix = "(+) "

    signals = ['select']

    def __init__(self, opts, index=0):
        self._options = []
        for opt in opts:
            if not isinstance(opt, tuple):
                if not isinstance(opt, str):
                    raise SelectorError("invalid option %r", opt)
                opt = (opt, True, opt)
            elif len(opt) == 1:
                opt = (opt[0], True, opt[0])
            elif len(opt) == 2:
                opt = (opt[0], opt[1], opt[0])
            elif len(opt) != 3:
                raise SelectorError("invalid option %r", opt)
            self._options.append(opt)
        self._button = SelectableIcon(self._prefix, len(self._prefix))
        self._set_index(index)
        super().__init__(self._button)

    def keypress(self, size, key):
        if self._command_map[key] != ACTIVATE:
            return key
        self.open_pop_up()

    def _set_index(self, val):
        self._button.set_text(self._prefix + self._options[val][0])
        self._index = val

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, val):
        self._emit('select', self._options[val][2])
        self._set_index(val)

    @property
    def value(self):
        return self._options[self._index][2]

    def create_pop_up(self):
        return _PopUpSelectDialog(self, self.index)

    def get_pop_up_parameters(self):
        width = max([len(o[0]) for o in self._options]) \
          + len(self._prefix) +  3 # line on left, space, line on right
        return {'left':-1, 'top':-self.index-1, 'overlay_width':width, 'overlay_height':len(self._options) + 2}


class YesNo(Selector):
    """ Yes/No selector
    """
    def __init__(self):
        opts = ['Yes', 'No']
        super().__init__(opts)
