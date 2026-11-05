package mars.mips.instructions.syscalls;
import mars.*;
import mars.mips.hardware.*;
import mars.ext.Host;
/** Headless version of the MARS dialog syscall: the front end shows the dialog. */
public class SyscallConfirmDialog extends AbstractSyscall {
   public SyscallConfirmDialog() { super(50, "ConfirmDialog"); }
   static String str(ProgramStatement st, int addr) throws ProcessingException {
      StringBuilder sb = new StringBuilder();
      try { int c; while ((c = Globals.memory.getByte(addr++)) != 0) sb.append((char) (c & 0xff)); }
      catch (AddressErrorException e) { throw new ProcessingException(st, e); }
      return sb.toString();
   }
   public void simulate(ProgramStatement statement) throws ProcessingException {
      String msg = str(statement, RegisterFile.getValue(4));
      String v = Host.Registry.get().dialog("confirm", msg, 3);
      int r = 2;
      try { if (v != null) r = Integer.parseInt(v.trim()); } catch (NumberFormatException e) { r = 2; }
      RegisterFile.updateRegister(4, r);
   }
}
