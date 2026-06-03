# 基准测试

本目录包含基准测试工具、基线记录和性能说明。

基准测试不应成为普通正确性测试的前置要求。标量和 SIMD 路径应使用
可比较的输入，并报告足够上下文，用来解释运行时间变化、分配行为，以及
对内存带宽敏感的路径。

`decode_bench.py` 会使用 `--force-scalar` 和 `--force-simd` 分别对生成的
IVF 解码样本进行基准测试，校验 YUV MD5，记录逐帧解码器统计信息，并在所选
输出目录下写入 `results.ndjson` 和 `summary.json`。每条结果都包含帧率
（fps）、每像素周期数（cycles/pixel）、线程数、每帧复制字节数和分配次数。

使用 `make bench-smoke` 做快速的单次重复验证；使用
`make bench-decode` 运行默认的重复 decode 基准测试。使用
`make bench-1080p-smoke` 生成并测试一个合成的 1920x1080 样本，该样本使用
四个解码器工作线程 scratch arena。

`kernel_thresholds.json` 定义未来 SIMD kernel 基准测试的默认启用门槛。
`make check-kernel-thresholds` 用于校验该表。加速比指标为
`scalar_median_ns / simd_median_ns`；内存受限 kernel 必须达到 1.10x，
计算密集型 kernel 必须达到 1.25x，端到端 decoder forced-SIMD 路径相比
forced scalar 不能慢超过 5%。每个默认启用的 kernel 还需要位精确输出、
代码生成检查和基准测试证据。
