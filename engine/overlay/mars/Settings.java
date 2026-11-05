package mars;

import java.util.Observable;

/**
 * Headless replacement for MARS's Settings: same constants and the subset of the API
 * used by the assembler/simulator. Values live in memory only; the front end persists them.
 * (Original: Pete Sanderson, MARS 4.5, MIT license.)
 */
public class Settings extends Observable {
   public static final int EXTENDED_ASSEMBLER_ENABLED = 0;
   public static final int BARE_MACHINE_ENABLED = 1;
   public static final int ASSEMBLE_ON_OPEN_ENABLED = 2;
   public static final int ASSEMBLE_ALL_ENABLED = 3;
   public static final int LABEL_WINDOW_VISIBILITY = 4;
   public static final int DISPLAY_ADDRESSES_IN_HEX = 5;
   public static final int DISPLAY_VALUES_IN_HEX = 6;
   public static final int EXCEPTION_HANDLER_ENABLED = 7;
   public static final int DELAYED_BRANCHING_ENABLED = 8;
   public static final int EDITOR_LINE_NUMBERS_DISPLAYED = 9;
   public static final int WARNINGS_ARE_ERRORS = 10;
   public static final int PROGRAM_ARGUMENTS = 11;
   public static final int DATA_SEGMENT_HIGHLIGHTING = 12;
   public static final int REGISTERS_HIGHLIGHTING = 13;
   public static final int START_AT_MAIN = 14;
   public static final int EDITOR_CURRENT_LINE_HIGHLIGHTING = 15;
   public static final int POPUP_INSTRUCTION_GUIDANCE = 16;
   public static final int POPUP_SYSCALL_INPUT = 17;
   public static final int GENERIC_TEXT_EDITOR = 18;
   public static final int AUTO_INDENT = 19;
   public static final int SELF_MODIFYING_CODE_ENABLED = 20;

   public static boolean[] defaultBooleanSettingsValues = {
      true, false, false, false, false, true, true, false, false,
      true, false, false, true, true, false, true, true, false, false, true, false };

   public static final int EXCEPTION_HANDLER = 0;
   public static final int TEXT_COLUMN_ORDER = 1;
   public static final int LABEL_SORT_STATE = 2;
   public static final int MEMORY_CONFIGURATION = 3;
   public static final int CARET_BLINK_RATE = 4;
   public static final int EDITOR_TAB_SIZE = 5;
   public static final int EDITOR_POPUP_PREFIX_LENGTH = 6;
   private static final String[] defaultStringSettingsValues = { "", "0 1 2 3 4", "0", "", "500", "8", "2" };

   private final boolean[] booleanSettingsValues = defaultBooleanSettingsValues.clone();
   private final String[] stringSettingsValues = defaultStringSettingsValues.clone();

   public Settings() { }
   public Settings(boolean gui) { }

   public boolean getBooleanSetting(int id) {
      if (id >= 0 && id < booleanSettingsValues.length) return booleanSettingsValues[id];
      throw new IllegalArgumentException("Invalid boolean setting ID");
   }
   public void setBooleanSetting(int id, boolean value) { setBooleanSettingNonPersistent(id, value); }
   public void setBooleanSettingNonPersistent(int id, boolean value) {
      if (id < 0 || id >= booleanSettingsValues.length) throw new IllegalArgumentException("Invalid boolean setting ID");
      booleanSettingsValues[id] = value;
      setChanged();
      notifyObservers();
   }

   public boolean getBackSteppingEnabled() {
      return Globals.program != null && Globals.program.getBackStepper() != null && Globals.program.getBackStepper().enabled();
   }
   public boolean getExtendedAssemblerEnabled() { return booleanSettingsValues[EXTENDED_ASSEMBLER_ENABLED]; }
   public boolean getBareMachineEnabled() { return booleanSettingsValues[BARE_MACHINE_ENABLED]; }
   public boolean getAssembleAllEnabled() { return booleanSettingsValues[ASSEMBLE_ALL_ENABLED]; }
   public boolean getDisplayAddressesInHex() { return booleanSettingsValues[DISPLAY_ADDRESSES_IN_HEX]; }
   public boolean getDisplayValuesInHex() { return booleanSettingsValues[DISPLAY_VALUES_IN_HEX]; }
   public boolean getExceptionHandlerEnabled() { return booleanSettingsValues[EXCEPTION_HANDLER_ENABLED]; }
   public boolean getDelayedBranchingEnabled() { return booleanSettingsValues[DELAYED_BRANCHING_ENABLED]; }
   public boolean getWarningsAreErrors() { return booleanSettingsValues[WARNINGS_ARE_ERRORS]; }
   public boolean getProgramArguments() { return booleanSettingsValues[PROGRAM_ARGUMENTS]; }
   public boolean getStartAtMain() { return booleanSettingsValues[START_AT_MAIN]; }
   public boolean getSelfModifyingCodeEnabled() { return booleanSettingsValues[SELF_MODIFYING_CODE_ENABLED]; }

   public String getExceptionHandler() { return stringSettingsValues[EXCEPTION_HANDLER]; }
   public void setExceptionHandler(String f) { stringSettingsValues[EXCEPTION_HANDLER] = f == null ? "" : f; }
   public String getMemoryConfiguration() { return stringSettingsValues[MEMORY_CONFIGURATION]; }
   public void setMemoryConfiguration(String c) { stringSettingsValues[MEMORY_CONFIGURATION] = c == null ? "" : c; }
   public int getEditorTabSize() { return Integer.parseInt(stringSettingsValues[EDITOR_TAB_SIZE]); }
}
