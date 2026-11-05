# @mars: smc
# @count: quirk  (MARS's ic also counts the lw that reads an instruction word from .text)
# self-modifying code: overwrite an instruction, then execute it
        .text
main:   la   $t0, target
        lw   $t1, patch
        sw   $t1, 0($t0)
target: li   $s0, 1
        li   $v0, 1
        move $a0, $s0
        syscall
        li   $v0, 10
        syscall
patch:  addi $s0, $zero, 42
