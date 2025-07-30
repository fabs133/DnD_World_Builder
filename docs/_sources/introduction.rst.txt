DnD Project Overview
====================

Welcome to the **DnD Project** — a powerful, modular scenario builder for grid-based Dungeons & Dragons 5e encounters. This tool is designed to empower Dungeon Masters to craft, simulate, and export tactical combat maps and in-game logic, all through an intuitive visual interface.

Purpose
-------

This project helps you:

- Build interactive tactical maps in minutes.
- Place monsters, NPCs, traps, and more using a grid editor.
- Define interactive game logic via triggers and conditions.
- Save and export entire scenarios as bundles for easy sharing.

The goal is to make complex encounters *easy to build* and *fun to run*, even for non-technical users.

Key Features
------------

- 🗺️ **Visual Map Editor**  
  Build square or hex grid maps with tile overlays, terrain tags, and embedded entities.

- ⚙️ **Trigger System**  
  Add modular logic using triggers: define when things happen and how entities react.

- 🧙 **Entity Manager**  
  Easily manage and import characters, monsters, and traps from a rulebook API.

- 🔁 **Turn-Based Logic Engine**  
  Schedule delayed effects and apply cooldowns using an integrated turn manager.

- 💾 **Auto Save, Backup & Export**  
  Never lose work. Save sessions and export scenarios as `.zip` bundles with assets included.

- 🖼️ **PyQt GUI with Editor Chooser**  
  Launch the app and choose between scenario types or editors with a single click.

Audience
--------

This tool is built for:

- **Game Masters (non-programmers)**  
  You don’t need to touch code. Just click, place, and build.

- **Tinkerers & Devs**  
  Want more? Extend the system with new conditions, reactions, entities, and UI logic.

Launch Instructions
-------------------

A single executable (`DnDProject.exe` or similar) is provided. Launch it to:

1. Open the application.
2. Choose the type of map or scenario you want to create.
3. Use the intuitive interface to build, edit, and export your encounter.

No technical knowledge required. No setup scripts, no terminal — just double-click.

Advanced Users
--------------

For those interested in development or customization:

- All trigger logic is pluggable via Python registries.
- Conditions and reactions are introspectable and serializable.
- Maps and scenarios are stored in readable JSON.
- The UI auto-adapts to new logic components through reflection.

Related Pages
-------------

- :doc:`System Architecture <overview/architecture_overview>`
- :doc:`Trigger System <overview/trigger_system>`
- :doc:`Runtime Data Flow <overview/data_flow>`

