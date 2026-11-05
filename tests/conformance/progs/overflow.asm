# signed overflow trap (no handler) → runtime error
        .text
main:   li   $t0, 0x7fffffff
        addi $t1, $t0, 1
        li   $v0, 10
        syscall
