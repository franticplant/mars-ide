package mars.mips.instructions.syscalls;
import mars.*;
import mars.mips.hardware.*;
import mars.ext.Host;
/** Headless version of the MARS dialog syscall: the front end shows the dialog. */
public class SyscallInputDialogDouble extends AbstractSyscall {
   public SyscallInputDialogDouble() { super(53, "InputDialogDouble"); }
   static String str(ProgramStatement st, int addr) throws ProcessingException {
      StringBuilder sb = new StringBuilder();
      try { int c; while ((c = Globals.memory.getByte(addr++)) != 0) sb.append((char) (c & 0xff)); }
      catch (AddressErrorException e) { throw new ProcessingException(st, e); }
      return sb.toString();
   }
   public void simulate(ProgramStatement statement) throws ProcessingException {
      String msg = str(statement, RegisterFile.getValue(4));
      String v = Host.Registry.get().dialog("double", msg, 3);
      try {
         if (v == null) { Coprocessor1.setRegisterPairToDouble(0, 0.0); RegisterFile.updateRegister(5, -2); return; }
         if (v.trim().isEmpty()) { Coprocessor1.setRegisterPairToDouble(0, 0.0); RegisterFile.updateRegister(5, -3); return; }
         try { Coprocessor1.setRegisterPairToDouble(0, Double.parseDouble(v.trim())); RegisterFile.updateRegister(5, 0); }
         catch (NumberFormatException e) { Coprocessor1.setRegisterPairToDouble(0, 0.0); RegisterFile.updateRegister(5, -1); }
      } catch (InvalidRegisterAccessException e) {
         throw new ProcessingException(statement, "invalid int reg. access during double input (syscall) " + e);
      }
   }
}
