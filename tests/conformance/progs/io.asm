# console input: int, string, char; output of each
        .data
buf:    .space 32
p1:     .asciiz "int? "
p2:     .asciiz "string? "
p3:     .asciiz "char? "
nl:     .asciiz "\n"
        .text
main:   li $v0, 4
        la $a0, p1
        syscall
        li $v0, 5
        syscall
        move $s0, $v0
        li $v0, 4
        la $a0, p2
        syscall
        li $v0, 8
        la $a0, buf
        li $a1, 32
        syscall
        li $v0, 4
        la $a0, p3
        syscall
        li $v0, 12
        syscall
        move $s1, $v0
        li $v0, 4
        la $a0, nl
        syscall
        li $v0, 1
        sll $a0, $s0, 1
        syscall
        li $v0, 4
        la $a0, buf
        syscall
        li $v0, 11
        move $a0, $s1
        syscall
        li $v0, 10
        syscall
