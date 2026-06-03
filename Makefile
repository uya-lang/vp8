SHELL := /bin/bash

BUILD_DIR := build
BIN := $(BUILD_DIR)/vp8uya
TOOLCHAIN_HELLO := $(BUILD_DIR)/toolchain_hello
SAMPLE_IVF := $(BUILD_DIR)/sample.ivf
TINY_MD5_DIR := $(BUILD_DIR)/tiny-md5
TINY_MD5_SCRIPT := tests/tiny_ivf_md5.py
SCALAR_VS_SIMD_DIR := $(BUILD_DIR)/scalar-vs-simd
SCALAR_VS_SIMD_SCRIPT := tests/scalar_vs_simd.py
BENCH_DIR := $(BUILD_DIR)/bench
BENCH_SCRIPT := bench/decode_bench.py
KERNEL_THRESHOLDS := bench/kernel_thresholds.json
KERNEL_THRESHOLDS_SCRIPT := bench/check_kernel_thresholds.py
SIMD_CODEGEN_DIR := $(BUILD_DIR)/simd-codegen
SIMD_CODEGEN_SCRIPT := tools/check_simd_codegen.py
KEYFRAME_MD5_DIR := $(BUILD_DIR)/keyframe-md5
INTER_MD5_DIR := $(BUILD_DIR)/inter-md5
NON16_MD5_DIR := $(BUILD_DIR)/non16-md5
SEGMENTATION_MD5_DIR := $(BUILD_DIR)/segmentation-md5
TOKEN_PARTITION_MD5_DIR := $(BUILD_DIR)/token-partition-md5
MALFORMED_IVF_DIR := $(BUILD_DIR)/malformed-ivf
MALFORMED_IVF_SCRIPT := tests/malformed_ivf.py
MALFORMED_VP8_DIR := $(BUILD_DIR)/malformed-vp8
MALFORMED_VP8_SCRIPT := tests/malformed_vp8.py
FUZZ_SMOKE_DIR := $(BUILD_DIR)/fuzz-smoke
FUZZ_SMOKE_SCRIPT := tests/fuzz_smoke.py
VPXDIFF_DIR := $(BUILD_DIR)/vpxdiff
VPXDIFF_SCRIPT := tests/vpxdiff.py
SRC := src/main.uya
SRC_FILES := $(shell find src -name '*.uya' -print)
TOOLCHAIN_HELLO_SRC := tests/toolchain_hello.uya
VECTOR_CAPABILITY_TEST := src/vp8_vector_capability_test.uya
ASM_X86_TEST := src/vp8_kernels_asm_x86_test.uya
UYA_TESTS := src/vp8_bitstream_readers_test.uya src/vp8_bitstream_header_test.uya src/vp8_bitstream_bool_reader_test.uya src/vp8_bitstream_bool_writer_test.uya src/vp8_container_ivf_test.uya src/vp8_container_raw_test.uya src/vp8_common_plane_test.uya src/vp8_common_frame_alloc_test.uya src/vp8_common_frame_test.uya src/vp8_common_mb_grid_test.uya src/vp8_common_mb_info_test.uya src/vp8_common_mode_context_test.uya src/vp8_common_coeff_context_test.uya src/vp8_common_scratch_test.uya src/vp8_common_decode_context_test.uya src/vp8_common_cpu_test.uya $(VECTOR_CAPABILITY_TEST) src/vp8_mode_parse_test.uya src/vp8_token_parse_test.uya src/vp8_kernels_scalar_test.uya src/vp8_kernels_dispatch_test.uya src/vp8_kernels_simd_test.uya src/vp8_decoder_token_partition_test.uya src/vp8_decoder_row_pipeline_test.uya src/vp8_decoder_scalar_test.uya
SCALAR_DECODER_TESTS := $(UYA_TESTS)
LOCAL_UYA := /media/winger/_dde_home/winger/uya/uya/bin/uya
UYA ?= $(shell if command -v uya >/dev/null 2>&1; then command -v uya; elif test -x "$(LOCAL_UYA)"; then printf '%s' "$(LOCAL_UYA)"; else printf '%s' uya; fi)

.PHONY: all build check check-toolchain check-simd-codegen check-kernel-thresholds test test-decoder-scalar test-vector-capabilities test-asm-x86 test-tiny-md5 test-scalar-vs-simd test-keyframe-md5 test-inter-md5 test-non16-md5 test-segmentation-md5 test-token-partition-md5 test-malformed-ivf test-malformed-vp8 test-fuzz-smoke test-vpxdiff bench bench-decode bench-smoke clean require-uya

all: build

build: require-uya $(BIN)

$(BIN): $(SRC_FILES) Makefile
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

check-simd-codegen: require-uya
	python3 $(SIMD_CODEGEN_SCRIPT) --uya $(UYA) --out-dir $(SIMD_CODEGEN_DIR) --report docs/simd_codegen.md

