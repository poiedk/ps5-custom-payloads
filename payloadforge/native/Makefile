HOST_CC ?= cc
PS5_PAYLOAD_SDK ?= /opt/ps5-payload-sdk
PS5_CC = $(PS5_PAYLOAD_SDK)/bin/prospero-clang
PYTHON ?= python3
FLAGS = -std=c11 -O2 -Wall -Wextra -Werror
ZLIB_DIR ?= $(CURDIR)/build/zlib
ZLIB_FILES = adler32.c crc32.c inflate.c inffast.c inftrees.c zutil.c
ZLIB_SRC = $(addprefix $(ZLIB_DIR)/,$(ZLIB_FILES))
.PHONY: host ps5 host-runtime ps5-runtime host-managed ps5-managed clean
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

host-runtime: build/payloadforge-runtime-host
ps5-runtime: build/payloadforge-runtime-read-only.elf
RUNTIME_SRC = core.c sha256.c zip.c manifest.c store.c version.c constraints.c inflate.c tar.c http.c transport.c runtime.c
RUNTIME_HDR = core.h sha256.h zip.h manifest.h store.h version.h constraints.h inflate.h tar.h http.h transport.h
build/payloadforge-runtime-host: $(RUNTIME_SRC) $(RUNTIME_HDR)
	mkdir -p build
	$(HOST_CC) $(FLAGS) $(RUNTIME_SRC) -o $@ -lz
build/payloadforge-runtime-read-only.elf: $(RUNTIME_SRC) $(RUNTIME_HDR)
	test -x "$(PS5_CC)"
	test -f "$(ZLIB_DIR)/zlib.h"
	mkdir -p build
	"$(PS5_CC)" $(FLAGS) -DZ_SOLO -I"$(ZLIB_DIR)" $(RUNTIME_SRC) $(ZLIB_SRC) -o $@

UI_ASSETS = web/index.html web/ui.css web/ui.js
CATALOG_INPUTS = ../catalog_preview.py ../catalog.py ../catalog_guard.py ../catalog_inputs/pldmgr_snapshot.json ../catalog_inputs/companion_snapshot.json
build/ui_assets.h: embed_ui.py $(UI_ASSETS) $(CATALOG_INPUTS)
	$(PYTHON) embed_ui.py $@

host-managed: build/payloadforge-runtime-managed-host
ps5-managed: build/payloadforge-runtime-managed-development.elf
build/payloadforge-runtime-managed-host: $(RUNTIME_SRC) $(RUNTIME_HDR) build/ui_assets.h
	mkdir -p build
	$(HOST_CC) $(FLAGS) -DPF_ENABLE_MANAGED -DPF_ENABLE_UI -Ibuild $(RUNTIME_SRC) -o $@ -lz
build/payloadforge-runtime-managed-development.elf: $(RUNTIME_SRC) $(RUNTIME_HDR) build/ui_assets.h
	test -x "$(PS5_CC)"
	test -f "$(ZLIB_DIR)/zlib.h"
	mkdir -p build
	"$(PS5_CC)" $(FLAGS) -DPF_ENABLE_MANAGED -DPF_ENABLE_UI -Ibuild -DPF_PS5_BUILD -DZ_SOLO -I"$(ZLIB_DIR)" $(RUNTIME_SRC) $(ZLIB_SRC) -o $@
