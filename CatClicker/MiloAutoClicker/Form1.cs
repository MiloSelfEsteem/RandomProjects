using System.Diagnostics;
using System.Runtime.InteropServices;

namespace CatClicker
{
    public partial class Form1 : Form
    {
        // --- DLL IMPORTS ---
        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr SetWindowsHookEx(int idHook, LowLevelProc lpfn, IntPtr hMod, uint dwThreadId);

        [DllImport("user32.dll", SetLastError = true)]
        static extern bool UnhookWindowsHookEx(IntPtr hhk);

        [DllImport("user32.dll", SetLastError = true)]
        static extern IntPtr CallNextHookEx(IntPtr hhk, int nCode, IntPtr wParam, IntPtr lParam);

        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        static extern IntPtr GetModuleHandle(string lpModuleName);

        [DllImport("user32.dll")]
        private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

        [DllImport("user32.dll")]
        private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

        private const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;

        // --- DATA STRUCTURES ---
        public struct UserAction { public Point Pos; public int Delay; public string Type; public byte KeyCode; }
        private delegate IntPtr LowLevelProc(int nCode, IntPtr wParam, IntPtr lParam);

        private LowLevelProc _mouseProc, _keyProc;
        private IntPtr _mouseHookID = IntPtr.Zero, _keyHookID = IntPtr.Zero;
        private List<UserAction> recordedActions = new List<UserAction>();
        private bool isRecording = false, isPlaying = false;
        private int hotkeyTarget = 0;
        private Keys startStopKey, recordKey, playbackKey;
        private Stopwatch watch = new Stopwatch();
        private int sessionClicks = 0;
        private Random rng = new Random();
        private long lastElapsedMs = 0;

        private enum AppStatus { Idle, Clicking, Recording, Playing }
        private AppStatus currentStatus = AppStatus.Idle;

        public Form1()
        {
            InitializeComponent();
            _mouseProc = MouseHookCallback;
            _keyProc = KeyboardHookCallback;

            this.KeyPreview = true;
            LoadSavedSettings();
            RegisterAllHotkeys();

            string appPath = AppDomain.CurrentDomain.BaseDirectory;
            string macroFolderPath = Path.Combine(appPath, "Macros");
            if (!Directory.Exists(macroFolderPath)) Directory.CreateDirectory(macroFolderPath);

            if (domainClickType != null && domainClickType.Items.Count == 0)
            {
                domainClickType.Items.AddRange(new object[] {
                    "Double Middle", "Double Right", "Double Left",
                    "Single Middle", "Single Right", "Single Left"
                });
                domainClickType.SelectedIndex = 5;
            }

            // Tooltips
            ToolTip tt = new ToolTip();
            tt.SetToolTip(chkDarkMode, "Toggle between Light and Dark interface themes.");
            tt.SetToolTip(chkRecordMode, "Switch between the basic AutoClicker and the Macro Recorder.");
            tt.SetToolTip(chkRandomize, "Randomly speeds/slows jitter up to 20% for each click.");
            tt.SetToolTip(chkLoopPlayback, "Automatically restarts the macro playback.");
            tt.SetToolTip(chkHoldClick, "Keeps the mouse button pressed until the clicker is stopped.");

            chkDarkMode_CheckedChanged(null!, null!);
        }

        // --- SETTINGS & HOTKEYS ---
        private void LoadSavedSettings()
        {
            Enum.TryParse(Properties.Settings.Default.startStopKey, out startStopKey);
            Enum.TryParse(Properties.Settings.Default.recordKey, out recordKey);
            Enum.TryParse(Properties.Settings.Default.PlaybackKey, out playbackKey);

            numMS.Value = Properties.Settings.Default.IntervalMS;
            numSecs.Value = Properties.Settings.Default.IntervalSecs;
            numMins.Value = Properties.Settings.Default.IntervalMins;
            numHours.Value = Properties.Settings.Default.IntervalHours;

            chkDarkMode.Checked = Properties.Settings.Default.IsDarkMode;
            UpdateTitleBarTheme(chkDarkMode.Checked);

            btnChangeHotKey.Text = $"Click to Change HotKey (Current: {startStopKey})";
            btnStart.Text = $"Start ({startStopKey})";
            btnStop.Text = $"Stop ({startStopKey})";
            btnChangeRecordKey.Text = $"Key: {recordKey}";
            btnChangePlaybackKey.Text = $"Key: {playbackKey}";
        }

