/* Small, illustrative MARS snippets for the instructions on the reference card. */
(function (global) {
  "use strict";
  const examples = Object.create(null);
  const add = (names, build) => names.split(" ").forEach(name => { examples[name] = build(name); });
  add("add addu sub subu and or nor xor slt sltu", op => `li    $t0, 12\nli    $t1, 5\n${op.padEnd(5)} $t2, $t0, $t1  # result in $t2`);
  add("addi addiu andi ori xori slti sltiu", op => `li    $t0, 12\n${op.padEnd(5)} $t1, $t0, 5   # result in $t1`);
  add("mult multu div divu", op => `li    $t0, 20\nli    $t1, 6\n${op.padEnd(5)} $t0, $t1\nmflo  $t2            # ${op.startsWith("div") ? "quotient" : "low 32 bits of product"}\nmfhi  $t3            # ${op.startsWith("div") ? "remainder" : "high 32 bits of product"}`);
  add("mfhi mflo", op => `li    $t0, 20\nli    $t1, 6\ndiv   $t0, $t1\n${op.padEnd(5)} $t2            # ${op === "mfhi" ? "remainder = 2" : "quotient = 3"}`);
  add("sll srl sra", op => `li    $t0, 16\n${op.padEnd(5)} $t1, $t0, 2   # shift by 2 bits`);
  add("sllv srlv srav", op => `li    $t0, 16\nli    $t1, 2\n${op.padEnd(5)} $t2, $t0, $t1  # shift amount comes from $t1`);
  add("beq bne bge bgt ble blt", op => {
    const right = ["bne", "bgt"].includes(op) ? 3 : op === "blt" ? 7 : 5;
    return `li    $t0, 5\nli    $t1, ${right}\n${op.padEnd(5)} $t0, $t1, matched\nnop                   # safe whether delayed branching is on or off\nli    $s0, 0          # skipped when branch is taken\nj     done\nnop\nmatched:\n  li  $s0, 1          # branch condition was true\ndone:\n  nop`;
  });
  examples.j = `j     done\nnop                   # safe delay slot\nli    $t0, 1          # skipped by the jump\ndone:\n  li  $v0, 10`;
  examples.jal = `jal   double_it\nnop                   # safe delay slot\n# $v0 contains the result here\nj     done\nnop\ndouble_it:\n  addu $v0, $a0, $a0\n  jr   $ra\n  nop\ndone:`;
  examples.jr = `# A routine returns to the address saved by jal.\ndouble_it:\n  addu $v0, $a0, $a0\n  jr   $ra\n  nop                   # safe delay slot`;
  examples.jalr = `la    $t0, double_it\njalr  $t0             # call address in $t0; return address in $ra\nnop                   # safe delay slot\nj     done\nnop\ndouble_it:\n  addu $v0, $a0, $a0\n  jr   $ra\n  nop\ndone:`;
  examples.syscall = `li    $v0, 1          # MARS service 1: print integer\nli    $a0, 42         # argument\nsyscall               # prints 42`;
  examples.lui = `lui   $t0, 0x1234     # $t0 = 0x12340000\nori   $t0, $t0, 0x5678  # $t0 = 0x12345678`;
  add("lb lbu lh lhu lw ll", op => {
    const type = op === "lb" || op === "lbu" ? ".byte 0x7f" : op === "lh" || op === "lhu" ? ".half 1234" : ".word 1234";
    return `.data\nvalue: ${type}\n.text\nla    $t0, value\n${op.padEnd(5)} $t1, 0($t0)    # load from address in $t0`;
  });
  add("sb sh sw", op => {
    const type = op === "sb" ? ".byte 0" : op === "sh" ? ".half 0" : ".word 0";
    return `.data\nvalue: ${type}\n.text\nla    $t0, value\nli    $t1, 42\n${op.padEnd(5)} $t1, 0($t0)    # store at address in $t0`;
  });
  examples.sc = `.data\nvalue: .word 0\n.text\nla    $t0, value\nll    $t1, 0($t0)     # load linked\naddiu $t1, $t1, 1\nsc    $t1, 0($t0)     # attempts store; $t1 becomes success flag`;
  examples.la = `.data\nvalue: .word 42\n.text\nla    $t0, value      # address, not the word itself\nlw    $t1, 0($t0)     # $t1 = 42`;
  examples.li = `li    $t0, 42         # assembler loads a constant\naddiu $t1, $t0, 1    # $t1 = 43`;
  examples.move = `li    $t0, 42\nmove  $t1, $t0        # copy; $t0 stays unchanged`;
  examples.nop = `beq   $t0, $t1, equal\nnop                   # safe delay slot\nequal:`;
  global.MIPS_EXAMPLES = examples;
})(window);
