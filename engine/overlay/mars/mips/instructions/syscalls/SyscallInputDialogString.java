package mars.mips.instructions.syscalls;
import mars.*;
import mars.mips.hardware.*;
import mars.ext.Host;
/** Headless version of the MARS dialog syscall: the front end shows the dialog. */
public class SyscallInputDialogString extends AbstractSyscall {
   public SyscallInputDialogString() { super(54, "InputDialogString"); }
   static String str(ProgramStatement st, int addr) throws ProcessingException {
      StringBuilder sb = new StringBuilder();
      try { int c; while ((c = Globals.memory.getByte(addr++)) != 0) sb.append((char) (c & 0xff)); }
      catch (AddressErrorException e) { throw new ProcessingException(st, e); }
      return sb.toString();
   }
   public void simulate(ProgramStatement statement) throws ProcessingException {
      String msg = str(statement, RegisterFile.getValue(4));
      int buf = RegisterFile.getValue(5), max = RegisterFile.getValue(6);
      String v = Host.Registry.get().dialog("string", msg, 3);
      try {
         if (v == null) { RegisterFile.updateRegister(5, -2); return; }
         if (v.isEmpty()) { RegisterFile.updateRegister(5, -3); return; }
         int n = Math.min(v.length(), Math.max(0, max - 1));
         for (int i = 0; i < n; i++) Globals.memory.setByte(buf + i, v.charAt(i));
         if (v.length() < max - 1) Globals.memory.setByte(buf + n++, '\n');
         if (max > 0) Globals.memory.setByte(buf + n, 0);
         RegisterFile.updateRegister(5, v.length() > max - 1 ? -4 : 0);
      } catch (AddressErrorException e) { throw new ProcessingException(statement, e); }
   }
}
