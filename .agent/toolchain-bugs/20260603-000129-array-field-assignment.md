## Summary

Assigning an array literal to a fixed-size array field passes UYA type checking but generates invalid C initializer syntax in assignment position.

## Affected Tasks

实现 above/left coefficient context。

## Toolchain Command

`/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_coeff_context_test.uya`

## Actual Error

The generated C fails to compile with:

```text
error: expected expression before '{' token
```

## Expected Behavior

Array field assignment should either be rejected during type checking or lower to valid element-wise assignment or `memcpy` code.

## Repro File
`.agent/toolchain-bugs/repros/20260603-000129-array-field-assignment.uya`

## Repro Code

```uya
struct Holder {
    values: [byte: 2]
}

fn clear(holder: &Holder) void {
    holder.values = [ 0 as byte, 0 as byte ];
}

fn main() i32 {
    var holder: Holder = Holder{ values: [ 1 as byte, 2 as byte ] };
    clear(&holder);
    return holder.values[0] as i32;
}
```

## Notes

The coefficient context implementation works around this by clearing fixed-size array fields element by element.
