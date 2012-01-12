SUBDIRS = icons

@INTLTOOL_DESKTOP_RULE@

desktopdir = $(datadir)/applications
desktop_in_files = mozo.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)

pkgdata_DATA = mozo.ui

CLEANFILES = $(desktop_DATA)

EXTRA_DIST = $(pkgdata_DATA)

install-data-hook: $(UPDATE_DESKTOP)

uninstall-hook: $(UPDATE_DESKTOP)

