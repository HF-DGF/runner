#!/bin/bash
# URL="http://ftp.gnu.org/gnu/binutils/binutils-2.28.tar.gz"
DIRNAME="binutils-2.28"
ARCHIVE=$DIRNAME".tar.gz"
CONFIG_OPTIONS="--disable-shared --disable-gdb \
                 --disable-libdecnumber --disable-readline \
                 --disable-sim --disable-ld"

# wget $URL -O $ARCHIVE
cp /projects_source/$ARCHIVE $ARCHIVE
rm -rf $DIRNAME
tar -xzf $ARCHIVE || exit 1
cd $DIRNAME
./configure $CONFIG_OPTIONS || exit 1
## Parallel building according to https://github.com/aflgo/aflgo/issues/59
## Altohough an issue with parallel building is observed in libxml (https://github.com/aflgo/aflgo/issues/41), 
## We have not yet encountered a problem with binutils.
make -j || exit 1
cd ../
cp $DIRNAME/binutils/objdump ./objdump || exit 1
cp $DIRNAME/binutils/objcopy ./objcopy || exit 1


# CFLAGS="-DFORTIFY_SOURCE=2 -fstack-protector-all -fno-omit-frame-pointer -g -Wno-error -g -O0 -fcommon -Wno-error -fsanitize=undefined,address" ./configure $CONFIG_OPTIONS
