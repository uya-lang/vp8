## Summary
UYA accepts direct field access on a pointer returned by a `try` expression during type checking, but C99 codegen emits `.` field access against the pointer expression instead of `->`, causing the host C compiler to fail.

## Affected Tasks
实现 `FramePool`：current/last/golden/altref。

## Toolchain Command
`/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test .agent/toolchain-bugs/repros/20260602-234209-try-pointer-field-access.uya`

## Actual Error
The generated C fails to compile with an error equivalent to: `is a pointer; did you mean to use '->'?`

## Expected Behavior
The UYA compiler should either generate pointer field access correctly for `(try get_ptr()).field`, or reject the source during type checking with a clear diagnostic.

## Repro File
`.agent/toolchain-bugs/repros/20260602-234209-try-pointer-field-access.uya`

## Repro Code
```uya
use std.testing.assert_eq_i32;

struct Holder {
    value: i32
}

error ErrBadSlot;

fn get_holder(holder: &Holder) !&Holder {
    return holder;
}

test "try pointer field access codegen" {
    var holder: Holder = Holder{ value: 7 };
    try assert_eq_i32((try get_holder(&holder)).value, 7);
}
```

## Notes
The repository test was changed to bind the returned pointer to a local `&FrameBuffer` before field access, which avoids the invalid C generation and does not block the FramePool implementation.
