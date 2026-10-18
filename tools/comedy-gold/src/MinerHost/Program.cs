using System.Diagnostics;

namespace ComedyGold.MinerHost;

internal static class Program
{
    [STAThread]
    private static int Main()
    {
        string here = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
        string script = Path.Combine(here, "mine_gui.py");
        if (!File.Exists(script))
        {
            Message("mine_gui.py is missing beside Miner.exe.");
            return 1;
        }

        foreach (string exe in new[] { "pythonw", "python" })
        {
            try
            {
                ProcessStartInfo start = new()
                {
                    FileName = exe,
                    Arguments = "\"" + script + "\"",
                    WorkingDirectory = here,
                    UseShellExecute = false,
                };
                using Process? process = Process.Start(start);
                if (process is not null)
                {
                    return 0;
                }
            }
            catch (Exception error) when (error is System.ComponentModel.Win32Exception or InvalidOperationException)
            {
            }
        }

        Message("Python is not on PATH. Miner.exe opens the same window as mine_gui.py.");
        return 1;
    }

    private static void Message(string text)
    {
        try
        {
            System.Windows.Forms.MessageBox.Show(text, "Comedy Gold miner");
        }
        catch (Exception)
        {
            // No UI toolkit bound. Fail closed.
        }
    }
}
