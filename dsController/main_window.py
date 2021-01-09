import pymel.core as pm
import pymel.api as pma
from PySide2 import QtWidgets

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from shiboken2 import getCppPointer
from dsController import rigFn


class MainWindow(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    WINDOW_TITLE = "dsController"
    UI_NAME = "dsController"
    UI_SCRIPT = "import dsController\ndsController.MainWindow()"
    UI_INSTANCE = None
    SCRIPT_JOB = 0

    @classmethod
    def display(cls):
        if not cls.UI_INSTANCE:
            cls.UI_INSTANCE = MainWindow()

        if cls.UI_INSTANCE.isHidden():
            cls.UI_INSTANCE.show(dockable=1, uiScript=cls.UI_SCRIPT)
        else:
            cls.UI_INSTANCE.raise_()
            cls.UI_INSTANCE.activateWindow()

    def __init__(self):
        super(MainWindow, self).__init__()

        self.__class__.UI_INSTANC = self
        self.setObjectName(self.__class__.UI_NAME)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.setMinimumSize(380, 130)
        self.setMaximumHeight(130)

        workspaceControlName = "{0}WorkspaceControl".format(self.UI_NAME)

        if pm.workspaceControl(workspaceControlName, q=1, ex=1):
            workspaceControlPtr = long(pma.MQtUtil.findControl(workspaceControlName))
            widgetPtr = long(getCppPointer(self)[0])

            pma.MQtUtil.addWidgetToMayaLayout(widgetPtr, workspaceControlPtr)

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.update_ui_options()
        self.create_script_job()

    def create_widgets(self):
        # FKIK
        self.fkik_grp = QtWidgets.QGroupBox("FKIK")
        self.fkik_spinbox = QtWidgets.QDoubleSpinBox()
        self.fkik_spinbox.setMaximum(1.0)
        self.fkik_spinbox.setMinimum(0.0)
        self.fkik_spinbox.setSingleStep(0.1)
        self.fkik_switch_btn = QtWidgets.QPushButton("Switch")
        self.fkik_match_checkbox = QtWidgets.QCheckBox("Match")
        # Shortcuts
        self.shortcuts_grp = QtWidgets.QGroupBox("Shortcuts")
        self.space_combo_box = QtWidgets.QComboBox()
        self.ctl_bind_post_btn = QtWidgets.QPushButton("Control bind pose")
        self.asset_bind_pose_btn = QtWidgets.QPushButton("Asset bind pose")

    def create_layouts(self):
        self.fkik_layout = QtWidgets.QHBoxLayout()
        self.fkik_layout.setContentsMargins(0, 0, 0, 0)
        self.fkik_layout.addWidget(QtWidgets.QLabel("State:"))
        self.fkik_layout.addWidget(self.fkik_spinbox)
        self.fkik_layout.addWidget(self.fkik_switch_btn)
        self.fkik_layout.addWidget(self.fkik_match_checkbox)
        self.fkik_layout.addStretch()
        self.fkik_grp.setLayout(self.fkik_layout)

        self.shortcuts_layout = QtWidgets.QHBoxLayout()
        self.shortcuts_layout.addWidget(QtWidgets.QLabel("Space:"))
        self.shortcuts_layout.addWidget(self.space_combo_box)
        self.shortcuts_layout.addWidget(self.ctl_bind_post_btn)
        self.shortcuts_layout.addWidget(self.asset_bind_pose_btn)
        self.shortcuts_grp.setLayout(self.shortcuts_layout)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addWidget(self.fkik_grp)
        self.main_layout.addWidget(self.shortcuts_grp)
        self.main_layout.addStretch()
        self.setLayout(self.main_layout)

    def create_connections(self):
        self.fkik_spinbox.valueChanged.connect(rigFn.set_fkik_blend)
        self.fkik_switch_btn.clicked.connect(lambda: rigFn.switch_fkik(matching=self.fkik_match_checkbox.isChecked()))
        self.space_combo_box.currentIndexChanged.connect(rigFn.switch_space)
        self.asset_bind_pose_btn.clicked.connect(self.asset_bind_pose)
        self.ctl_bind_post_btn.clicked.connect(self.ctl_bind_pose)

    def update_ui_options(self):
        if self.isHidden():
            return
        sel = pm.ls(sl=1)
        if not sel:
            self.fkik_grp.setEnabled(False)
            self.shortcuts_grp.setEnabled(False)
            return
        ctl = sel[-1]
        self.shortcuts_grp.setEnabled(True)
        self.fkik_grp.setEnabled(rigFn.isIKFKLimb(ctl))
        self.asset_bind_pose_btn.setEnabled(rigFn.isMainControl(ctl))
        if ctl.hasAttr("space"):
            spaces = sorted(ctl.space.getEnums().items())
            space_names = [pair[0] for pair in spaces]
            current_space = ctl.space.get(asString=1)
            self.space_combo_box.clear()
            self.space_combo_box.addItems(space_names)
            self.space_combo_box.setCurrentText(current_space)
            self.space_combo_box.setEnabled(True)
        else:
            self.space_combo_box.clear()
            self.space_combo_box.setEnabled(False)

    def create_script_job(self):
        if not self.SCRIPT_JOB:
            self.SCRIPT_JOB = pm.scriptJob(e=("SelectionChanged", self.update_ui_options))  # type: int

    def kill_script_job(self):
        if self.SCRIPT_JOB:
            pm.scriptJob(k=self.SCRIPT_JOB, f=1)
            self.SCRIPT_JOB = 0

    # Events
    def showEvent(self, event):
        if not self.SCRIPT_JOB:
            self.create_script_job()

    def closeEvent(self, e):
        self.kill_script_job()

    def dockCloseEventTriggered(self):
        self.kill_script_job()

    def asset_bind_pose(self):
        rigFn.revert_asset_bind_pose()
        self.update_ui_options()

    def ctl_bind_pose(self):
        rigFn.revert_selection_bind_pose()
        self.update_ui_options()


if __name__ == "__main__":
    try:
        if window and window.parent():  # noqa: F821
            workspaceControlName = window.parent().objectName()  # noqa: F821

            if pm.window(workspaceControlName, ex=1, q=1):
                pm.deleteUI(workspaceControlName)
    except Exception:
        pass

    window = MainWindow()
    # example: uiScript =  "from dsRigging.ui.dialogs.renamingTool import dsRenamingTool\ndsRenamer = dsRenamingTool.Dialog()"
    window.show(dockable=1, uiScript="")
