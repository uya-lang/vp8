# UYA SIMD 缺口记录

## 证据来源

- `../uya/docs/uya.md` 的 SIMD 第一阶段暂缓项仍列出 `shuffle` 和 `widen/truncate/bitcast/convert`。
- `../uya/docs/grammar_quick.md` 的 SIMD 表列出当前已支持的 vector 运算：基础算术/比较/位运算、`@vector.splat`、`load/store/select`、`reduce_*`、`any/all`，以及有符号整数向量 `+|` / `-|` / `*|`。
- `make test-vector-capabilities` 已在本项目验证 signed `i16` / `i32` vector saturating arithmetic 可编译并通过运行时断言。
- UYA 负例 `../uya/tests/error_simd_u32_vector_plus_pipe.uya` 当前报错：`向量饱和运算仅支持有符号整数元素类型的 @vector(T, N)`。

## VP8 相关缺口

| capability | current UYA state | VP8 impact | current fallback |
| --- | --- | --- | --- |
| widen | no direct vector widen from narrow lanes to wider lanes | SAD、sub-pixel filter、loop filter 中的 `u8 -> i16/i32` 中间值需要额外步骤 | scalar tile helper 或拆成多个 scalar lanes |
| narrow / truncate / convert | no direct vector narrow or lane conversion builtin | residual add/clamp、inverse transform 后写回 `u8` 时缺少 `i16/i32 -> u8` vector path | scalar clamp and store；未来可用 `@vector.select` 组合局部替代 |
| shuffle / lane shift | no `@vector.shuffle` or lane permute builtin | 6-tap sub-pixel、transpose、loop filter 邻域重排难以表达 | multiple loads plus scalar lane handling, or optional `@asm` microkernel |
| unsigned saturating add/sub | signed vector `+|` / `-|` works, unsigned vector saturating is rejected | VP8 pixel math needs unsigned clamp semantics and narrow-to-u8 saturation | signed intermediate plus scalar clamp, or explicit compare/select when practical |

## 设计约束

- 依赖这些能力的 kernel 不进入默认 dispatcher，除非有 scalar-vs-simd 正确性、生成代码检查和 benchmark 阈值证据。
- SIMD kernel 接口应先保留 scalar fallback，避免把缺失 builtin 写进 hot path 的默认路径。
- 需要向 UYA 编译器反馈或实现的能力：`@vector.shuffle` / lane extract、`widen` / `narrow` / `convert`、unsigned 或 narrow saturating arithmetic。