check-kernel-thresholds:
	python3 $(KERNEL_THRESHOLDS_SCRIPT) $(KERNEL_THRESHOLDS)

test: build check-toolchain $(SAMPLE_IVF)
	$(MAKE) check-kernel-thresholds
	$(MAKE) test-decoder-scalar
	test -x $(BIN)
	$(BIN) --help >/dev/null
	$(BIN) version >/dev/null
	$(BIN) --force-scalar version >/dev/null
	$(BIN) --force-simd version >/dev/null
	VP8UYA_FORCE_SCALAR=1 $(BIN) version >/dev/null
	VP8UYA_FORCE_SIMD=1 $(BIN) version >/dev/null
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.frame_count=1'
	$(BIN) --force-scalar info $(SAMPLE_IVF) | grep -q 'ivf.frame_count=1'
	$(BIN) --force-simd info $(SAMPLE_IVF) | grep -q 'ivf.frame_count=1'
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.width=640'
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.height=480'
	$(BIN) info $(SAMPLE_IVF) | grep -q 'ivf.fps=30/1'
	printf 'BAD' > $(BUILD_DIR)/short.ivf
	$(BIN) info $(BUILD_DIR)/short.ivf >/dev/null || test $$? -eq 2
	$(BIN) decode sample.ivf --yuv out.yuv >/dev/null || test $$? -eq 2
	$(MAKE) test-malformed-ivf
	$(MAKE) test-malformed-vp8
	$(MAKE) test-fuzz-smoke
	$(MAKE) test-scalar-vs-simd
	$(MAKE) test-asm-x86

test-decoder-scalar: build
	set -e; for test_src in $(SCALAR_DECODER_TESTS); do VP8UYA_FORCE_SCALAR=1 $(UYA) test $$test_src; done
	VP8UYA_FORCE_SCALAR=1 python3 $(TINY_MD5_SCRIPT) $(BIN) $(TINY_MD5_DIR)

test-vector-capabilities: require-uya
	$(UYA) test $(VECTOR_CAPABILITY_TEST)

test-asm-x86: require-uya
	@arch="$$(uname -m 2>/dev/null || printf unknown)"; \
	if [[ "$$arch" == "x86_64" || "$$arch" == "amd64" ]]; then \
		$(UYA) test $(ASM_X86_TEST); \
	else \
		printf '%s\n' "Skipping x86 asm kernel test on $$arch host."; \
	fi

test-tiny-md5: build
	python3 $(TINY_MD5_SCRIPT) $(BIN) $(TINY_MD5_DIR)

test-scalar-vs-simd: build
	python3 $(SCALAR_VS_SIMD_SCRIPT) $(BIN) $(SCALAR_VS_SIMD_DIR)

test-keyframe-md5: build
	python3 $(TINY_MD5_SCRIPT) --group key $(BIN) $(KEYFRAME_MD5_DIR)

test-inter-md5: build
	python3 $(TINY_MD5_SCRIPT) --group inter $(BIN) $(INTER_MD5_DIR)

test-non16-md5: build
	python3 $(TINY_MD5_SCRIPT) --group non16 $(BIN) $(NON16_MD5_DIR)

test-segmentation-md5: build
	python3 $(TINY_MD5_SCRIPT) --group segmentation $(BIN) $(SEGMENTATION_MD5_DIR)

test-token-partition-md5: build
	python3 $(TINY_MD5_SCRIPT) --group token-partition $(BIN) $(TOKEN_PARTITION_MD5_DIR)

test-malformed-ivf: build
	python3 $(MALFORMED_IVF_SCRIPT) $(BIN) $(MALFORMED_IVF_DIR)

test-malformed-vp8: build
	python3 $(MALFORMED_VP8_SCRIPT) $(BIN) $(MALFORMED_VP8_DIR)

test-fuzz-smoke: build
	python3 $(FUZZ_SMOKE_SCRIPT) $(BIN) $(FUZZ_SMOKE_DIR)

test-vpxdiff: build
	python3 $(VPXDIFF_SCRIPT) $(VPXDIFF_DIR) $(BIN)

bench: bench-decode

bench-decode: build
	python3 $(BENCH_SCRIPT) $(BIN) $(BENCH_DIR)

bench-smoke: build
	python3 $(BENCH_SCRIPT) --repeats 1 --warmups 0 $(BIN) $(BENCH_DIR)

require-uya:
	@if ! command -v "$(UYA)" >/dev/null 2>&1 && ! test -x "$(UYA)"; then \
		printf '%s\n' "UYA compiler not found. Set UYA=/path/to/uya or install uya in PATH." >&2; \
		exit 127; \
	fi

clean:
	rm -rf $(BUILD_DIR) .uyacache
