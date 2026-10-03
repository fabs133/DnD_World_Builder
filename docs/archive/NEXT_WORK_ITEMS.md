# DnD World Builder — Next Work Items

> Format: each bug has a root-cause analysis, the exact file/line to change,
> and a concrete code sketch. Process order: complete bugs top-to-bottom;
> each one is independent so they can be parallelised if needed.

---

## Bug 1 — Hex grid selection always renders square tiles

### Root Cause

`ui/main_window.py:305` hardcodes `self.grid_type = "square"` inside
`initialize_default_map()`, ignoring whatever the user selected in
`MainMenuDialog` (which saves `grid_type` to settings).

Compounding this, `initialize_default_map()` calls `self.init_grid(rows, cols)`
**first** (which already builds a full grid of tiles via `create_square_grid` /
`create_hex_grid`), and **then** runs a second nested loop (lines 310-329) that
creates a second, overlapping set of tiles. Two grids are drawn on top of each
other; because `grid_type` is forced to `"square"` by line 305, both layers are
always square.

### Changes Required

#### `ui/main_window.py` — `initialize_default_map()` lines 303-329

Replace the top of the method with:
```python
def initialize_default_map(self):
    self.scene.clear()
    self.grid_type = self.settings.get("grid_type", "square")   # was hardcoded "square"
    rows = self.settings.get("default_rows", 15)
    cols = self.settings.get("default_cols", 15)
    self.init_grid(rows, cols)   # init_grid already creates all tiles
    app_logger.info(f"[Grid Initialized] {self.grid_type} {rows}x{cols}")
```

Delete the entire second nested loop (old lines 310-331) — `init_grid()` dispatches
to `create_square_grid()` or `create_hex_grid()` which build the tiles. The second
loop is a leftover and causes every tile to be added twice.

---

## Bug 2 — Right-click to open Tile Attributes is undiscoverable

### Root Cause

No visual hint exists in the map editor. Users are left to stumble upon the
right-click interaction by accident.

### Changes Required

#### `ui/main_window.py` — `init_ui()` (after `layout.addWidget(self.view)`)

Add a persistent hint label directly below the canvas:
```python
hint = QLabel(
    "Tip: Right-click any tile to edit its attributes  ·  "
    "Enable Paint Mode then Left-click to paint"
)
hint.setAlignment(Qt.AlignCenter)
hint.setStyleSheet("font-size: 11px; color: gray; padding: 2px;")
layout.addWidget(hint)
```

Add a status bar message at the end of `init_ui()`:
```python
self.statusBar().showMessage(
    "Right-click a tile to edit attributes  |  Ctrl+Z Undo  |  Ctrl+Y Redo"
)
```

#### `ui/main_window.py` — `init_menu()` — add Help menu

```python
help_menu = menubar.addMenu("Help")
tutorial_action = QAction("Tutorial", self)
tutorial_action.triggered.connect(self._show_tutorial)
help_menu.addAction(tutorial_action)
```

```python
def _show_tutorial(self):
    from ui.dialogs.tutorial_dialog import TutorialDialog
    TutorialDialog(self.settings, self).exec_()
```

---

## Bug 3 — Tag checkboxes appear unselected under dark themes

### Root Cause

Under qt-material dark themes, `QCheckBox`'s checked indicator is a dark SVG
rendered against a dark background — effectively invisible. The data is saved
correctly; only the visual feedback is broken.

### Changes Required

#### `ui/dialogs/tile_dialog.py` — `__init__()` tag loop (~lines 101-105)

After creating each checkbox, apply an explicit stylesheet:
```python
for tag in TileTag:
    cb = QCheckBox(tag.name.replace("_", " ").title())
    cb.setChecked(tag in tile_data.tags)
    cb.setStyleSheet("""
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #888;
            border-radius: 3px;
            background: transparent;
        }
        QCheckBox::indicator:checked {
            background-color: #6d4c9e;
            border-color: #c084fc;
        }
    """)
    self.tag_checkboxes[tag] = cb
    tag_layout.addWidget(cb)
```

The checked state fills the indicator box in the accent purple so it is clearly
distinguishable regardless of the dark theme background.

#### `ui/dialogs/tile_dialog.py` — `save_attributes()` (end of method, before `self.accept()`)

Force the tile graphic to repaint so any future tag-driven visuals (e.g., TRAP_ZONE
tint) refresh immediately after saving:
```python
if self.tile_item:
    self.tile_item.update()
```

---

## Bug 4 — Trigger editor: nodes overlap + "Save Trigger" appears twice

### Problem A — Nodes overlap when multiple triggers share a BFS column

`build_graph()` in `graph_view.py` places every node at `y=20` regardless of
how many triggers map to the same column. Two independent chain roots both land
in column 0 and render on top of each other.

### Fix A — `ui/dialogs/trigger_editor/graph_view.py` — `build_graph()`

Track a per-column row counter and stack nodes vertically. Replace the node
placement loop:

```python
col_map = self._assign_columns(context.triggers)
col_row_counter = {}   # col -> next available row index within that column

for trigger in context.triggers:
    col = col_map.get(trigger.label, 0)
    row_in_col = col_row_counter.get(col, 0)
    col_row_counter[col] = row_in_col + 1

    x = col * COLUMN_WIDTH
    y = 40 + row_in_col * 120   # 100 node height + 20 px gap
    node_item = TriggerNodeItem(trigger, x, y)
    self.scene.addItem(node_item)
    self.node_items.append(node_item)
    app_logger.debug(f"Node '{trigger.label}' col={col} row={row_in_col} → ({x},{y})")
```

