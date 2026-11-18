HOST_CC ?= cc
PS5_PAYLOAD_SDK ?= /opt/ps5-payload-sdk
PS5_CC = $(PS5_PAYLOAD_SDK)/bin/prospero-clang
FLAGS = -std=c11 -O2 -Wall -Wextra -Werror
ZLIB_DIR ?= $(CURDIR)/build/zlib
ZLIB_FILES = adler32.c crc32.c inflate.c inffast.c inftrees.c zutil.c
ZLIB_SRC = $(addprefix $(ZLIB_DIR)/,$(ZLIB_FILES))
.PHONY: host ps5 clean
host: build/payloadforge-preflight-host
	./build/payloadforge-preflight-host
build/payloadforge-preflight-host: core.c core.h sha256.c sha256.h zip.c zip.h manifest.c manifest.h store.c store.h version.c version.h constraints.c constraints.h inflate.c inflate.h tar.c tar.h http.c http.h transport.c transport.h preflight.c
	mkdir -p build
	$(HOST_CC) $(FLAGS) core.c sha256.c zip.c manifest.c store.c version.c constraints.c inflate.c tar.c http.c transport.c preflight.c -o $@ -lz
ps5: build/payloadforge-preflight.elf
build/payloadforge-preflight.elf: core.c core.h sha256.c sha256.h zip.c zip.h manifest.c manifest.h store.c store.h version.c version.h constraints.c constraints.h inflate.c inflate.h tar.c tar.h http.c http.h transport.c transport.h preflight.c
	test -x "$(PS5_CC)"
	test -f "$(ZLIB_DIR)/zlib.h"
	mkdir -p build
	"$(PS5_CC)" $(FLAGS) -DZ_SOLO -I"$(ZLIB_DIR)" core.c sha256.c zip.c manifest.c store.c version.c constraints.c inflate.c tar.c http.c transport.c preflight.c $(ZLIB_SRC) -o $@
clean:
	rm -rf build
