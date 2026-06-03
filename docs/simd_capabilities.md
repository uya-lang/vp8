# UYA SIMD 编译能力记录

## 当前验证对象

- UYA 源：`src/vp8_vector_capability_test.uya`
- 复现命令：`make test-vector-capabilities`
- 后端：UYA C99 后端，随后由本机 `cc -std=c99 -O0 -g -fno-builtin` 链接测试程序。

## 已验证能力

| element type | lanes | vector type | mask type | checked operations |
| --- | ---: | --- | --- | --- |
| `u8` | 16 | `@vector(u8, 16)` | `@mask(16)` | `@vector.splat`, `+`, `==`, `@vector.all` |
| `u8` | 32 | `@vector(u8, 32)` | `@mask(32)` | `@vector.splat`, `+`, `==`, `@vector.all` |
| `u8` | 64 | `@vector(u8, 64)` | `@mask(64)` | `@vector.splat`, `+`, `==`, `@vector.all` |
| `i16` | 8 | `@vector(i16, 8)` | `@mask(8)` | `@vector.splat`, `-`, `==`, `@vector.all` |
| `i16` | 16 | `@vector(i16, 16)` | `@mask(16)` | `@vector.splat`, `+`, `==`, `@vector.all` |
| `i32` | 4 | `@vector(i32, 4)` | `@mask(4)` | `@vector.splat`, `*`, `==`, `@vector.all` |
| `i32` | 8 | `@vector(i32, 8)` | `@mask(8)` | `@vector.splat`, `+`, `==`, `@vector.all` |
| signed `i16` / `i32` | 8 / 16 / 4 / 8 | `@vector(i16, N)`, `@vector(i32, N)` | matching `@mask(N)` | `+|`, `-|`, `==`, `@vector.all` |

## 当前结论

- `@vector(u8,16/32/64)`、`@vector(i16,8/16)`、`@vector(i32,4/8)` 均可编译、生成 C、链接并通过运行时断言。
- 该验证只证明这些 vector 宽度和基础逐 lane 运算可用，不证明宽 vector 一定会降低为真实硬件 SIMD 指令。
- 宽 vector 的 load/store lowering、shuffle、widen/narrow、unsigned 或 narrow saturating arithmetic 仍需要后续专项记录。
