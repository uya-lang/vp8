# UYA Toolchain

The local UYA compiler is available at:

```text
/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya
```

`make` also honors `UYA=/path/to/uya` and falls back to `uya` from `PATH`
before using the local path above.

The minimum toolchain smoke test is:

```sh
make check-toolchain
```

This builds `tests/toolchain_hello.uya` into `build/toolchain_hello` and runs
the resulting executable. It validates that the compiler can produce a native
hello-world binary on this machine.
