# file syscalls: create, write, close, reopen, read back, print
        .data
fn:     .asciiz "conformance_out.txt"
msg:    .asciiz "written by MIPS\n"
buf:    .space 64
        .text
main:   li $v0, 13
        la $a0, fn
        li $a1, 1
        li $a2, 0
        syscall
        move $s0, $v0
        li $v0, 15
        move $a0, $s0
        la $a1, msg
        li $a2, 16
        syscall
        move $s1, $v0
        li $v0, 16
        move $a0, $s0
        syscall
        li $v0, 13
        la $a0, fn
        li $a1, 0
        li $a2, 0
        syscall
        move $s0, $v0
        li $v0, 14
        move $a0, $s0
        la $a1, buf
        li $a2, 64
        syscall
        move $s2, $v0
        li $v0, 16
        move $a0, $s0
        syscall
        li $v0, 4
        la $a0, buf
        syscall
        li $v0, 10
        syscall
