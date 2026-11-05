        .text
main:   li   $a0, 25
        jal  fib
        move $a0, $v0
        li   $v0, 1
        syscall
        li   $v0, 10
        syscall
fib:    addi $sp, $sp, -12
        sw   $ra, 8($sp)
        sw   $a0, 4($sp)
        move $v0, $a0
        slti $t0, $a0, 2
        bnez $t0, done
        addi $a0, $a0, -1
        jal  fib
        sw   $v0, 0($sp)
        lw   $a0, 4($sp)
        addi $a0, $a0, -2
        jal  fib
        lw   $t1, 0($sp)
        add  $v0, $v0, $t1
done:   lw   $ra, 8($sp)
        addi $sp, $sp, 12
        jr   $ra
