# -*- coding: utf-8 -*-
#   Mozo Menu Editor - Simple fd.o Compliant Menu Editor
#   Copyright (C) 2006  Travis Watkins
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Library General Public
#   License as published by the Free Software Foundation; either
#   version 2 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Library General Public License for more details.
#
#   You should have received a copy of the GNU Library General Public
#   License along with this library; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('MateMenu', '2.0')
from gi.repository import GLib, Gio
from gi.repository import Gtk, Gdk, GdkPixbuf
from gi.repository import MateMenu
import html
import os
import gettext
import subprocess
import shutil
import urllib.parse
try:
    from Mozo import config
    gettext.bindtextdomain(config.GETTEXT_PACKAGE,config.localedir)
    gettext.textdomain(config.GETTEXT_PACKAGE)
    GETTEXT_PACKAGE = config.GETTEXT_PACKAGE
except:
    GETTEXT_PACKAGE = "mozo"
_ = gettext.gettext
from Mozo.MenuEditor import MenuEditor
from Mozo import util

class MainWindow:
    #hack to make editing menu properties work
    allow_update = True
    #drag-and-drop stuff
    dnd_items = [('MOZO_ITEM_ROW', Gtk.TargetFlags.SAME_APP, 0), ('text/plain', 0, 1)]
    dnd_menus = [('MOZO_MENU_ROW', Gtk.TargetFlags.SAME_APP, 0)]
    dnd_both = [dnd_items[0],] + dnd_menus
    drag_data = None
    edit_pool = []

    def __init__(self, datadir, version, argv):
        self.file_path = datadir
        self.version = version
        Gtk.Window.set_default_icon_name('mozo')
        self.tree = Gtk.Builder()
        self.tree.set_translation_domain(GETTEXT_PACKAGE)
        self.tree.add_from_file(os.path.join(self.file_path, 'mozo.ui'))
        self.editor = MenuEditor(undo_button=self.tree.get_object('undo_button'),
                                 redo_button=self.tree.get_object('redo_button'))
        self.tree.connect_signals(self)
        self.setupMenuTree()
        self.setupItemTree()
        self.tree.get_object('edit_delete').set_sensitive(False)
        self.tree.get_object('edit_revert_to_original').set_sensitive(False)
        self.tree.get_object('edit_properties').set_sensitive(False)
        self.tree.get_object('move_up_button').set_sensitive(False)
        self.tree.get_object('move_down_button').set_sensitive(False)
        self.tree.get_object('new_separator_button').set_sensitive(False)
        self.tree.get_object('properties_button').set_sensitive(False)
        self.tree.get_object('delete_button').set_sensitive(False)
        accelgroup = Gtk.AccelGroup()
        keyval, modifier = Gtk.accelerator_parse('<Ctrl>Z')
        accelgroup.connect(keyval, modifier, Gtk.AccelFlags.VISIBLE, self.on_mainwindow_undo)
        keyval, modifier = Gtk.accelerator_parse('<Ctrl><Shift>Z')
        accelgroup.connect(keyval, modifier, Gtk.AccelFlags.VISIBLE, self.on_mainwindow_redo)
        keyval, modifier = Gtk.accelerator_parse('F1')
        accelgroup.connect(keyval, modifier, Gtk.AccelFlags.VISIBLE, self.on_help_button_clicked)
        self.tree.get_object('mainwindow').add_accel_group(accelgroup)
        self.main_window = self.tree.get_object('mainwindow')

    def run(self):
        self.loadMenus()
        self.editor.applications.tree.connect("changed", self.menuChanged)
        self.editor.settings.tree.connect("changed", self.menuChanged)
        self.tree.get_object('mainwindow').show_all()
        Gtk.main()

    def menuChanged(self, *a):
        self.loadUpdates()

    def loadUpdates(self):
        if not self.allow_update:
            return False
        menu_tree = self.tree.get_object('menu_tree')
        item_tree = self.tree.get_object('item_tree')
        items, iter = item_tree.get_selection().get_selected()
        update_items = False
        update_type = None
        item_id = None
        if iter and items[iter][3].get_desktop_file_path():
            update_items = True
            if isinstance(items[iter][3], MateMenu.TreeDirectory):
                item_id = os.path.split(items[iter][3].get_desktop_file_path())[1]
                update_type = MateMenu.TreeItemType.DIRECTORY
            elif isinstance(items[iter][3], MateMenu.TreeEntry):
                item_id = items[iter][3].get_desktop_file_id()
                update_type = MateMenu.TreeItemType.ENTRY
            elif isinstance(items[iter][3], MateMenu.TreeSeparator):
                item_id = items.get_path(iter)
                update_type = MateMenu.TreeItemType.SEPARATOR
        menus, iter = menu_tree.get_selection().get_selected()
        update_menus = False
        menu_id = None
        if iter:
            if menus[iter][2].get_desktop_file_path():
                menu_id = os.path.split(menus[iter][2].get_desktop_file_path())[1]
            else:
                menu_id = menus[iter][2].get_menu_id()
            update_menus = True
        self.loadMenus()
        #find current menu in new tree
        if update_menus:
            menu_tree.get_model().foreach(self.findMenu, menu_id)
            menus, iter = menu_tree.get_selection().get_selected()
            if iter:
                self.on_menu_tree_cursor_changed(menu_tree)
        #find current item in new list
        if update_items:
            i = 0
            for item in item_tree.get_model():
                found = False
                if update_type != MateMenu.TreeItemType.SEPARATOR:
                    if isinstance (item[3], MateMenu.TreeEntry) and item[3].get_desktop_file_id() == item_id:
                        found = True
                    if isinstance (item[3], MateMenu.TreeDirectory) and item[3].get_desktop_file_path() and update_type == MateMenu.TreeItemType.DIRECTORY:
                        if os.path.split(item[3].get_desktop_file_path())[1] == item_id:
                            found = True
                if isinstance(item[3], MateMenu.TreeSeparator):
                    if not isinstance(item_id, tuple):
                        #we may not skip the increment via "continue"
                        i += 1
                        continue
                    #separators have no id, have to find them manually
                    #probably won't work with two separators together
                    if (item_id[0] - 1,) == (i,):
                        found = True
                    elif (item_id[0] + 1,) == (i,):
                        found = True
                    elif (item_id[0],) == (i,):
                        found = True
                if found:
                    item_tree.get_selection().select_path((i,))
                    self.on_item_tree_cursor_changed(item_tree)
                    break
                i += 1
        return False

    def findMenu(self, menus, path, iter, menu_id):
        if not menus[path][2].get_desktop_file_path():
            if menu_id == menus[path][2].get_menu_id():
                menu_tree = self.tree.get_object('menu_tree')
                menu_tree.expand_to_path(path)
                menu_tree.get_selection().select_path(path)
                return True
            return False
        if os.path.split(menus[path][2].get_desktop_file_path())[1] == menu_id:
            menu_tree = self.tree.get_object('menu_tree')
            menu_tree.expand_to_path(path)
            menu_tree.get_selection().select_path(path)
            return True

    def setupMenuTree(self):
        self.menu_store = Gtk.TreeStore(GdkPixbuf.Pixbuf, str, object)
        menus = self.tree.get_object('menu_tree')
        column = Gtk.TreeViewColumn(_('Name'))
        column.set_spacing(4)
        cell = Gtk.CellRendererPixbuf()
        column.pack_start(cell, False)
        column.add_attribute(cell, 'pixbuf', 0)
        cell = Gtk.CellRendererText()
        cell.set_fixed_size(-1, 25)
        column.pack_start(cell, True)
        column.add_attribute(cell, 'markup', 1)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        menus.append_column(column)
        menus.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, self.dnd_menus, Gdk.DragAction.MOVE)
        menus.enable_model_drag_dest(self.dnd_both, Gdk.DragAction.PRIVATE)
        menus.get_selection().set_mode(Gtk.SelectionMode.BROWSE)

    def setupItemTree(self):
        items = self.tree.get_object('item_tree')
        column = Gtk.TreeViewColumn(_('Show'))
        cell = Gtk.CellRendererToggle()
        cell.connect('toggled', self.on_item_tree_show_toggled)
        column.pack_start(cell, True)
        column.add_attribute(cell, 'active', 0)
        #hide toggle for separators
        column.set_cell_data_func(cell, self._cell_data_toggle_func)
        items.append_column(column)
        column = Gtk.TreeViewColumn(_('Item'))
        column.set_spacing(4)
        cell = Gtk.CellRendererPixbuf()
        column.pack_start(cell, False)
        column.add_attribute(cell, 'pixbuf', 1)
        cell = Gtk.CellRendererText()
        cell.set_fixed_size(-1, 25)
        column.pack_start(cell, True)
        column.add_attribute(cell, 'markup', 2)
        items.append_column(column)
        self.item_store = Gtk.ListStore(bool, GdkPixbuf.Pixbuf, str, object)
        items.set_model(self.item_store)
        items.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, self.dnd_items, Gdk.DragAction.MOVE)
        items.enable_model_drag_dest(self.dnd_items, Gdk.DragAction.PRIVATE)

    def _cell_data_toggle_func(self, tree_column, renderer, model, treeiter, data=None):
        if isinstance(model[treeiter][3], MateMenu.TreeSeparator):
            renderer.set_property('visible', False)
        else:
            renderer.set_property('visible', True)

    def loadMenus(self):
        self.menu_store.clear()
        for menu in self.editor.getMenus():
            iters = [None]*20
            self.loadMenu(iters, menu)
        menu_tree = self.tree.get_object('menu_tree')
        menu_tree.set_model(self.menu_store)
        for menu in self.menu_store:
            #this might not work for some reason
            try:
                menu_tree.expand_to_path(menu.path)
            except:
                pass
        menu_tree.get_selection().select_path((0,))
        self.on_menu_tree_cursor_changed(menu_tree)

    def loadMenu(self, iters, parent, depth=0):
        if depth == 0:
            icon = util.getIcon(parent)
            iters[depth] = self.menu_store.append(None, (icon, html.escape(parent.get_name()), parent))
        depth += 1
        for menu, show in self.editor.getMenus(parent):
            if show:
                name = html.escape(menu.get_name())
            else:
                name = '<small><i>' + html.escape(menu.get_name()) + '</i></small>'
            icon = util.getIcon(menu)
            iters[depth] = self.menu_store.append(iters[depth-1], (icon, name, menu))
            self.loadMenu(iters, menu, depth)
        depth -= 1

    def loadItems(self, menu, menu_path):
        self.item_store.clear()
        for item, show in self.editor.getItems(menu):
            icon = util.getIcon(item)
            if isinstance(item, MateMenu.TreeSeparator):
                name = '---'
            elif isinstance(item, MateMenu.TreeEntry):
                if show:
                    name = html.escape(item.get_app_info().get_display_name())
                else:
                    name = '<small><i>' + html.escape(item.get_app_info().get_display_name()) + '</i></small>'
            else:
                if show:
                    name = html.escape(item.get_name())
                else:
                    name = '<small><i>' + html.escape(item.get_name()) + '</i></small>'
            self.item_store.append((show, icon, name, item))

    #this is a little timeout callback to insert new items after
    #mate-desktop-item-edit has finished running
    def waitForNewItemProcess(self, process, parent_id, file_path):
        if process.poll() is not None:
            if os.path.isfile(file_path):
                self.editor.insertExternalItem(os.path.split(file_path)[1], parent_id)
            return False
        return True

    def waitForNewMenuProcess(self, process, parent_id, file_path):
        if process.poll() is not None:
            #hack for broken mate-desktop-item-edit
            broken_path = os.path.join(os.path.split(file_path)[0], '.directory')
            if os.path.isfile(broken_path):
                os.rename(broken_path, file_path)
            if os.path.isfile(file_path):
                self.editor.insertExternalMenu(os.path.split(file_path)[1], parent_id)
            return False
        return True

    #this callback keeps you from editing the same item twice
    def waitForEditProcess(self, process, file_path):
        if process.poll() is not None:
            self.edit_pool.remove(file_path)
            return False
        return True

    def on_delete_event(self, widget, event):
        self.quit()

    def on_new_menu_button_clicked(self, button):
        menu_tree = self.tree.get_object('menu_tree')
        menus, iter = menu_tree.get_selection().get_selected()
        if not iter:
            parent = menus[(0,)][2]
            menu_tree.expand_to_path((0,))
            menu_tree.get_selection().select_path((0,))
        else:
            parent = menus[iter][2]
        file_path = os.path.join(util.getUserDirectoryPath(), util.getUniqueFileId('mozo-made', '.directory'))
        process = subprocess.Popen(['mate-desktop-item-edit', file_path], env=os.environ)
        GLib.timeout_add(100, self.waitForNewMenuProcess, process, parent.get_menu_id(), file_path)

    def on_new_item_button_clicked(self, button):
        menu_tree = self.tree.get_object('menu_tree')
        menus, iter = menu_tree.get_selection().get_selected()
        if not iter:
            parent = menus[(0,)][2]
            menu_tree.expand_to_path((0,))
            menu_tree.get_selection().select_path((0,))
        else:
            parent = menus[iter][2]
        file_path = os.path.join(util.getUserItemPath(), util.getUniqueFileId('mozo-made', '.desktop'))
        process = subprocess.Popen(['mate-desktop-item-edit', file_path], env=os.environ)
        GLib.timeout_add(100, self.waitForNewItemProcess, process, parent.get_menu_id(), file_path)

    def on_new_separator_button_clicked(self, button):
        item_tree = self.tree.get_object('item_tree')
        items, iter = item_tree.get_selection().get_selected()
        if not iter:
            return
        else:
            after = items[iter][3]
            menu_tree = self.tree.get_object('menu_tree')
            menus, iter = menu_tree.get_selection().get_selected()
            parent = menus[iter][2]
            self.editor.createSeparator(parent, after=after)

    def on_edit_delete_activate(self, menu):
        item_tree = self.tree.get_object('item_tree')
        items, iter = item_tree.get_selection().get_selected()
        if not iter:
            return
        item = items[iter][3]
        if isinstance(item, MateMenu.TreeEntry):
            self.editor.deleteItem(item)
        elif isinstance(item, MateMenu.TreeDirectory):
            self.editor.deleteMenu(item)
        elif isinstance(item, MateMenu.TreeSeparator):
            self.editor.deleteSeparator(item)

    def on_edit_revert_to_original_activate(self, menu):
        item_tree = self.tree.get_object('item_tree')
        items, iter = item_tree.get_selection().get_selected()
        if not iter:
            return
        item = items[iter][3]
        if isinstance(item, MateMenu.TreeEntry):
            self.editor.revertItem(item)
        elif isinstance(item, MateMenu.TreeDirectory):
            self.editor.revertMenu(item)

    def on_edit_properties_activate(self, menu):
        item_tree = self.tree.get_object('item_tree')
        items, iter = item_tree.get_selection().get_selected()
        if not iter:
            return
        item = items[iter][3]
        if not isinstance(item, MateMenu.TreeEntry) and not isinstance(item, MateMenu.TreeDirectory):
            return

        if isinstance(item, MateMenu.TreeEntry):
            file_path = os.path.join(util.getUserItemPath(), item.get_desktop_file_id())
            file_type = 'Item'
        elif isinstance(item, MateMenu.TreeDirectory):
            file_path = os.path.join(util.getUserDirectoryPath(), os.path.split(item.get_desktop_file_path())[1])
            file_type = 'Menu'

        if not os.path.isfile(file_path):
            shutil.copy(item.get_desktop_file_path(), file_path)
            self.editor._MenuEditor__addUndo([(file_type, os.path.split(file_path)[1]),])
        else:
            self.editor._MenuEditor__addUndo([item,])
        if file_path not in self.edit_pool:
            self.edit_pool.append(file_path)
            process = subprocess.Popen(['mate-desktop-item-edit', file_path], env=os.environ)
            GLib.timeout_add(100, self.waitForEditProcess, process, file_path)

    def on_menu_tree_cursor_changed(self, treeview):
        selection = treeview.get_selection()
        if selection is None:
            return
        menus, iter = selection.get_selected()
        if iter is None:
            return
        menu_path = menus.get_path(iter)
        item_tree = self.tree.get_object('item_tree')
        item_tree.get_selection().unselect_all()
        self.loadItems(self.menu_store[menu_path][2], menu_path)
        self.tree.get_object('edit_delete').set_sensitive(False)
        self.tree.get_object('edit_revert_to_original').set_sensitive(False)
        self.tree.get_object('edit_properties').set_sensitive(False)
        self.tree.get_object('move_up_button').set_sensitive(False)
        self.tree.get_object('move_down_button').set_sensitive(False)
        self.tree.get_object('new_separator_button').set_sensitive(False)
        self.tree.get_object('properties_button').set_sensitive(False)
        self.tree.get_object('delete_button').set_sensitive(False)

    def on_menu_tree_drag_data_get(self, treeview, context, selection, target_id, etime):
        menus, iter = treeview.get_selection().get_selected()
        self.drag_data = menus[iter][2]

    def on_menu_tree_drag_data_received(self, treeview, context, x, y, selection, info, etime):
        menus = treeview.get_model()
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            types = (Gtk.TreeViewDropPosition.INTO_OR_BEFORE, Gtk.TreeViewDropPosition.INTO_OR_AFTER)
            if position not in types:
                context.finish(False, False, etime)
                return False
            if str(selection.get_target()) in ('MOZO_ITEM_ROW', 'MOZO_MENU_ROW'):
                if self.drag_data is None:
                    return False
                item = self.drag_data
                new_parent = menus[path][2]
                if isinstance(item, MateMenu.TreeEntry):
                    self.editor.moveItem(item, new_parent)
                elif isinstance(item, MateMenu.TreeDirectory):
                    if not self.editor.moveMenu(item, new_parent):
                        self.loadUpdates()
                elif isinstance(item, MateMenu.TreeSeparator):
                    self.editor.moveSeparator(item, new_parent)
                else:
                    context.finish(False, False, etime)
                context.finish(True, True, etime)
        self.drag_data = None

    def on_item_tree_show_toggled(self, cell, path):
        item = self.item_store[path][3]
        if isinstance(item, MateMenu.TreeSeparator):
            return
        if self.item_store[path][0]:
            self.editor.setVisible(item, False)
        else:
            self.editor.setVisible(item, True)
        self.item_store[path][0] = not self.item_store[path][0]

    def on_item_tree_cursor_changed(self, treeview):
        selection = treeview.get_selection()
        if selection is None:
            return
        items, iter = selection.get_selected()
        if iter is None:
            return

        item = items[iter][3]
        self.tree.get_object('edit_delete').set_sensitive(True)
        self.tree.get_object('new_separator_button').set_sensitive(True)
        self.tree.get_object('delete_button').set_sensitive(True)

        can_revert = self.editor.canRevert(item)
        self.tree.get_object('edit_revert_to_original').set_sensitive(can_revert)

        can_edit = not isinstance(item, MateMenu.TreeSeparator)
        self.tree.get_object('edit_properties').set_sensitive(can_edit)
        self.tree.get_object('properties_button').set_sensitive(can_edit)

        index = items.get_path(iter).get_indices()[0]
        can_go_up = index > 0
        can_go_down = index < len(items) - 1
        self.tree.get_object('move_up_button').set_sensitive(can_go_up)
        self.tree.get_object('move_down_button').set_sensitive(can_go_down)

    def on_item_tree_row_activated(self, treeview, path, column):
        self.on_edit_properties_activate(None)

    def on_item_tree_popup_menu(self, item_tree, event=None):
        model, iter = item_tree.get_selection().get_selected()
        if event:
            #don't show if it's not the right mouse button
            if event.button != 3:
                return
            button = event.button
            event_time = event.time
            info = item_tree.get_path_at_pos(int(event.x), int(event.y))
            if info is not None:
                path, col, cellx, celly = info
                item_tree.grab_focus()
                item_tree.set_cursor(path, col, 0)
        else:
            path = model.get_path(iter)
            button = 0
            event_time = 0
            item_tree.grab_focus()
            item_tree.set_cursor(path, item_tree.get_columns()[0], 0)
        popup = self.tree.get_object('edit_menu')
        popup.popup(None, None, None, None, button, event_time)
        #without this shift-f10 won't work
        return True

    def on_item_tree_drag_data_get(self, treeview, context, selection, target_id, etime):
        items, iter = treeview.get_selection().get_selected()
        self.drag_data = items[iter][3]

    def on_item_tree_drag_data_received(self, treeview, context, x, y, selection, info, etime):
        items = treeview.get_model()
        types_before = (Gtk.TreeViewDropPosition.BEFORE, Gtk.TreeViewDropPosition.INTO_OR_BEFORE)
        types_into = (Gtk.TreeViewDropPosition.INTO_OR_BEFORE, Gtk.TreeViewDropPosition.INTO_OR_AFTER)
        types_after = (Gtk.TreeViewDropPosition.AFTER, Gtk.TreeViewDropPosition.INTO_OR_AFTER)
        if str(selection.get_target()) == 'MOZO_ITEM_ROW':
            drop_info = treeview.get_dest_row_at_pos(x, y)
            before = None
            after = None
            if self.drag_data is None:
                return False
            item = self.drag_data
            # by default we assume, that the items stays in the same menu
            destination = item.get_parent()
            if drop_info:
                path, position = drop_info
                target = items[path][3]
                # move the item to the directory, if the item was dropped into it
                if isinstance(target, MateMenu.TreeDirectory) and (position in types_into):
                    # append the selected item to the choosen menu
                    destination = target
                elif position in types_before:
                    before = target
                elif position in types_after:
                    after = target
                else:
                    # this does not happen
                    pass
            else:
                path = (len(items) - 1,)
                after = items[path][3]
            if isinstance(item, MateMenu.TreeEntry):
                self.editor.moveItem(item, destination, before, after)
            elif isinstance(item, MateMenu.TreeDirectory):
                if not self.editor.moveMenu(item, destination, before, after):
                    self.loadUpdates()
            elif isinstance(item, MateMenu.TreeSeparator):
                self.editor.moveSeparator(item, destination, before, after)
            context.finish(True, True, etime)
        elif str(selection.get_target()) == 'text/plain':
            if selection.get_data() is None:
                return False
            menus, iter = self.tree.get_object('menu_tree').get_selection().get_selected()
            parent = menus[iter][2]
            drop_info = treeview.get_dest_row_at_pos(x, y)
            before = None
            after = None
            if drop_info:
                path, position = drop_info
                if position in types_before:
                    before = items[path][3]
                else:
                    after = items[path][3]
            else:
                path = (len(items) - 1,)
                after = items[path][3]
            file_path = urllib.parse.unquote(selection.get_data().decode("utf-8")).strip()
            if not file_path.startswith('file:'):
                return
            myfile = Gio.File.new_for_uri(uri=file_path)
            file_info = myfile.query_info(Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE, Gio.FileQueryInfoFlags.NONE)
            content_type = file_info.get_content_type()
            if content_type == 'application/x-desktop':
                input_stream = myfile.read()
                keyfile = GLib.KeyFile()
                keyfile.load_from_bytes(input_stream.read_bytes(1024*1024), GLib.KeyFileFlags.NONE)
                self.editor.createItem(parent, before, after, KeyFile=keyfile)
            elif content_type in ('application/x-shellscript', 'application/x-executable'):
                self.editor.createItem(parent, before, after,
                                       Name=os.path.split(file_path)[1].strip(),
                                       Exec=file_path.replace('file://', '').strip(),
                                       Terminal=False)
        self.drag_data = None

    def on_item_tree_key_press_event(self, item_tree, event):
        if event.keyval == Gdk.KEY_Delete:
            self.on_edit_delete_activate(item_tree)

    def on_move_up_button_clicked(self, button):
        item_tree = self.tree.get_object('item_tree')
        items, iter = item_tree.get_selection().get_selected()
        if not iter:
            return
        path = items.get_path(iter)
        #at top, can't move up
        if path.get_indices()[0] == 0:
            return
        item = items[path][3]
        before = items[(path.get_indices()[0] - 1,)][3]
        if isinstance(item, MateMenu.TreeEntry):
            self.editor.moveItem(item, item.get_parent(), before=before)
        elif isinstance(item, MateMenu.TreeDirectory):
            self.editor.moveMenu(item, item.get_parent(), before=before)
        elif isinstance(item, MateMenu.TreeSeparator):
            self.editor.moveSeparator(item, item.get_parent(), before=before)

    def on_move_down_button_clicked(self, button):
        item_tree = self.tree.get_object('item_tree')
        items, iter = item_tree.get_selection().get_selected()
        if not iter:
            return
        path = items.get_path(iter)
        #at bottom, can't move down
        if path.get_indices()[0] == (len(items) - 1):
            return
        item = items[path][3]
        after = items[path][3]
        if isinstance(item, MateMenu.TreeEntry):
            self.editor.moveItem(item, item.get_parent(), after=after)
        elif isinstance(item, MateMenu.TreeDirectory):
            self.editor.moveMenu(item, item.get_parent(), after=after)
        elif isinstance(item, MateMenu.TreeSeparator):
            self.editor.moveSeparator(item, item.get_parent(), after=after)

    def on_mainwindow_undo(self, *_args):
        self.editor.undo()

    def on_mainwindow_redo(self, *_args):
        self.editor.redo()

    def on_help_button_clicked(self, *_args):
        Gtk.show_uri(Gdk.Screen.get_default(), "help:mate-user-guide/menu-editor", Gtk.get_current_event_time())

    def on_revert_button_clicked(self, button):
        dialog = self.tree.get_object('revertdialog')
        dialog.set_transient_for(self.tree.get_object('mainwindow'))
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.YES:
            self.editor.revert()
        dialog.hide()

    def on_close_button_clicked(self, button):
        try:
            self.tree.get_object('mainwindow').hide()
        except:
            pass
        GLib.timeout_add(10, self.quit)

    def on_properties_button_clicked(self, button):
        self.on_edit_properties_activate(None)

    def on_delete_button_clicked(self, button):
        self.on_edit_delete_activate(None)

    def on_style_updated(self, *args):
        self.loadUpdates()

    def quit(self):
        self.editor.quit()
        Gtk.main_quit()
