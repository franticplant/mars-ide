# a long-running loop (instruction count and timing)
        .text
main:   li $t0, 0
        li $t1, 300000
loop:   addi $t0, $t0, 1
        andi $t2, $t0, 7
        sll  $t3, $t2, 2
        bne  $t0, $t1, loop
        li $v0, 1
        move $a0, $t0
        syscall
        li $v0, 10
        syscall
