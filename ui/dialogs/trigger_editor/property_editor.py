# trigger_editor/property_editor.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QComboBox,
    QPushButton, QLabel, QHBoxLayout, QLineEdit, QSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt
from registries.condition_registry import condition_registry
from registries.reaction_registry import reaction_registry
from core.gameCreation.trigger import Trigger
from core.logger import app_logger
import inspect
import uuid
import copy

class TriggerPropertyEditor(QWidget):
    """
    Widget for editing the properties of a Trigger object.

    Allows selection and configuration of event type, condition, reaction,
    and next trigger, as well as saving changes to the context.
    """
    def __init__(self):
        """
        Initialize the TriggerPropertyEditor widget.
        """
        super().__init__()
        self.trigger = None
        self.context = None
        self.condition_params = {}
        self.reaction_params = {}

        layout = QVBoxLayout(self)

        # --- Static fields ---
        form = QFormLayout()
        self.event_type_input = QComboBox()
        self.event_type_input.addItems([
            "ENTER_TILE", "PLAYER_IN_RANGE", "TURN_START", "ON_DAMAGE", "CUSTOM"
        ])
        form.addRow("Event Type:", self.event_type_input)
        self.event_type_input.setCurrentIndex(0)

        self.next_trigger_input = QComboBox()
        self.next_trigger_input.addItem("None")  # default unlinked
        form.addRow("Next Trigger:", self.next_trigger_input)

        self.condition_input = QComboBox()
        self.condition_input.addItems(condition_registry.list_keys())
        form.addRow("Condition:", self.condition_input)
        self.condition_input.currentTextChanged.connect(self.update_condition_fields)

        self.reaction_input = QComboBox()
        self.reaction_input.addItems(reaction_registry.list_keys())
        form.addRow("Reaction:", self.reaction_input)
        self.reaction_input.currentTextChanged.connect(self.on_reaction_changed)

        layout.addLayout(form)

        # --- Dynamic fields ---
        self.condition_param_layout = QFormLayout()
        layout.addLayout(self.condition_param_layout)

        self.reaction_param_layout = QFormLayout()
        layout.addLayout(self.reaction_param_layout)

        # --- Buttons ---
        btns = QHBoxLayout()
        self.save_btn = QPushButton("Save Trigger")
        self.cancel_btn = QPushButton("Cancel")
        btns.addWidget(self.save_btn)
        btns.addWidget(self.cancel_btn)
        layout.addLayout(btns)

        self.save_btn.clicked.connect(self.save_trigger)

    def update_condition_fields(self, name):
        """
        Update the condition parameter fields based on the selected condition.

        :param name: Name of the selected condition class.
        :type name: str
        """
        cls = condition_registry.get_class(name)
        if cls:
            self.build_condition_fields(cls)

    def on_reaction_changed(self, reaction_name):
        """
        Update the reaction parameter fields based on the selected reaction.

        :param reaction_name: Name of the selected reaction class.
        :type reaction_name: str
        """
        cls = reaction_registry.get_class(reaction_name)
        if cls:
            self.build_reaction_fields(cls)

    def build_condition_fields(self, condition_cls):
        """
        Build and display input fields for the parameters of the given condition class.

        :param condition_cls: The condition class to inspect.
        :type condition_cls: type
        """
        # Clear old inputs
        for i in reversed(range(self.condition_param_layout.count())):
            widget = self.condition_param_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()

        self.condition_params = {}

        # Inspect the signature of the condition class' constructor
        sig = inspect.signature(condition_cls.__init__)

        # Check if there are any parameters other than 'self', 'args', or 'kwargs'
        parameters = [
            param for param in sig.parameters.values()
            if param.name not in ('self', 'args', 'kwargs')
        ]

        # If there are no parameters (besides 'self', 'args', and 'kwargs'), don't add any fields
        if not parameters:
            return  # Exit if no parameters to show

        # Iterate over parameters and create widgets for each
        for param in parameters:
            # Create widget based on parameter type
            if param.annotation == int:
                widget = QSpinBox()
            else:
                widget = QLineEdit()

            # Align the label to the right
            label = QLabel(param.name)
            label.setAlignment(Qt.AlignRight)

            # Add widget and label to the layout
            self.condition_params[param.name] = widget
            self.condition_param_layout.addRow(label, widget)

        # Force layout update
        self.condition_param_layout.update()

    def build_reaction_fields(self, reaction_cls):
        """
        Build and display input fields for the parameters of the given reaction class.

        :param reaction_cls: The reaction class to inspect.
        :type reaction_cls: type
        """
        # Clear previous widgets
        for i in reversed(range(self.reaction_param_layout.count())):
            widget = self.reaction_param_layout.takeAt(i).widget()
            if widget:
                widget.deleteLater()

        self.reaction_params = {}

        sig = inspect.signature(reaction_cls.__init__)
        for name, param in sig.parameters.items():
            if name == 'self':
                continue

            # Create widget based on parameter type
            if param.annotation == int:
                widget = QSpinBox()
            else:
                widget = QLineEdit()

            # Align the label to the right
            label = QLabel(name)
            label.setAlignment(Qt.AlignRight)

            self.reaction_params[name] = widget
            self.reaction_param_layout.addRow(label, widget)  # Add widget with label

        self.reaction_param_layout.update()  # Force layout update

    def set_trigger(self, trigger=None):
        """
        Set the trigger to be edited.

        :param trigger: The Trigger object to edit, or None to clear.
        :type trigger: Trigger or None
        """
        if trigger is not None:
            self.trigger = copy.deepcopy(trigger)
        else:
            self.trigger = None

        self.refresh_next_trigger_choices()

        if self.trigger:
            self.event_type_input.setCurrentText(self.trigger.event_type)
            self.condition_input.setCurrentText(self.trigger.condition.__class__.__name__)
            self.reaction_input.setCurrentText(self.trigger.reaction.__class__.__name__)

            self.update_condition_fields(self.trigger.condition.__class__.__name__)
            self.build_reaction_fields(type(self.trigger.reaction))

            if hasattr(self.trigger, "next_trigger") and self.trigger.next_trigger:
                idx = self.next_trigger_input.findText(self.trigger.next_trigger)
                if idx != -1:
                    self.next_trigger_input.setCurrentIndex(idx)
        else:
            self.event_type_input.setCurrentIndex(0)
            self.condition_input.setCurrentIndex(0)
            self.reaction_input.setCurrentIndex(0)

            self.update_condition_fields(self.condition_input.currentText())
            reaction_cls = reaction_registry.get_class(self.reaction_input.currentText())
            if reaction_cls:
                self.build_reaction_fields(reaction_cls)

        if self.next_trigger_input.count() == 0:
            self.next_trigger_input.addItem("None")

    def save_trigger(self):
        """
        Save the current trigger configuration to the context.
        """
        from core.gameCreation.trigger import Trigger

        condition_name = self.condition_input.currentText()
        reaction_name = self.reaction_input.currentText()
        event_type = self.event_type_input.currentText()

        condition_cls = condition_registry.get_class(condition_name)
        reaction_cls = reaction_registry.get_class(reaction_name)

        condition_args = {
            name: widget.value() if hasattr(widget, "value") else widget.text()
            for name, widget in self.condition_params.items()
        }
        reaction_args = {
            name: widget.value() if hasattr(widget, "value") else widget.text()
            for name, widget in self.reaction_params.items()
        }

        try:
            condition = condition_cls(**condition_args)
            reaction = reaction_cls(**reaction_args)
        except Exception as e:
            QMessageBox.critical(self, "Trigger Creation Failed", f"Error: {e}")
            return

        next_label = self.next_trigger_input.currentText()
        if next_label == "None":
            next_label = None

        # 🧠 Use existing label if editing
        if self.trigger and self.trigger.label:
            label = self.trigger.label
        else:
            unique_id = uuid.uuid4().hex[:6].upper()
            label = f"{event_type}:{reaction_name}:{unique_id}"

        app_logger.debug(f"Creating trigger with label: {label}")

        new_trigger = Trigger(
            event_type=event_type,
            condition=condition,
            reaction=reaction,
            label=label,
            source=getattr(self.context, "name", "Unknown"),
            flags={},
        )
        new_trigger.next_trigger = next_label

        # 🔁 Replace existing trigger in context, if editing
        if hasattr(self.context, "triggers"):
            if self.trigger:
                for i, existing in enumerate(self.context.triggers):
                    if existing.label == self.trigger.label:
                        app_logger.debug(f"Replacing trigger at index {i}")
                        self.context.triggers[i] = new_trigger
                        break
                else:
                    app_logger.debug("Trigger not found; appending new one.")
                    self.context.triggers.append(new_trigger)
            else:
                self.context.triggers.append(new_trigger)
        else:
            app_logger.warning("Context has no triggers list.")

        # 🔄 Call register_trigger if it's needed elsewhere
        if hasattr(self.context, "register_trigger"):
            self.context.register_trigger(new_trigger)

        # Update the graph view
        self.parent().set_context(self.context)
        self.parent().setCurrentWidget(self.parent().graph_view)

    def set_context(self, context):
        """
        Set the context object that contains triggers.

        :param context: The context object (should have a 'triggers' attribute).
        :type context: object
        """
        self.context = context
        app_logger.debug(f"Context set: {context}")
        # Clear dropdown before repopulating
        self.next_trigger_input.clear()
        self.next_trigger_input.addItem("None")

        if hasattr(context, "triggers"):
            current_label = getattr(self.trigger, "label", None)

            for trig in context.triggers:
                app_logger.debug(f"Candidate: {trig.label}, Current: {current_label}")
                if trig.label != current_label:
                    self.next_trigger_input.addItem(trig.label)

    def clear_inputs(self):
        """
        Clear all input fields and reset to defaults.
        """
        self.event_type_input.setCurrentIndex(0)
        self.condition_input.setCurrentIndex(0)
        self.reaction_input.setCurrentIndex(0)
        self.next_trigger_input.setCurrentIndex(0)

        # Clear and rebuild fields
        self.condition_params.clear()
        self.reaction_params.clear()

        for layout in (self.condition_param_layout, self.reaction_param_layout):
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

    def set_defaults(self):
        """
        Reset the editor to default state, clearing all fields and rebuilding parameter inputs.
        """
        self.set_context(self.context)  # keep existing context if available
        self.clear_inputs()
        self.set_trigger(None)

        # Rebuild default condition/reaction input fields
        self.update_condition_fields(self.condition_input.currentText())
        reaction_cls = reaction_registry.get_class(self.reaction_input.currentText())
        if reaction_cls:
            self.build_reaction_fields(reaction_cls)
    
    def refresh_next_trigger_choices(self):
        """
        Refresh the list of available next triggers in the dropdown.
        """
        self.next_trigger_input.clear()
        self.next_trigger_input.addItem("None")

        if hasattr(self.context, "triggers"):
            for t in self.context.triggers:
                if t != self.trigger:
                    self.next_trigger_input.addItem(t.label)
