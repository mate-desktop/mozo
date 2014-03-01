dnl -*- Mode: autoconf -*-
dnl Process this file with autoconf to produce a configure script.
AC_PREREQ(2.53)
AC_INIT(mozo, 1.8.0, http://www.mate-desktop.org)
AC_CONFIG_SRCDIR(mozo.in)
AC_CONFIG_HEADERS([config.h])
AM_INIT_AUTOMAKE([1.7 dist-xz no-dist-gzip check-news])
AM_MAINTAINER_MODE

m4_define(required_pygobject_version, 2.15.1)
m4_define(required_pygtk_version, 2.13.0)

dnl put the ACLOCAL flags in the makefile
ACLOCAL="$ACLOCAL $ACLOCAL_FLAGS"


GETTEXT_PACKAGE=mozo
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Gettext package])
AM_GLIB_GNU_GETTEXT
IT_PROG_INTLTOOL([0.40.0])

AM_PATH_PYTHON_VERSION(2.7, 2.7.0, 2.6, 2.6.0, 2.5, 2.5.0, 2.4, 2.4.0)

PKG_CHECK_MODULES(MOZO, libmate-menu >= 1.1.0)

dnl Check for correctly installed pygobject
AC_MSG_CHECKING(for pygobject required_pygobject_version installed for python required_python_abi)
prog="
import pygtk; pygtk.require('2.0')
import gobject
assert gobject.pygobject_version >= tuple(map(int, 'required_pygobject_version'.split('.')))
"

if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC; then
    AC_MSG_RESULT(found)
else
    AC_MSG_RESULT(not found)
    AC_MSG_ERROR(required pygobject version not found)
fi

dnl Check for correctly installed pygtk
AC_MSG_CHECKING(for pygtk required_pygtk_version installed for python ${PYTHON_VERSION})
prog="
import pygtk; pygtk.require('2.0')
import gobject
assert gobject.pygtk_version >= tuple(map(int, 'required_pygtk_version'.split('.')))
"

if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC; then
    AC_MSG_RESULT(found)
else
    AC_MSG_RESULT(not found)
    AC_MSG_ERROR(required pygtk version not found)
fi

dnl Check for correctly installed python-glade
dnl AC_MSG_CHECKING(for pyglade required_pygtk_version installed for python ${PYTHON_VERSION})
dnl prog="
dnl import pygtk; pygtk.require('2.0')
dnl import gtk.glade
dnl "
dnl if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC; then
dnl    AC_MSG_RESULT(found)
dnl else
dnl    AC_MSG_RESULT(not found)
dnl    AC_MSG_ERROR(required pyglade version not found)
dnl fi

AC_ARG_ENABLE(icon-update, AC_HELP_STRING([--disable-icon-update],
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

