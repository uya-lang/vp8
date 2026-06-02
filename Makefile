SHELL := /bin/bash

BUILD_DIR := build
BIN := $(BUILD_DIR)/vp8uya
SRC := src/main.uya
LOCAL_UYA := /media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya
UYA ?= $(shell if command -v uya >/dev/null 2>&1; then command -v uya; elif test -x "$(LOCAL_UYA)"; then printf '%s' "$(LOCAL_UYA)"; else printf '%s' uya; fi)

.PHONY: all build check test clean require-uya

all: build

build: require-uya $(BIN)

$(BIN): $(SRC) Makefile
	mkdir -p $(BUILD_DIR)
	$(UYA) build $(SRC) -o $@

check: require-uya
	$(UYA) check $(SRC)

test: build
	test -x $(BIN)
	$(BIN) --help >/dev/null
	$(BIN) version >/dev/null
	$(BIN) info sample.ivf >/dev/null || test $$? -eq 2
	$(BIN) decode sample.ivf --yuv out.yuv >/dev/null || test $$? -eq 2

require-uya:
	@if ! command -v "$(UYA)" >/dev/null 2>&1 && ! test -x "$(UYA)"; then \
		printf '%s\n' "UYA compiler not found. Set UYA=/path/to/uya or install uya in PATH." >&2; \
		exit 127; \
	fi

clean:
	rm -rf $(BUILD_DIR) .uyacache
