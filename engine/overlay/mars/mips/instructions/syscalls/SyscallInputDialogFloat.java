package mars.mips.instructions.syscalls;
import mars.*;
import mars.mips.hardware.*;
import mars.ext.Host;
/** Headless version of the MARS dialog syscall: the front end shows the dialog. */
public class SyscallInputDialogFloat extends AbstractSyscall {
   public SyscallInputDialogFloat() { super(52, "InputDialogFloat"); }
   static String str(ProgramStatement st, int addr) throws ProcessingException {
      StringBuilder sb = new StringBuilder();
      try { int c; while ((c = Globals.memory.getByte(addr++)) != 0) sb.append((char) (c & 0xff)); }
      catch (AddressErrorException e) { throw new ProcessingException(st, e); }
      return sb.toString();
   }
   public void simulate(ProgramStatement statement) throws ProcessingException {
      String msg = str(statement, RegisterFile.getValue(4));
      String v = Host.Registry.get().dialog("float", msg, 3);
      if (v == null) { Coprocessor1.setRegisterToFloat(0, 0f); RegisterFile.updateRegister(5, -2); return; }
      if (v.trim().isEmpty()) { Coprocessor1.setRegisterToFloat(0, 0f); RegisterFile.updateRegister(5, -3); return; }
      try { Coprocessor1.setRegisterToFloat(0, Float.parseFloat(v.trim())); RegisterFile.updateRegister(5, 0); }
      catch (NumberFormatException e) { Coprocessor1.setRegisterToFloat(0, 0f); RegisterFile.updateRegister(5, -1); }
   }
}
