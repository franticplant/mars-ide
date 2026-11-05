package mars.mips.instructions.syscalls;
import mars.*;
import mars.mips.hardware.*;
import mars.ext.Host;
/** Headless version of the MARS dialog syscall: the front end shows the dialog. */
public class SyscallMessageDialogDouble extends AbstractSyscall {
   public SyscallMessageDialogDouble() { super(58, "MessageDialogDouble"); }
   static String str(ProgramStatement st, int addr) throws ProcessingException {
      StringBuilder sb = new StringBuilder();
      try { int c; while ((c = Globals.memory.getByte(addr++)) != 0) sb.append((char) (c & 0xff)); }
      catch (AddressErrorException e) { throw new ProcessingException(st, e); }
      return sb.toString();
   }
   public void simulate(ProgramStatement statement) throws ProcessingException {
      String msg = str(statement, RegisterFile.getValue(4));
      try { Host.Registry.get().dialog("message", msg + mars.ext.IO.doubleText(Coprocessor1.getDoubleFromRegisterPair(12)), 1); }
      catch (InvalidRegisterAccessException e) { throw new ProcessingException(statement, "invalid int reg. access during double output (syscall) " + e); }
   }
}
