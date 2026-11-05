# pseudo-instructions expanded by the assembler
        .text
main:   li   $t0, 0x12345678
        li   $t1, -5
        abs  $s0, $t1
        neg  $s1, $t0
        not  $s2, $t1
        mul  $s3, $t0, 3
        div  $s4, $t0, 7
        rem  $s5, $t0, 7
        seq  $s6, $t1, -5
        sne  $s7, $t1, -5
        rol  $t2, $t0, 8
        ror  $t3, $t0, 8
        sge  $t4, $t0, $t1
        sgtu $t5, $t1, $t0
        li   $t6, 0
        li   $t7, 3
loop:   addi $t6, $t6, 2
        blt  $t6, $t7, loop
        bge  $t6, 100, far
        ble  $t6, $t7, far
        bgt  $t6, 5, far
        li   $v0, 10
        syscall
far:    li   $t8, 99
        li   $v0, 10
        syscall