        private void SaveAllSettings()
        {
            Properties.Settings.Default.startStopKey = startStopKey.ToString();
            Properties.Settings.Default.recordKey = recordKey.ToString();
            Properties.Settings.Default.PlaybackKey = playbackKey.ToString();
            Properties.Settings.Default.IsDarkMode = chkDarkMode.Checked;
            Properties.Settings.Default.IntervalMS = numMS.Value;
            Properties.Settings.Default.IntervalSecs = numSecs.Value;
            Properties.Settings.Default.IntervalMins = numMins.Value;
            Properties.Settings.Default.IntervalHours = numHours.Value;
            Properties.Settings.Default.Save();
        }

        private void RegisterAllHotkeys()
        {
            UnregisterHotKey(this.Handle, 1);
            UnregisterHotKey(this.Handle, 2);
            UnregisterHotKey(this.Handle, 3);

            RegisterHotKey(this.Handle, 1, 0, (uint)startStopKey);
            if (chkRecordMode.Checked)
            {
                RegisterHotKey(this.Handle, 2, 0, (uint)recordKey);
                RegisterHotKey(this.Handle, 3, 0, (uint)playbackKey);
            }
        }

        // --- MACRO ENGINE (RECORDING) ---
        private void ToggleRecording()
        {
            if (!isRecording && IsAppBusy(AppStatus.Recording)) return;

            isRecording = !isRecording;

            if (isRecording)
            {
                currentStatus = AppStatus.Recording;
                recordedActions.Clear();
                lstRecordedActions.Items.Clear();
                lastElapsedMs = 0;

                _mouseHookID = SetHook(14, _mouseProc);
                _keyHookID = SetHook(13, _keyProc);

                watch.Restart();
                timerRecord.Start();

                lblRecordStatus.Text = "Recording...";
                btnRecordStart.Text = "Stop";
                btnStart.Enabled = btnPlaybackStart.Enabled = false;
            }
            else
            {
                currentStatus = AppStatus.Idle;
                timerRecord.Stop();
                watch.Stop();

                // Optimized individual hook cleanup
                if (_mouseHookID != IntPtr.Zero) { UnhookWindowsHookEx(_mouseHookID); _mouseHookID = IntPtr.Zero; }
                if (_keyHookID != IntPtr.Zero) { UnhookWindowsHookEx(_keyHookID); _keyHookID = IntPtr.Zero; }

                lblRecordStatus.Text = "Status: Idle";
                btnRecordStart.Text = "Record";
                btnStart.Enabled = btnPlaybackStart.Enabled = true;
            }
        }

        private IntPtr SetHook(int idHook, LowLevelProc proc)
        {
            using (Process curP = Process.GetCurrentProcess())
            using (ProcessModule curM = curP.MainModule!)
            {
                return SetWindowsHookEx(idHook, proc, GetModuleHandle(curM.ModuleName!), 0);
            }
        }

        private IntPtr MouseHookCallback(int nCode, IntPtr wParam, IntPtr lParam)
        {
            if (nCode >= 0 && isRecording)
            {
                if (wParam == (IntPtr)0x0201) AddAction("MouseDownL");
                else if (wParam == (IntPtr)0x0202) AddAction("MouseUpL");
                else if (wParam == (IntPtr)0x0204) AddAction("MouseDownR");
                else if (wParam == (IntPtr)0x0205) AddAction("MouseUpR");
            }
            return CallNextHookEx(_mouseHookID, nCode, wParam, lParam);
        }

        private IntPtr KeyboardHookCallback(int nCode, IntPtr wParam, IntPtr lParam)
        {
            if (nCode >= 0 && isRecording)
            {
                byte vkCode = (byte)Marshal.ReadInt32(lParam);
                if (vkCode != (byte)recordKey)
                {
                    if (wParam == (IntPtr)0x0100) AddAction("KeyDown", vkCode);
                    else if (wParam == (IntPtr)0x0101) AddAction("KeyUp", vkCode);
                }
            }
            return CallNextHookEx(_keyHookID, nCode, wParam, lParam);
        }

        private void AddAction(string type, byte keyCode = 0)
        {
            if (this.InvokeRequired) { this.BeginInvoke((MethodInvoker)delegate { AddAction(type, keyCode); }); return; }

            long currentElapsed = watch.ElapsedMilliseconds;
            int delay = (int)(currentElapsed - lastElapsedMs);
            if (delay < 1 && type == "Move") delay = 1;
            lastElapsedMs = currentElapsed;

            recordedActions.Add(new UserAction { Pos = Cursor.Position, Delay = delay, Type = type, KeyCode = keyCode });

            if (type != "Move")
            {
                string label = type.Replace("MouseDown", "M-DN").Replace("MouseUp", "M-UP");
                lstRecordedActions.Items.Add($"[{label}] {Cursor.Position.X},{Cursor.Position.Y} (+{delay}ms)");
                lstRecordedActions.TopIndex = lstRecordedActions.Items.Count - 1;
            }
        }

