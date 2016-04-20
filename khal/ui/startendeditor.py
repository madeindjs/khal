# Copyright (c) 2013-2016 Christian Geier et al.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from datetime import datetime, time

import urwid
import pytz

from .widgets import DateWidget, TimeWidget, NColumns, NPile, ValidatedEdit, EditSelect
from .calendarwidget import CalendarWidget


class DateConversionError(Exception):
    pass


class StartEnd(object):

    def __init__(self, startdate, starttime, enddate, endtime):
        """collecting some common properties"""
        self.startdate = startdate
        self.starttime = starttime
        self.enddate = enddate
        self.endtime = endtime


class CalendarPopUp(urwid.PopUpLauncher):
    def __init__(self, widget, conf, on_date_change):
        self._conf = conf
        self._on_date_change = on_date_change
        self.__super.__init__(widget)

    def keypress(self, size, key):
        if key == 'enter':
            self.open_pop_up()
        else:
            return super().keypress(size, key)

    def create_pop_up(self):
        def on_change(new_date):
            self._get_base_widget().set_value(new_date)
            self._on_date_change(new_date)

        keybindings = self._conf['keybindings']
        on_press = {'enter': lambda _, __: self.close_pop_up(),
                    'esc': lambda _, __: self.close_pop_up()}
        pop_up = CalendarWidget(
            on_change, keybindings, on_press,
            firstweekday=self._conf['locale']['firstweekday'],
            weeknumbers=self._conf['locale']['weeknumbers'],
            initial=self.base_widget._get_current_value())
        pop_up = urwid.LineBox(pop_up)
        return pop_up

    def get_pop_up_parameters(self):
        width = 31 if self._conf['locale']['weeknumbers'] == 'right' else 28
        return {'left': 0, 'top': 1, 'overlay_width': width, 'overlay_height': 8}


