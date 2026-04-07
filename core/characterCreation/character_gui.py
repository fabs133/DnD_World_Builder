import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QGroupBox, QPushButton, QHBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QLabel, QInputDialog, QTabWidget, QMessageBox, QFileDialog,
    QCheckBox, QScrollArea, QGridLayout,
)
from PyQt5.QtCore import Qt

from models.entities.game_entity import GameEntity
from core.logger import app_logger

CLASS_TO_SPELL_ABILITY = {
    "Bard": "CHA", "Cleric": "WIS", "Druid": "WIS", "Paladin": "CHA",
    "Ranger": "WIS", "Sorcerer": "CHA", "Warlock": "CHA", "Wizard": "INT",
    "Artificer": "INT"
}

CLASS_SAVING_THROW_PROFS = {
    "Barbarian": ["STR", "CON"], "Bard": ["DEX", "CHA"],
    "Cleric": ["WIS", "CHA"], "Druid": ["INT", "WIS"],
    "Fighter": ["STR", "CON"], "Monk": ["STR", "DEX"],
    "Paladin": ["WIS", "CHA"], "Ranger": ["STR", "DEX"],
    "Rogue": ["DEX", "INT"], "Sorcerer": ["CON", "CHA"],
    "Warlock": ["WIS", "CHA"], "Wizard": ["INT", "WIS"],
}

SKILLS = {
    "Acrobatics": "DEX", "Animal Handling": "WIS", "Arcana": "INT",
    "Athletics": "STR", "Deception": "CHA", "History": "INT",
    "Insight": "WIS", "Intimidation": "CHA", "Investigation": "INT",
    "Medicine": "WIS", "Nature": "INT", "Perception": "WIS",
    "Performance": "CHA", "Persuasion": "CHA", "Religion": "INT",
    "Sleight of Hand": "DEX", "Stealth": "DEX", "Survival": "WIS",
}

DND_CONDITIONS = [
    "Blinded", "Charmed", "Deafened", "Exhaustion",
    "Frightened", "Grappled", "Incapacitated", "Invisible",
    "Paralyzed", "Petrified", "Poisoned", "Prone",
    "Restrained", "Stunned", "Unconscious",
]