Update the scene rect to use the new max height:
```python
max_rows   = max(col_row_counter.values(), default=1)
total_height = 40 + max_rows * 120 + 40
num_cols   = max(col_map.values(), default=0) + 1 if col_map else 1
total_width  = num_cols * COLUMN_WIDTH + 100
self.scene.setSceneRect(0, -40, total_width, total_height)
```

### Problem B — "Save Trigger" button appears twice

`TriggerPropertyEditor.__init__()` at `property_editor.py:67-75` adds its own
"Save Trigger" + "Cancel" row. `TriggerEditorDialog` also provides "Save Trigger"
in its bottom bar. The internal button calls `save_trigger()` without notifying
the dialog to refresh the graph or list.

### Fix B — `ui/dialogs/trigger_editor/property_editor.py` — `__init__()`

Delete the internal button row:
```python
# REMOVE the following block (lines 67-75):
# btns = QHBoxLayout()
# self.save_btn = QPushButton("Save Trigger")
# self.cancel_btn = QPushButton("Cancel")
# btns.addWidget(self.save_btn)
# btns.addWidget(self.cancel_btn)
# layout.addLayout(btns)
# self.save_btn.clicked.connect(self.save_trigger)
```

The dialog's "Save Trigger" button already calls `property_editor.save_trigger()`
followed by `graph_view.refresh()` and `list_view.set_context()`.

Any test that references `property_editor.save_btn` must also be updated to call
`save_trigger()` directly.

---

## Bug 5 — Stat Block: text obscured by dark background; name has white bar

### Root Cause

Two separate issues:

**A — Document body inherits qt-material dark background.**
`setHtml()` is given a bare `<style>` block + div content with no
`<html><head><body>` wrapper. Qt's renderer applies the application palette's
`base` colour (often very dark under qt-material) to the document body,
showing through wherever the `.stat-block` div does not fill the full browser
area (e.g., below short content, or when the div background differs from the
browser background).

**B — White bar behind `<h1>`.**
Qt's HTML renderer applies `background-color: palette(base)` — often **white**
in light palette base — to heading elements by default unless overridden. The
CSS only sets `.header h1 { color: ... }` with no `background-color`, so the
`<h1>` inherits the browser's white base colour, producing a white rectangle
behind the entity name.

### Changes Required

#### `ui/dialogs/stat_block_dialog.py` — `__init__()` (after creating `self.browser`)

Set the widget's own background to match the stat block colour so the area
outside the HTML div matches:
```python
from core import theme_palette as tp
self.browser.setStyleSheet(
    f"background-color: {tp.get('stat_bg')}; border: none;"
)
self.browser.setHtml(self._build_html())
```

#### `ui/dialogs/stat_block_dialog.py` — `_build_html()` lines 39-73

Wrap all content in a proper HTML document with an explicit body background:
```python
def _build_html(self):
    from core import theme_palette as tp
    bg = tp.get("stat_bg")
    css_block = self._css()
    e = self.entity

    parts = [
        f'<html><head>{css_block}</head>',
        f'<body style="margin:0;padding:0;background-color:{bg};">',
        '<div class="stat-block">',
    ]
    # ... all existing _header_section, _core_stats_section, etc. calls ...
    parts.append('</div></body></html>')
    return "\n".join(parts)
```

#### `ui/dialogs/stat_block_dialog.py` — `_css()` — `.header h1` rule (~line 321)

Add `background-color: transparent` to kill Qt's default white heading
background:
```python
.header h1 {{
    margin: 0;
    font-size: 22px;
    color: {header};
    background-color: transparent;
    font-variant: small-caps;
}}
```

---

## Scope / Order

```
[ ] Bug 1: main_window.py — fix hardcoded grid_type + remove double tile loop
[ ] Bug 2: main_window.py — hint label, status bar, Help > Tutorial menu
[ ] Bug 3: tile_dialog.py — explicit checkbox stylesheet + tile_item.update()
[ ] Bug 4a: graph_view.py — vertical stacking for same-column nodes
[ ] Bug 4b: property_editor.py — remove duplicate internal Save Trigger row
[ ] Bug 5: stat_block_dialog.py — HTML wrapper + browser stylesheet + h1 bg fix
[ ] Run tests
```

---

## Key File Reference

| File | Bug | Key location |
|---|---|---|
| `ui/main_window.py` | 1, 2 | `initialize_default_map()` line 298; `init_ui()` line 81; `init_menu()` line 111 |
| `ui/dialogs/tile_dialog.py` | 3 | tag checkbox loop ~line 101; `save_attributes()` line 208 |
| `ui/dialogs/trigger_editor/graph_view.py` | 4a | `build_graph()` node-placement loop |
| `ui/dialogs/trigger_editor/property_editor.py` | 4b | `__init__()` button row lines 67-75 |
| `ui/dialogs/stat_block_dialog.py` | 5 | `__init__()` line 30; `_build_html()` line 39; `_css()` `.header h1` rule ~line 321 |
