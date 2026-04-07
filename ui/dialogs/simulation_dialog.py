"""Dialog for DM scene simulation / rehearsal mode."""

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QSplitter,
    QSpinBox, QHeaderView, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class SimulationDialog(QDialog):
    """Modal dialog for running sandboxed combat simulations."""

    def __init__(self, entities: list[dict], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._entity_dicts = entities
        self._simulator = None
        self.setWindowTitle("Scene Simulation")
        self.setMinimumSize(800, 500)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Banner
        banner = QLabel("SIMULATION — No changes will be saved")
        banner.setAlignment(Qt.AlignCenter)
        banner.setStyleSheet(
            "background: #2d1b2e; color: #e0e0e0; padding: 6px; "
            "font-weight: bold; font-size: 13px;"
        )
        layout.addWidget(banner)

        # Config row
        config_row = QHBoxLayout()
        config_row.addWidget(QLabel("Seed:"))
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 999999)
        self._seed_spin.setValue(42)
        config_row.addWidget(self._seed_spin)

        config_row.addWidget(QLabel("Max Rounds:"))
        self._rounds_spin = QSpinBox()
        self._rounds_spin.setRange(1, 100)
        self._rounds_spin.setValue(20)
        config_row.addWidget(self._rounds_spin)
        config_row.addStretch()

        entity_count = len(self._entity_dicts)
        config_row.addWidget(QLabel(f"Entities: {entity_count}"))
        layout.addLayout(config_row)

        # Middle: splitter with entity table + action log
        splitter = QSplitter(Qt.Horizontal)

        # Entity table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Name", "Type", "HP", "Status"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._populate_table_initial()
        splitter.addWidget(self._table)

        # Action log
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 10))
        self._log.setPlaceholderText("Action log will appear here...")
        splitter.addWidget(self._log)

        splitter.setSizes([350, 450])
        layout.addWidget(splitter)

        # Control buttons
        btn_row = QHBoxLayout()

        self._step_btn = QPushButton("Step Round")
        self._step_btn.clicked.connect(self._on_step_round)
        btn_row.addWidget(self._step_btn)

        self._run_btn = QPushButton("Run All")
        self._run_btn.clicked.connect(self._on_run_all)
        btn_row.addWidget(self._run_btn)

        self._reset_btn = QPushButton("Reset")
        self._reset_btn.clicked.connect(self._on_reset)
        btn_row.addWidget(self._reset_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Table
    # ------------------------------------------------------------------

    def _populate_table_initial(self) -> None:
        self._table.setRowCount(len(self._entity_dicts))
        for i, ent in enumerate(self._entity_dicts):
            self._table.setItem(i, 0, QTableWidgetItem(ent.get("name", "?")))
            self._table.setItem(i, 1, QTableWidgetItem(ent.get("entity_type", "?")))
            hp = ent.get("hp", 0)
            max_hp = ent.get("max_hp", hp)
            self._table.setItem(i, 2, QTableWidgetItem(f"{hp}/{max_hp}"))
            self._table.setItem(i, 3, QTableWidgetItem("Ready"))

    def _update_table_from_state(self, state) -> None:
        if not state:
            return
        entities = state.entities if hasattr(state, "entities") else []
        self._table.setRowCount(len(entities))
        for i, es in enumerate(entities):
            self._table.setItem(i, 0, QTableWidgetItem(es.name))
            self._table.setItem(i, 1, QTableWidgetItem(es.entity_type))
            self._table.setItem(i, 2, QTableWidgetItem(f"{es.hp}/{es.max_hp}"))
            alive_str = "Alive" if es.is_alive else "Dead"
            self._table.setItem(i, 3, QTableWidgetItem(alive_str))

    # ------------------------------------------------------------------
    # Simulator lifecycle
    # ------------------------------------------------------------------

    def _ensure_simulator(self) -> bool:
        if self._simulator is not None:
            return True
        try:
            from core.engine.simulation import SceneSimulator, SimulationConfig
            config = SimulationConfig(
                seed=self._seed_spin.value(),
                max_rounds=self._rounds_spin.value(),
            )
            self._simulator = SceneSimulator(self._entity_dicts, config)
            self._simulator.setup()
            self._log.append("Simulation initialized.\n")
            return True
        except Exception as exc:
            self._log.append(f"ERROR: {exc}\n")
            return False

    def _on_step_round(self) -> None:
        if not self._ensure_simulator():
            return
        try:
            lines = self._simulator.run_one_round()
            for line in lines:
                self._log.append(line)
            state = self._simulator.get_state()
            self._update_table_from_state(state)
            if self._simulator.is_finished:
                self._log.append("\n=== COMBAT ENDED ===")
                self._step_btn.setEnabled(False)
                self._run_btn.setEnabled(False)
        except Exception as exc:
            self._log.append(f"ERROR: {exc}")

    def _on_run_all(self) -> None:
        if not self._ensure_simulator():
            return
        try:
            result = self._simulator.run_to_completion()
            for line in result.action_log:
                self._log.append(line)
            self._log.append(f"\n=== RESULT: {result.winner or 'Timeout'} "
                             f"in {result.rounds_played} rounds ===")
            # Update table with final states
            self._table.setRowCount(len(result.final_entity_states))
            for i, es in enumerate(result.final_entity_states):
                self._table.setItem(i, 0, QTableWidgetItem(es["name"]))
                self._table.setItem(i, 1, QTableWidgetItem(es["entity_type"]))
                self._table.setItem(i, 2, QTableWidgetItem(f"{es['hp']}/{es['max_hp']}"))
                self._table.setItem(i, 3, QTableWidgetItem("Alive" if es["is_alive"] else "Dead"))
            self._step_btn.setEnabled(False)
            self._run_btn.setEnabled(False)
        except Exception as exc:
            self._log.append(f"ERROR: {exc}")

    def _on_reset(self) -> None:
        if self._simulator:
            self._simulator.cleanup()
            self._simulator = None
        self._log.clear()
        self._populate_table_initial()
        self._step_btn.setEnabled(True)
        self._run_btn.setEnabled(True)
        self._log.append("Simulation reset. Click Step Round or Run All to begin.\n")

    def closeEvent(self, event) -> None:
        if self._simulator:
            self._simulator.cleanup()
            self._simulator = None
        super().closeEvent(event)
