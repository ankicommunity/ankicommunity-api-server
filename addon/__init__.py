from PyQt5.Qt import Qt, QCheckBox, QLabel, QHBoxLayout, QLineEdit, \
    QListWidget, QAbstractItemView, QListWidgetItem
from aqt.forms import preferences
from anki.hooks import wrap, addHook
import aqt
import anki.consts
import anki.sync
import os

DEFAULT_ADDR = "http://localhost:27701/"
config = aqt.mw.addonManager.getConfig(__name__)

# TODO: force the user to log out before changing any of the settings

def addui(self, _):
    self = self.form
    parent_w = self.tab_2
    parent_l = self.vboxlayout
    self.useCustomServer = QCheckBox(parent_w)
    self.useCustomServer.setText("Use custom sync server")
    parent_l.addWidget(self.useCustomServer)
    cshl = QHBoxLayout()
    parent_l.addLayout(cshl)

    self.serverAddrLabel = QLabel(parent_w)
    self.serverAddrLabel.setText("Server address")
    cshl.addWidget(self.serverAddrLabel)
    self.customServerAddr = QLineEdit(parent_w)
    self.customServerAddr.setPlaceholderText(DEFAULT_ADDR)
    cshl.addWidget(self.customServerAddr)

    sphl = QHBoxLayout()
    parent_l.addLayout(sphl)

    self.onlySelected = QCheckBox(parent_w)
    self.onlySelected.setText("Only use custom sync server\nfor selected profiles")
    sphl.addWidget(self.onlySelected)

    self.selectedProfilesLabel = QLabel(parent_w)
    self.selectedProfilesLabel.setText("Selected profiles")
    sphl.addWidget(self.selectedProfilesLabel)
    self.selectedProfilesList = QListWidget(parent_w)
    for p in aqt.mw.pm.profiles():
        item = QListWidgetItem(p)
        self.selectedProfilesList.addItem(item)
        if p in config["selectedprofiles"]:
            item.setSelected(True)
    self.selectedProfilesList.setFixedHeight(
        self.selectedProfilesList.sizeHintForRow(0) * self.selectedProfilesList.count() + \
        2 * self.selectedProfilesList.frameWidth()
    )

    self.selectedProfilesList.setSelectionMode(QAbstractItemView.MultiSelection)
    sphl.addWidget(self.selectedProfilesList)

    if config["enabled"]:
        self.useCustomServer.setCheckState(Qt.Checked)
    if config["addr"]:
        self.customServerAddr.setText(config['addr'])

    if config["onlyselected"]:
        self.onlySelected.setCheckState(Qt.Checked)
    self.customServerAddr.textChanged.connect(lambda text: updateserver(self, text))
    def onchecked(state):
        config["enabled"] = state == Qt.Checked
        updateui(self, state)
        updateserver(self, self.customServerAddr.text())
    self.useCustomServer.stateChanged.connect(onchecked)

    self.selectedProfilesList.itemClicked.connect(lambda _: updateprofiles(self))
    def ononlyselectedchecked(state):
        config["onlyselected"] = state == Qt.Checked
        updateuiprofiles(self, state)
        updateprofiles(self)
    self.onlySelected.stateChanged.connect(ononlyselectedchecked)

    updateui(self, self.useCustomServer.checkState())
    updateuiprofiles(self, self.onlySelected.checkState())

def updateserver(self, text):
    if config['enabled']:
        addr = text or self.customServerAddr.placeholderText()
        config['addr'] = addr
        setserver()
    aqt.mw.addonManager.writeConfig(__name__, config)

def updateprofiles(self):
    # For simplicity just flush the whole list rather than toggle the item
    config["selectedprofiles"] = [x.text() for x in self.selectedProfilesList.selectedItems()]
    aqt.mw.addonManager.writeConfig(__name__, config)

def updateuiprofiles(self, state):
    self.selectedProfilesLabel.setEnabled(state == Qt.Checked and config['enabled'])
    self.selectedProfilesList.setEnabled(state == Qt.Checked and config['enabled'])

def updateui(self, state):
    self.serverAddrLabel.setEnabled(state == Qt.Checked)
    self.customServerAddr.setEnabled(state == Qt.Checked)
    self.onlySelected.setEnabled(state == Qt.Checked)
    self.selectedProfilesLabel.setEnabled(state == Qt.Checked and config['onlyselected'])
    self.selectedProfilesList.setEnabled(state == Qt.Checked and config['onlyselected'])

def setserver():
    if config['enabled'] and (not config['onlyselected'] or aqt.mw.pm.name in config['selectedprofiles']):
        os.environ["SYNC_ENDPOINT"] = config['addr'] + ("" if config['addr'][-1] == "/" else "/") + "sync/"
        os.environ["SYNC_ENDPOINT_MEDIA"] = config['addr'] + ("" if config['addr'][-1] == "/" else "/") + "msync/"

addHook("profileLoaded", setserver)
aqt.preferences.Preferences.__init__ = wrap(aqt.preferences.Preferences.__init__, addui, "after")