        // --- MACRO ENGINE (PLAYBACK) ---
        private async void Playback()
        {
            if (recordedActions.Count == 0 || isPlaying) return;

            currentStatus = AppStatus.Playing;
            isPlaying = true;

            await Task.Run(async () =>
            {
                const uint MOUSEEVENTF_MOVE = 0x0001;
                const uint MOUSEEVENTF_LEFTDOWN = 0x0002;
                // ... other flags as needed

                Point lastPoint = recordedActions[0].Pos;

                foreach (var action in recordedActions)
                {
                    if (!isPlaying) break;

                    // 1. Precise Wait
                    if (action.Delay > 0)
                    {
                        if (action.Delay > 16) await Task.Delay(action.Delay - 10);
                        long targetTicks = Stopwatch.GetTimestamp() + (action.Delay * Stopwatch.Frequency / 1000);
                        while (Stopwatch.GetTimestamp() < targetTicks) { }
                    }

                    if (action.Type == "Move")
                    {
                        // 1. Calculate the Delta (How much did the mouse move since the last frame?)
                        int deltaX = action.Pos.X - lastPoint.X;
                        int deltaY = action.Pos.Y - lastPoint.Y;

                        // 2. THE FIX FOR ROBLOX:
                        // Do NOT use Cursor.Position = action.Pos here.
                        // Setting Cursor.Position fights the game's internal centering logic.

                        // 3. Send ONLY the Raw Move Signal
                        if (deltaX != 0 || deltaY != 0)
                        {
                            // 0x0001 is MOUSEEVENTF_MOVE (Relative).
                            // This injects movement that Roblox interprets as a camera turn.
                            ClickerEngine.SendMouse(0x0001, deltaX, deltaY);
                        }

                        lastPoint = action.Pos;
                    }
                    else
                    {
                        Cursor.Position = action.Pos;
                        ExecuteAction(action);
                        lastPoint = action.Pos;
                    }
                }
            });

            isPlaying = false;
            currentStatus = AppStatus.Idle;
            this.Invoke((MethodInvoker)delegate { ClickerEngine.ReleaseAll(); });
        }

        private void ExecuteAction(UserAction action)
        {
            string statusText = "";
            switch (action.Type)
            {
                case "MouseDownL": ClickerEngine.SendMouse(0x02); statusText = "L-DOWN"; break;
                case "MouseUpL": ClickerEngine.SendMouse(0x04); statusText = "L-UP"; break;
                case "MouseDownR": ClickerEngine.SendMouse(0x08); statusText = "R-DOWN"; break;
                case "MouseUpR": ClickerEngine.SendMouse(0x10); statusText = "R-UP"; break;
                case "KeyDown": ClickerEngine.SendKey(action.KeyCode, false); break;
                case "KeyUp": ClickerEngine.SendKey(action.KeyCode, true); break;
            }

            if (!string.IsNullOrEmpty(statusText))
            {
                this.BeginInvoke((MethodInvoker)delegate {
                    lblClickCount.Text = $"Clicks: {sessionClicks} | {statusText}";
                });
            }
        }

        // --- AUTOCLICKER LOGIC ---
        private void StartClicking()
        {
            if (IsAppBusy(AppStatus.Clicking)) return;
            currentStatus = AppStatus.Clicking;
            int totalMs = (int)numMS.Value + ((int)numSecs.Value * 1000) + ((int)numMins.Value * 60000) + ((int)numHours.Value * 3600000);
            timerClick.Interval = totalMs < 1 ? 1 : totalMs;
            timerClick.Start();
            timerClick_Tick(null!, null!);

            btnStart.Enabled = false;
            btnStop.Enabled = true;
            btnRecordStart.Enabled = btnPlaybackStart.Enabled = false;
        }

        private void StopClicking()
        {
            timerClick.Stop();
            ClickerEngine.ReleaseAll(); // Safety Fix
            currentStatus = AppStatus.Idle;
            btnStart.Enabled = true;
            btnStop.Enabled = false;
            btnRecordStart.Enabled = btnPlaybackStart.Enabled = true;
        }

