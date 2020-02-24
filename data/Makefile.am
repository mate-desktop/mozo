SUBDIRS = icons

desktopdir = $(datadir)/applications
desktop_in_files = mozo.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)

$(desktop_DATA): $(desktop_in_files)
	$(AM_V_GEN) $(MSGFMT) --desktop --template $< -d $(top_srcdir)/po -o $@

man_MANS = mozo.1

pkgdata_DATA = mozo.ui

CLEANFILES = $(desktop_DATA)

EXTRA_DIST = \
	meson.build \
	$(pkgdata_DATA) \
	$(man_MANS)

install-data-hook: $(UPDATE_DESKTOP)

uninstall-hook: $(UPDATE_DESKTOP)

