# -*- coding: utf-8 -*-
#   Mozo Menu Editor - Simple fd.o Compliant Menu Editor
#   Copyright (C) 2006  Travis Watkins, Heinrich Wendel
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

import codecs
import os
import xml.dom.minidom
import xml.parsers.expat
import locale
import gi
gi.require_version('MateMenu', '2.0')
from gi.repository import MateMenu, GLib
from Mozo import util

class Menu:
    tree = None
    visible_tree = None
    path = None
    dom = None

class MenuEditor(object):
    def __init__(self):
        self.locale = locale.getdefaultlocale()[0]
        self.__undo = []
        self.__redo = []
        self.applications = Menu()
        self.applications.tree = MateMenu.Tree.new('mate-applications.menu', MateMenu.TreeFlags.SHOW_EMPTY|MateMenu.TreeFlags.INCLUDE_EXCLUDED|MateMenu.TreeFlags.INCLUDE_NODISPLAY|MateMenu.TreeFlags.SHOW_ALL_SEPARATORS|MateMenu.TreeFlags.SORT_DISPLAY_NAME)
        self.applications.visible_tree = MateMenu.Tree.new('mate-applications.menu', MateMenu.TreeFlags.SORT_DISPLAY_NAME)
        self.applications.tree.sort_key = MateMenu.TreeFlags.SORT_DISPLAY_NAME
        self.applications.visible_tree.sort_key = MateMenu.TreeFlags.SORT_DISPLAY_NAME
        self.applications.tree.connect('changed', self.menuChanged)

        self.settings = Menu()
        self.settings.tree = MateMenu.Tree.new('mate-settings.menu', MateMenu.TreeFlags.SHOW_EMPTY|MateMenu.TreeFlags.INCLUDE_EXCLUDED|MateMenu.TreeFlags.INCLUDE_NODISPLAY|MateMenu.TreeFlags.SHOW_ALL_SEPARATORS|MateMenu.TreeFlags.SORT_DISPLAY_NAME)
        self.settings.visible_tree = MateMenu.Tree.new('mate-settings.menu', MateMenu.TreeFlags.SORT_DISPLAY_NAME)
        self.settings.tree.sort_key = MateMenu.TreeFlags.SORT_DISPLAY_NAME
        self.settings.visible_tree.sort_key = MateMenu.TreeFlags.SORT_DISPLAY_NAME
        self.settings.tree.connect('changed', self.menuChanged)
        self.load()
        self.__loadMenus()

    def __loadMenus(self):
        self.applications.path = os.path.join(util.getUserMenuPath(), self.applications.tree.props.menu_basename)
        try:
            self.applications.dom = xml.dom.minidom.parse(self.applications.path)
        except (IOError, xml.parsers.expat.ExpatError):
            self.applications.dom = xml.dom.minidom.parseString(util.getUserMenuXml(self.applications.tree))
        util.removeWhitespaceNodes(self.applications.dom)

        self.settings.path = os.path.join(util.getUserMenuPath(), self.settings.tree.props.menu_basename)
        try:
            self.settings.dom = xml.dom.minidom.parse(self.settings.path)
        except (IOError, xml.parsers.expat.ExpatError):
            self.settings.dom = xml.dom.minidom.parseString(util.getUserMenuXml(self.settings.tree))
        util.removeWhitespaceNodes(self.settings.dom)
        self.save(True)

    def load(self):
        if not self.applications.tree.load_sync():
            raise ValueError("can not load menu tree %r" % (self.applications.tree.props.menu_basename,))
        if not self.settings.tree.load_sync():
            raise ValueError("can not load menu tree %r" % (self.settings.tree.props.menu_basename,))
        if not self.applications.visible_tree.load_sync():
            raise ValueError("can not load menu tree %r" % (self.applications.visible_tree.props.menu_basename,))
        if not self.settings.visible_tree.load_sync():
            raise ValueError("can not load menu tree %r" % (self.settings.visible_tree.props.menu_basename,))

    def menuChanged(self, *a):
        self.load()

    def save(self, from_loading=False):
        for menu in ('applications', 'settings'):
            with codecs.open(getattr(self, menu).path, 'w', 'utf-8') as f:
                f.write(getattr(self, menu).dom.toprettyxml())
        if not from_loading:
            self.load()
            self.__loadMenus()

    def quit(self):
        for file_name in os.listdir(util.getUserItemPath()):
            if file_name[-6:-2] in ('redo', 'undo'):
                file_path = os.path.join(util.getUserItemPath(), file_name)
                os.unlink(file_path)
        for file_name in os.listdir(util.getUserDirectoryPath()):
            if file_name[-6:-2] in ('redo', 'undo'):
                file_path = os.path.join(util.getUserDirectoryPath(), file_name)
                os.unlink(file_path)
        for file_name in os.listdir(util.getUserMenuPath()):
            if file_name[-6:-2] in ('redo', 'undo'):
                file_path = os.path.join(util.getUserMenuPath(), file_name)
                os.unlink(file_path)

    def revert(self):
        for name in ('applications', 'settings'):
            menu = getattr(self, name)
            self.revertTree(menu.tree.get_root_directory())
            path = os.path.join(util.getUserMenuPath(), menu.tree.props.menu_basename)
            try:
                os.unlink(path)
            except OSError:
                pass
            #reload DOM for each menu
            try:
                menu.dom = xml.dom.minidom.parse(menu.path)
            except (IOError, xml.parsers.expat.ExpatError):
                menu.dom = xml.dom.minidom.parseString(util.getUserMenuXml(menu.tree))
            util.removeWhitespaceNodes(menu.dom)
        #reset undo/redo, no way to recover from this
        self.__undo, self.__redo = [], []
        self.save()

    def revertTree(self, menu):
        item_iter = menu.iter()
        item_type = item_iter.next()
        while item_type != MateMenu.TreeItemType.INVALID:
            if item_type == MateMenu.TreeItemType.DIRECTORY:
                item = item_iter.get_directory()
                self.revertTree(item)
            elif item_type == MateMenu.TreeItemType.ENTRY:
                item = item_iter.get_entry()
                self.revertItem(item)
            item_type = item_iter.next()
        self.revertMenu(menu)

    def revertItem(self, item):
        if not self.canRevert(item):
            return
        self.__addUndo([item,])
        try:
            os.remove(item.get_desktop_file_path())
        except OSError:
            pass
        self.save()

    def revertMenu(self, menu):
        if not self.canRevert(menu):
            return
        #wtf happened here? oh well, just bail
        if not menu.get_desktop_file_path():
            return
        self.__addUndo([menu,])
        file_id = os.path.split(menu.get_desktop_file_path())[1]
        path = os.path.join(util.getUserDirectoryPath(), file_id)
        try:
            os.remove(path)
        except OSError:
            pass
        self.save()

    def undo(self):
        if len(self.__undo) == 0:
            return
        files = self.__undo.pop()
        redo = []
        for undo_path in files[::-1]:
            new_path = undo_path.rsplit('.', 1)[0]
            redo_path = util.getUniqueRedoFile(new_path)

            # create redo file
            with codecs.open(new_path, 'r', 'utf-8') as f_new:
                with codecs.open(redo_path, 'w', 'utf-8') as f_redo:
                    f_redo.write(f_new.read())
            redo.append(redo_path)

            # restore undo file
            with codecs.open(undo_path, 'r', 'utf-8') as f_undo:
                with codecs.open(new_path, 'w', 'utf-8') as f_new:
                    f_new.write(f_undo.read())
            os.unlink(undo_path)

        # reload DOM to make changes stick
        for name in ('applications', 'settings'):
            menu = getattr(self, name)
            try:
                menu.dom = xml.dom.minidom.parse(menu.path)
            except (IOError, xml.parsers.expat.ExpatError):
                menu.dom = xml.dom.minidom.parseString(util.getUserMenuXml(menu.tree))
            util.removeWhitespaceNodes(menu.dom)
        self.__redo.append(redo)

    def redo(self):
        if len(self.__redo) == 0:
            return
        files = self.__redo.pop()
        undo = []
        for redo_path in files[::-1]:
            new_path = redo_path.rsplit('.', 1)[0]
            undo_path = util.getUniqueUndoFile(new_path)

            # create undo file
            with codecs.open(new_path, 'r', 'utf-8') as f_new:
                with codecs.open(undo_path, 'w', 'utf-8') as f_undo:
                    f_undo.write(f_new.read())
            undo.append(undo_path)

            # restore redo file
            with codecs.open(redo_path, 'r', 'utf-8') as f_redo:
                with codecs.open(new_path, 'w', 'utf-8') as f_new:
                    f_new.write(f_redo.read())
            os.unlink(redo_path)

        #reload DOM to make changes stick
        for name in ('applications', 'settings'):
            menu = getattr(self, name)
            try:
                menu.dom = xml.dom.minidom.parse(menu.path)
            except (IOError, xml.parsers.expat.ExpatError):
                menu.dom = xml.dom.minidom.parseString(util.getUserMenuXml(menu.tree))
            util.removeWhitespaceNodes(menu.dom)
        self.__undo.append(undo)

    def getMenus(self, parent=None):
        if parent is None:
            yield self.applications.tree.get_root_directory()
            yield self.settings.tree.get_root_directory()
        else:
            item_iter = parent.iter()
            item_type = item_iter.next()
            while item_type != MateMenu.TreeItemType.INVALID:
                if item_type == MateMenu.TreeItemType.DIRECTORY:
                    item = item_iter.get_directory()
                    yield (item, self.__isVisible(item))
                item_type = item_iter.next()

    def getContents(self, item):
        contents = []
        item_iter = item.iter()
        item_type = item_iter.next()

        while item_type != MateMenu.TreeItemType.INVALID:
            item = None
            if item_type == MateMenu.TreeItemType.DIRECTORY:
                item = item_iter.get_directory()
            elif item_type == MateMenu.TreeItemType.ENTRY:
                item = item_iter.get_entry()
            elif item_type == MateMenu.TreeItemType.HEADER:
                item = item_iter.get_header()
            elif item_type == MateMenu.TreeItemType.ALIAS:
                item = item_iter.get_alias()
            elif item_type == MateMenu.TreeItemType.SEPARATOR:
                item = item_iter.get_separator()
            if item:
                contents.append(item)
            item_type = item_iter.next()
        return contents

    def getItems(self, menu):
        for item in self.getContents(menu):
            if isinstance(item, MateMenu.TreeSeparator):
                yield(item, True)
            else:
                if isinstance(item, MateMenu.TreeEntry) and item.get_desktop_file_id()[-19:] == '-usercustom.desktop':
                     continue
                yield (item, self.__isVisible(item))

    def canRevert(self, item):
        if isinstance(item, MateMenu.TreeEntry):
            if util.getItemPath(item.get_desktop_file_id()) is not None:
                path = util.getUserItemPath()
                if os.path.isfile(os.path.join(path, item.get_desktop_file_id())):
                    return True
        elif isinstance(item, MateMenu.TreeDirectory):
            if item.get_desktop_file_path():
                file_id = os.path.split(item.get_desktop_file_path())[1]
            else:
                file_id = item.get_menu_id() + '.directory'
            if util.getDirectoryPath(file_id) is not None:
                path = util.getUserDirectoryPath()
                if os.path.isfile(os.path.join(path, file_id)):
                    return True
        return False

    def setVisible(self, item, visible):
        dom = self.__getMenu(item).dom
        if isinstance(item, MateMenu.TreeEntry):
            self.__addUndo([self.__getMenu(item), item])
            menu_xml = self.__getXmlMenu(self.__getPath(item.get_parent()), dom.documentElement, dom)
            if visible:
                self.__addXmlFilename(menu_xml, dom, item.get_desktop_file_id(), 'Include')
                self.__writeItem(item, NoDisplay=False)
            else:
                self.__addXmlFilename(menu_xml, dom, item.get_desktop_file_id(), 'Exclude')
            self.__addXmlTextElement(menu_xml, 'AppDir', util.getUserItemPath(), dom)
        elif isinstance(item, MateMenu.TreeDirectory):
            self.__addUndo([self.__getMenu(item), item])
            item_iter = item.iter()
            first_child_type = item_iter.next()
            #don't mess with it if it's empty
            if first_child_type == MateMenu.TreeItemType.INVALID:
                return
            menu_xml = self.__getXmlMenu(self.__getPath(item), dom.documentElement, dom)
            for node in self.__getXmlNodesByName(['Deleted', 'NotDeleted'], menu_xml):
                node.parentNode.removeChild(node)
            self.__writeMenu(item, NoDisplay=not visible)
            self.__addXmlTextElement(menu_xml, 'DirectoryDir', util.getUserDirectoryPath(), dom)
        self.save()

    def createItem(self, parent, before, after, **kwargs):
        file_id = self.__writeItem(None, **kwargs)
        self.insertExternalItem(file_id, parent.get_menu_id(), before, after)

    def insertExternalItem(self, file_id, parent_id, before=None, after=None):
        parent = self.__findMenu(parent_id)
        dom = self.__getMenu(parent).dom
        self.__addItem(parent, file_id, dom)
        self.__positionItem(parent, ('Item', file_id), before, after)
        self.__addUndo([self.__getMenu(parent), ('Item', file_id)])
        self.save()

    def insertExternalMenu(self, file_id, parent_id, before=None, after=None):
        menu_id = file_id.rsplit('.', 1)[0]
        parent = self.__findMenu(parent_id)
        dom = self.__getMenu(parent).dom
        self.__addXmlDefaultLayout(self.__getXmlMenu(self.__getPath(parent), dom.documentElement, dom) , dom)
        menu_xml = self.__getXmlMenu(self.__getPath(parent) + [menu_id], dom.documentElement, dom)
        self.__addXmlTextElement(menu_xml, 'Directory', file_id, dom)
        self.__positionItem(parent, ('Menu', menu_id), before, after)
        self.__addUndo([self.__getMenu(parent), ('Menu', file_id)])
        self.save()

    def createSeparator(self, parent, before=None, after=None):
        self.__positionItem(parent, ('Separator',), before, after)
        self.__addUndo([self.__getMenu(parent), ('Separator',)])
        self.save()

    def editItem(self, item, icon, name, comment, command, use_term, parent=None, final=True):
        #if nothing changed don't make a user copy
        app_info = item.get_app_info()
        if icon == app_info.get_icon() and name == app_info.get_display_name() and comment == item.get_comment() and command == item.get_exec() and use_term == item.get_launch_in_terminal():
            return
        #hack, item.get_parent() seems to fail a lot
        if not parent:
            parent = item.get_parent()
        if final:
            self.__addUndo([self.__getMenu(parent), item])
        self.__writeItem(item, Icon=icon, Name=name, Comment=comment, Exec=command, Terminal=use_term)
        if final:
            dom = self.__getMenu(parent).dom
            menu_xml = self.__getXmlMenu(self.__getPath(parent), dom.documentElement, dom)
            self.__addXmlTextElement(menu_xml, 'AppDir', util.getUserItemPath(), dom)
        self.save()

    def editMenu(self, menu, icon, name, comment, final=True):
        #if nothing changed don't make a user copy
        if icon == menu.get_icon() and name == menu.get_name() and comment == menu.get_comment():
            return
        #we don't use this, we just need to make sure the <Menu> exists
        #otherwise changes won't show up
        dom = self.__getMenu(menu).dom
        menu_xml = self.__getXmlMenu(self.__getPath(menu), dom.documentElement, dom)
        self.__writeMenu(menu, Icon=icon, Name=name, Comment=comment)
        if final:
            self.__addXmlTextElement(menu_xml, 'DirectoryDir', util.getUserDirectoryPath(), dom)
            self.__addUndo([self.__getMenu(menu), menu])
        self.save()

    def copyItem(self, item, new_parent, before=None, after=None):
        dom = self.__getMenu(new_parent).dom
        file_path = item.get_desktop_file_path()
        keyfile = GLib.KeyFile()
        keyfile.load_from_file(file_path, util.KEY_FILE_FLAGS)
        util.fillKeyFile(keyfile, dict(Categories=[], Hidden=False))

        file_id = util.getUniqueFileId(os.path.basename(file_path).split(".desktop", 1)[0], ".desktop")
        out_path = os.path.join(util.getUserItemPath(), file_id)

        contents = keyfile.to_data()[0]

        with open(out_path, 'w') as f:
            f.write(contents)

        self.__addItem(new_parent, file_id, dom)
        self.__positionItem(new_parent, ('Item', file_id), before, after)
        self.__addUndo([self.__getMenu(new_parent), ('Item', file_id)])
        self.save()
        return file_id

    def moveItem(self, item, new_parent, before=None, after=None):
        undo = []
        if item.get_parent() != new_parent:
            # create new item
            file_id = self.copyItem(item, new_parent)
            # hide old item
            self.deleteItem(item)
            item = ('Item', file_id)
        self.__positionItem(new_parent, item, before, after)
        undo.append(self.__getMenu(new_parent))
        self.__addUndo(undo)
        # merge the undo entries created by the previous operations in the
        # correct order so we can undo in one go
        items = self.__undo.pop()[::-1] + self.__undo.pop()[::-1] + self.__undo.pop()[::-1]
        self.__undo.append(items[::-1])
        self.save()

    def moveMenu(self, menu, new_parent, before=None, after=None):
        parent = new_parent
        #don't move a menu into it's child
        while parent.get_parent():
            parent = parent.get_parent()
            if parent == menu:
                return False

        #don't move a menu into itself
        if new_parent == menu:
            return False

        #can't move between top-level menus
        if self.__getMenu(menu) != self.__getMenu(new_parent):
            return False
        if menu.get_parent() != new_parent:
            dom = self.__getMenu(menu).dom
            path = self.__getPath(menu)
            xml_root = self.__getXmlMenu(path[0], dom.documentElement, dom)
            new_path = self.__getPath(new_parent) + [menu.get_menu_id()]
            self.__addXmlMove(xml_root, '/'.join(path), '/'.join(new_path), dom)
        self.__positionItem(new_parent, menu, before, after)
        self.__addUndo([self.__getMenu(new_parent),])
        self.save()

    def moveSeparator(self, separator, new_parent, before=None, after=None):
        undo = []
        # remove the original separator if its parent is not the new destination
        if separator.get_parent() != new_parent:
            self.deleteSeparator(separator)
            undo.append(separator)
        # this adds the new separator to the specified position
        self.__positionItem(new_parent, separator, before, after)
        undo.append(self.__getMenu(new_parent))
        self.__addUndo(undo)
        self.save()

    def deleteItem(self, item):
        self.__addUndo([item,])
        self.__writeItem(item, Hidden=True)
        self.save()

    def deleteMenu(self, menu):
        dom = self.__getMenu(menu).dom
        menu_xml = self.__getXmlMenu(self.__getPath(menu), dom.documentElement, dom)
        self.__addDeleted(menu_xml, dom)
        self.__addUndo([self.__getMenu(menu),])
        self.save()

    def deleteSeparator(self, item):
        parent = item.get_parent()
        contents = self.getContents(parent)
        contents.remove(item)
        layout = self.__createLayout(contents)
        dom = self.__getMenu(parent).dom
        menu_xml = self.__getXmlMenu(self.__getPath(parent), dom.documentElement, dom)
        self.__addXmlLayout(menu_xml, layout, dom)
        self.__addUndo([self.__getMenu(item.get_parent()),])
        self.save()

    #private stuff
    def __addUndo(self, items):
        self.__undo.append([])
        for item in items:
            if isinstance(item, Menu):
                file_path = item.path
            elif isinstance(item, tuple):
                if item[0] == 'Item':
                    file_path = os.path.join(util.getUserItemPath(), item[1])
                    if not os.path.isfile(file_path):
                        file_path = util.getItemPath(item[1])
                elif item[0] == 'Menu':
                    file_path = os.path.join(util.getUserDirectoryPath(), item[1])
                    if not os.path.isfile(file_path):
                        file_path = util.getDirectoryPath(item[1])
                else:
                    continue
            elif isinstance(item, MateMenu.TreeDirectory):
                if item.get_desktop_file_path() is None:
                    continue
                file_path = os.path.join(util.getUserDirectoryPath(), os.path.split(item.get_desktop_file_path())[1])
                if not os.path.isfile(file_path):
                    file_path = item.get_desktop_file_path()
            elif isinstance(item, MateMenu.TreeEntry):
                file_path = os.path.join(util.getUserItemPath(), item.get_desktop_file_id())
                if not os.path.isfile(file_path):
                    file_path = item.get_desktop_file_path()
            else:
                continue
            with codecs.open(file_path, 'r', 'utf-8') as f:
                data = f.read()
            undo_path = util.getUniqueUndoFile(file_path)
            with codecs.open(undo_path, 'w', 'utf-8') as f:
                f.write(data)
            self.__undo[-1].append(undo_path)

    def __getMenu(self, item):
        root = item.get_parent()
        if not root:
            #already at the top
            root = item
        else:
            while True:
                if root.get_parent():
                    root = root.get_parent()
                else:
                    break
        if root.get_menu_id() == self.applications.tree.get_root_directory().get_menu_id():
            return self.applications
        return self.settings

    def __findMenu(self, menu_id, parent=None):
        if parent is None:
            menu = self.__findMenu(menu_id, self.applications.tree.get_root_directory())
            if menu is not None:
                return menu
            else:
                return self.__findMenu(menu_id, self.settings.tree.get_root_directory())
        if menu_id == self.applications.tree.get_root_directory().get_menu_id():
            return self.applications.tree.get_root_directory()
        if menu_id == self.settings.tree.get_root_directory().get_menu_id():
            return self.settings.tree.get_root_directory()

        item_iter = parent.iter()
        item_type = item_iter.next()
        while item_type != MateMenu.TreeItemType.INVALID:
            if item_type == MateMenu.TreeItemType.DIRECTORY:
                item = item_iter.get_directory()
                if item.get_menu_id() == menu_id:
                    return item
                menu = self.__findMenu(menu_id, item)
                if menu is not None:
                    return menu
            item_type = item_iter.next()

    def __isVisible(self, item):
        if isinstance(item, MateMenu.TreeEntry):
            app_info = item.get_app_info()
            return not (item.get_is_excluded() or app_info.get_nodisplay())
        menu = self.__getMenu(item)
        if menu == self.applications:
            root = self.applications.visible_tree.get_root_directory()
        elif menu == self.settings:
            root = self.settings.visible_tree.get_root_directory()
        if isinstance(item, MateMenu.TreeDirectory):
            if self.__findMenu(item.get_menu_id(), root) is None:
                return False
        return True

    def __getPath(self, menu):
        names = []
        current = menu
        while current is not None:
            names.append(current.get_menu_id())
            current = current.get_parent()

        # XXX - don't append root menu name, mozo doesn't
        # expect it. look into this more.
        names.pop(-1)
        return names[::-1]

    def __getXmlMenuPart(self, element, name):
        for node in self.__getXmlNodesByName('Menu', element):
            for child in self.__getXmlNodesByName('Name', node):
                if child.childNodes[0].nodeValue == name:
                    return node
        return None

    def __getXmlMenu(self, path, element, dom):
        if isinstance(path, str):
            return element
        for name in path:
            found = self.__getXmlMenuPart(element, name)
            if found is not None:
                element = found
            else:
                element = self.__addXmlMenuElement(element, name, dom)
        return element

    def __addXmlMenuElement(self, element, name, dom):
        if isinstance(name, bytes):
            name = name.decode('utf-8')

        node = dom.createElement('Menu')
        self.__addXmlTextElement(node, 'Name', name, dom)
        return element.appendChild(node)

    def __addXmlTextElement(self, element, name, text, dom):
        if isinstance(name, bytes):
            name = name.decode('utf-8')
        if isinstance(text, bytes):
            text = text.decode('utf-8')

        for temp in element.childNodes:
            if temp.nodeName == name:
                if temp.childNodes[0].nodeValue == text:
                    return
        node = dom.createElement(name)
        text = dom.createTextNode(text)
        node.appendChild(text)
        return element.appendChild(node)

    def __addXmlFilename(self, element, dom, filename, type = 'Include'):
        if isinstance(filename, bytes):
            filename = filename.decode('utf-8')

        # remove old filenames
        for node in self.__getXmlNodesByName(['Include', 'Exclude'], element):
            if node.childNodes[0].nodeName == 'Filename' and node.childNodes[0].childNodes[0].nodeValue == filename:
                element.removeChild(node)

        # add new filename
        node = dom.createElement(type)
        node.appendChild(self.__addXmlTextElement(node, 'Filename', filename, dom))
        return element.appendChild(node)

    def __addDeleted(self, element, dom):
        node = dom.createElement('Deleted')
        return element.appendChild(node)

    def __makeKeyFile(self, file_path, kwargs):
        if 'KeyFile' in kwargs:
            return kwargs['KeyFile']

        keyfile = GLib.KeyFile()

        if file_path is not None:
            keyfile.load_from_file(file_path, util.KEY_FILE_FLAGS)

        util.fillKeyFile(keyfile, kwargs)
        return keyfile

    def __writeItem(self, item, **kwargs):
        if item is not None:
            file_path = item.get_desktop_file_path()
        else:
            file_path = None

        keyfile = self.__makeKeyFile(file_path, kwargs)

        if item is not None:
            file_id = item.get_desktop_file_id()
        else:
            file_id = util.getUniqueFileId(keyfile.get_string(GLib.KEY_FILE_DESKTOP_GROUP, 'Name'), '.desktop')

        contents = keyfile.to_data()[0]

        with open(os.path.join(util.getUserItemPath(), file_id), 'w') as f:
            f.write(contents)
        return file_id

    def __writeMenu(self, menu, **kwargs):
        if menu is not None:
            file_id = os.path.split(menu.get_desktop_file_path())[1]
            file_path = menu.get_desktop_file_path()
            keyfile = GLib.KeyFile()
            keyfile.load_from_file(file_path, util.KEY_FILE_FLAGS)
        elif menu is None and 'Name' not in kwargs:
            raise Exception('New menus need a name')
        else:
            file_id = util.getUniqueFileId(kwargs['Name'], '.directory')
            keyfile = GLib.KeyFile()

        util.fillKeyFile(keyfile, kwargs)

        contents = keyfile.to_data()[0]

        with open(os.path.join(util.getUserDirectoryPath(), file_id), 'w') as f:
            f.write(contents)
        return file_id

    def __getXmlNodesByName(self, name, element):
        for child in element.childNodes:
            if child.nodeType == xml.dom.Node.ELEMENT_NODE:
                if isinstance(name, str) and child.nodeName == name:
                    yield child
                elif isinstance(name, list) or isinstance(name, tuple):
                    if child.nodeName in name:
                        yield child

    def __addXmlMove(self, element, old, new, dom):
        if not self.__undoMoves(element, old, new, dom):
            node = dom.createElement('Move')
            node.appendChild(self.__addXmlTextElement(node, 'Old', old, dom))
            node.appendChild(self.__addXmlTextElement(node, 'New', new, dom))
            #are parsed in reverse order, need to put at the beginning
            return element.insertBefore(node, element.firstChild)

    def __addXmlLayout(self, element, layout, dom):
        # remove old layout
        for node in self.__getXmlNodesByName('Layout', element):
            element.removeChild(node)

        # add new layout
        node = dom.createElement('Layout')
        for order in layout.order:
            if order[0] == 'Separator':
                child = dom.createElement('Separator')
                node.appendChild(child)
            elif order[0] == 'Filename':
                child = self.__addXmlTextElement(node, 'Filename', order[1], dom)
            elif order[0] == 'Menuname':
                child = self.__addXmlTextElement(node, 'Menuname', order[1], dom)
            elif order[0] == 'Merge':
                child = dom.createElement('Merge')
                child.setAttribute('type', order[1])
                node.appendChild(child)
        return element.appendChild(node)

    def __addXmlDefaultLayout(self, element, dom):
        # remove old default layout
        for node in self.__getXmlNodesByName('DefaultLayout', element):
            element.removeChild(node)

        # add new layout
        node = dom.createElement('DefaultLayout')
        node.setAttribute('inline', 'false')
        return element.appendChild(node)

    def __createLayout(self, items):
        layout = Layout()
        layout.order = []

        layout.order.append(['Merge', 'menus'])
        for item in items:
            if isinstance(item, tuple):
                if item[0] == 'Separator':
                    layout.parseSeparator()
                elif item[0] == 'Menu':
                    layout.parseMenuname(item[1])
                elif item[0] == 'Item':
                    layout.parseFilename(item[1])
            elif isinstance(item, MateMenu.TreeDirectory):
                layout.parseMenuname(item.get_menu_id())
            elif isinstance(item, MateMenu.TreeEntry):
                layout.parseFilename(item.get_desktop_file_id())
            elif isinstance(item, MateMenu.TreeSeparator):
                layout.parseSeparator()
        layout.order.append(['Merge', 'files'])
        return layout

    def __addItem(self, parent, file_id, dom):
        xml_parent = self.__getXmlMenu(self.__getPath(parent), dom.documentElement, dom)
        self.__addXmlFilename(xml_parent, dom, file_id, 'Include')

    def __positionItem(self, parent, item, before=None, after=None):
        contents = self.getContents(parent)
        if after:
            index = contents.index(after) + 1
        elif before:
            index = contents.index(before)
        else:
            # append the item to the list
            index = len(contents)
        #if this is a move to a new parent you can't remove the item
        if item in contents:
            # decrease the destination index, if we shorten the list
            if (before and (contents.index(item) < index)) \
                    or (after and (contents.index(item) < index - 1)):
                index -= 1
            contents.remove(item)
        contents.insert(index, item)
        layout = self.__createLayout(contents)
        dom = self.__getMenu(parent).dom
        menu_xml = self.__getXmlMenu(self.__getPath(parent), dom.documentElement, dom)
        self.__addXmlLayout(menu_xml, layout, dom)

    def __undoMoves(self, element, old, new, dom):
        nodes = []
        matches = []
        original_old = old
        final_old = old
        #get all <Move> elements
        for node in self.__getXmlNodesByName(['Move'], element):
            nodes.insert(0, node)
        #if the <New> matches our old parent we've found a stage to undo
        for node in nodes:
            xml_old = node.getElementsByTagName('Old')[0]
            xml_new = node.getElementsByTagName('New')[0]
            if xml_new.childNodes[0].nodeValue == old:
                matches.append(node)
                #we should end up with this path when completed
                final_old = xml_old.childNodes[0].nodeValue
        #undoing <Move>s
        for node in matches:
            element.removeChild(node)
        if len(matches) > 0:
            for node in nodes:
                xml_old = node.getElementsByTagName('Old')[0]
                xml_new = node.getElementsByTagName('New')[0]
                path = os.path.split(xml_new.childNodes[0].nodeValue)
                if path[0] == original_old:
                    element.removeChild(node)
                    for node in dom.getElementsByTagName('Menu'):
                        name_node = node.getElementsByTagName('Name')[0]
                        name = name_node.childNodes[0].nodeValue
                        if name == os.path.split(new)[1]:
                            #copy app and dir directory info from old <Menu>
                            root_path = dom.getElementsByTagName('Menu')[0].getElementsByTagName('Name')[0].childNodes[0].nodeValue
                            xml_menu = self.__getXmlMenu(root_path + '/' + new, dom.documentElement, dom)
                            for app_dir in node.getElementsByTagName('AppDir'):
                                xml_menu.appendChild(app_dir)
                            for dir_dir in node.getElementsByTagName('DirectoryDir'):
                                xml_menu.appendChild(dir_dir)
                            parent = node.parentNode
                            parent.removeChild(node)
                    node = dom.createElement('Move')
                    node.appendChild(self.__addXmlTextElement(node, 'Old', xml_old.childNodes[0].nodeValue, dom))
                    node.appendChild(self.__addXmlTextElement(node, 'New', os.path.join(new, path[1]), dom))
                    element.appendChild(node)
            if final_old == new:
                return True
            node = dom.createElement('Move')
            node.appendChild(self.__addXmlTextElement(node, 'Old', final_old, dom))
            node.appendChild(self.__addXmlTextElement(node, 'New', new, dom))
            return element.appendChild(node)

class Layout:
    def __init__(self, node=None):
        self.order = []

    def parseMenuname(self, value):
        self.order.append(['Menuname', value])

    def parseSeparator(self):
        self.order.append(['Separator'])

    def parseFilename(self, value):
        self.order.append(['Filename', value])

    def parseMerge(self, merge_type='all'):
        self.order.append(['Merge', merge_type])
