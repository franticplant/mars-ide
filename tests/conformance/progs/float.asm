# single and double precision, conversions, compares, printing, reading a float
        .data
a:      .float  3.25
b:      .double 2.5
        .text
main:   l.s     $f0, a
        l.d     $f2, b
        add.s   $f4, $f0, $f0
        mul.d   $f6, $f2, $f2
        cvt.d.s $f8, $f0
        add.d   $f8, $f8, $f6
        cvt.w.d $f10, $f8
        mfc1    $s0, $f10
        li      $v0, 2
        mov.s   $f12, $f4
        syscall
        li      $v0, 11
        li      $a0, 10
        syscall
        li      $v0, 3
        mov.d   $f12, $f8
        syscall
        li      $v0, 11
        li      $a0, 10
        syscall
        li      $v0, 6
        syscall
        mul.s   $f12, $f0, $f0
        li      $v0, 2
        syscall
        c.lt.s  $f0, $f4
        bc1f    skip
        li      $s1, 1
skip:   sqrt.d  $f14, $f6
        mfc1    $s2, $f14
        mfc1    $s3, $f15
        li      $v0, 10
        syscall
