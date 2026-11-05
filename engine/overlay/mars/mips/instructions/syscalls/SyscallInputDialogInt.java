package mars.mips.instructions.syscalls;
import mars.*;
import mars.mips.hardware.*;
import mars.ext.Host;
/** Headless version of the MARS dialog syscall: the front end shows the dialog. */
public class SyscallInputDialogInt extends AbstractSyscall {
   public SyscallInputDialogInt() { super(51, "InputDialogInt"); }
   static String str(ProgramStatement st, int addr) throws ProcessingException {
      StringBuilder sb = new StringBuilder();
      try { int c; while ((c = Globals.memory.getByte(addr++)) != 0) sb.append((char) (c & 0xff)); }
      catch (AddressErrorException e) { throw new ProcessingException(st, e); }
      return sb.toString();
   }
   public void simulate(ProgramStatement statement) throws ProcessingException {
      String msg = str(statement, RegisterFile.getValue(4));
      String v = Host.Registry.get().dialog("int", msg, 3);
      if (v == null) { RegisterFile.updateRegister(4, 0); RegisterFile.updateRegister(5, -2); return; }
      if (v.trim().isEmpty()) { RegisterFile.updateRegister(4, 0); RegisterFile.updateRegister(5, -3); return; }
      try { RegisterFile.updateRegister(4, Integer.decode(v.trim())); RegisterFile.updateRegister(5, 0); }
      catch (NumberFormatException e) { RegisterFile.updateRegister(4, 0); RegisterFile.updateRegister(5, -1); }
   }
}
