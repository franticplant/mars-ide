# .eqv, .macro with arguments, .include
        .include "inc_print.asm"
        .eqv  LIMIT 4
        .text
main:   li   $s0, 0
loop:   print_int($s0)
        addi $s0, $s0, 1
        blt  $s0, LIMIT, loop
        done
