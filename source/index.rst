.. DnD Editor documentation master file, created by
   sphinx-quickstart on Tue Jun 10 10:31:19 2025.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

DnD Editor documentation
========================

Add your content using ``reStructuredText`` syntax. See the
`reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
documentation for details.

.. toctree::
   :maxdepth: 2
   :caption: Introduction:

   introduction

.. toctree::
   :caption: Overviews
   :maxdepth: 2

   overview/architecture_overview
   overview/trigger_system
   overview/data_flow

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   core
   models
   registries
   data.profile.profile_manager
   ui
   ui.commands
   ui.dialogs
   ui.dialogs.trigger_editor
   ui.dialogs.tile_edit
   utils.backup
   utils.string.slugify
   versioning
   versioning.migrations
   trigger_flow
   trigger_logic_mermaid
