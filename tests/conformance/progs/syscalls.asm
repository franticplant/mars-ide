# heap allocation, seeded random numbers, time-free services, exit2
        .text
main:   li  $v0, 9
        li  $a0, 64
        syscall
        move $s0, $v0
        sw  $s0, 0($s0)
        li  $v0, 9
        li  $a0, 4
        syscall
        move $s1, $v0
        li  $v0, 40
        li  $a0, 1
        li  $a1, 12345
        syscall
        li  $v0, 41
        li  $a0, 1
        syscall
        move $s2, $a0
        li  $v0, 42
        li  $a0, 1
        li  $a1, 1000
        syscall
        move $s3, $a0
        li  $v0, 1
        move $a0, $s3
        syscall
        li  $v0, 17
        li  $a0, 3
        syscall
