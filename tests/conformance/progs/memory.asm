# loads/stores of every width, data directives, alignment; ends with an unaligned store error
        .data
b:      .byte   1, -2, 127, -128
h:      .half   1000, -1000
        .align  2
w:      .word   0x12345678, -1
sp1:    .space  16
str:    .asciiz "MIPS"
        .text
main:   la   $t0, b
        lb   $s0, 1($t0)
        lbu  $s1, 1($t0)
        la   $t0, h
        lh   $s2, 2($t0)
        lhu  $s3, 2($t0)
        la   $t0, w
        lw   $s4, 0($t0)
        lw   $s5, 4($t0)
        la   $t1, sp1
        sw   $s4, 0($t1)
        sh   $s2, 4($t1)
        sb   $s0, 6($t1)
        lw   $s6, 4($t1)
        la   $t2, str
        lbu  $s7, 3($t2)
        li   $v0, 4
        move $a0, $t2
        syscall
        sw   $s4, 2($t1)
        li   $v0, 10
        syscall