        private void timerClick_Tick(object sender, EventArgs e)
        {
            if (chkRandomize.Checked)
            {
                int baseInterval = (int)numMS.Value + ((int)numSecs.Value * 1000) + ((int)numMins.Value * 60000) + ((int)numHours.Value * 3600000);
                int range = (int)(baseInterval * 0.20);
                timerClick.Interval = Math.Max(1, baseInterval + rng.Next(-range, range + 1));
            }

            string selectedType = domainClickType.Text;
            int downFlag = 0, upFlag = 0;
            if (selectedType.Contains("Left")) { downFlag = 0x02; upFlag = 0x04; }
            else if (selectedType.Contains("Right")) { downFlag = 0x08; upFlag = 0x10; }
            else if (selectedType.Contains("Middle")) { downFlag = 0x20; upFlag = 0x40; }

            bool isDouble = selectedType.Contains("Double");
            if (chkHoldClick.Checked && !isDouble) ClickerEngine.SendMouse(downFlag);
            else ClickerEngine.SendMouse(downFlag | upFlag);

            if (isDouble && !chkHoldClick.Checked)
            {
                Thread.Sleep(10);
                ClickerEngine.SendMouse(downFlag | upFlag);
            }

            sessionClicks += isDouble ? 2 : 1;
            lblClickCount.Text = $"Clicks: {sessionClicks}";
            double currentCPS = (1000.0 / timerClick.Interval) * (isDouble ? 2 : 1);
            lblCPS.Text = $"CPS: {currentCPS:F1}";
        }

        // --- UI & THEME EVENTS ---
        protected override void OnKeyDown(KeyEventArgs e)
        {
            if (hotkeyTarget > 0)
            {
                if (hotkeyTarget == 1) startStopKey = e.KeyCode;
                else if (hotkeyTarget == 2) recordKey = e.KeyCode;
                else if (hotkeyTarget == 3) playbackKey = e.KeyCode;

                hotkeyTarget = 0;
                SaveAllSettings();
                LoadSavedSettings();
                RegisterAllHotkeys();
                e.Handled = e.SuppressKeyPress = true;
            }
            base.OnKeyDown(e);
        }

        protected override void WndProc(ref Message m)
        {
            if (m.Msg == 0x0312)
            {
                int id = m.WParam.ToInt32();
                if (id == 1) { if (timerClick.Enabled) StopClicking(); else StartClicking(); }
                if (id == 2 && chkRecordMode.Checked) ToggleRecording();
                if (id == 3 && chkRecordMode.Checked) { if (isPlaying) isPlaying = false; else Playback(); }
            }
            base.WndProc(ref m);
        }

        private void chkDarkMode_CheckedChanged(object sender, EventArgs e)
        {
            UpdateTitleBarTheme(chkDarkMode.Checked);
            Color back = chkDarkMode.Checked ? Color.FromArgb(45, 45, 48) : SystemColors.Control;
            Color fore = chkDarkMode.Checked ? Color.White : SystemColors.ControlText;
            ApplyTheme(this, back, fore);
            SaveAllSettings();
        }

        private void ApplyTheme(Control parent, Color back, Color fore)
        {
            parent.BackColor = back;
            parent.ForeColor = fore;
            if (parent is Button) parent.BackColor = chkDarkMode.Checked ? Color.FromArgb(60, 60, 65) : SystemColors.Control;
            foreach (Control child in parent.Controls) ApplyTheme(child, back, fore);
        }

        private void UpdateTitleBarTheme(bool isDark)
        {
            int darkMode = isDark ? 1 : 0;
            DwmSetWindowAttribute(this.Handle, DWMWA_USE_IMMERSIVE_DARK_MODE, ref darkMode, sizeof(int));
            this.Size = new Size(this.Size.Width, this.Size.Height + 1);
            this.Size = new Size(this.Size.Width, this.Size.Height - 1);
        }

        private void chkRecordMode_CheckedChanged(object sender, EventArgs e)
        {
            bool active = chkRecordMode.Checked;
            btnChangeRecordKey.Enabled = btnChangePlaybackKey.Enabled = btnRecordStart.Enabled = btnPlaybackStart.Enabled = active;
            lstRecordedActions.Enabled = chkLoopPlayback.Enabled = lblRecordStatus.Enabled = btnSaveMacro.Enabled = btnLoadMacro.Enabled = active;
            RegisterAllHotkeys();
        }

        private void chkAdvancedToggle_CheckedChanged(object sender, EventArgs e)
        {
            grpHoldMode.Visible = chkAdvancedToggle.Checked;
            if (!chkAdvancedToggle.Checked) chkHoldClick.Checked = false;
        }

