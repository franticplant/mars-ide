        .macro print_int (%r)
        li   $v0, 1
        move $a0, %r
        syscall
        li   $v0, 11
        li   $a0, 44
        syscall
        .end_macro
        .macro done
        li   $v0, 10
        syscall
        .end_macro