class StartEndEditor(urwid.WidgetWrap):
    """Wigdet for editing start and end times (of an event)"""

    def __init__(self, start, end, conf, on_date_change=lambda x: None):
        """
        :type start: datetime.datetime
        :type end: datetime.datetime
        :param on_date_change: a callable that gets called everytime a new
            date is entered, with that new date as an argument
        """
        self.allday = not isinstance(start, datetime)
        self._tz_state = False
        self.conf = conf
        self._startdt, self._original_start = start, start
        self._enddt, self._original_end = end, end
        self.on_date_change = on_date_change
        self._datewidth = len(start.strftime(self.conf['locale']['longdateformat']))
        self._timewidth = len(start.strftime(self.conf['locale']['timeformat']))
        # this will contain the widgets for [start|end] [date|time]
        self.widgets = StartEnd(None, None, None, None)

        self.checkallday = urwid.CheckBox(
            'Allday', state=self.allday, on_state_change=self.toggle_allday)
        self.rebuild()

    def keypress(self, size, key):
        return super().keypress(size, key)

    @property
    def startdt(self):
        if self.allday and isinstance(self._startdt, datetime):
            return self._startdt.date()
        else:
            return self._startdt

    @property
    def _start_time(self):
        try:
            return self._startdt.time()
        except AttributeError:
            return time(0)

    @property
    def timezone_start(self):
        if getattr(self.startdt, 'tzinfo', None) is None:
            return self.conf['locale']['default_timezone']
        else:
            return self.startdt.tzinfo

    @property
    def localize_start(self):
        return self.timezone_start.localize

    @property
    def timezone_end(self):
        if getattr(self.enddt, 'tzinfo', None) is None:
            return self.conf['locale']['default_timezone']
        else:
            return self.enddt.tzinfo

    @property
    def localize_end(self):
        return self.timezone_end.localize

    @property
    def enddt(self):
        if self.allday and isinstance(self._enddt, datetime):
            return self._enddt.date()
        else:
            return self._enddt

    @property
    def _end_time(self):
        try:
            return self._enddt.time()
        except AttributeError:
            return time(0)

    def _validate_start_time(self, text):
        try:
            startval = datetime.strptime(text, self.conf['locale']['timeformat'])
            self._startdt = self.localize_start(
                datetime.combine(self._startdt.date(), startval.time()))
        except ValueError:
            return False
        else:
            return startval

    def _validate_start_date(self, text):
        try:
            startval = datetime.strptime(text, self.conf['locale']['longdateformat'])
            self._startdt = self.localize_start(
                datetime.combine(startval.date(), self._start_time))
        except ValueError:
            return False
        else:
            return startval

    def _validate_end_time(self, text):
        try:
            endval = datetime.strptime(text, self.conf['locale']['timeformat'])
            self._enddt = self.localize_end(datetime.combine(self._enddt.date(), endval.time()))
        except ValueError:
            return False
        else:
            return endval

    def _validate_end_date(self, text):
        try:
            endval = datetime.strptime(text, self.conf['locale']['longdateformat'])
            self._enddt = self.localize_end(datetime.combine(endval.date(), self._end_time))
        except ValueError:
            return False
        else:
            return endval

    def toggle_allday(self, checkbox, state):
        """change from allday to datetime event

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: allday-eventness of this event;
                      True if allday event, False if datetime
        :type state: bool
        """

        if self.allday is True and state is False:
            self._startdt = datetime.combine(self._startdt, datetime.min.time())
            self._enddt = datetime.combine(self._enddt, datetime.min.time())
        elif self.allday is False and state is True:
            self._startdt = self._startdt.date()
            self._enddt = self._enddt.date()
        self.allday = state
        self.rebuild()

    def toggle_tz(self, checkbox, state):
        """change from displaying the timezone chooser or not

        :param checkbox: the checkbox instance that is used for toggling, gets
                         automatically passed by urwid (is not used)
        :type checkbox: checkbox
        :param state: show timezone chooser or not
        :type state: bool

        """
        if self._tz_state is False and state is True:
            self._startdt = self._startdt.astimezone(self._get_chosen_timezone())
            self._enddt = self._enddt.astimezone(self._get_chosen_timezone())
        elif self._tz_state is True and state is False:
            self._startdt = self._startdt.astimezone(self.conf['locale']['default_timezone'])
            self._enddt = self._enddt.astimezone(self.conf['locale']['default_timezone'])
        self._tz_state = state
        self.rebuild()
        self._start_edit.set_focus(3)

    def rebuild(self):
        """rebuild the start/end/timezone editor"""
        datewidth = self._datewidth + 7
        # startdate
        edit = ValidatedEdit(
            dateformat=self.conf['locale']['longdateformat'],
            EditWidget=DateWidget,
            validate=self._validate_start_date,
            caption=('', 'From: '),
            edit_text=self.startdt.strftime(self.conf['locale']['longdateformat']),
            on_date_change=self.on_date_change)
        edit = CalendarPopUp(edit, self.conf, self.on_date_change)
        edit = urwid.Padding(edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.startdate = edit

        # enddate
        edit = ValidatedEdit(
            dateformat=self.conf['locale']['longdateformat'],
            EditWidget=DateWidget,
            validate=self._validate_end_date,
            caption=('', 'To:   '),
            edit_text=self.enddt.strftime(self.conf['locale']['longdateformat']),
            on_date_change=self.on_date_change)
        edit = CalendarPopUp(edit, self.conf, self.on_date_change)
        edit = urwid.Padding(edit, align='left', width=datewidth, left=0, right=1)
        self.widgets.enddate = edit

        if self.allday is True:
            timewidth = 1
            self.widgets.starttime = urwid.Text('')
            self.widgets.endtime = urwid.Text('')
        elif self.allday is False:
            timewidth = self._timewidth + 1
            edit = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_start_time,
                edit_text=self.startdt.strftime(self.conf['locale']['timeformat']),
            )
            edit = urwid.Padding(
                edit, align='left', width=self._timewidth + 1, left=1)
            self.widgets.starttime = edit

            edit = ValidatedEdit(
                dateformat=self.conf['locale']['timeformat'],
                EditWidget=TimeWidget,
                validate=self._validate_end_time,
                edit_text=self.enddt.strftime(self.conf['locale']['timeformat']),
            )
            edit = urwid.Padding(
                edit, align='left', width=self._timewidth + 1, left=1)
            self.widgets.endtime = edit

        if self._tz_state:
            self._tz_widget = EditSelect(
                pytz.common_timezones, str(self.timezone_start), win_len=10)
        else:
            self._tz_widget = urwid.Text('')

        self._start_edit = NColumns(
            [
                (datewidth, self.widgets.startdate),
                (timewidth, self.widgets.starttime),
                (2, urwid.Text('\N{EARTH GLOBE EUROPE-AFRICA}')),
                (4, urwid.CheckBox('', state=self._tz_state, on_state_change=self.toggle_tz)),
                self._tz_widget,
            ],
            dividechars=1
        )
        self._end_edit = NColumns(
            [(datewidth, self.widgets.enddate), (timewidth, self.widgets.endtime)],
            dividechars=1)
        columns = NPile(
            [self.checkallday, self._start_edit, self._end_edit],
            focus_item=1)
        urwid.WidgetWrap.__init__(self, columns)

    def _get_chosen_timezone(self):
        import ipdb; ipdb.set_trace()


    @property
    def changed(self):
        """returns True if content has been edited, False otherwise"""
        return (self.startdt != self._original_start) or (self.enddt != self._original_end)

    def validate(self):
        """make sure startdt <= enddt"""
        return self.startdt <= self.enddt
