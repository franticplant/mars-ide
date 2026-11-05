# hello.asm - reads a number, prints its square
        .data
prompt: .asciiz "Enter a number: "
result: .asciiz "Square = "
nl:     .asciiz "\n"

        .text
        .globl main
main:
        li   $v0, 4          # print prompt
        la   $a0, prompt
        syscall

        li   $v0, 5          # read int
        syscall
        move $t0, $v0

        mul  $t1, $t0, $t0   # square it

        li   $v0, 4
        la   $a0, result
        syscall
        li   $v0, 1
        move $a0, $t1
        syscall
        li   $v0, 4
        la   $a0, nl
        syscall

        li   $v0, 10         # exit
        syscall
