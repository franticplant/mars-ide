# a kernel exception handler: catch the overflow, skip the instruction, continue
        .text
main:   li   $t0, 0x7fffffff
        addi $t1, $t0, 1
        li   $s0, 77
        li   $v0, 1
        move $a0, $s0
        syscall
        li   $v0, 10
        syscall
        .ktext 0x80000180
        mfc0 $k0, $13
        srl  $k0, $k0, 2
        andi $k1, $k0, 31
        mfc0 $k0, $14
        addi $k0, $k0, 4
        mtc0 $k0, $14
        eret
