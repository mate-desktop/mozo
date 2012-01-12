#!/bin/sh
# Run this to generate all the initial makefiles, etc.

srcdir=`dirname $0`
test -z "$srcdir" && srcdir=.

PKG_NAME="mate-menu-editor"
REQUIRED_AUTOCONF_VERSION=2.53
REQUIRED_AUTOMAKE_VERSION=${REQUIRED_AUTOMAKE_VERSION:-1.9}

(test -f $srcdir/configure.ac \
  && test -f $srcdir/autogen.sh) || {
    echo -n "**Error**: Directory "\`$srcdir\'" does not look like the"
    echo " top-level $PKG_NAME directory"
    exit 1
}

DIE=0

# This is a bit complicated here since we can't use mate-config yet.
# It'll be easier after switching to pkg-config since we can then
# use pkg-config to find the mate-autogen.sh script.

mate_autogen=
mate_datadir=

ifs_save="$IFS"; IFS=":"
for dir in $PATH ; do
  test -z "$dir" && dir=.
  if test -f $dir/mate-autogen.sh ; then
    mate_autogen="$dir/mate-autogen.sh"
    mate_datadir=`echo $dir | sed -e 's,/bin$,/share,'`
    break
  fi
done
IFS="$ifs_save"

if test -z "$mate_autogen" ; then
  echo "You need to install the mate-common module and make"
  echo "sure the mate-autogen.sh script is in your \$PATH."
  exit 1
fi

MATE_DATADIR="$mate_datadir" USE_MATE2_MACROS=1 . $mate_autogen
