"""Modal dialog for transferring items and gold between entities."""

from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSpinBox, QFrame,
)
from PyQt5.QtCore import Qt

_TYPE_COLORS = {
    "weapon": "#c0392b",
    "armor": "#2980b9",
    "consumable": "#27ae60",
    "quest": "#e8c840",
    "trinket": "#95a5a6",
}


class ItemTransferDialog(QDialog):
    """Dialog for giving items and gold from one entity to another.

    After exec_() returns QDialog.Accepted, call transferred_items()
    and transferred_gold() to get what was given.
    """

    def __init__(self, source_entity, target_entity, parent=None):
        super().__init__(parent)
        self._source = source_entity
        self._target = target_entity
        self._transferred: list[dict] = []
        self._gold_given: int = 0

        src_name = getattr(source_entity, "name", "You")
        tgt_name = getattr(target_entity, "name", "Them")
        self.setWindowTitle(f"Give Items to {tgt_name}")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QLabel(f"<b>{src_name}</b> gives to <b>{tgt_name}</b>")
        header.setStyleSheet("font-size: 14px; color: #e8c840;")
        layout.addWidget(header)

        # Inventory list
        inv_label = QLabel(f"Select items from {src_name}'s inventory:")
        inv_label.setStyleSheet("font-size: 12px; color: #c0b8a0;")
        layout.addWidget(inv_label)

        self._item_list = QListWidget()
        self._item_list.setStyleSheet(
            "QListWidget { background: rgba(30,28,24,200); color: #e0d8c8;"
            "border: 1px solid rgba(200,170,100,60); font-size: 12px; }"
            "QListWidget::item { padding: 4px; }"
        )
        inventory = getattr(source_entity, "inventory", [])
        for i, item in enumerate(inventory):
            if isinstance(item, dict):
                name = item.get("name", "???")
                itype = item.get("type", "trinket")
                gv = item.get("gold_value", 0)
                color = _TYPE_COLORS.get(itype, "#95a5a6")
                text = f"[{itype}] {name}"
                if gv:
                    text += f"  ({gv} gp)"
            else:
                text = str(item)
            li = QListWidgetItem(text)
            li.setFlags(li.flags() | Qt.ItemIsUserCheckable)
            li.setCheckState(Qt.Unchecked)
            li.setData(Qt.UserRole, i)  # store inventory index
            self._item_list.addItem(li)

        if not inventory:
            li = QListWidgetItem("(no items)")
            li.setFlags(li.flags() & ~Qt.ItemIsEnabled)
            self._item_list.addItem(li)

        layout.addWidget(self._item_list)

        # Gold transfer
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(200,170,100,40);")
        layout.addWidget(sep)

        gold_row = QHBoxLayout()
        gold_row.setSpacing(8)
        current_gold = source_entity.stats.get("gold", 0) if hasattr(source_entity, "stats") else 0

        gold_label = QLabel("Gold to give:")
        gold_label.setStyleSheet("font-size: 12px; color: #e8c840;")
        gold_row.addWidget(gold_label)

        self._gold_spin = QSpinBox()
        self._gold_spin.setRange(0, max(0, current_gold))
        self._gold_spin.setValue(0)
        self._gold_spin.setSuffix(" gp")
        self._gold_spin.setStyleSheet("font-size: 12px;")
        gold_row.addWidget(self._gold_spin)

        avail_label = QLabel(f"(have {current_gold} gp)")
        avail_label.setStyleSheet("font-size: 11px; color: #807868;")
        gold_row.addWidget(avail_label)
        gold_row.addStretch()

        layout.addLayout(gold_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        give_btn = QPushButton("Give Selected")
        give_btn.setMinimumHeight(32)
        give_btn.setStyleSheet(
            "QPushButton { background: rgba(60,55,45,200); color: #e8c840;"
            "border: 1px solid rgba(200,170,100,80); border-radius: 5px;"
            "padding: 6px 20px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(100,90,60,200); }"
        )
        give_btn.clicked.connect(self._on_give)
        btn_row.addWidget(give_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(32)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        layout.addLayout(btn_row)

    def _on_give(self) -> None:
        """Collect selected items and accept."""
        inventory = getattr(self._source, "inventory", [])
        selected_indices = []
        for row in range(self._item_list.count()):
            li = self._item_list.item(row)
            if li.checkState() == Qt.Checked:
                idx = li.data(Qt.UserRole)
                if idx is not None:
                    selected_indices.append(idx)

        self._gold_given = self._gold_spin.value()

        # Nothing selected and no gold — just close
        if not selected_indices and self._gold_given == 0:
            self.reject()
            return

        # Collect items by index (reverse to avoid shifting)
        self._transferred = []
        for idx in sorted(selected_indices, reverse=True):
            if 0 <= idx < len(inventory):
                self._transferred.append(inventory.pop(idx))

        # Transfer gold
        if self._gold_given > 0:
            src_gold = self._source.stats.get("gold", 0)
            actual = min(self._gold_given, src_gold)
            self._source.stats["gold"] = src_gold - actual
            tgt_gold = self._target.stats.get("gold", 0) if hasattr(self._target, "stats") else 0
            self._target.stats["gold"] = tgt_gold + actual
            self._gold_given = actual

        # Add items to target
        target_inv = getattr(self._target, "inventory", None)
        if target_inv is None:
            self._target.inventory = []
            target_inv = self._target.inventory
        for item in self._transferred:
            target_inv.append(item)

        self.accept()

    def transferred_items(self) -> list[dict]:
        return list(self._transferred)

    def transferred_gold(self) -> int:
        return self._gold_given