        // --- MACRO FILE I/O ---
        private void btnSaveMacro_Click(object sender, EventArgs e)
        {
            using (SaveFileDialog sfd = new SaveFileDialog { Filter = "Macro Files|*.txt", InitialDirectory = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Macros") })
            {
                if (sfd.ShowDialog() == DialogResult.OK)
                {
                    var lines = recordedActions.Select(a => $"{a.Type}|{a.Pos.X}|{a.Pos.Y}|{a.Delay}|{a.KeyCode}");
                    File.WriteAllLines(sfd.FileName, lines);
                }
            }
        }

        private void btnLoadMacro_Click(object sender, EventArgs e)
        {
            using (OpenFileDialog ofd = new OpenFileDialog { Filter = "Macro Files|*.txt", Title = "Load a Macro" })
            {
                if (ofd.ShowDialog() == DialogResult.OK)
                {
                    recordedActions.Clear();
                    lstRecordedActions.Items.Clear();
                    foreach (string line in File.ReadAllLines(ofd.FileName))
                    {
                        string[] p = line.Split('|');
                        recordedActions.Add(new UserAction
                        {
                            Type = p[0],
                            Pos = new Point(int.Parse(p[1]), int.Parse(p[2])),
                            Delay = int.Parse(p[3]),
                            KeyCode = byte.Parse(p[4])
                        });
                        lstRecordedActions.Items.Add($"Loaded: {p[0]} at {p[1]},{p[2]}");
                    }
                }
            }
        }

        // --- HELPERS ---
        private bool IsAppBusy(AppStatus requestedMode) => currentStatus != AppStatus.Idle && currentStatus != requestedMode;
        private void btnRecordStart_Click(object sender, EventArgs e) => ToggleRecording();
        private void btnPlaybackStart_Click(object sender, EventArgs e) => Playback();
        private void btnStart_Click(object sender, EventArgs e) => StartClicking();
        private void btnStop_Click(object sender, EventArgs e) => StopClicking();
        private void btnChangeHotKey_Click(object sender, EventArgs e) { hotkeyTarget = 1; btnChangeHotKey.Text = "..."; UnregisterHotKey(this.Handle, 1); }
        private void btnChangeRecordKey_Click(object sender, EventArgs e) { hotkeyTarget = 2; btnChangeRecordKey.Text = "..."; UnregisterHotKey(this.Handle, 2); }
        private void btnChangePlaybackKey_Click(object sender, EventArgs e) { hotkeyTarget = 3; btnChangePlaybackKey.Text = "..."; UnregisterHotKey(this.Handle, 3); }
        private void timerRecord_Tick(object? sender, EventArgs? e) { if (isRecording) AddAction("Move"); }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            SaveAllSettings();
            if (_mouseHookID != IntPtr.Zero) UnhookWindowsHookEx(_mouseHookID);
            if (_keyHookID != IntPtr.Zero) UnhookWindowsHookEx(_keyHookID);
            base.OnFormClosing(e);
        }
    }

    public static class ClickerEngine
    {
        [StructLayout(LayoutKind.Sequential)]
        public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }

        [StructLayout(LayoutKind.Sequential)]
        public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }

        [StructLayout(LayoutKind.Explicit)]
        public struct INPUT_UNION
        {
            [FieldOffset(0)] public MOUSEINPUT mi;
            [FieldOffset(0)] public KEYBDINPUT ki;
        }

        public struct INPUT { public uint type; public INPUT_UNION u; }

        [DllImport("user32.dll", SetLastError = true)]
        public static extern uint SendInput(uint nInputs, INPUT[] pInputs, int cbSize);

        // Precise Mouse Method - Using int to match your existing calls
        public static void SendMouse(int flags, int x = 0, int y = 0)
        {
            INPUT[] inputs = new INPUT[1];
            inputs[0].type = 0; // INPUT_MOUSE
            inputs[0].u.mi.dx = x;
            inputs[0].u.mi.dy = y;
            inputs[0].u.mi.dwFlags = (uint)flags;
            SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
        }

        // Restored SendKey Method
        public static void SendKey(byte keyCode, bool isUp)
        {
            INPUT[] inputs = new INPUT[1];
            inputs[0].type = 1; // INPUT_KEYBOARD
            inputs[0].u.ki.wVk = keyCode;
            inputs[0].u.ki.dwFlags = isUp ? (uint)0x0002 : 0; // 0x0002 is KEYEVENTF_KEYUP
            SendInput(1, inputs, Marshal.SizeOf(typeof(INPUT)));
        }

        public static void ReleaseAll() => SendMouse(0x0004 | 0x0010 | 0x0040);
    }
}