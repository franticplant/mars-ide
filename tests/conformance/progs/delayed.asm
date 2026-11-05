# @mars: db
# with delayed branching the instruction after a branch always executes
        .text
main:   li   $t0, 0
        li   $t1, 0
        b    next
        addi $t0, $t0, 1
        addi $t1, $t1, 1
next:   jal  f
        addi $t0, $t0, 10
        li   $v0, 10
        syscall
f:      jr   $ra
        addi $t1, $t1, 100
