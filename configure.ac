dnl -*- Mode: autoconf -*-
dnl Process this file with autoconf to produce a configure script.
AC_PREREQ(2.58)
AC_INIT(mozo, 1.28.0, https://mate-desktop.org)
m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])
AC_CONFIG_SRCDIR(mozo.in)
AC_CONFIG_HEADERS([config.h])
AM_INIT_AUTOMAKE([1.7 dist-xz no-dist-gzip check-news])
AM_MAINTAINER_MODE

dnl put the ACLOCAL flags in the makefile
ACLOCAL="$ACLOCAL $ACLOCAL_FLAGS"


GETTEXT_PACKAGE=mozo
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
AM_GNU_GETTEXT_VERSION([0.19.8])
AM_GNU_GETTEXT_REQUIRE_VERSION([0.19.8])
AM_GNU_GETTEXT([external])

AM_PATH_PYTHON(3.5)

PKG_CHECK_MODULES(MOZO, libmate-menu >= 1.21.0 pygobject-3.0)

AC_ARG_ENABLE(icon-update, AS_HELP_STRING([--disable-icon-update],
					[Disable icon cache update]))
if (test "$enable_icon_update" != no); then
	AC_PATH_PROG(UPDATE_ICON_CACHE, [gtk-update-icon-cache])
fi
AM_CONDITIONAL([ICON_UPDATE], [test -n "$UPDATE_ICON_CACHE"])

AC_CONFIG_FILES([
        Makefile
        po/Makefile.in
        Mozo/Makefile
        data/mozo.desktop.in
        data/Makefile
        data/icons/Makefile
        ])

AC_OUTPUT

