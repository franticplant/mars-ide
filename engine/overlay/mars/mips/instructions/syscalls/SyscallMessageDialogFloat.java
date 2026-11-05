package mars.mips.instructions.syscalls;
import mars.*;
import mars.mips.hardware.*;
import mars.ext.Host;
/** Headless version of the MARS dialog syscall: the front end shows the dialog. */
public class SyscallMessageDialogFloat extends AbstractSyscall {
   public SyscallMessageDialogFloat() { super(57, "MessageDialogFloat"); }
   static String str(ProgramStatement st, int addr) throws ProcessingException {
      StringBuilder sb = new StringBuilder();
      try { int c; while ((c = Globals.memory.getByte(addr++)) != 0) sb.append((char) (c & 0xff)); }
      catch (AddressErrorException e) { throw new ProcessingException(st, e); }
      return sb.toString();
   }
   public void simulate(ProgramStatement statement) throws ProcessingException {
      String msg = str(statement, RegisterFile.getValue(4));
      Host.Registry.get().dialog("message", msg + mars.ext.IO.floatText(Coprocessor1.getFloatFromRegister(12)), 1);
   }
}
