## Process this file with automake to produce Makefile.in

SUBDIRS = data po Mozo

CLEANFILES=

bin_SCRIPTS = mozo
CLEANFILES += mozo

DISTCLEANFILES = ChangeLog

DISTCHECK_CONFIGURE_FLAGS = \
	--disable-icon-update \
	CFLAGS='-Wno-deprecated-declarations'

mozo: mozo.in
	$(AM_V_GEN)sed -e s!\@PYTHON\@!@PYTHON@!	\
	    -e s!\@PYOPTIONS\@!-OOt!			\
	    < $< > $@
mozo: Makefile

EXTRA_DIST = \
	autogen.sh \
	mozo.in

# Build ChangeLog from GIT  history
ChangeLog:
	$(AM_V_GEN) if test -d $(top_srcdir)/.git; then \
		GIT_DIR="$(top_srcdir)/.git" git log --stat > $@; \
	fi

dist: ChangeLog

.PHONY: ChangeLog
