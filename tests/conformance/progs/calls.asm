# recursion through the stack: factorial and fibonacci, jal/jr, frames
        .text
main:   li   $a0, 10
        jal  fact
        move $s0, $v0
        li   $v0, 1
        move $a0, $s0
        syscall
        li   $v0, 11
        li   $a0, 32
        syscall
        li   $a0, 15
        jal  fib
        move $s1, $v0
        li   $v0, 1
        move $a0, $s1
        syscall
        li   $v0, 10
        syscall
fact:   addi $sp, $sp, -8
        sw   $ra, 4($sp)
        sw   $a0, 0($sp)
        li   $v0, 1
        blez $a0, fdone
        addi $a0, $a0, -1
        jal  fact
        lw   $a0, 0($sp)
        mul  $v0, $v0, $a0
fdone:  lw   $ra, 4($sp)
        addi $sp, $sp, 8
        jr   $ra
fib:    addi $sp, $sp, -12
        sw   $ra, 8($sp)
        sw   $a0, 4($sp)
        move $v0, $a0
        slti $t0, $a0, 2
        bnez $t0, fbdone
        addi $a0, $a0, -1
        jal  fib
        sw   $v0, 0($sp)
        lw   $a0, 4($sp)
        addi $a0, $a0, -2
        jal  fib
        lw   $t1, 0($sp)
        add  $v0, $v0, $t1
fbdone: lw   $ra, 8($sp)
        addi $sp, $sp, 12
        jr   $ra