class CharacterCreationWindow(QWidget):
    def __init__(self, api=None, base_path="core/data_/rulebook_json"):
        super().__init__()
        self.setWindowFlags(
            Qt.Window | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
        )
        if api is not None:
            self.api_handler = api
        else:
            from core.db_api_handler import LocalAPIHandler
            self.api_handler = LocalAPIHandler(base_path)

        self.speed_values = []
        self.races_names = []
        self.initUI()
        self.load_classes()
        self.load_languages()
        self.load_races()
        self.update_spells()

    def initUI(self):
        self.setWindowTitle('Character Creation')
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # === Basics Tab ===
        self.name_input = QLineEdit()
        self.languages_input = QComboBox()
        self.race_input = QComboBox()
        self.char_class_input = QComboBox()
        self.subclass_input = QComboBox()

        basics_tab = QWidget()
        basics_layout = QFormLayout(basics_tab)
        basics_layout.addRow("Name:", self.name_input)
        basics_layout.addRow("Languages:", self.languages_input)
        basics_layout.addRow("Races:", self.race_input)
        basics_layout.addRow("Class:", self.char_class_input)
        basics_layout.addRow("Subclass:", self.subclass_input)
        self.tab_widget.addTab(basics_tab, "Basics")

        self.char_class_input.currentIndexChanged.connect(self.update_subclasses)
        self.race_input.currentIndexChanged.connect(self.load_speed)

        # === Attributes Tab ===
        self.proficiency_bonus_label = QLabel()
        self.stats_inputs = {}
        self.stats_modifiers = {}
        self.stats_warnings = {}
        self.saving_throw_profs = {}
        self.saving_throw_labels = {}
        self.skill_profs = {}
        self.skill_labels = {}

        stats_group = QGroupBox("Ability Scores")
        stats_form = QFormLayout(stats_group)
        for ability in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
            spin = QSpinBox()
            spin.setRange(8, 15)
            spin.setValue(10)
            spin.valueChanged.connect(lambda _, a=ability: self.validate_stats(a))

            warning = QLabel("")
            warning.setStyleSheet("color: red")
            warning.setVisible(False)

            modifier = QLabel("(mod: +0)")
            self.stats_modifiers[ability] = modifier

            container = QHBoxLayout()
            container.addWidget(spin)
            container.addWidget(modifier)
            container.addWidget(warning)

            self.stats_inputs[ability] = spin
            self.stats_warnings[ability] = warning

            stats_form.addRow(f"{ability}:", container)

        stats_form.addRow("Proficiency Bonus:", self.proficiency_bonus_label)

        attributes_content = QWidget()
        attributes_vbox = QVBoxLayout(attributes_content)
        attributes_vbox.addWidget(stats_group)
        attributes_vbox.addWidget(self._build_saving_throws_widget())
        attributes_vbox.addWidget(self._build_skills_widget())
        attributes_vbox.addStretch()

        attributes_scroll = QScrollArea()
        attributes_scroll.setWidget(attributes_content)
        attributes_scroll.setWidgetResizable(True)

        attributes_tab = QWidget()
        QVBoxLayout(attributes_tab).addWidget(attributes_scroll)
        self.tab_widget.addTab(attributes_tab, "Attributes")

        # === Combat Tab ===
        self.armor_class_input = QSpinBox(); self.armor_class_input.setRange(0, 30); self.armor_class_input.setValue(10)
        self.initiative_input = QSpinBox(); self.initiative_input.setRange(-10, 10); self.initiative_input.setValue(0)
        self.speed_label = QLabel()
        self.temporary_hp_input = QSpinBox(); self.temporary_hp_input.setRange(0, 100); self.temporary_hp_input.setValue(0)
        self.conditions_list = QListWidget()
        self.conditions_list.setFixedHeight(160)
        for _cond in DND_CONDITIONS:
            _item = QListWidgetItem(_cond)
            _item.setFlags(_item.flags() | Qt.ItemIsUserCheckable)
            _item.setCheckState(Qt.Unchecked)
            self.conditions_list.addItem(_item)
        self.currency_input = QLineEdit()
        self.inventory_list = QListWidget()
        self.inventory_add_button = QPushButton("Add Item")
        self.inventory_remove_button = QPushButton("Remove Selected")

        # Setup add/remove logic
        self.inventory_add_button.clicked.connect(self.add_inventory_item)
        self.inventory_remove_button.clicked.connect(self.remove_inventory_item)
        inventory_container = QVBoxLayout()
        inventory_container.addWidget(self.inventory_list)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.inventory_add_button)
        btn_row.addWidget(self.inventory_remove_button)
        inventory_container.addLayout(btn_row)

        self.passive_perception_label = QLabel()
        self.spellslots_input = QSpinBox(); self.spellslots_input.setRange(0, 4); self.spellslots_input.setValue(0)
        self.combat_warning_label = QLabel(""); self.combat_warning_label.setStyleSheet("color: red"); self.combat_warning_label.setVisible(False)

        combat_tab = QWidget()
        combat_layout = QFormLayout(combat_tab)
        combat_layout.addRow("Armor Class:", self.armor_class_input)
        combat_layout.addRow("Initiative:", self.initiative_input)
        combat_layout.addRow("Speed:", self.speed_label)
        combat_layout.addRow("Temporary HP:", self.temporary_hp_input)
        combat_layout.addRow("Conditions:", self._build_conditions_widget())
        combat_layout.addRow("Currency:", self.currency_input)
        combat_layout.addRow("Inventory:", self._wrap_layout(inventory_container))
        combat_layout.addRow("Passive Perception:", self.passive_perception_label)
        combat_layout.addRow("Spell Slots:", self.spellslots_input)
        combat_layout.addRow(self.combat_warning_label)
        self.tab_widget.addTab(combat_tab, "Combat")

        # === Spells Tab ===
        self.spells_input = QListWidget()
        self.spellcasting_ability_label = QLabel()

        spells_tab = QWidget()
        spells_layout = QFormLayout(spells_tab)
        spells_layout.addRow("Spells:", self.spells_input)
        spells_layout.addRow("Spellcasting Ability:", self.spellcasting_ability_label)
        self.tab_widget.addTab(spells_tab, "Spells")

        # === Roleplay Tab ===
        self.appearance_input = QTextEdit(); self.appearance_input.setFixedHeight(50)
        self.backstory_input = QTextEdit(); self.backstory_input.setFixedHeight(100)
        self.personality_input = QLineEdit()

        roleplay_tab = QWidget()
        roleplay_layout = QFormLayout(roleplay_tab)
        roleplay_layout.addRow("Appearance:", self.appearance_input)
        roleplay_layout.addRow("Backstory:", self.backstory_input)
        roleplay_layout.addRow("Personality:", self.personality_input)
        self.tab_widget.addTab(roleplay_tab, "Roleplay")

        # === Voice Tab ===
        voice_tab = QWidget()
        voice_layout = QVBoxLayout(voice_tab)
        voice_layout.addWidget(QLabel("Configure how your character sounds in dialogue:"))
        from ui.voice.voice_settings_widget import VoiceSettingsWidget
        self._voice_widget = VoiceSettingsWidget()
        self._voice_widget.set_preview_text("Greetings, I am ready for adventure!")
        voice_layout.addWidget(self._voice_widget)
        voice_layout.addStretch()
        self.tab_widget.addTab(voice_tab, "Voice")

        # === Summary Tab ===
        self.summary_tab = QWidget()
        summary_layout = QFormLayout(self.summary_tab)
        self.summary_labels = {}  # Store dynamic QLabel references

        for field in [
            "Name", "Race", "Class", "Subclass", "AC", "Initiative", "Speed",
            "Passive Perception", "Spellcasting Ability"
        ] + ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
            label = QLabel("-")
            self.summary_labels[field] = label
            summary_layout.addRow(f"{field}:", label)

        self.tab_widget.addTab(self.summary_tab, "Summary")

        # === Final Setup ===
        self.update_proficiency_bonus()
        self.update_class_saving_throw_profs()
        self.update_saving_throws()
        self.update_skills()
        self.update_passive_perception()
        self.update_spellcasting_ability()
        self.update_summary()
        self.update_stat_modifiers()

        self.name_input.textChanged.connect(self.update_summary)
        self.name_input.textChanged.connect(
            lambda name: self._voice_widget.set_preview_text(
                f"I am {name}, ready for adventure!" if name else "Greetings, I am ready for adventure!")
        )
        self.race_input.currentIndexChanged.connect(self.update_summary)
        self.char_class_input.currentIndexChanged.connect(self.update_summary)
        self.subclass_input.currentIndexChanged.connect(self.update_summary)
        for stat in self.stats_inputs.values():
            stat.valueChanged.connect(self.update_summary)
            stat.valueChanged.connect(self.update_stat_modifiers)
            stat.valueChanged.connect(self.update_saving_throws)
            stat.valueChanged.connect(self.update_skills)

        self.stats_inputs["WIS"].valueChanged.connect(self.update_passive_perception)
        self.skill_profs["Perception"].stateChanged.connect(self.update_passive_perception)
        self.char_class_input.currentIndexChanged.connect(self.update_spellcasting_ability)
        self.char_class_input.currentIndexChanged.connect(self.update_class_saving_throw_profs)
        for _cb in self.saving_throw_profs.values():
            _cb.stateChanged.connect(self.update_saving_throws)
        for _cb in self.skill_profs.values():
            _cb.stateChanged.connect(self.update_skills)
        self.armor_class_input.valueChanged.connect(self.validate_combat_inputs)
        self.initiative_input.valueChanged.connect(self.validate_combat_inputs)
        self.temporary_hp_input.valueChanged.connect(self.validate_combat_inputs)
        self.spellslots_input.valueChanged.connect(self.validate_combat_inputs)

        button_layout = QHBoxLayout()
        for btn in ['Save', 'Load', 'Clear']:
            button_layout.addWidget(QPushButton(btn))

        self.import_button = QPushButton("Import Existing")
        self.import_button.clicked.connect(self.import_existing_character)
        button_layout.addWidget(self.import_button)

        self.export_button = QPushButton('Export')
        self.export_button.clicked.connect(self.export_data)
        button_layout.addWidget(self.export_button)

        main_layout.addLayout(button_layout)


    def import_existing_character(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Character", "", "Character Files (*.json *.entity.json)")
        if not file_path:
            return

        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            entity = GameEntity.from_dict(data)

            # Populate UI
            self.name_input.setText(entity.name)
            self.inventory_list.clear()
            for item in entity.inventory:
                self.inventory_list.addItem(item)

            for stat, val in entity.stats.items():
                if stat in self.stats_inputs:
                    self.stats_inputs[stat].setValue(val)

            # Guess race/class if stored in entity_type
            etype = str(entity.entity_type) if entity.entity_type else ""
            parts = etype.split()
            if parts:
                self.race_input.setCurrentText(parts[0])
                if len(parts) > 1:
                    self.char_class_input.setCurrentText(parts[1])

            self.update_stat_modifiers()
            self.update_summary()
            app_logger.info(f"[CharacterGUI] Loaded character: {entity.name}")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import character: {e}")



    def update_stat_modifiers(self):
        for ability, spin in self.stats_inputs.items():
            value = spin.value()
            mod = (value - 10) // 2
            sign = '+' if mod >= 0 else ''
            self.stats_modifiers[ability].setText(f"(mod: {sign}{mod})")

    def to_game_entity(self):
        data = self.collect_data()
        entity_type = f"{data['race']} {data['class']}"
        return GameEntity(
            name=data["name"],
            entity_type=entity_type,
            stats=data["stats"],
            inventory=data["inventory"]
        )


    def validate_required_fields(self):
        missing = []
        if not self.name_input.text().strip():
            missing.append("Name")
        if not self.char_class_input.currentText().strip():
            missing.append("Class")
        if not self.race_input.currentText().strip():
            missing.append("Race")

        if missing:
            QMessageBox.warning(self, "Missing Required Fields", f"Please fill in the following: {', '.join(missing)}")
            return False
        return True


    def export_data(self):
        if not self.validate_required_fields():
            return
        if not self.validate_stats():
            QMessageBox.critical(self, "Invalid Stats", "Total point-buy exceeds 27 or contains invalid values.")
            return
        if not self.is_character_reasonable():
            QMessageBox.warning(self, "Unbalanced Character", "This character exceeds sane starting limits. Please adjust AC, initiative, HP or spell slots.")
            return

        file_name = self.get_file_name()
        if file_name:
            with open(f'{file_name}.json', 'w') as file:
                json.dump(self.collect_data(), file, indent=4)
            app_logger.info("[CharacterGUI] Data exported successfully")



        
    def _wrap_layout(self, layout):
        container = QWidget()
        container.setLayout(layout)
        return container

    def update_summary(self):
        self.summary_labels["Name"].setText(self.name_input.text())
        self.summary_labels["Race"].setText(self.race_input.currentText())
        self.summary_labels["Class"].setText(self.char_class_input.currentText())
        self.summary_labels["Subclass"].setText(self.subclass_input.currentText())

        for stat in ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']:
            self.summary_labels[stat].setText(str(self.stats_inputs[stat].value()))

        self.summary_labels["AC"].setText(str(self.armor_class_input.value()))
        self.summary_labels["Initiative"].setText(str(self.initiative_input.value()))
        self.summary_labels["Speed"].setText(self.speed_label.text())
        self.summary_labels["Passive Perception"].setText(self.passive_perception_label.text())
        self.summary_labels["Spellcasting Ability"].setText(self.spellcasting_ability_label.text())


    def collect_data(self):
        return {
            'name': self.name_input.text(),
            'appearance': self.appearance_input.toPlainText(),
            'backstory': self.backstory_input.toPlainText(),
            'personality': self.personality_input.text(),
            'languages': self.languages_input.currentText(),
            'race': self.race_input.currentText(),
            'class': self.char_class_input.currentText(),
            'subclass': self.subclass_input.currentText(),
            'proficiency_bonus': self.proficiency_bonus_label.text(),
            'saving_throws': self._get_saving_throw_values(),
            'skills': self._get_skill_values(),
            'stats': {key: spin.value() for key, spin in self.stats_inputs.items()},
            'armor_class': self.armor_class_input.value(),
            'speed': self.speed_label.text(),
            'initiative': self.initiative_input.value(),
            'conditions': [
                self.conditions_list.item(i).text()
                for i in range(self.conditions_list.count())
                if self.conditions_list.item(i).checkState() == Qt.Checked
            ],
            'temporary_hp': self.temporary_hp_input.value(),
            'inventory': [self.inventory_list.item(i).text() for i in range(self.inventory_list.count())],
            'currency': self.currency_input.text(),
            'passive_perception': self.passive_perception_label.text(),
            'spells': [self.spells_input.item(i).text() for i in range(self.spells_input.count())],
            'spell_slots': self.spellslots_input.value(),
            'spellcasting_ability': self.spellcasting_ability_label.text(),
            'voice_profile': self._voice_widget.get_profile().to_dict(),
        }

    def update_proficiency_bonus(self):
        level = self.level_input.value() if hasattr(self, "level_input") else 1
        bonus = 2 + (level - 1) // 4  # D&D 5e: +2 at L1, +3 at L5, +4 at L9, etc.
        self.proficiency_bonus_label.setText(f"+{bonus}")


    def update_passive_perception(self):
        wis_widget = self.stats_inputs.get("WIS")
        wis = wis_widget.value() if wis_widget else 10
        wis_mod = (wis - 10) // 2
        prof_bonus = 2 if self.skill_profs["Perception"].isChecked() else 0
        value = 10 + wis_mod + prof_bonus
        self.passive_perception_label.setText(str(value))
        self.update_summary()

    def add_inventory_item(self):
        text, ok = QInputDialog.getText(self, "Add Inventory Item", "Enter item name:")
        if ok and text.strip():
            self.inventory_list.addItem(text.strip())

    def remove_inventory_item(self):
        selected_items = self.inventory_list.selectedItems()
        for item in selected_items:
            self.inventory_list.takeItem(self.inventory_list.row(item))


    def update_spellcasting_ability(self):
        class_name = self.char_class_input.currentText()
        ability = CLASS_TO_SPELL_ABILITY.get(class_name, "—")
        self.spellcasting_ability_label.setText(ability)
        self.update_summary()

    def get_file_name(self):
        text, ok = QInputDialog.getText(self, 'Save Character', 'Enter file name:')
        return text if ok and text else None


    def validate_combat_inputs(self):
        ac = self.armor_class_input.value()
        init = self.initiative_input.value()
        temp_hp = self.temporary_hp_input.value()
        spell_slots = self.spellslots_input.value()

        warnings = []

        # Clamp values hard
        if ac > 20:
            self.armor_class_input.setValue(20)
            warnings.append("AC capped at 20")
        if init > 6:
            self.initiative_input.setValue(6)
            warnings.append("Initiative capped at 6")
        if temp_hp > 50:
            self.temporary_hp_input.setValue(50)
            warnings.append("Temporary HP capped at 50")
        if spell_slots > 2:
            self.spellslots_input.setValue(2)
            warnings.append("Spell slots capped at 2")

        # Display feedback
        if warnings:
            self.combat_warning_label.setText(" / ".join(warnings))
            self.combat_warning_label.setVisible(True)
            self.export_button.setEnabled(False)
        else:
            self.combat_warning_label.setVisible(False)
            self.export_button.setEnabled(True)
        self.update_summary()



    def is_character_reasonable(self) -> bool:
        # Clamp values if needed
        if self.armor_class_input.value() > 20:
            self.armor_class_input.setValue(20)
        if self.initiative_input.value() > 6:
            self.initiative_input.setValue(6)
        if self.temporary_hp_input.value() > 50:
            self.temporary_hp_input.setValue(50)
        if self.spellslots_input.value() > 2:
            self.spellslots_input.setValue(2)

        # Recheck after clamping
        return (
            self.armor_class_input.value() <= 20 and
            self.initiative_input.value() <= 6 and
            self.temporary_hp_input.value() <= 50 and
            self.spellslots_input.value() <= 2
        )



    def update_spells(self):
        selected_class = self.char_class_input.currentText()
        self.spells_input.clear()
        levels = self.api_handler.get('levels')
        if not levels:
            return
        spell_names = [
            feature['name']
            for level in levels
            if level.get("class", {}).get("name") == selected_class
            for feature in level.get("features", [])
            if "spell" in feature.get("name", "").lower()
        ]
        self.spells_input.addItems(sorted(set(spell_names)) or ["(No spell-related features found)"])

    def load_languages(self):
        data = self.api_handler.get('languages')
        if data:
            self.languages_input.addItems([lang['name'] for lang in data])

    def load_races(self):
        data = self.api_handler.get('races')
        if data:
            self.races_names = [race['name'] for race in data]
            self.race_input.addItems(self.races_names)

    def load_speed(self):
        try:
            selected_race = self.races_names[self.race_input.currentIndex()].lower().replace(" ", "-")
            data = self.api_handler.get_raw(f'/api/races/{selected_race}')
            if data:
                walk_speed = data.get('speed', 0)
                bonuses = data.get('ability_bonuses', [])
                bonus = bonuses[0]['bonus'] if bonuses else 0
                self.speed_label.setText(str(walk_speed + bonus))
        except Exception as e:
            app_logger.error(f"[CharacterGUI] Error loading speed: {e}")

    def load_classes(self):
        data = self.api_handler.get('classes')
        if data:
            self.char_class_input.addItems([cls['name'] for cls in data])

    def validate_stats(self, changed_stat: str = None):
        cost_table = {
            8: 0, 9: 1, 10: 2, 11: 3, 12: 4,
            13: 5, 14: 7, 15: 9
        }
        total_cost = 0

        for stat_name, spin in self.stats_inputs.items():
            val = spin.value()
            if val > 15:
                spin.setValue(15)
                val = 15
            elif val < 8:
                spin.setValue(8)
                val = 8
            total_cost += cost_table.get(val, 0)

        # Always reset all warnings
        for label in self.stats_warnings.values():
            label.setVisible(False)

        if total_cost > 27:
            if changed_stat:
                self.stats_warnings[changed_stat].setText("Point-buy limit exceeded!")
                self.stats_warnings[changed_stat].setVisible(True)
            else:
                # Show generic warning, if desired
                app_logger.debug("[CharacterGUI] Total cost exceeds 27, but no stat specified for warning.")
            self.export_button.setEnabled(False)
                    # Still update summary and perception
            self.update_passive_perception()
            self.update_summary()
            return False
        else:
            if changed_stat:
                self.stats_warnings[changed_stat].setVisible(False)
            self.export_button.setEnabled(True)
                    # Still update summary and perception
            self.update_passive_perception()
            self.update_summary()
            return True








    # ------------------------------------------------------------------
    # Widget builders
    # ------------------------------------------------------------------

    def _build_saving_throws_widget(self):
        group = QGroupBox("Saving Throws")
        grid = QGridLayout(group)
        for i, ability in enumerate(['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']):
            cb = QCheckBox()
            lbl = QLabel(f"{ability} Save: +0")
            self.saving_throw_profs[ability] = cb
            self.saving_throw_labels[ability] = lbl
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.addWidget(cb)
            cell_layout.addWidget(lbl)
            grid.addWidget(cell, i // 2, i % 2)
        return group

    def _build_skills_widget(self):
        group = QGroupBox("Skills")
        grid = QGridLayout(group)
        for i, (skill, ability) in enumerate(SKILLS.items()):
            cb = QCheckBox()
            lbl = QLabel(f"{skill} ({ability}): +0")
            self.skill_profs[skill] = cb
            self.skill_labels[skill] = lbl
            cell = QWidget()
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.addWidget(cb)
            cell_layout.addWidget(lbl)
            grid.addWidget(cell, i // 2, i % 2)
        return group

    def _build_conditions_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.conditions_list)
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Custom")
        add_btn.clicked.connect(self._add_custom_condition)
        remove_btn = QPushButton("Remove Custom")
        remove_btn.clicked.connect(self._remove_custom_condition)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        layout.addLayout(btn_row)
        return widget

    def _add_custom_condition(self):
        text, ok = QInputDialog.getText(self, "Add Custom Condition", "Condition name:")
        if ok and text.strip():
            item = QListWidgetItem(text.strip())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.conditions_list.addItem(item)

    def _remove_custom_condition(self):
        for item in self.conditions_list.selectedItems():
            if item.text() not in DND_CONDITIONS:
                self.conditions_list.takeItem(self.conditions_list.row(item))

    # ------------------------------------------------------------------
    # Derived-value updaters
    # ------------------------------------------------------------------

    def update_class_saving_throw_profs(self):
        class_name = self.char_class_input.currentText()
        profs = CLASS_SAVING_THROW_PROFS.get(class_name, [])
        for ability, checkbox in self.saving_throw_profs.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(ability in profs)
            checkbox.blockSignals(False)
        self.update_saving_throws()

    def update_saving_throws(self):
        prof = 2
        for ability, checkbox in self.saving_throw_profs.items():
            mod = (self.stats_inputs[ability].value() - 10) // 2
            total = mod + (prof if checkbox.isChecked() else 0)
            sign = '+' if total >= 0 else ''
            self.saving_throw_labels[ability].setText(f"{ability} Save: {sign}{total}")

    def update_skills(self):
        prof = 2
        for skill, ability in SKILLS.items():
            mod = (self.stats_inputs[ability].value() - 10) // 2
            total = mod + (prof if self.skill_profs[skill].isChecked() else 0)
            sign = '+' if total >= 0 else ''
            self.skill_labels[skill].setText(f"{skill} ({ability}): {sign}{total}")

    def _get_saving_throw_values(self):
        prof = 2
        return {
            ability: (self.stats_inputs[ability].value() - 10) // 2
                     + (prof if cb.isChecked() else 0)
            for ability, cb in self.saving_throw_profs.items()
        }

    def _get_skill_values(self):
        prof = 2
        return {
            skill: (self.stats_inputs[ability].value() - 10) // 2
                   + (prof if self.skill_profs[skill].isChecked() else 0)
            for skill, ability in SKILLS.items()
        }

    def update_subclasses(self):
        selected_class = self.char_class_input.currentText()
        self.subclass_input.clear()
        subclasses = self.api_handler.get('subclasses')
        if not subclasses:
            return
        self.subclass_input.addItems([
            sub['name'] for sub in subclasses
            if sub.get('class', {}).get('name') == selected_class
        ])


if __name__ == "__main__":
    app = QApplication([])
    window = CharacterCreationWindow()
    window.show()
    app.exec_()
