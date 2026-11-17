HOST_CC ?= cc
PS5_PAYLOAD_SDK ?= /opt/ps5-payload-sdk
PS5_CC = $(PS5_PAYLOAD_SDK)/bin/prospero-clang
FLAGS = -std=c11 -O2 -Wall -Wextra -Werror
.PHONY: host ps5 clean
host: build/payloadforge-preflight-host
	./build/payloadforge-preflight-host
build/payloadforge-preflight-host: core.c core.h sha256.c sha256.h zip.c zip.h preflight.c
	mkdir -p build
	$(HOST_CC) $(FLAGS) core.c sha256.c zip.c preflight.c -o $@
ps5: build/payloadforge-preflight.elf
build/payloadforge-preflight.elf: core.c core.h sha256.c sha256.h zip.c zip.h preflight.c
	test -x "$(PS5_CC)"
	mkdir -p build
	"$(PS5_CC)" $(FLAGS) core.c sha256.c zip.c preflight.c -o $@
clean:
	rm -rf build
