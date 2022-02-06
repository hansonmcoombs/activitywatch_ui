"""
created matt_dumont 
on: 6/02/22
"""
import datetime

import pandas as pd
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import numpy as np
from matplotlib.cm import get_cmap
from api_support.get_data import get_afk_data, get_window_watcher_data, get_manual, get_labels_from_unix, \
    add_manual_data
import pyqtgraph as pg
from pyqtgraph.dockarea import DockArea, Dock

# todo manage time, it seems like there are some TZ issues
class AwQtManual(QtGui.QMainWindow):
    data_mapper = {
        'sum by: afk': 'afk_data',
        'sum by: app': 'ww_data',
        'sum by: tag': 'manual_data',
    }
    sum_col = {
        'sum by: afk': 'status',
        'sum by: app': 'app',
        'sum by: tag': 'tag',
    }

    def __init__(self, start_day: str):
        QtWidgets.QMainWindow.__init__(self)
        self.resize(1500, 900)
        area = DockArea()
        self.setCentralWidget(area)
        self.dock1 = Dock("main plot", size=(1000, 900), hideTitle=True)
        self.dock2 = Dock("tag data", size=(500, 300), hideTitle=True)
        self.dock3 = Dock('table_data', size=(500, 600), hideTitle=True)

        area.addDock(self.dock1, 'left')
        area.addDock(self.dock2, 'right', self.dock1)
        area.addDock(self.dock3, 'bottom', self.dock2)
        self.day = start_day
        self.day_dt = datetime.datetime.fromisoformat(start_day)
        self.inialize_plot_window()
        self.dock1.addWidget(self.plot_window)

        # add plot data
        self.data = {}
        self.data['afk_data'] = self.add_afk()
        self.data['ww_data'] = self.add_windowwatcher()
        self.data['manual_data'] = self.add_manual_data()

        self.initialize_datatable()
        self.initialize_button_section()

        self.show()

    def inialize_plot_window(self):
        self.plot_window = pg.GraphicsLayoutWidget(show=False)
        self.plot_label1 = pg.LabelItem(justify='right')
        self.plot_label2 = pg.LabelItem(justify='right')
        self.plot_label3 = pg.LabelItem(justify='right')
        self.plot_window.addItem(self.plot_label1)
        self.plot_window.nextRow()
        self.plot_window.addItem(self.plot_label2)
        self.plot_window.nextRow()
        self.plot_window.addItem(self.plot_label3)
        self.plot_window.nextRow()
        self.data_plot = self.plot_window.addPlot(axisItems={'bottom': pg.DateAxisItem()})
        self.data_plot.setYRange(0, 3)
        self.data_plot.setMouseEnabled(x=True, y=False)
        self.data_plot.resize(1000, 600)
        self.data_plot.setWindowTitle('pyqtgraph example: Plotting')

        self.selection = pg.LinearRegionItem([self.day_dt.timestamp() + 3600 * 9,
                                              self.day_dt.timestamp() + 3600 * 10])  # set window to 9 and 10am
        self.selection.setZValue(-10)
        self.data_plot.addItem(self.selection)
        # hover over info
        self.vb = self.data_plot.vb

    def initialize_button_section(self):

        self.date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.date_edit.setDateTime(self.day_dt)
        self.date_edit.dateChanged.connect(self.change_date)
        self.dock2.addWidget(self.date_edit)

        self.data_selector = QtGui.QComboBox()
        self.data_selector.addItem('sum by: afk')  # afk_data
        self.data_selector.addItem('sum by: app')  # ww_data
        self.data_selector.addItem('sum by: tag')  # manual_data
        self.dock2.addWidget(self.data_selector)
        self.selectionchange(1)
        self.data_selector.currentIndexChanged.connect(self.selectionchange)

        # tag text area
        self.tag = QtGui.QLineEdit('Tag:')
        self.dock2.addWidget(self.tag)

        # overlap option
        self.overlap_option = QtGui.QComboBox()
        self.overlap_option.addItem('overwrite')  # afk_data
        self.overlap_option.addItem('underwrite')  # ww_data
        self.overlap_option.addItem('raise')  # manual_data
        self.dock2.addWidget(self.overlap_option)
        self.overlap_option.currentIndexChanged.connect(self.overlap_sel_change)
        self.overlap_sel_change(1)

        # tag button
        self.tag_button = QtGui.QPushButton('Tag selected Time')
        self.tag_button.clicked.connect(self.tag_time)
        self.dock2.addWidget(self.tag_button)

    def initialize_datatable(self):
        self.datatable = pg.TableWidget()
        self.datatable.resize(500, 500)
        self.dock3.addWidget(self.datatable)

    def tag_time(self):  # todo check!!!!!
        low, high = self.selection.getRegion()
        print(high - low)
        add_manual_data(start=datetime.datetime.fromtimestamp(low, datetime.timezone.utc), # todo manage timezones in the future
                        duration=high - low, tag=self.tag.text().replace('Tag:', ''),
                        overlap=self.overlap)

    def change_date(self): # todo pull date again
        print(self.date_edit.date())

    def overlap_sel_change(self, i):
        self.overlap = self.overlap_option.currentText()

    def selectionchange(self, i):
        j = self.data_selector.currentText()
        data = self.data[self.data_mapper[j]]
        if data is not None:
            self.show_data = data.groupby(self.sum_col[j]).sum().to_records()
        else:
            data = pd.DataFrame(columns=['duration min'])
            data.index.name = self.sum_col[j]
            self.show_data = data.to_records()
        self.datatable.setData(self.show_data)

    def mouseMoved(self, evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.data_plot.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            index = mousePoint.x()
            tag, tag_dur, afk, afk_dur, cur_app, window, ww_dur = get_labels_from_unix(
                index,
                self.data['afk_data'],
                self.data['ww_data'],
                self.data['manual_data'])
            text = (f"<span style='font-size: 12pt'>"
                    f"{datetime.datetime.fromtimestamp(index).isoformat(sep=' ', timespec='seconds')};"
                    f"  Tag: {tag}; {tag_dur}m")
            self.plot_label1.setText(text)
            text2 = f"<span style='font-size: 12pt'>AKF:{afk}; {afk_dur}m  app:{cur_app}; {ww_dur}"
            self.plot_label2.setText(text2)
            text3 = f"<span style='font-size: 12pt'> Window: {window}"
            self.plot_label3.setText(text3)

    def add_windowwatcher(self):  # todo make these updating see basicplotting updating
        start = datetime.datetime.fromisoformat(self.day)
        data = get_window_watcher_data(start.isoformat(), (start + datetime.timedelta(days=1)).isoformat())
        if data is not None:
            apps = pd.unique(data.loc[:, 'app'])
            cm = get_cmap('gist_ncar')
            n_scens = len(apps)
            colors = [cm(e / n_scens) for e in range(n_scens)]
            for k, c in zip(apps, colors):
                idx = data.loc[:, 'app'] == k
                bg = pg.BarGraphItem(x0=data.loc[idx, 'start_unix'], x1=data.loc[idx, 'stop_unix'], y0=0, y1=1,
                                     brush='b')
                self.data_plot.addItem(bg)
            data = data.loc[:, ['title', 'app', 'duration_min', 'start_unix', 'stop_unix']]
        return data

    def add_afk(self):  # todo make these updating see basicplotting updating
        start = datetime.datetime.fromisoformat(self.day)
        data = get_afk_data(start.isoformat(), (start + datetime.timedelta(days=1)).isoformat())
        if data is not None:
            idx = data.status == 'afk'
            bg2 = pg.BarGraphItem(x0=data.loc[idx, 'start_unix'], x1=data.loc[idx, 'stop_unix'], y0=1, y1=2, brush='r')
            idx = data.status != 'afk'
            bg1 = pg.BarGraphItem(x0=data.loc[idx, 'start_unix'], x1=data.loc[idx, 'stop_unix'], y0=1, y1=2, brush='g')

            self.data_plot.addItem(bg1)
            self.data_plot.addItem(bg2)

            data = data.loc[:, ['status', 'duration_min', 'start_unix', 'stop_unix']]
        return data

    def add_manual_data(self):  # todo make these updating see basicplotting updating
        start = datetime.datetime.fromisoformat(self.day)
        data = get_manual(start.isoformat(), (start + datetime.timedelta(days=1)).isoformat())
        if data is not None:
            apps = pd.unique(data.loc[:, 'tag'])
            cm = get_cmap('gist_ncar')
            n_scens = len(apps)
            colors = [cm(e / n_scens) for e in range(n_scens)]
            for k, c in zip(apps, colors):
                idx = data.loc[:, 'tag'] == k
                bg = pg.BarGraphItem(x0=data.loc[idx, 'start_unix'], x1=data.loc[idx, 'stop_unix'], y0=2, y1=3,
                                     brush='b')
                self.data_plot.addItem(bg)
                data = data.loc[:, ['tag', 'duration_min', 'start_unix', 'stop_unix']]
        return data


def main():
    app = pg.mkQApp()
    loader = AwQtManual('2022-02-06')
    proxy = pg.SignalProxy(loader.data_plot.scene().sigMouseMoved, rateLimit=60, slot=loader.mouseMoved)
    pg.exec()


if __name__ == '__main__':
    main()
