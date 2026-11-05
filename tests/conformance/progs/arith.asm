# integer arithmetic, logic, shifts, set-on-less-than, mult/div, printing
        .text
main:   li   $t0, 1234567
        li   $t1, -89
        add  $s0, $t0, $t1
        sub  $s1, $t1, $t0
        mult $t0, $t1
        mfhi $s2
        mflo $s3
        div  $t0, $t1
        mfhi $s4
        mflo $s5
        and  $s6, $t0, 0xff00
        or   $s7, $t1, $t0
        xor  $t2, $t0, $t1
        nor  $t3, $t0, $zero
        sll  $t4, $t0, 7
        srl  $t5, $t1, 3
        sra  $t6, $t1, 3
        slt  $t7, $t1, $t0
        sltu $t8, $t1, $t0
        lui  $t9, 0xdead
        ori  $t9, $t9, 0xbeef
        li   $v0, 1
        move $a0, $s3
        syscall
        li   $v0, 11
        li   $a0, 10
        syscall
        li   $v0, 34
        move $a0, $t9
        syscall
        li   $v0, 11
        li   $a0, 10
        syscall
        li   $v0, 35
        move $a0, $t6
        syscall
        li   $v0, 11
        li   $a0, 10
        syscall
        li   $v0, 36
        move $a0, $t1
        syscall
        li   $v0, 10
        syscall
