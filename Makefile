SHELL := /bin/bash

BUILD_DIR := build
BIN := $(BUILD_DIR)/vp8uya
TOOLCHAIN_HELLO := $(BUILD_DIR)/toolchain_hello
SAMPLE_IVF := $(BUILD_DIR)/sample.ivf
SRC := src/main.uya
TOOLCHAIN_HELLO_SRC := tests/toolchain_hello.uya
UYA_TESTS := src/vp8_bitstream_readers_test.uya src/vp8_bitstream_header_test.uya src/vp8_bitstream_bool_reader_test.uya src/vp8_bitstream_bool_writer_test.uya src/vp8_container_ivf_test.uya src/vp8_container_raw_test.uya src/vp8_common_plane_test.uya src/vp8_common_frame_alloc_test.uya src/vp8_common_frame_test.uya src/vp8_common_mb_grid_test.uya src/vp8_common_mb_info_test.uya src/vp8_common_mode_context_test.uya src/vp8_common_coeff_context_test.uya src/vp8_common_scratch_test.uya src/vp8_mode_parse_test.uya
LOCAL_UYA := /media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya
UYA ?= $(shell if command -v uya >/dev/null 2>&1; then command -v uya; elif test -x "$(LOCAL_UYA)"; then printf '%s' "$(LOCAL_UYA)"; else printf '%s' uya; fi)

.PHONY: all build check check-toolchain test clean require-uya

all: build

build: require-uya $(BIN)

$(BIN): $(SRC) Makefile
	mkdir -p $(BUILD_DIR)
	$(UYA) build $(SRC) -o $@

$(TOOLCHAIN_HELLO): $(TOOLCHAIN_HELLO_SRC) Makefile
	mkdir -p $(BUILD_DIR)
	$(UYA) build $(TOOLCHAIN_HELLO_SRC) -o $@

$(SAMPLE_IVF): Makefile
	mkdir -p $(BUILD_DIR)
	printf 'DKIF\000\000\040\000VP80\200\002\340\001\036\000\000\000\001\000\000\000\001\000\000\000\000\000\000\000\003\000\000\000\000\000\000\000\000\000\000\000\252\273\314' > $@

check: require-uya
	$(UYA) check $(SRC)

check-toolchain: require-uya $(TOOLCHAIN_HELLO)
	$(TOOLCHAIN_HELLO) >/dev/null

test: build check-toolchain $(SAMPLE_IVF)
	set -e; for test_src in $(UYA_TESTS); do $(UYA) test $$test_src; done
	test -x $(BIN)
	$(BIN) --help >/dev/null
	$(BIN) version >/dev/null
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.frame_count=1'
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.width=640'
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.height=480'
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.fps=30/1'
	printf 'BAD' > $(BUILD_DIR)/short.ivf
	$(BIN) info $(BUILD_DIR)/short.ivf >/dev/null || test $$? -eq 2
	$(BIN) decode sample.ivf --yuv out.yuv >/dev/null || test $$? -eq 2

require-uya:
	@if ! command -v "$(UYA)" >/dev/null 2>&1 && ! test -x "$(UYA)"; then \
		printf '%s\n' "UYA compiler not found. Set UYA=/path/to/uya or install uya in PATH." >&2; \
		exit 127; \
	fi

clean:
	rm -rf $(BUILD_DIR) .uyacache
