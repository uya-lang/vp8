## Summary
The UYA single-file C99 backend emits private helper functions from different modules with unqualified C symbol names, so same-named non-exported helpers collide at host C compile time.

## Affected Tasks
实现 `encode <input.yuv> --width --height --out out.ivf`。

## Toolchain Command
`/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya build --no-split-c .agent/toolchain-bugs/repros/20260604-002756-private-helper-symbol-collision/main.uya -o build/private-helper-symbol-collision-repro`

## Actual Error
`error: redefinition of 'shared_private'` from generated C containing two `static` functions named `shared_private`. The same issue blocks `make test` at `src/vp8_kernels_simd_test.uya` with duplicate helpers such as `abs_i32`, `signed_char_clamp`, and `subpixel_offset_index`.

## Expected Behavior
Private helpers from different UYA modules should lower to unique C symbols or separate translation units so same-named internal helpers do not collide.

## Repro File
`.agent/toolchain-bugs/repros/20260604-002756-private-helper-symbol-collision/main.uya`

## Repro Code
```uya
use left.mod.left_value;
use right.mod.right_value;

export extern fn main() i32 {
    return left_value() + right_value();
}
```

## Notes
The repro also includes `.agent/toolchain-bugs/repros/20260604-002756-private-helper-symbol-collision/left/mod.uya` and `.agent/toolchain-bugs/repros/20260604-002756-private-helper-symbol-collision/right/mod.uya`; each module defines a private helper named `shared_private` and one exported wrapper.
