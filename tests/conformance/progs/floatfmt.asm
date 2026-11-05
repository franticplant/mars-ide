# float/double printing must match Java's Float/Double.toString exactly
        .data
fl:     .word 0x00000001, 0x7f7fffff, 0x00800000, 0x4b189680, 0x4b18967f, 0x3a83126f, 0x3a83126e, 0x3eaaaaab, 0x80000000, 0x7fc00000, 0x7f800000, 0xff800000, 0x47f12065, 0x37a7c5ac, 0x40490fdb, 0x3dcccccd
dl:     .word 0x00000001, 0x00000000, 0xffffffff, 0x7fefffff, 0x00000000, 0x416312d0, 0x9999999a, 0x3fb99999, 0xd2f1a9fc, 0x3f50624d, 0x55555555, 0x3fd55555, 0x54442d18, 0x400921fb, 0x00000000, 0x44b52d02
        .text
main:   la   $s0, fl
        li   $s1, 16
floop:  lwc1 $f12, 0($s0)
        li   $v0, 2
        syscall
        li   $v0, 11
        li   $a0, 10
        syscall
        addi $s0, $s0, 4
        addi $s1, $s1, -1
        bnez $s1, floop
        la   $s0, dl
        li   $s1, 8
dloop:  lwc1 $f12, 0($s0)
        lwc1 $f13, 4($s0)
        li   $v0, 3
        syscall
        li   $v0, 11
        li   $a0, 10
        syscall
        addi $s0, $s0, 8
        addi $s1, $s1, -1
        bnez $s1, dloop
        li   $v0, 10
        syscall
