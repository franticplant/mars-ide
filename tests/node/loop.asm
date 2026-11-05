        .text
main:   li $t0, 0
        li $t1, 2000000
loop:   addi $t0, $t0, 1
        bne $t0, $t1, loop
        li $v0, 1
        move $a0, $t0
        syscall
        li $v0, 10
        syscall
