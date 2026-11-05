package mars.venus;
/** Headless replacement: run speed is controlled by the engine, MARS always sees "unlimited". */
public class RunSpeedPanel {
   public static final double UNLIMITED_SPEED = 40;
   private static final RunSpeedPanel INSTANCE = new RunSpeedPanel();
   public static RunSpeedPanel getInstance() { return INSTANCE; }
   public double getRunSpeed() { return UNLIMITED_SPEED; }
}
